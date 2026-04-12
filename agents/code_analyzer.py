from __future__ import annotations

import re

from state import State
from .common import ModelRegistry, call_code_model, normalize_approach, extract_approach, parse_json_object


def _detect_pattern_from_code(code: str) -> str:
    c = code.lower()
    if "dp[" in c or "memo" in c or "tabulation" in c:
        return "dp"
    if "priority_queue" in c or "sort(" in c or "sorted(" in c:
        return "greedy"
    if "dfs(" in c or "bfs(" in c or "adj" in c or "graph" in c:
        return "graph"
    nested_for = c.count("for ") >= 2 or c.count("for(") >= 2
    if nested_for:
        return "brute_force"
    if "while" in c and "left" in c and "right" in c:
        return "two_pointers"
    if "binary_search" in c or "mid =" in c:
        return "binary_search"
    return "unknown"


def _analysis_heuristics(code: str) -> list[str]:
    feedback: list[str] = []
    c = code.lower()

    if not code.strip():
        return ["No code provided for analysis."]

    if "input(" in c and "strip" not in c:
        feedback.append("Input parsing may fail on trailing spaces/newlines.")
    if "for" in c and "range(n)" in c and c.count("for") >= 2:
        feedback.append("Potential O(n^2) or worse complexity; verify against constraints.")
    if "recursion" in c or "def dfs" in c:
        feedback.append("Check recursion depth limits for large test cases.")
    if "mod" in c and "%" not in c:
        feedback.append("Modulo logic may be incomplete or inconsistent.")
    if not feedback:
        feedback.append("Code looks structurally reasonable; verify edge cases and complexity bounds.")

    return feedback


def code_analyzer_node(state: State, models: ModelRegistry | None = None) -> State:
    code = state.get("code") or ""
    pattern = _detect_pattern_from_code(code)
    heuristic_feedback = _analysis_heuristics(code)

    prompt = (
        "Analyze this competitive programming code for logical errors, inefficiencies, and edge cases. "
        "Return strict JSON with keys: analysis_points (array of short strings), detected_approach (single label). "
        "Allowed labels: dp, greedy, brute_force, graph, math, binary_search, two_pointers, prefix_sum, string, backtracking, unknown. "
        f"Code:\n{code}"
    )
    model_out = call_code_model(prompt, state, models=models)

    if model_out:
        obj = parse_json_object(model_out)
        points = [str(item).strip() for item in obj.get("analysis_points", []) if str(item).strip()] if obj else []
        analysis_result = "\n".join(f"- {line}" for line in points) if points else model_out.strip()
        inferred = extract_approach(obj.get("detected_approach", "") if obj else model_out)
        if inferred != "unknown":
            pattern = inferred
        else:
            match = re.search(r"approach\s*[:=]\s*([a-z_ ]+)", model_out.lower())
            if match:
                pattern = extract_approach(match.group(1))
    else:
        analysis_result = "\n".join(f"- {line}" for line in heuristic_feedback)

    return {
        "analysis_result": analysis_result,
        "detected_approach": normalize_approach(pattern),
    }
