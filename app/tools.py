from __future__ import annotations

import asyncio
import random
import re
import time
from typing import Any, Dict, List, Optional

import aiohttp
import httpx
from bs4 import BeautifulSoup
from fetcher.main import get_problem

from .models import ProblemContext
from .settings import settings


CODEFORCES_API_URL = "https://codeforces.com/api/problemset.problems"
CATALOG_CACHE_TTL_SECONDS = 900
CF_HTML_FETCH_RETRIES = 2

_catalog_cache: Dict[str, Any] = {
    "loaded_at": 0.0,
    "problems": [],
    "stats_by_key": {},
}

TAG_ALIASES: Dict[str, List[str]] = {
    "dp": ["dp", "dynamic programming"],
    "graphs": ["graphs", "graph"],
    "greedy": ["greedy"],
    "math": ["math", "number theory"],
    "strings": ["strings", "string"],
    "binary search": ["binary search", "bs"],
    "two pointers": ["two pointers", "two-pointers"],
    "implementation": ["implementation"],
    "constructive algorithms": ["constructive algorithms", "constructive"],
}


def _parse_codeforces_identifiers(text: str) -> tuple[Optional[int], Optional[str]]:
    match_url = re.search(r"codeforces\.com/(?:contest|problemset/problem)/(\d+)/(\w+)", text)
    if match_url:
        return int(match_url.group(1)), match_url.group(2)

    match_short = re.search(r"\b(\d{3,5})([A-Za-z]\d?)\b", text)
    if match_short:
        return int(match_short.group(1)), match_short.group(2)

    return None, None


def _problem_key(problem: Dict[str, Any]) -> tuple[int, str]:
    return int(problem.get("contestId") or 0), str(problem.get("index") or "")


def _problem_code(problem: Dict[str, Any]) -> str:
    contest_id, index = _problem_key(problem)
    if not contest_id or not index:
        return ""
    return f"{contest_id}{index}"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _extract_topics_from_text(text: str) -> List[str]:
    lower = _normalize_text(text)
    found: List[str] = []
    for canonical, aliases in TAG_ALIASES.items():
        if any(alias in lower for alias in aliases):
            found.append(canonical)
    return list(dict.fromkeys(found))


def _to_problem_summary(problem: Dict[str, Any], solved_count: int = 0) -> Dict[str, Any]:
    contest_id, index = _problem_key(problem)
    code = f"{contest_id}{index}" if contest_id and index else ""
    return {
        "code": code,
        "contest_id": contest_id,
        "index": index,
        "name": problem.get("name", ""),
        "tags": problem.get("tags", []),
        "rating": problem.get("rating"),
        "solved_count": solved_count,
        "url": f"https://codeforces.com/contest/{contest_id}/problem/{index}" if contest_id and index else "",
        "description": "",
        "constraints": "",
        "examples": "",
        "fetch_error": "",
        "fetch_method": "",
    }


def _to_problem_context(problem: Dict[str, Any], solved_count: int = 0) -> ProblemContext:
    summary = _to_problem_summary(problem, solved_count=solved_count)
    constraints = []
    if summary["rating"] is not None:
        constraints.append(f"rating={summary['rating']}")
    if summary["tags"]:
        constraints.append("tags=" + ", ".join(summary["tags"]))
    constraints.append(f"code={summary['code']}")
    statement = (
        f"Codeforces problem: {summary['name']} ({summary['code']}). "
        f"Solve count: {summary['solved_count']}. "
        f"Open: {summary['url']}"
    )
    return ProblemContext(
        title=summary["name"],
        statement=statement,
        constraints=" | ".join(constraints),
    )


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _extract_description(problem_statement: BeautifulSoup) -> str:
    title_block = problem_statement.select_one(".title")
    lines: List[str] = []
    for child in problem_statement.find_all(recursive=False):
        classes = child.get("class", [])
        if "header" in classes:
            continue
        if child.name == "div" and "input-spec" in classes:
            break
        if child.name == "div" and "output-spec" in classes:
            break
        if child.name == "div" and "sample-tests" in classes:
            break
        if child.name == "div" and "note" in classes:
            break
        text = _normalize_spaces(child.get_text("\n", strip=True))
        if text:
            lines.append(text)

    description = "\n\n".join(lines).strip()
    if not description and title_block is not None:
        description = _normalize_spaces(problem_statement.get_text("\n", strip=True))
    return description


