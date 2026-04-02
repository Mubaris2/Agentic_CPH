import json
from typing import Any, Dict, List

from agents.llm_utils import call_llm


def _fallback_summary(score: int, issues: List[str], problem_type: str) -> Dict[str, Any]:
    strengths = ["Shows working implementation structure."]
    if score >= 70:
        strengths.append("Good balance of correctness and efficiency.")

    weaknesses = []
    if issues and "No major" not in issues[0]:
        weaknesses.extend(issues[:2])
    if score < 60:
        weaknesses.append("Needs better pre-coding planning and edge-case checks.")

    if not weaknesses:
        weaknesses.append("No critical weakness detected in this short evaluation.")

    next_focus = [f"Practice more {problem_type} problems.", "Write tests for edge and boundary cases."]

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "next_focus": next_focus,
    }


def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    score = input_data.get("evaluation", {}).get("score", 0)
    issues = input_data.get("code_analysis", {}).get("detected_issues", [])
    problem_type = input_data.get("pattern", {}).get("problem_type", "General")

    system_prompt = "You are a concise coaching summarizer. Return JSON only."
    user_prompt = f"""
Score: {score}
Issues: {issues}
Problem type: {problem_type}
Return JSON with keys: strengths (array), weaknesses (array), next_focus (array).
"""

    llm_text = call_llm(system_prompt, user_prompt)
    if llm_text:
        try:
            parsed = json.loads(llm_text)
            if parsed.get("strengths") and parsed.get("weaknesses") and parsed.get("next_focus"):
                return parsed
        except Exception:
            pass

    return _fallback_summary(score, issues, problem_type)
