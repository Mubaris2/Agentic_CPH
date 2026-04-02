from typing import Any, Dict


def _guess_time_complexity(code: str) -> str:
    loop_count = code.count("for ") + code.count("while ")
    has_sort = "sorted(" in code or ".sort(" in code

    if loop_count >= 3:
        return "O(n^3) or higher"
    if loop_count == 2:
        return "O(n^2)"
    if loop_count == 1 and has_sort:
        return "O(n log n)"
    if loop_count == 1:
        return "O(n)"
    if has_sort:
        return "O(n log n)"
    return "O(1) to O(log n)"


def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    code = input_data.get("code", "")
    time_complexity = _guess_time_complexity(code)

    suggestions = []
    if "O(n^2)" in time_complexity or "O(n^3)" in time_complexity:
        suggestions.append("Try reducing nested loops using hashing, prefix sums, or two-pointers.")
    if "sort" in code:
        suggestions.append("If sorting is avoidable, consider counting arrays / hash maps for linear time.")
    if not suggestions:
        suggestions.append("Complexity looks acceptable; focus on edge-case correctness.")

    return {
        "time_complexity": time_complexity,
        "optimization_suggestions": suggestions,
    }
