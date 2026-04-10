from __future__ import annotations

import re
from typing import Optional

import aiohttp

from .models import ProblemContext


def _parse_codeforces_identifiers(text: str) -> tuple[Optional[int], Optional[str]]:
    # Supports URLs like /contest/1234/problem/A and free-form "1234A"
    match_url = re.search(r"codeforces\.com/(?:contest|problemset/problem)/(\d+)/(\w+)", text)
    if match_url:
        return int(match_url.group(1)), match_url.group(2)

    match_short = re.search(r"\b(\d{3,5})([A-Za-z]\d?)\b", text)
    if match_short:
        return int(match_short.group(1)), match_short.group(2)

    return None, None


async def fetch_codeforces_problem(text: str) -> ProblemContext:
    contest_id, index = _parse_codeforces_identifiers(text)
    if contest_id is None or index is None:
        return ProblemContext()

    url = "https://codeforces.com/api/problemset.problems"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=15) as resp:
            if resp.status != 200:
                return ProblemContext()
            data = await resp.json()

    if data.get("status") != "OK":
        return ProblemContext()

    for p in data.get("result", {}).get("problems", []):
        if p.get("contestId") == contest_id and str(p.get("index", "")).upper() == index.upper():
            title = p.get("name", "")
            tags = ", ".join(p.get("tags", []))
            rating = p.get("rating")
            constraints = f"rating={rating}" if rating is not None else ""
            statement = "Open the Codeforces problem page for full statement."
            if tags:
                statement += f" Tags: {tags}."
            return ProblemContext(title=title, statement=statement, constraints=constraints)

    return ProblemContext()
