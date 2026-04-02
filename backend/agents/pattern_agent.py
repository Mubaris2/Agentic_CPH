from typing import Any, Dict


def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    code = input_data.get("code", "").lower()
    problem_description = input_data.get("problem_description", "").lower()
    text = f"{code}\n{problem_description}"

    if "graph" in text or "adj" in text or "bfs" in text or "dfs" in text:
        problem_type = "Graph"
    elif "dp" in text or "memo" in text or "state" in text:
        problem_type = "Dynamic Programming"
    elif "sort" in text or "interval" in text or "choose" in text:
        problem_type = "Greedy/Sorting"
    elif "window" in text or "two pointer" in text or "left" in text and "right" in text:
        problem_type = "Two Pointers / Sliding Window"
    elif "prefix" in text or "sum" in text:
        problem_type = "Prefix Sum / Array"
    else:
        problem_type = "General Implementation"

    return {"problem_type": problem_type}
