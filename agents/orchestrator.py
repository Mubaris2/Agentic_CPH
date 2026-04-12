from __future__ import annotations

import re

from state import State
from .common import ModelRegistry, call_intent_model, extract_intent, parse_json_object


SUPPORTED_INTENTS = {"hint", "strategy", "analyze", "general"}


def _heuristic_intent(text: str, has_code: bool) -> str:
    lower = text.lower()
    if re.search(r"\bhint\b|stuck|nudge", lower):
        return "hint"
    if re.search(r"\bstrategy\b|approach|complexity|optimal", lower):
        return "strategy"
    if has_code or re.search(r"debug|wrong answer|tle|runtime error|analy", lower):
        return "analyze"
    return "general"


def orchestrator_node(state: State, models: ModelRegistry | None = None) -> State:
    user_input = state.get("user_input", "") or ""
    has_code = bool((state.get("code") or "").strip())
    memory_notes = state.get("memory_notes") or []
    trainer_profile = state.get("trainer_profile") or "Supportive personal CP trainer"

    prompt = (
        "You are a personal competitive programming trainer. "
        "Classify intent into one label: hint, strategy, analyze, general. "
        "Also propose one short coaching goal for this turn and one memory note to remember. "
        "Return strict JSON: {\"intent\":...,\"coaching_goal\":...,\"memory_note\":...}. "
        f"Trainer profile: {trainer_profile}. "
        f"Recent memory notes: {memory_notes[-3:]}. "
        f"Input: {user_input}. Has code: {has_code}."
    )
    model_out = call_intent_model(prompt, state, models=models)

    intent = _heuristic_intent(user_input, has_code)
    coaching_goal = state.get("coaching_goal") or "Improve one concept and one implementation habit in each session."
    new_memory_note = ""

    if model_out:
        obj = parse_json_object(model_out)
        normalized = extract_intent(obj.get("intent") if obj else model_out)
        if normalized in SUPPORTED_INTENTS:
            intent = normalized
        candidate_goal = (obj.get("coaching_goal") if obj else "") or ""
        if isinstance(candidate_goal, str) and candidate_goal.strip():
            coaching_goal = candidate_goal.strip()
        candidate_memory = (obj.get("memory_note") if obj else "") or ""
        if isinstance(candidate_memory, str) and candidate_memory.strip():
            new_memory_note = candidate_memory.strip()

    if not new_memory_note:
        new_memory_note = f"User focus: {user_input[:120]}"

    merged_notes = [*memory_notes, new_memory_note][-8:]

    return {
        "intent": intent,
        "trainer_profile": trainer_profile,
        "coaching_goal": coaching_goal,
        "memory_notes": merged_notes,
    }
