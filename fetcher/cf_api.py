from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

from .cache import load_api_cache, save_api_cache

logger = logging.getLogger(__name__)
CF_API_URL = "https://codeforces.com/api/problemset.problems"
_api_lock = asyncio.Lock()


async def _fetch_api_payload() -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(CF_API_URL)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "OK":
            raise RuntimeError("Codeforces API returned non-OK status")
        return payload


async def _get_problemset_payload(force_refresh: bool = False) -> Dict[str, Any]:
    async with _api_lock:
        if not force_refresh:
            cached = load_api_cache()
            if cached and cached.get("status") == "OK":
                return cached

        payload = await _fetch_api_payload()
        save_api_cache(payload)
        return payload


async def get_problem_metadata(contest_id: int, index: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    try:
        payload = await _get_problemset_payload(force_refresh=force_refresh)
    except Exception as exc:
        logger.exception("Codeforces API fetch failed: %s", exc)
        return None

    normalized_index = str(index).upper()
    problems = payload.get("result", {}).get("problems", [])
    stats = payload.get("result", {}).get("problemStatistics", [])

    found_problem: Optional[Dict[str, Any]] = None
    for problem in problems:
        if int(problem.get("contestId") or 0) == contest_id and str(problem.get("index") or "").upper() == normalized_index:
            found_problem = problem
            break

    if not found_problem:
        return None

    solved_count = None
    for stat in stats:
        if int(stat.get("contestId") or 0) == contest_id and str(stat.get("index") or "").upper() == normalized_index:
            solved_count = int(stat.get("solvedCount") or 0)
            break

    return {
        "title": found_problem.get("name", ""),
        "tags": found_problem.get("tags", []) or [],
        "rating": found_problem.get("rating"),
        "solved_count": solved_count,
    }
