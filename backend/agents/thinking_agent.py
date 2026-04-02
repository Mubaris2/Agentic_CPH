import json
from typing import Any, Dict

from agents.llm_utils import call_llm


def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    issues = input_data.get("code_analysis", {}).get("detected_issues", [])
    complexity = input_data.get("complexity", {}).get("time_complexity", "unknown")
    is_correct = input_data.get("is_correct", False)

    system_prompt = "You are a concise CP thinking coach. Return JSON only."
    user_prompt = f"""
Correctness: {is_correct}
Issues: {issues}
Complexity: {complexity}
Return JSON with key "thinking_feedback" that explains what the user likely missed in their thinking process.
"""

    llm_text = call_llm(system_prompt, user_prompt)
    if llm_text:
        try:
            parsed = json.loads(llm_text)
            feedback = parsed.get("thinking_feedback")
            if feedback:
                return {"thinking_feedback": feedback}
        except Exception:
            pass

    fallback = (
        "You likely focused on implementation before validating edge cases and complexity trade-offs. "
        "Try a quick plan-first workflow: constraints -> pattern -> edge cases -> implementation."
    )
    return {"thinking_feedback": fallback}
