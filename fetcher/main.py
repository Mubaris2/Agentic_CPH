from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from fetcher.cache import load_problem_cache, save_problem_cache
    from fetcher.cf_api import get_problem_metadata
    from fetcher.parser import parse_problem_html
    from fetcher.scraper import fetch_problem_html
    from fetcher.cftool_adapter import parse_with_cftool
else:
    from .cache import load_problem_cache, save_problem_cache
    from .cf_api import get_problem_metadata
    from .parser import parse_problem_html
    from .scraper import fetch_problem_html
    from .cftool_adapter import parse_with_cftool

logger = logging.getLogger(__name__)


def _merge_result(parsed: Dict[str, Any], metadata: Dict[str, Any] | None) -> Dict[str, Any]:
    metadata = metadata or {}
    title = parsed.get("title") or metadata.get("title", "")
    return {
        "title": title,
        "time_limit": parsed.get("time_limit", ""),
        "memory_limit": parsed.get("memory_limit", ""),
        "statement": parsed.get("statement", ""),
        "input": parsed.get("input", ""),
        "output": parsed.get("output", ""),
        "examples": parsed.get("examples", []),
        "tags": metadata.get("tags", []),
        "rating": metadata.get("rating"),
        "solved_count": metadata.get("solved_count"),
    }


async def get_problem(
    contest_id: int,
    index: str,
    force_refresh: bool = False,
    cftool_workdir: str | None = None,
    cftool_bin: str | None = None,
) -> Dict[str, Any]:
    normalized_index = str(index).upper()

    if not force_refresh:
        cached = load_problem_cache(contest_id, normalized_index)
        if cached:
            logger.info("Problem %s%s loaded from cache", contest_id, normalized_index)
            return cached

    metadata = await get_problem_metadata(contest_id, normalized_index, force_refresh=force_refresh)
    cftool_result = await parse_with_cftool(
        contest_id,
        normalized_index,
        workdir_path=cftool_workdir,
        cftool_bin=cftool_bin,
    )

    try:
        html = await fetch_problem_html(contest_id, normalized_index, retries=3)
        parsed = parse_problem_html(html)
        if cftool_result.get("ok") and cftool_result.get("examples"):
            parsed["examples"] = cftool_result["examples"]
        result = _merge_result(parsed, metadata)
        result["source_method"] = "cftool+playwright" if cftool_result.get("ok") else "playwright"
        result["cftool_workdir"] = cftool_result.get("workdir")
        result["cftool_method"] = cftool_result.get("method")
        if not cftool_result.get("ok") and cftool_result.get("error"):
            result["cftool_warning"] = cftool_result.get("error")
        save_problem_cache(contest_id, normalized_index, result)
        return result
    except Exception as exc:
        logger.exception("Failed to fetch problem %s%s", contest_id, normalized_index)
        if cftool_result.get("ok") and cftool_result.get("examples"):
            return {
                "title": (metadata or {}).get("title", ""),
                "time_limit": "",
                "memory_limit": "",
                "statement": "",
                "input": "",
                "output": "",
                "examples": cftool_result.get("examples", []),
                "tags": (metadata or {}).get("tags", []),
                "rating": (metadata or {}).get("rating"),
                "solved_count": (metadata or {}).get("solved_count"),
                "source_method": "cftool_only",
                "cftool_workdir": cftool_result.get("workdir"),
                "cftool_method": cftool_result.get("method"),
                "error": f"Statement scraping failed, but samples loaded via cftool: {str(exc)}",
            }
        return {
            "title": (metadata or {}).get("title", ""),
            "time_limit": "",
            "memory_limit": "",
            "statement": "",
            "input": "",
            "output": "",
            "examples": [],
            "tags": (metadata or {}).get("tags", []),
            "rating": (metadata or {}).get("rating"),
            "solved_count": (metadata or {}).get("solved_count"),
            "source_method": "none",
            "cftool_workdir": cftool_result.get("workdir"),
            "cftool_error": cftool_result.get("error", ""),
            "error": f"Statement scraping failed: {str(exc)}",
        }


def get_problem_sync(
    contest_id: int,
    index: str,
    force_refresh: bool = False,
    cftool_workdir: str | None = None,
    cftool_bin: str | None = None,
) -> Dict[str, Any]:
    return asyncio.run(
        get_problem(
            contest_id,
            index,
            force_refresh=force_refresh,
            cftool_workdir=cftool_workdir,
            cftool_bin=cftool_bin,
        )
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Codeforces problem details")
    parser.add_argument("contest_id", type=int, help="Contest ID, e.g., 734")
    parser.add_argument("index", type=str, help="Problem index, e.g., A")
    parser.add_argument("--force-refresh", action="store_true", help="Ignore cache and re-fetch")
    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON output")
    parser.add_argument("--cftool-workdir", type=str, default=None, help="Custom directory where cftool should create problem files")
    parser.add_argument("--cftool-bin", type=str, default=None, help="Path to cftool/cf executable")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()
    result = get_problem_sync(
        args.contest_id,
        args.index,
        force_refresh=args.force_refresh,
        cftool_workdir=args.cftool_workdir,
        cftool_bin=args.cftool_bin,
    )
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
