from typing import Dict, Any, List
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
from .llm import chat_completion
from .utils import parse_json_object
from .settings import settings

NODE_MODELS = {
    "orchestrator": settings.MODEL_INTENT_DETECTION,
    "code_analyzer": settings.MODEL_CODE_ANALYZER,
    "approach_detection": settings.MODEL_APPROACH_DETECTOR,
    "approach_validator": settings.MODEL_APPROACH_VALIDATOR,
    "hint_agent": settings.MODEL_HINT_AGENT,
    "strategy_agent": settings.MODEL_STRATEGY_AGENT,
    "counterexample_gen": settings.MODEL_COUNTEREXAMPLE_GEN,
    "response_aggregator": settings.MODEL_GENERAL_CHAT,
    "problem_fetch_tool": "codeforces_api",
}


def _normalize_intent(value: str) -> str:
    intent = (value or "").strip().lower()
    if intent in {"hint", "debug", "strategy", "problem_fetch", "general"}:
        return intent
    return "general"


def _normalize_approach(value: str) -> str:
    allowed = {
        "unknown", "brute_force", "greedy", "dp", "graph", "binary_search",
        "two_pointers", "prefix_sum", "math", "string", "backtracking"
    }
    approach = (value or "").strip().lower()
    return approach if approach in allowed else "unknown"


def _obj_to_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return {}


