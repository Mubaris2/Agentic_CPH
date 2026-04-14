"""Unified state shim for the application.

This module re-exports the canonical assistant state type from
`app.models` as `State` and provides `default_state()` to create a
runtime-initialized state dictionary. Centralizing here keeps older
callers that import `state.State` working while consolidating the
schema in `app.models`.
"""

from __future__ import annotations

from typing import Optional

from app.models import CPAssistantState as StateType


def default_state(user_input: str, code: Optional[str] = None, problem_context: Optional[dict] = None) -> StateType:
    return {
        "user_input": user_input,
        "code": code,
        "intent": "general",
        "next_node": "",
        "problem_fetch_attempted": False,
        "problem_context": problem_context or {"title": "", "statement": "", "constraints": ""},
        "problem_candidates": [],
        "analysis_result": {},
        "detected_approach": "unknown",
        "expected_approach": "unknown",
        "validation_result": {},
        "hints": [],
        "strategy": {},
        "counterexample": "",
        "final_response": "",
        "intermediate_steps": [],
        "run_parallel_strategy": True,
        "model_usage": {},
        "trainer_profile": "Supportive personal CP trainer",
        "coaching_goal": "Improve one concept and one implementation habit in each session.",
        "memory_notes": [],
    }

# export State name for backwards compatibility
State = StateType
