from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional
import json
import re

from state import State


ModelCallable = Callable[[str, State], str]


@dataclass
class ModelRegistry:
    intent_model: Optional[ModelCallable] = None
    reasoning_model: Optional[ModelCallable] = None
    code_model: Optional[ModelCallable] = None


intent_model = None  # to be injected
reasoning_model = None  # to be injected
code_model = None  # to be injected


def _call(candidate: Optional[ModelCallable], prompt: str, state: State) -> Optional[str]:
    if candidate is None:
        return None
    try:
        return candidate(prompt, state)
    except Exception:
        return None


def call_intent_model(prompt: str, state: State, models: Optional[ModelRegistry] = None) -> Optional[str]:
    result = _call(models.intent_model if models else None, prompt, state)
    if result is not None:
        return result
    return _call(intent_model, prompt, state)


def call_reasoning_model(prompt: str, state: State, models: Optional[ModelRegistry] = None) -> Optional[str]:
    result = _call(models.reasoning_model if models else None, prompt, state)
    if result is not None:
        return result
    return _call(reasoning_model, prompt, state)


def call_code_model(prompt: str, state: State, models: Optional[ModelRegistry] = None) -> Optional[str]:
    result = _call(models.code_model if models else None, prompt, state)
    if result is not None:
        return result
    return _call(code_model, prompt, state)


def normalize_approach(value: str | None) -> str:
    allowed = {
        "unknown",
        "dp",
        "greedy",
        "brute_force",
        "graph",
        "math",
        "binary_search",
        "two_pointers",
        "prefix_sum",
        "string",
        "backtracking",
    }
    candidate = (value or "").strip().lower()
    return candidate if candidate in allowed else "unknown"


def extract_intent(value: str | None) -> str | None:
    text = (value or "").strip().lower()
    if not text:
        return None
    for label in ("hint", "strategy", "analyze", "general"):
        if text == label:
            return label
    match = re.search(r"\b(hint|strategy|analyze|general)\b", text)
    return match.group(1) if match else None


def extract_approach(value: str | None) -> str:
    direct = normalize_approach(value)
    if direct != "unknown":
        return direct

    text = (value or "").strip().lower()
    if not text:
        return "unknown"

    for label in (
        "dp",
        "greedy",
        "brute_force",
        "graph",
        "math",
        "binary_search",
        "two_pointers",
        "prefix_sum",
        "string",
        "backtracking",
    ):
        if re.search(rf"\b{re.escape(label.replace('_', ' '))}\b", text) or label in text:
            return label

    return "unknown"


def parse_json_object(text: str | None) -> dict:
    raw = (text or "").strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        pass

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
    if fenced:
        try:
            obj = json.loads(fenced.group(1))
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            obj = json.loads(raw[start:end + 1])
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}
    return {}
