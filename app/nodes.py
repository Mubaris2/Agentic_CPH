from typing import Dict, Any, List
import asyncio
from .models import (
    CPAssistantState,
    AnalysisResult,
    HintItem,
    ProblemContext,
    StrategyResult,
    ValidationResult,
    IntermediateStep,
)
from .tools import fetch_codeforces_problem

# model placeholders preserved intentionally
NODE_MODELS = {
    "orchestrator": "<TO_BE_FILLED>",
    "code_analyzer": "<TO_BE_FILLED>",
    "approach_detection": "<TO_BE_FILLED>",
    "approach_validator": "<TO_BE_FILLED>",
    "hint_agent": "<TO_BE_FILLED>",
    "strategy_agent": "<TO_BE_FILLED>",
    "response_aggregator": "<TO_BE_FILLED>",
    "problem_fetch_tool": "<TO_BE_FILLED>",
}


async def orchestrator_node(state: CPAssistantState) -> Dict[str, Any]:
    ui = state.get("user_input", "") or ""
    lower_ui = ui.lower()
    problem_fetch_attempted = bool(state.get("problem_fetch_attempted", False))
    problem_context = state.get("problem_context")
    has_problem_context = False
    if isinstance(problem_context, dict):
        has_problem_context = bool(problem_context.get("title"))
    elif problem_context is not None:
        has_problem_context = bool(getattr(problem_context, "title", ""))

    intent = "general"
    if "hint" in lower_ui:
        intent = "hint"
    elif "strategy" in lower_ui:
        intent = "strategy"
    elif "codeforces" in lower_ui or "contest" in lower_ui:
        if not problem_fetch_attempted and not has_problem_context:
            intent = "problem_fetch"
        else:
            intent = "strategy"
    elif state.get("code"):
        intent = "debug"

    step = IntermediateStep(node="orchestrator", summary="intent classified", payload={"intent": intent})
    return {"intent": intent, "next_node": "", "intermediate_steps": [step]}


async def debug_fork_node(state: CPAssistantState) -> Dict[str, Any]:
    step = IntermediateStep(node="debug_fork", summary="fork debug path", payload={})
    return {"intermediate_steps": [step]}


async def code_analyzer_node(state: CPAssistantState) -> Dict[str, Any]:
    code = state.get("code") or ""
    issues: List[str] = []
    bugs: List[str] = []
    edge_cases: List[str] = []

    if not code:
        issues.append("no code provided")
    else:
        if "==" in code and "=" in code and "===" not in code:
            bugs.append("possible assignment instead of comparison")
        if "for i in range" in code and "if" not in code:
            edge_cases.append("check empty input or extreme bounds")

    res = AnalysisResult(code_issues=issues, bugs=bugs, edge_cases=edge_cases)
    step = IntermediateStep(node="code_analyzer", summary="analysis complete", payload={"issues": issues, "bugs": bugs})
    await asyncio.sleep(0)  # yield
    return {"analysis_result": res, "intermediate_steps": [step]}


async def approach_detection_node(state: CPAssistantState) -> Dict[str, Any]:
    code = (state.get("code") or "").lower()
    # naive pattern detection
    if "dp" in code or "dp[" in code or "memo" in code:
        detected = "dp"
    elif "greedy" in code or "sort(" in code:
        detected = "greedy"
    elif "dfs" in code or "bfs" in code or "graph" in code:
        detected = "graph"
    else:
        detected = "unknown"

    step = IntermediateStep(node="approach_detection", summary="approach detected", payload={"detected": detected})
    return {"detected_approach": detected, "intermediate_steps": [step]}


