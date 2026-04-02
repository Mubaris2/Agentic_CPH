from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    code: str = Field(..., min_length=1)
    problem_description: Optional[str] = ""
    is_correct: bool = False
    used_hints: bool = False


class AnalyzeResponse(BaseModel):
    code_analysis: Dict[str, Any]
    complexity: Dict[str, Any]
    pattern: Dict[str, Any]
    strategy: Dict[str, Any]
    hints: Dict[str, Any]
    thinking: Dict[str, Any]
    evaluation: Dict[str, Any]
    summary: Dict[str, Any]


class ProgressResponse(BaseModel):
    past_scores: List[Dict[str, Any]]
    average_score: float
    insights: List[str]
