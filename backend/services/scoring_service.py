from typing import Any, Dict


class ScoringService:
    def _efficiency_points(self, complexity: str) -> int:
        text = complexity.lower()
        if "o(1)" in text or "o(log n)" in text:
            return 30
        if "o(n)" in text and "log" not in text:
            return 24
        if "o(n log n)" in text:
            return 20
        if "o(n^2)" in text:
            return 12
        if "o(n^3)" in text or "2^n" in text:
            return 5
        return 15

    def compute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        is_correct = data.get("is_correct", False)
        used_hints = data.get("used_hints", False)
        complexity = data.get("complexity", {}).get("time_complexity", "")
        clean_logic = data.get("code_analysis", {}).get("clean_logic", False)

        correctness_points = 40 if is_correct else 0
        efficiency_points = self._efficiency_points(complexity)
        hint_penalty = -10 if used_hints else 0
        clean_logic_bonus = 10 if clean_logic else 0

        total = max(0, min(100, correctness_points + efficiency_points + hint_penalty + clean_logic_bonus))

        return {
            "score": total,
            "breakdown": {
                "correctness": correctness_points,
                "efficiency": efficiency_points,
                "hint_penalty": hint_penalty,
                "clean_logic_bonus": clean_logic_bonus,
            },
        }