def _extract_constraints(description: str, rating: Optional[int], tags: List[str]) -> str:
    possible = []
    for line in description.splitlines():
        lower = line.lower()
        if any(token in lower for token in ["constraint", "1 ≤", "<=", "<=" ]):
            possible.append(line.strip())
    base = []
    if possible:
        base.extend(possible[:8])
    if rating is not None:
        base.append(f"rating={rating}")
    if tags:
        base.append("tags=" + ", ".join(tags))
    return "\n".join(dict.fromkeys([item for item in base if item]))


def _extract_header_constraints(problem_statement: BeautifulSoup) -> List[str]:
    out: List[str] = []
    for selector in [".time-limit", ".memory-limit", ".input-file", ".output-file"]:
        node = problem_statement.select_one(selector)
        if node:
            text = _normalize_spaces(node.get_text(" ", strip=True))
            if text:
                out.append(text)
    return out


def _extract_examples(problem_statement: BeautifulSoup) -> str:
    sample = problem_statement.select_one(".sample-tests")
    if sample is None:
        return ""

    entries = []
    tests = sample.select(".sample-test")
    if tests:
        for i, test in enumerate(tests, start=1):
            inp = test.select_one(".input pre")
            out = test.select_one(".output pre")
            inp_text = inp.get_text("\n", strip=False).strip() if inp else ""
            out_text = out.get_text("\n", strip=False).strip() if out else ""
            block = [f"Example {i}"]
            if inp_text:
                block.append(f"Input:\n{inp_text}")
            if out_text:
                block.append(f"Output:\n{out_text}")
            entries.append("\n".join(block))
    else:
        input_blocks = sample.select(".input")
        output_blocks = sample.select(".output")
        for i, (inp, out) in enumerate(zip(input_blocks, output_blocks), start=1):
            inp_text = inp.get_text("\n", strip=False).strip()
            out_text = out.get_text("\n", strip=False).strip()
            entries.append(f"Example {i}\nInput:\n{inp_text}\nOutput:\n{out_text}")

    return "\n\n".join(entries).strip()


