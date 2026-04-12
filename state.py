from __future__ import annotations

from typing import Optional, TypedDict, Literal, Any

Intent = Literal["hint", "strategy", "analyze", "general"]
Approach = Literal[
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
]


class ProblemContext(TypedDict, total=False):
    title: str
    statement: str
    constraints: str


class Intervention(TypedDict, total=False):
    warning: str
    hint: str
    counterexample: Optional[str]


class ValidationResult(TypedDict, total=False):
    status: Literal["match", "mismatch"]
    reason: str
    confidence: float
    intervention: Intervention


class State(TypedDict, total=False):
    user_input: str
    code: Optional[str]
    intent: Optional[Intent]

    problem_context: ProblemContext

    analysis_result: Optional[str]
    detected_approach: Optional[Approach]
    expected_approach: Optional[Approach]
    validation_result: Optional[ValidationResult]

    hints: Optional[list[str]]
    strategy: Optional[str]

    final_response: Optional[str]

    run_parallel_strategy: bool
    model_usage: dict[str, Any]
    trainer_profile: Optional[str]
    coaching_goal: Optional[str]
    memory_notes: Optional[list[str]]


def default_state(user_input: str, code: Optional[str] = None, problem_context: Optional[ProblemContext] = None) -> State:
    return {
        "user_input": user_input,
        "code": code,
        "intent": None,
        "problem_context": problem_context or {
            "title": "",
            "statement": "",
            "constraints": "",
        },
        "analysis_result": None,
        "detected_approach": None,
        "expected_approach": None,
        "validation_result": None,
        "hints": None,
        "strategy": None,
        "final_response": None,
        "run_parallel_strategy": True,
        "model_usage": {},
        "trainer_profile": "Supportive personal CP trainer",
        "coaching_goal": "Improve one concept and one implementation habit in each session.",
        "memory_notes": [],
    }
