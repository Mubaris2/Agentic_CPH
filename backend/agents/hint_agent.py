import json
from typing import Any, Dict, List

from agents.llm_utils import call_llm


def _fallback_hints(problem_type: str) -> List[str]:
    return [
        f"Level 1: Identify core pattern hints for {problem_type}.",
        "Level 2: Write down states/variables and transitions before coding.",
        "Level 3: Dry-run on smallest edge case, then optimize bottlenecks.",
    ]


def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    problem_type = input_data.get("pattern", {}).get("problem_type", "General")
    description = input_data.get("problem_description", "")

    system_prompt = "You are a CP hint coach. Return JSON only."
    user_prompt = f"""
Generate progressive hints for a {problem_type} problem.
Description: {description}
Return JSON with key "hints" as array of exactly 3 hints labeled by difficulty.
"""

    llm_text = call_llm(system_prompt, user_prompt, temperature=0.3)
    if llm_text:
        try:
            parsed = json.loads(llm_text)
            hints = parsed.get("hints", [])
            if len(hints) >= 3:
                return {"progressive_hints": hints[:3]}
        except Exception:
            pass

    return {"progressive_hints": _fallback_hints(problem_type)}
