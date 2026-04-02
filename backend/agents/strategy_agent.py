import json
from typing import Any, Dict, List

from agents.llm_utils import call_llm


def _fallback_strategy(problem_type: str) -> List[Dict[str, str]]:
    return [
        {
            "approach": "Brute Force Baseline",
            "when_to_use": "Small constraints or for quick validation.",
            "explanation": "Start with a straightforward implementation to verify logic and test cases.",
        },
        {
            "approach": f"{problem_type}-optimized approach",
            "when_to_use": "When constraints are moderate to high.",
            "explanation": "Use the most natural data structure/paradigm for the recognized pattern.",
        },
        {
            "approach": "Hybrid with preprocessing",
            "when_to_use": "When multiple queries or repeated computations exist.",
            "explanation": "Precompute reusable information (prefix arrays, maps, or ordering).",
        },
    ]


def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    problem_type = input_data.get("pattern", {}).get("problem_type", "General")
    description = input_data.get("problem_description", "")

    system_prompt = "You are a competitive programming coach. Output strict JSON only."
    user_prompt = f"""
Given problem type: {problem_type}
Problem description: {description}
Return JSON with key "alternatives": array of 2-3 objects with keys:
- approach
- explanation
- when_to_use
"""

    llm_text = call_llm(system_prompt, user_prompt)
    if llm_text:
        try:
            parsed = json.loads(llm_text)
            alternatives = parsed.get("alternatives", [])
            if alternatives:
                return {"alternative_approaches": alternatives[:3]}
        except Exception:
            pass

    return {"alternative_approaches": _fallback_strategy(problem_type)}
