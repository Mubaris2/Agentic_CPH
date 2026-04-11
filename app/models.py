from typing import TypedDict, Optional, Literal, List, Dict, Any
from pydantic import BaseModel, Field

IntentLabel = Literal["hint", "debug", "strategy", "problem_fetch", "general"]
ApproachLabel = Literal[
    "unknown", "brute_force", "greedy", "dp", "graph", "binary_search", "two_pointers",
    "prefix_sum", "math", "string", "backtracking"
]
MatchLabel = Literal["match", "mismatch", "unknown"]


class ProblemContext(BaseModel):
    title: str = ""
    statement: str = ""
    constraints: str = ""


class AnalysisResult(BaseModel):
    code_issues: List[str] = Field(default_factory=list)
    bugs: List[str] = Field(default_factory=list)
    edge_cases: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    status: MatchLabel = "unknown"
    reason: str = ""
    trigger_counterexample: bool = False


class HintItem(BaseModel):
    level: Literal[1, 2, 3]
    text: str


class StrategyResult(BaseModel):
    optimal_approach: str = ""
    complexity_analysis: str = ""
    alternative_methods: List[str] = Field(default_factory=list)


class IntermediateStep(BaseModel):
    node: str
    summary: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class CPAssistantState(TypedDict, total=False):
    user_input: str
    code: Optional[str]
    user_data: Dict[str, Any]
    intent: IntentLabel
    next_node: str
    problem_fetch_attempted: bool
    problem_context: ProblemContext
    problem_candidates: List[Dict[str, Any]]
    analysis_result: AnalysisResult
    detected_approach: ApproachLabel
    expected_approach: ApproachLabel
    validation_result: ValidationResult
    hints: List[HintItem]
    strategy: StrategyResult
    counterexample: str
    final_response: str
    intermediate_steps: List[IntermediateStep]


def init_state(user_input: str, code: Optional[str] = None, user_data: Optional[Dict[str, Any]] = None) -> CPAssistantState:
    return {
        "user_input": user_input,
        "code": code,
        "user_data": user_data or {},
        "intent": "general",
        "next_node": "",
        "problem_fetch_attempted": False,
        "problem_context": ProblemContext(),
        "problem_candidates": [],
        "analysis_result": AnalysisResult(),
        "detected_approach": "unknown",
        "expected_approach": "unknown",
        "validation_result": ValidationResult(),
        "hints": [],
        "strategy": StrategyResult(),
        "counterexample": "",
        "final_response": "",
        "intermediate_steps": [],
    }