def _candidate_problem_urls(contest_id: int, index: str) -> List[str]:
    normalized_index = str(index).upper()
    urls = [
        f"https://codeforces.com/problemset/problem/{contest_id}/{normalized_index}",
        f"https://codeforces.com/contest/{contest_id}/problem/{normalized_index}",
        f"https://codeforces.com/problemset/problem/{contest_id}/{normalized_index}?locale=en",
        f"https://codeforces.com/contest/{contest_id}/problem/{normalized_index}?locale=en",
        f"https://m1.codeforces.com/problemset/problem/{contest_id}/{normalized_index}",
    ]
    seen = set()
    deduped: List[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        deduped.append(url)
    return deduped


def _browser_headers(referer: Optional[str] = None) -> Dict[str, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    if referer:
        headers["Referer"] = referer
    return headers


async def _fetch_html_aiohttp(url: str, referer: Optional[str] = None) -> tuple[Optional[str], str]:
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(headers=_browser_headers(referer), timeout=timeout) as session:
            async with session.get(url, allow_redirects=True, proxy=settings.CODEFORCES_PROXY_URL) as resp:
                text = await resp.text()
                if resp.status != 200:
                    return None, f"aiohttp HTTP {resp.status}"
                if "problem-statement" not in text:
                    return None, "aiohttp HTML missing problem-statement"
                return text, ""
    except Exception as exc:
        return None, f"aiohttp error: {str(exc)}"


async def _fetch_html_httpx(url: str, referer: Optional[str] = None) -> tuple[Optional[str], str]:
    try:
        async with httpx.AsyncClient(
            headers=_browser_headers(referer),
            follow_redirects=True,
            timeout=30.0,
            proxy=settings.CODEFORCES_PROXY_URL,
        ) as client:
            resp = await client.get(url)
            text = resp.text
            if resp.status_code != 200:
                return None, f"httpx HTTP {resp.status_code}"
            if "problem-statement" not in text:
                return None, "httpx HTML missing problem-statement"
            return text, ""
    except Exception as exc:
        return None, f"httpx error: {str(exc)}"


async def _fetch_html_playwright(url: str) -> tuple[Optional[str], str]:
    try:
        from playwright.async_api import async_playwright
    except Exception:
        return None, "playwright not installed"

    try:
        async with async_playwright() as p:
            launch_args: Dict[str, Any] = {"headless": True}
            if settings.CODEFORCES_PROXY_URL:
                launch_args["proxy"] = {"server": settings.CODEFORCES_PROXY_URL}
            browser = await p.chromium.launch(**launch_args)
            context_args: Dict[str, Any] = {
                "user_agent": _browser_headers()["User-Agent"],
                "locale": "en-US",
            }
            context = await browser.new_context(**context_args)
            page = await context.new_page()
            await page.goto("https://codeforces.com/", wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(1200)
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000)
            current_url = page.url.lower()
            if any(token in current_url for token in ["/enter", "captcha", "human-verification"]):
                await context.close()
                await browser.close()
                return None, f"playwright blocked at {page.url}"
            content = await page.content()
            await context.close()
            await browser.close()
            if "problem-statement" not in content:
                if any(token in content.lower() for token in ["captcha", "cloudflare", "verify you are human", "access denied"]):
                    return None, "playwright anti-bot challenge page"
                return None, "playwright HTML missing problem-statement"
            return content, ""
    except Exception as exc:
        return None, f"playwright error: {str(exc)}"


async def _fetch_problem_html(contest_id: int, index: str) -> tuple[Optional[str], str, str, str]:
    urls = _candidate_problem_urls(contest_id, index)
    error_log: List[str] = []

    for url in urls:
        referer = "https://codeforces.com/problemset"
        for attempt in range(CF_HTML_FETCH_RETRIES):
            html, err = await _fetch_html_aiohttp(url, referer=referer)
            if html:
                return html, "aiohttp", "", url
            error_log.append(f"{url} [aiohttp attempt {attempt + 1}]: {err}")
            await asyncio.sleep(0.3 * (attempt + 1))

        html, err = await _fetch_html_httpx(url, referer=referer)
        if html:
            return html, "httpx", "", url
        error_log.append(f"{url} [httpx]: {err}")

        html, err = await _fetch_html_playwright(url)
        if html:
            return html, "playwright", "", url
        error_log.append(f"{url} [playwright]: {err}")

    return None, "", " | ".join(error_log[:8]), urls[0]


async def fetch_codeforces_problem_detail(
    contest_id: int,
    index: str,
    cftool_workdir: str | None = None,
    cftool_bin: str | None = None,
    force_refresh: bool = False,
) -> Dict[str, Any] | None:
    problems, stats_by_key = await _load_problem_catalog()
    if not problems:
        return None

    target = None
    for problem in problems:
        if int(problem.get("contestId") or 0) == contest_id and str(problem.get("index") or "").upper() == str(index).upper():
            target = problem
            break

    if target is None:
        return None

    solved_count = stats_by_key.get((contest_id, str(index)), 0)
    summary = _to_problem_summary(target, solved_count=solved_count)

    result = await get_problem(
        contest_id,
        str(index),
        force_refresh=force_refresh,
        cftool_workdir=cftool_workdir,
        cftool_bin=cftool_bin,
    )

    statement = (result.get("statement") or "").strip()
    input_spec = (result.get("input") or "").strip()
    output_spec = (result.get("output") or "").strip()
    time_limit = (result.get("time_limit") or "").strip()
    memory_limit = (result.get("memory_limit") or "").strip()
    examples_list = result.get("examples") or []

    constraints_lines = []
    if time_limit:
        constraints_lines.append(time_limit)
    if memory_limit:
        constraints_lines.append(memory_limit)
    inferred_constraints = _extract_constraints(statement, summary.get("rating"), summary.get("tags") or [])
    if inferred_constraints:
        constraints_lines.extend(inferred_constraints.splitlines())
    constraints = "\n".join(dict.fromkeys([line.strip() for line in constraints_lines if line.strip()]))

    examples_text_blocks = []
    for i, item in enumerate(examples_list, start=1):
        if not isinstance(item, dict):
            continue
        inp = (item.get("input") or "").strip()
        out = (item.get("output") or "").strip()
        block = [f"Example {i}"]
        if inp:
            block.append(f"Input:\n{inp}")
        if out:
            block.append(f"Output:\n{out}")
        examples_text_blocks.append("\n".join(block))

    summary["name"] = result.get("title") or summary.get("name")
    summary["description"] = statement
    summary["input"] = input_spec
    summary["output"] = output_spec
    summary["constraints"] = constraints
    summary["examples"] = "\n\n".join(examples_text_blocks).strip()
    summary["examples_list"] = examples_list
    summary["time_limit"] = time_limit
    summary["memory_limit"] = memory_limit
    summary["fetch_method"] = result.get("source_method", "playwright_cache_hybrid")
    if result.get("cftool_workdir"):
        summary["cftool_workdir"] = result.get("cftool_workdir")
    if result.get("cftool_method"):
        summary["cftool_method"] = result.get("cftool_method")
    if result.get("cftool_warning"):
        summary["cftool_warning"] = result.get("cftool_warning")
    if result.get("cftool_error"):
        summary["cftool_error"] = result.get("cftool_error")
    if result.get("error"):
        summary["fetch_error"] = str(result.get("error"))
    elif not statement:
        summary["fetch_error"] = "Statement extraction returned empty content"
    return summary


async def _load_problem_catalog() -> tuple[List[Dict[str, Any]], Dict[tuple[int, str], int]]:
    now = time.time()
    loaded_at = float(_catalog_cache.get("loaded_at", 0.0))
    cached_problems = _catalog_cache.get("problems") or []
    cached_stats = _catalog_cache.get("stats_by_key") or {}

    if cached_problems and (now - loaded_at) < CATALOG_CACHE_TTL_SECONDS:
        return cached_problems, cached_stats

    async with aiohttp.ClientSession() as session:
        async with session.get(CODEFORCES_API_URL, timeout=30) as resp:
            if resp.status != 200:
                return cached_problems, cached_stats
            data = await resp.json()

    if data.get("status") != "OK":
        return cached_problems, cached_stats

    result = data.get("result", {})
    problems: List[Dict[str, Any]] = result.get("problems", []) or []
    stats = result.get("problemStatistics", []) or []
    stats_by_key: Dict[tuple[int, str], int] = {}
    for stat in stats:
        contest_id = int(stat.get("contestId") or 0)
        index = str(stat.get("index") or "")
        if contest_id and index:
            stats_by_key[(contest_id, index)] = int(stat.get("solvedCount") or 0)

    _catalog_cache["loaded_at"] = now
    _catalog_cache["problems"] = problems
    _catalog_cache["stats_by_key"] = stats_by_key
    return problems, stats_by_key


async def search_codeforces_by_code_or_name(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    problems, stats_by_key = await _load_problem_catalog()
    if not query.strip() or not problems:
        return []

    contest_id, index = _parse_codeforces_identifiers(query)
    normalized = _normalize_text(query)
    normalized_no_spaces = normalized.replace(" ", "")

    direct_matches: List[Dict[str, Any]] = []
    fuzzy_matches: List[Dict[str, Any]] = []

    for problem in problems:
        code = _problem_code(problem).lower()
        name = _normalize_text(str(problem.get("name", "")))
        tags = " ".join([_normalize_text(tag) for tag in problem.get("tags", [])])
        solved_count = stats_by_key.get(_problem_key(problem), 0)
        summary = _to_problem_summary(problem, solved_count=solved_count)

        if contest_id is not None and index is not None:
            if summary["contest_id"] == contest_id and str(summary["index"]).upper() == str(index).upper():
                direct_matches.append(summary)
                continue

        if normalized_no_spaces and (normalized_no_spaces == code or normalized_no_spaces in code):
            direct_matches.append(summary)
            continue

        if normalized and (normalized in name or normalized in tags):
            fuzzy_matches.append(summary)

    direct_matches.sort(key=lambda item: (item["rating"] is None, item["rating"] or 10**9, -item["solved_count"]))
    fuzzy_matches.sort(key=lambda item: (-item["solved_count"], item["rating"] or 10**9))
    merged = direct_matches + [item for item in fuzzy_matches if item not in direct_matches]
    return merged[: max(1, min(limit, 50))]


async def list_codeforces_by_topics(
    topics: List[str],
    limit: int = 20,
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None,
) -> List[Dict[str, Any]]:
    problems, stats_by_key = await _load_problem_catalog()
    if not problems:
        return []

    normalized_topics = [_normalize_text(topic) for topic in topics if str(topic).strip()]
    if not normalized_topics:
        return []

    candidates: List[Dict[str, Any]] = []
    for problem in problems:
        rating = problem.get("rating")
        if min_rating is not None and (rating is None or rating < min_rating):
            continue
        if max_rating is not None and (rating is None or rating > max_rating):
            continue

        tags = [_normalize_text(tag) for tag in problem.get("tags", [])]
        if not all(any(topic in tag or tag in topic for tag in tags) for topic in normalized_topics):
            continue

        solved_count = stats_by_key.get(_problem_key(problem), 0)
        candidates.append(_to_problem_summary(problem, solved_count=solved_count))

    candidates.sort(key=lambda item: (-item["solved_count"], item["rating"] or 10**9))
    return candidates[: max(1, min(limit, 100))]


async def random_codeforces_problem(
    user_data: Optional[Dict[str, Any]] = None,
    fallback_topics: Optional[List[str]] = None,
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None,
) -> Dict[str, Any] | None:
    problems, stats_by_key = await _load_problem_catalog()
    if not problems:
        return None

    user_data = user_data or {}
    preferred_topics = user_data.get("preferred_topics") or fallback_topics or []
    avoided_topics = user_data.get("avoided_topics") or []
    solved_codes = {str(code).lower() for code in (user_data.get("solved_problem_codes") or [])}
    target_rating = user_data.get("target_rating")
    rating_window = int(user_data.get("rating_window") or 200)

    if target_rating is not None:
        min_rating = max(min_rating or 0, int(target_rating) - rating_window)
        max_rating = min(max_rating or 10**9, int(target_rating) + rating_window)

    preferred_topics_norm = [_normalize_text(topic) for topic in preferred_topics if str(topic).strip()]
    avoided_topics_norm = [_normalize_text(topic) for topic in avoided_topics if str(topic).strip()]

    pool: List[Dict[str, Any]] = []
    for problem in problems:
        rating = problem.get("rating")
        if min_rating is not None and (rating is None or rating < min_rating):
            continue
        if max_rating is not None and (rating is None or rating > max_rating):
            continue

        summary = _to_problem_summary(problem, solved_count=stats_by_key.get(_problem_key(problem), 0))
        if summary["code"].lower() in solved_codes:
            continue

        tags = [_normalize_text(tag) for tag in summary["tags"]]
        if preferred_topics_norm and not any(any(pref in tag or tag in pref for tag in tags) for pref in preferred_topics_norm):
            continue
        if avoided_topics_norm and any(any(avoid in tag or tag in avoid for tag in tags) for avoid in avoided_topics_norm):
            continue
        pool.append(summary)

    if not pool:
        return None

    weights = []
    for item in pool:
        solved_bonus = min(item["solved_count"], 20000) / 20000
        rating = item["rating"]
        rating_weight = 1.0
        if target_rating is not None and rating is not None:
            diff = abs(int(rating) - int(target_rating))
            rating_weight = max(0.2, 1.0 - (diff / 1200))
        weights.append(0.6 + solved_bonus + rating_weight)

    chosen = random.choices(pool, weights=weights, k=1)[0]
    return chosen


async def fetch_codeforces_problem(text: str, user_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    normalized_text = _normalize_text(text)
    topics = _extract_topics_from_text(text)

    if "random" in normalized_text:
        random_problem = await random_codeforces_problem(user_data=user_data, fallback_topics=topics)
        if random_problem:
            detailed = await fetch_codeforces_problem_detail(random_problem["contest_id"], random_problem["index"]) or random_problem
            context = ProblemContext(
                title=detailed.get("name", ""),
                statement=detailed.get("description", "") or f"Open: {detailed.get('url', '')}",
                constraints=detailed.get("constraints", ""),
            )
            return {
                "mode": "random",
                "problem_context": context,
                "candidates": [detailed],
            }
        return {"mode": "random", "problem_context": ProblemContext(), "candidates": []}

    if topics and any(token in normalized_text for token in ["topic", "topics", "tag", "tags", "list"]):
        topic_list = await list_codeforces_by_topics(topics, limit=10)
        if topic_list:
            first = topic_list[0]
            detailed_first = await fetch_codeforces_problem_detail(first["contest_id"], first["index"]) or first
            context = ProblemContext(
                title=detailed_first.get("name", ""),
                statement=detailed_first.get("description", "") or f"Open: {detailed_first.get('url', '')}",
                constraints=detailed_first.get("constraints", ""),
            )
            return {
                "mode": "topic_list",
                "problem_context": context,
                "candidates": topic_list,
            }
        return {"mode": "topic_list", "problem_context": ProblemContext(), "candidates": []}

    matches = await search_codeforces_by_code_or_name(text, limit=10)
    if matches:
        first = matches[0]
        detailed_first = await fetch_codeforces_problem_detail(first["contest_id"], first["index"]) or first
        context = ProblemContext(
            title=detailed_first.get("name", ""),
            statement=detailed_first.get("description", "") or f"Open: {detailed_first.get('url', '')}",
            constraints=detailed_first.get("constraints", ""),
        )
        return {
            "mode": "code_or_name",
            "problem_context": context,
            "candidates": matches,
        }

    return {
        "mode": "none",
        "problem_context": ProblemContext(),
        "candidates": [],
    }
