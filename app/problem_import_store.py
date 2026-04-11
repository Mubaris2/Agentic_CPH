from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parents[1]
IMPORT_CACHE_DIR = BASE_DIR / "cache" / "imported"


def _ensure_dir() -> None:
    IMPORT_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _path_for(problem_id: str) -> Path:
    return IMPORT_CACHE_DIR / f"{problem_id}.json"


def exists(problem_id: str) -> bool:
    _ensure_dir()
    return _path_for(problem_id).exists()


def save_problem(data: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_dir()
    payload = dict(data)
    payload.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    path = _path_for(payload["id"])
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_problem(problem_id: str) -> Dict[str, Any] | None:
    _ensure_dir()
    path = _path_for(problem_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_latest_problem() -> Dict[str, Any] | None:
    _ensure_dir()
    files = list(IMPORT_CACHE_DIR.glob("*.json"))
    if not files:
        return None

    latest = max(files, key=lambda p: p.stat().st_mtime)
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        return None
