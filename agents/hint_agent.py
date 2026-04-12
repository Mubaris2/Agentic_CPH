from __future__ import annotations

from state import State
from .common import ModelRegistry, call_reasoning_model, normalize_approach, parse_json_object


def _heuristic_hints(approach: str) -> list[str]:
    if approach == "dp":
        return [
            "Level 1: Define what each DP state represents before writing transitions.",
            "Level 2: Write the recurrence and base cases explicitly, then test on n=1/2.",
            "Level 3: Check iteration order and memory optimization only after correctness.",
        ]
    if approach == "graph":
        return [
            "Level 1: Decide if the graph is weighted/unweighted and directed/undirected.",
            "Level 2: Pick BFS/DFS/Dijkstra based on edge weights and objective.",
            "Level 3: Validate visited-state handling to avoid revisits/cycles.",
        ]
    if approach == "greedy":
        return [
            "Level 1: Identify the local decision made at each step.",
            "Level 2: Argue why local optimality preserves global optimality.",
            "Level 3: Build a failing case for non-greedy alternatives to verify intuition.",
        ]
    return [
        "Level 1: Re-read constraints and target complexity before coding.",
        "Level 2: Derive a key invariant the algorithm must preserve.",
        "Level 3: Dry-run on edge cases (smallest, largest, and duplicate-heavy inputs).",
    ]


def hint_agent_node(state: State, models: ModelRegistry | None = None) -> State:
    expected = normalize_approach(state.get("expected_approach"))
    detected = normalize_approach(state.get("detected_approach"))
    chosen = expected if expected != "unknown" else detected

    prompt = (
        "Provide 3 progressive hints for a competitive programming problem. "
        "Do NOT provide full solution code. "
        "Return strict JSON: {\"hints\":[\"...\",\"...\",\"...\"]}. "
        f"User input: {state.get('user_input', '')}. "
        f"Problem context: {state.get('problem_context', {})}. "
        f"Suggested approach: {chosen}."
    )
    model_out = call_reasoning_model(prompt, state, models=models)

    hints: list[str] = []
    if model_out:
        obj = parse_json_object(model_out)
        if obj:
            hints = [str(item).strip() for item in obj.get("hints", []) if str(item).strip()]

        if not hints:
            lines = [line.strip("- • ") for line in model_out.splitlines() if line.strip()]
            hints = lines[:3]

    if not hints:
        hints = _heuristic_hints(chosen)

    hints = hints[:3]

    return {"hints": hints}