async def orchestrator_node(state: CPAssistantState) -> Dict[str, Any]:
    ui = state.get("user_input", "") or ""
    problem_fetch_attempted = bool(state.get("problem_fetch_attempted", False))
    problem_context = state.get("problem_context")
    has_problem_context = False
    if isinstance(problem_context, dict):
        has_problem_context = bool(problem_context.get("title"))
    elif problem_context is not None:
        has_problem_context = bool(getattr(problem_context, "title", ""))

    if not settings.OXLO_API_KEY:
        lower_ui = ui.lower()
        intent = "general"
        if "hint" in lower_ui:
            intent = "hint"
        elif any(token in lower_ui for token in ["random problem", "find problem", "fetch problem", "codeforces", "question", "problem"]):
            intent = "problem_fetch"
        elif "strategy" in lower_ui or "optimiz" in lower_ui:
            intent = "strategy"
        elif state.get("code"):
            intent = "debug"
    else:
        prompt = (
            "Classify user intent into exactly one label: "
            "hint, debug, strategy, problem_fetch, general.\n"
            "Return strict JSON: {\"intent\": \"...\"}.\n"
            f"User input: {ui}\n"
            f"Has code: {bool(state.get('code'))}\n"
            f"Has problem context: {has_problem_context}\n"
            f"Problem fetch attempted: {problem_fetch_attempted}"
        )
        raw = await chat_completion(
            NODE_MODELS["orchestrator"],
            [
                {"role": "system", "content": "You are an intent classifier for coding assistant routing."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=120,
        )
        intent = _normalize_intent(parse_json_object(raw).get("intent", "general"))

    if intent == "problem_fetch" and (problem_fetch_attempted or has_problem_context):
        intent = "general"

    step = IntermediateStep(node="orchestrator", summary="intent classified", payload={"intent": intent})
    return {"intent": intent, "next_node": "", "intermediate_steps": [step]}


async def debug_fork_node(state: CPAssistantState) -> Dict[str, Any]:
    step = IntermediateStep(node="debug_fork", summary="fork debug path", payload={})
    return {"intermediate_steps": [step]}


async def code_analyzer_node(state: CPAssistantState) -> Dict[str, Any]:
    code = state.get("code") or ""
    if not code.strip():
        res = AnalysisResult(code_issues=["No code provided."], bugs=[], edge_cases=[])
        step = IntermediateStep(node="code_analyzer", summary="analysis complete", payload={"issues": res.code_issues, "bugs": []})
        return {"analysis_result": res, "intermediate_steps": [step]}

    if not settings.OXLO_API_KEY:
        res = AnalysisResult(
            code_issues=["LLM analysis unavailable (missing OXLO_API_KEY)."],
            bugs=[],
            edge_cases=["Configure OXLO_API_KEY to enable deep code analysis."],
        )
        step = IntermediateStep(node="code_analyzer", summary="analysis fallback", payload={"issues": res.code_issues})
        return {"analysis_result": res, "intermediate_steps": [step]}

    prompt = (
        "Analyze the code for competitive programming.\n"
        "Return strict JSON with keys code_issues, bugs, edge_cases; each must be an array of short strings.\n"
        f"User request: {state.get('user_input', '')}\n"
        f"Code:\n{code}"
    )
    raw = await chat_completion(
        NODE_MODELS["code_analyzer"],
        [
            {"role": "system", "content": "You are an expert competitive programming code analyzer."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=700,
    )
    obj = parse_json_object(raw)
    res = AnalysisResult(
        code_issues=[str(x) for x in obj.get("code_issues", [])][:8],
        bugs=[str(x) for x in obj.get("bugs", [])][:8],
        edge_cases=[str(x) for x in obj.get("edge_cases", [])][:8],
    )
    step = IntermediateStep(node="code_analyzer", summary="analysis complete", payload={"issues": res.code_issues, "bugs": res.bugs})
    return {"analysis_result": res, "intermediate_steps": [step]}


async def approach_detection_node(state: CPAssistantState) -> Dict[str, Any]:
    code = state.get("code") or ""
    if not code.strip() or not settings.OXLO_API_KEY:
        detected = "unknown"
    else:
        prompt = (
            "Detect the dominant algorithmic approach used in code.\n"
            "Allowed labels: unknown, brute_force, greedy, dp, graph, binary_search, two_pointers, prefix_sum, math, string, backtracking.\n"
            "Return strict JSON: {\"detected_approach\": \"label\"}.\n"
            f"Code:\n{code}"
        )
        raw = await chat_completion(
            NODE_MODELS["approach_detection"],
            [
                {"role": "system", "content": "You classify algorithmic approaches."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=120,
        )
        detected = _normalize_approach(parse_json_object(raw).get("detected_approach", "unknown"))

    step = IntermediateStep(node="approach_detection", summary="approach detected", payload={"detected": detected})
    return {"detected_approach": detected, "intermediate_steps": [step]}


async def approach_validator_node(state: CPAssistantState) -> Dict[str, Any]:
    detected = _normalize_approach(state.get("detected_approach", "unknown"))
    expected = _normalize_approach(state.get("expected_approach", "unknown"))

    if not settings.OXLO_API_KEY:
        if detected == "unknown" or expected == "unknown":
            vr = ValidationResult(status="unknown", reason="insufficient signal", trigger_counterexample=False)
        elif detected == expected:
            vr = ValidationResult(status="match", reason="approach aligns with expected", trigger_counterexample=False)
        else:
            vr = ValidationResult(status="mismatch", reason=f"detected={detected}, expected={expected}", trigger_counterexample=True)
    else:
        prompt = (
            "Compare detected and expected competitive programming approaches.\n"
            "Return strict JSON: {\"status\":\"match|mismatch|unknown\",\"reason\":\"...\",\"trigger_counterexample\":true|false}.\n"
            f"Detected: {detected}\nExpected: {expected}\n"
            f"User input: {state.get('user_input', '')}\n"
            f"Code:\n{state.get('code') or ''}"
        )
        raw = await chat_completion(
            NODE_MODELS["approach_validator"],
            [
                {"role": "system", "content": "You validate whether the coding approach matches expected strategy."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=220,
        )
        obj = parse_json_object(raw)
        status = obj.get("status", "unknown")
        if status not in {"match", "mismatch", "unknown"}:
            status = "unknown"
        reason = str(obj.get("reason", ""))
        trigger = bool(obj.get("trigger_counterexample", status == "mismatch"))
        vr = ValidationResult(status=status, reason=reason, trigger_counterexample=trigger)

    step = IntermediateStep(node="approach_validator", summary="validation", payload={"status": vr.status})
    return {"validation_result": vr, "intermediate_steps": [step]}


async def hint_agent_node(state: CPAssistantState) -> Dict[str, Any]:
    ui = state.get("user_input", "")
    level = 1
    lower_ui = ui.lower()
    if "hint 2" in lower_ui or "level 2" in lower_ui:
        level = 2
    if "hint 3" in lower_ui or "level 3" in lower_ui:
        level = 3

    if not settings.OXLO_API_KEY:
        hints = [HintItem(level=1, text="Configure OXLO_API_KEY to enable model-generated hints.")]
        step = IntermediateStep(node="hint_agent", summary=f"provided {len(hints)} hints", payload={"level": 1})
        return {"hints": hints, "intermediate_steps": [step]}

    prompt = (
        "Generate progressive hints for a competitive programming problem.\n"
        "Return strict JSON: {\"hints\":[{\"level\":1,\"text\":\"...\"},{\"level\":2,\"text\":\"...\"},{\"level\":3,\"text\":\"...\"}]}.\n"
        "Hints must avoid giving full final code unless explicitly asked.\n"
        f"Requested max hint level: {level}\n"
        f"User input: {ui}\n"
        f"Problem context: {state.get('problem_context')}\n"
        f"Code:\n{state.get('code') or ''}"
    )
    raw = await chat_completion(
        NODE_MODELS["hint_agent"],
        [
            {"role": "system", "content": "You are a coaching-style hint assistant for competitive programming."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=700,
    )
    obj = parse_json_object(raw)
    hints: List[HintItem] = []
    for item in obj.get("hints", []):
        if not isinstance(item, dict):
            continue
        item_level = item.get("level", 1)
        if item_level not in (1, 2, 3):
            continue
        text = str(item.get("text", "")).strip()
        if not text or item_level > level:
            continue
        hints.append(HintItem(level=item_level, text=text))

    if not hints:
        hints = [HintItem(level=1, text="Start by deriving the target time complexity from constraints.")]

    step = IntermediateStep(node="hint_agent", summary=f"provided {len(hints)} hints", payload={"level": level})
    return {"hints": hints, "intermediate_steps": [step]}


async def strategy_agent_node(state: CPAssistantState) -> Dict[str, Any]:
    if not settings.OXLO_API_KEY:
        optimal = "unknown"
        complexity = "N/A (missing OXLO_API_KEY)"
        alternatives = []
        step = IntermediateStep(node="strategy_agent", summary="strategy fallback", payload={"optimal": optimal})
        strat = StrategyResult(optimal_approach=optimal, complexity_analysis=complexity, alternative_methods=alternatives)
        return {"strategy": strat, "expected_approach": optimal, "intermediate_steps": [step]}

    prompt = (
        "Given the user request, problem context, and optional code, suggest an algorithmic strategy.\n"
        "Return strict JSON: {\"optimal_approach\":\"label\",\"complexity_analysis\":\"...\",\"alternative_methods\":[\"...\"]}.\n"
        "Use approach labels from: unknown, brute_force, greedy, dp, graph, binary_search, two_pointers, prefix_sum, math, string, backtracking.\n"
        f"User input: {state.get('user_input', '')}\n"
        f"Problem context: {state.get('problem_context')}\n"
        f"Code:\n{state.get('code') or ''}"
    )
    raw = await chat_completion(
        NODE_MODELS["strategy_agent"],
        [
            {"role": "system", "content": "You are a strategy planner for competitive programming."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=700,
    )
    obj = parse_json_object(raw)
    optimal = _normalize_approach(obj.get("optimal_approach", "unknown"))
    complexity = str(obj.get("complexity_analysis", ""))
    alternatives = [str(x) for x in obj.get("alternative_methods", [])][:5]

    step = IntermediateStep(node="strategy_agent", summary="strategy suggested", payload={"optimal": optimal})
    strat = StrategyResult(optimal_approach=optimal, complexity_analysis=complexity, alternative_methods=alternatives)
    return {"strategy": strat, "expected_approach": optimal, "intermediate_steps": [step]}


async def counterexample_gen_node(state: CPAssistantState) -> Dict[str, Any]:
    validation = state.get("validation_result")
    status = validation.get("status") if isinstance(validation, dict) else getattr(validation, "status", "unknown")
    if status != "mismatch":
        return {"counterexample": "", "intermediate_steps": [IntermediateStep(node="counterexample_gen", summary="skipped", payload={"reason": "status_not_mismatch"})]}

    if not settings.OXLO_API_KEY:
        text = "Potential mismatch detected. Configure OXLO_API_KEY to generate a concrete counterexample."
        return {"counterexample": text, "intermediate_steps": [IntermediateStep(node="counterexample_gen", summary="fallback", payload={})]}

    prompt = (
        "Generate one minimal counterexample input where the current approach/code is likely to fail.\n"
        "Explain expected output briefly. Keep concise.\n"
        f"User input: {state.get('user_input', '')}\n"
        f"Detected approach: {state.get('detected_approach', 'unknown')}\n"
        f"Expected approach: {state.get('expected_approach', 'unknown')}\n"
        f"Code:\n{state.get('code') or ''}"
    )
    text = await chat_completion(
        NODE_MODELS["counterexample_gen"],
        [
            {"role": "system", "content": "You generate concrete failing tests for algorithmic solutions."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=350,
    )
    step = IntermediateStep(node="counterexample_gen", summary="counterexample generated", payload={"chars": len(text)})
    return {"counterexample": text, "intermediate_steps": [step]}


async def response_aggregator_node(state: CPAssistantState) -> Dict[str, Any]:
    vr = state.get("validation_result") or ValidationResult()
    analysis = state.get("analysis_result")
    strategy = state.get("strategy")
    hints = state.get("hints") or []

    hint_texts = []
    for h in hints:
        if isinstance(h, dict):
            hint_texts.append(h.get("text", ""))
        else:
            hint_texts.append(h.text)

    analysis_payload = _obj_to_dict(analysis)
    strategy_payload = _obj_to_dict(strategy)
    validation_payload = _obj_to_dict(vr)
    counterexample = state.get("counterexample", "")
    problem_context = _obj_to_dict(state.get("problem_context"))
    problem_candidates = state.get("problem_candidates") or []

    if not settings.OXLO_API_KEY:
        lines = []
        if analysis_payload:
            lines.append(f"Analysis: {analysis_payload}")
        if strategy_payload:
            lines.append(f"Strategy: {strategy_payload}")
        if hint_texts:
            lines.append("Hints: " + " | ".join([t for t in hint_texts if t]))
        if validation_payload.get("status") == "mismatch" and counterexample:
            lines.append(f"Counterexample: {counterexample}")
        if problem_context.get("title"):
            lines.append(f"Problem: {problem_context}")
        if problem_candidates:
            lines.append(f"Candidates: {problem_candidates[:5]}")
        final = "\n\n".join(lines) if lines else "No actionable output."
    else:
        prompt = (
            "Compose a concise helpful response for a coding IDE assistant.\n"
            "Use markdown. If there is a mismatch, warn gently and include counterexample section.\n"
            "Do not hallucinate missing fields.\n"
            f"User input: {state.get('user_input', '')}\n"
            f"Intent: {state.get('intent', 'general')}\n"
            f"Analysis: {analysis_payload}\n"
            f"Strategy: {strategy_payload}\n"
            f"Hints: {hint_texts}\n"
            f"Validation: {validation_payload}\n"
            f"Counterexample: {counterexample}\n"
            f"Problem Context: {problem_context}\n"
            f"Problem Candidates: {problem_candidates[:10]}"
        )
        final = await chat_completion(
            NODE_MODELS["response_aggregator"],
            [
                {"role": "system", "content": "You are a helpful competitive programming AI assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=700,
        )

    step = IntermediateStep(node="response_aggregator", summary="final composed", payload={"len": len(final)})
    return {"final_response": final, "intermediate_steps": [step]}


async def problem_fetch_tool_node(state: CPAssistantState) -> Dict[str, Any]:
    ui = state.get("user_input", "")
    fetch_result = await fetch_codeforces_problem(ui, user_data=state.get("user_data") or {})
    pc: ProblemContext = fetch_result.get("problem_context", ProblemContext())
    candidates = fetch_result.get("candidates", [])
    mode = fetch_result.get("mode", "none")
    step = IntermediateStep(
        node="problem_fetch_tool",
        summary="fetched problem",
        payload={"has_problem": bool(pc.title), "mode": mode, "candidate_count": len(candidates)},
    )
    return {
        "problem_context": pc,
        "problem_candidates": candidates,
        "problem_fetch_attempted": True,
        "intermediate_steps": [step],
    }