async def approach_validator_node(state: CPAssistantState) -> Dict[str, Any]:
    detected = state.get("detected_approach", "unknown")
    expected = state.get("expected_approach", "unknown")
    if detected == "unknown" or expected == "unknown":
        vr = ValidationResult(status="unknown", reason="insufficient signal", trigger_counterexample=False)
    elif detected == expected:
        vr = ValidationResult(status="match", reason="approach aligns with expected", trigger_counterexample=False)
    else:
        vr = ValidationResult(status="mismatch", reason=f"detected={detected}, expected={expected}", trigger_counterexample=True)

    step = IntermediateStep(node="approach_validator", summary="validation", payload={"status": vr.status})
    return {"validation_result": vr, "intermediate_steps": [step]}


async def hint_agent_node(state: CPAssistantState) -> Dict[str, Any]:
    # determine desired level from user_input quick parse
    ui = state.get("user_input", "").lower()
    level = 1
    if "hint 2" in ui or "level 2" in ui:
        level = 2
    if "hint 3" in ui or "level 3" in ui:
        level = 3

    hints = []
    if level >= 1:
        hints.append(HintItem(level=1, text="Check constraints to pick complexity target."))
    if level >= 2:
        hints.append(HintItem(level=2, text="Consider greedy ordering by end/time or sorting by key."))
    if level >= 3:
        hints.append(HintItem(level=3, text="Think about prefix/suffix aggregates to reduce nested loops."))

    step = IntermediateStep(node="hint_agent", summary=f"provided {len(hints)} hints", payload={"level": level})
    return {"hints": hints, "intermediate_steps": [step]}


async def strategy_agent_node(state: CPAssistantState) -> Dict[str, Any]:
    pc = state.get("problem_context")
    # naive heuristics for demo
    optimal = "greedy"
    complexity = "O(n log n)"
    alternatives = ["dp O(n^2)"]
    step = IntermediateStep(node="strategy_agent", summary="strategy suggested", payload={"optimal": optimal})
    strat = StrategyResult(optimal_approach=optimal, complexity_analysis=complexity, alternative_methods=alternatives)
    return {"strategy": strat, "expected_approach": optimal, "intermediate_steps": [step]}


async def response_aggregator_node(state: CPAssistantState) -> Dict[str, Any]:
    vr = state.get("validation_result") or ValidationResult()
    intervention = ""
    if getattr(vr, "status", None) == "mismatch":
        intervention = "Soft warning: your approach may fail; see hints or request counterexample."

    analysis = state.get("analysis_result")
    strategy = state.get("strategy")
    hints = state.get("hints") or []

    parts = []
    if intervention:
        parts.append(intervention)
    if analysis:
        if isinstance(analysis, dict):
            parts.append(f"Analysis: issues={analysis.get('code_issues', [])}, bugs={analysis.get('bugs', [])}")
        else:
            parts.append(f"Analysis: issues={analysis.code_issues}, bugs={analysis.bugs}")
    if strategy:
        if isinstance(strategy, dict):
            parts.append(f"Strategy: {strategy.get('optimal_approach', '')} ({strategy.get('complexity_analysis', '')})")
        else:
            parts.append(f"Strategy: {strategy.optimal_approach} ({strategy.complexity_analysis})")
    if hints:
        hint_texts = []
        for h in hints:
            if isinstance(h, dict):
                hint_texts.append(h.get("text", ""))
            else:
                hint_texts.append(h.text)
        parts.append("Hints: " + ", ".join([text for text in hint_texts if text]))

    final = "\n\n".join(parts) if parts else "No actionable output."
    step = IntermediateStep(node="response_aggregator", summary="final composed", payload={"len": len(final)})
    return {"final_response": final, "intermediate_steps": [step]}


async def problem_fetch_tool_node(state: CPAssistantState) -> Dict[str, Any]:
    ui = state.get("user_input", "")
    pc: ProblemContext = await fetch_codeforces_problem(ui)
    step = IntermediateStep(node="problem_fetch_tool", summary="fetched problem", payload={"has_problem": bool(pc.title)})
    return {"problem_context": pc, "problem_fetch_attempted": True, "intermediate_steps": [step]}
