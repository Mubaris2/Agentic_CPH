from __future__ import annotations

from state import State
from .common import ModelRegistry, call_reasoning_model, normalize_approach, extract_approach, parse_json_object


KEYWORDS = {
    "dp": ["dp", "memo", "tabulation", "state transition"],
    "greedy": ["greedy", "locally optimal", "sort then pick"],
    "graph": ["graph", "bfs", "dfs", "dijkstra", "topological"],
    "brute_force": ["brute", "try all", "all pairs", "enumerate"],
    "math": ["gcd", "mod", "number theory", "combinatorics"],
    "binary_search": ["binary search", "mid", "monotonic"],
    "two_pointers": ["two pointers", "left", "right", "sliding window"],
    "prefix_sum": ["prefix sum", "cumulative"],
    "string": ["string", "kmp", "z-function", "suffix"],
    "backtracking": ["backtrack", "subset", "permutation", "dfs tree"],
}


def _keyword_detect(text: str) -> str:
    lower = text.lower()
    for label, words in KEYWORDS.items():
        if any(word in lower for word in words):
            return label
    return "unknown"


def approach_detection_node(state: State, models: ModelRegistry | None = None) -> State:
    current = normalize_approach(state.get("detected_approach"))
    code = state.get("code") or ""
    user_input = state.get("user_input") or ""

    merged_text = f"{code}\n{user_input}"
    heuristic = _keyword_detect(merged_text)

    prompt = (
        "Normalize algorithmic approach into one of: dp, greedy, brute_force, graph, math, "
        "binary_search, two_pointers, prefix_sum, string, backtracking, unknown. "
        "Return strict JSON: {\"detected_approach\": \"label\"}. "
        f"Context:\n{merged_text}"
    )
    model_out = call_reasoning_model(prompt, state, models=models)

    if model_out:
        obj = parse_json_object(model_out)
        normalized = extract_approach(obj.get("detected_approach", "") if obj else model_out)
        if normalized != "unknown":
            return {"detected_approach": normalized}

    if current != "unknown":
        return {"detected_approach": current}

    return {"detected_approach": normalize_approach(heuristic)}
