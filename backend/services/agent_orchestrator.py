from typing import Any, Dict

from agents import (
    code_analyzer,
    complexity_agent,
    evaluation_agent,
    hint_agent,
    pattern_agent,
    strategy_agent,
    summary_agent,
    thinking_agent,
)


class AgentOrchestrator:
    async def run_full_analysis(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "code": input_data.get("code", ""),
            "problem_description": input_data.get("problem_description", ""),
            "is_correct": input_data.get("is_correct", False),
            "used_hints": input_data.get("used_hints", False),
        }

        payload["code_analysis"] = code_analyzer.run(payload)
        payload["complexity"] = complexity_agent.run(payload)
        payload["pattern"] = pattern_agent.run(payload)
        payload["strategy"] = strategy_agent.run(payload)
        payload["hints"] = hint_agent.run(payload)
        payload["thinking"] = thinking_agent.run(payload)
        payload["evaluation"] = evaluation_agent.run(payload)
        payload["summary"] = summary_agent.run(payload)

        return {
            "code_analysis": payload["code_analysis"],
            "complexity": payload["complexity"],
            "pattern": payload["pattern"],
            "strategy": payload["strategy"],
            "hints": payload["hints"],
            "thinking": payload["thinking"],
            "evaluation": payload["evaluation"],
            "summary": payload["summary"],
        }
