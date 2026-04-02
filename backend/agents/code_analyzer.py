from typing import Any, Dict, List


def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    code = input_data.get("code", "")

    issues: List[str] = []
    possible_bugs: List[str] = []
    edge_cases_missed: List[str] = []

    if "global " in code:
        issues.append("Uses global state, which can cause hidden side effects.")
    if "print(" in code:
        issues.append("Debug prints found; remove for final competitive submission.")
    if code.count("for ") >= 2 and "break" not in code:
        possible_bugs.append("Nested loops may be too slow for large constraints.")
    if "while True" in code and "break" not in code:
        possible_bugs.append("Potential infinite loop detected.")
    if "if" not in code:
        edge_cases_missed.append("No branching logic; may miss boundary conditions.")
    if "len(" not in code:
        edge_cases_missed.append("No obvious length checks for empty/small inputs.")
    if "-1" not in code:
        edge_cases_missed.append("No fallback/error return path detected.")

    if not issues:
        issues.append("No major style issues detected by heuristic analysis.")
    if not possible_bugs:
        possible_bugs.append("No obvious runtime bug pattern detected.")
    if not edge_cases_missed:
        edge_cases_missed.append("Edge-case handling appears reasonable for an MVP check.")

    return {
        "detected_issues": issues,
        "possible_bugs": possible_bugs,
        "edge_cases_missed": edge_cases_missed,
        "clean_logic": len(issues) <= 1 and len(possible_bugs) <= 1,
    }
