from typing import Any, Dict

from services.scoring_service import ScoringService


def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    scoring = ScoringService().compute(input_data)
    return {
        "score": scoring["score"],
        "score_breakdown": scoring["breakdown"],
    }
