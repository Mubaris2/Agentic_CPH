from __future__ import annotations

from state import State
from .common import ModelRegistry, call_reasoning_model, normalize_approach, parse_json_object


def _default_strategy(approach: str) -> str:
    if approach == "dp":
        return (
            "Optimal approach: Dynamic Programming with state compression where possible.\n"
            "Time complexity: typically O(n * state).\n"
            "Alternatives: memoized DFS, greedy if exchange argument exists."
        )
    if approach == "graph":
        return (
            "Optimal approach: Graph traversal/shortest path based on edge model.\n"
            "Time complexity: BFS O(V+E), Dijkstra O((V+E)logV).\n"
            "Alternatives: union-find for connectivity-only variants."
        )
    if approach == "greedy":
        return (
            "Optimal approach: Greedy after sorting/prioritizing decisions.\n"
            "Time complexity: O(n log n) dominated by sort.\n"
            "Alternatives: DP when greedy choice property is not provable."
        )
    return (
        "Optimal approach: Constraint-driven selection (often greedy or DP).\n"
        "Time complexity: choose the smallest feasible asymptotic bound from constraints.\n"
        "Alternatives: brute force for validation on tiny inputs only."
    )


def strategy_agent_node(state: State, models: ModelRegistry | None = None) -> State:
    if state.get("intent") == "analyze" and not state.get("run_parallel_strategy", True):
        return {}

    expected = normalize_approach(state.get("expected_approach"))
    detected = normalize_approach(state.get("detected_approach"))
    chosen = expected if expected != "unknown" else detected

    prompt = (
        "Explain the optimal approach, time complexity, and alternatives for the problem. "
        "Keep it concise and implementation-focused. "
        "Return strict JSON with keys: optimal_approach, time_complexity, alternatives (array), implementation_notes. "
        f"Problem context: {state.get('problem_context', {})}. "
        f"Detected approach: {detected}."
    )
    model_out = call_reasoning_model(prompt, state, models=models)

    strategy = ""
    if model_out:
        obj = parse_json_object(model_out)
        if obj:
            optimal = str(obj.get("optimal_approach", "")).strip()
            complexity = str(obj.get("time_complexity", "")).strip()
            notes = str(obj.get("implementation_notes", "")).strip()
            alternatives = [str(item).strip() for item in obj.get("alternatives", []) if str(item).strip()]
            strategy_lines = []
            if optimal:
                strategy_lines.append(f"Optimal approach: {optimal}")
            if complexity:
                strategy_lines.append(f"Time complexity: {complexity}")
            if alternatives:
                strategy_lines.append(f"Alternatives: {', '.join(alternatives[:4])}")
            if notes:
                strategy_lines.append(f"Implementation notes: {notes}")
            strategy = "\n".join(strategy_lines).strip()

        if not strategy:
            strategy = model_out.strip()

    if not strategy:
        strategy = _default_strategy(chosen)

    return {"strategy": strategy}
