from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parents[1]
CACHE_DIR = BASE_DIR / "cache"
API_CACHE_FILE = CACHE_DIR / "api_cache.json"


def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_problem_cache(contest_id: int, index: str) -> Optional[Dict[str, Any]]:
    _ensure_cache_dir()
    key = f"{contest_id}_{str(index).upper()}.json"
    path = CACHE_DIR / key
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_problem_cache(contest_id: int, index: str, data: Dict[str, Any]) -> None:
    _ensure_cache_dir()
    key = f"{contest_id}_{str(index).upper()}.json"
    path = CACHE_DIR / key
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_api_cache() -> Optional[Dict[str, Any]]:
    _ensure_cache_dir()
    if not API_CACHE_FILE.exists():
        return None
    try:
        return json.loads(API_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_api_cache(data: Dict[str, Any]) -> None:
    _ensure_cache_dir()
    API_CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
