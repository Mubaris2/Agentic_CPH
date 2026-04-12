from __future__ import annotations

from state import State
from .common import ModelRegistry, call_reasoning_model, normalize_approach, parse_json_object


def _derive_expected(problem_context: dict) -> str:
    title = (problem_context.get("title") or "").lower()
    statement = (problem_context.get("statement") or "").lower()
    constraints = (problem_context.get("constraints") or "").lower()
    text = "\n".join([title, statement, constraints])

    if "tree" in text or "graph" in text or "path" in text:
        return "graph"
    if "maximize" in text or "minimum number of" in text or "sorted" in text:
        return "greedy"
    if "number of ways" in text or "subsequence" in text or "n <= 2000" in text:
        return "dp"
    if "binary search" in text or "monotonic" in text:
        return "binary_search"
    if "gcd" in text or "prime" in text or "mod" in text:
        return "math"
    return "unknown"


def approach_validator_node(state: State, models: ModelRegistry | None = None) -> State:
    problem_context = state.get("problem_context") or {}
    detected = normalize_approach(state.get("detected_approach"))
    expected = normalize_approach(state.get("expected_approach"))

    if expected == "unknown":
        expected = _derive_expected(problem_context)

    if expected == "unknown":
        status = "match" if detected != "unknown" else "mismatch"
        confidence = 0.52 if detected != "unknown" else 0.35
    else:
        status = "match" if detected != "unknown" and detected == expected else "mismatch"
        confidence = 0.45 if detected == "unknown" else (0.86 if status == "match" else 0.81)

    reason = f"Detected `{detected}` while expected `{expected}` based on problem context."
    warning = ""
    hint = ""
    counterexample = None

    if status == "mismatch" and expected != "unknown":
        warning = "Your current approach may not satisfy constraints or correctness requirements."
        hint = f"Try reformulating with `{expected}` style transitions/invariants."
        counterexample = "Edge case: minimal/maximum boundary values where greedy local choices fail globally."
    elif status == "mismatch":
        warning = "Expected approach could not be derived from context."
        hint = "Provide clearer problem constraints or title so the validator can infer a target approach."
        counterexample = None
    else:
        warning = ""
        hint = "Approach appears aligned; focus on edge cases and implementation details."

    prompt = (
        "Validate detected approach vs expected approach for CP problem. "
        "Return strict JSON with keys status, reason, confidence, intervention. "
        "status must be match or mismatch. intervention must include warning, hint, counterexample. "
        f"Detected: {detected}. Expected: {expected}. Problem: {problem_context}."
    )
    model_out = call_reasoning_model(prompt, state, models=models)
    if model_out:
        obj = parse_json_object(model_out)
        if obj:
            model_status = str(obj.get("status", "")).strip().lower()
            if model_status in {"match", "mismatch"}:
                status = model_status

            model_reason = str(obj.get("reason", "")).strip()
            if model_reason:
                reason = model_reason

            model_confidence = obj.get("confidence")
            if isinstance(model_confidence, (int, float)):
                confidence = float(max(0.0, min(1.0, model_confidence)))

            intervention_obj = obj.get("intervention", {}) if isinstance(obj.get("intervention", {}), dict) else {}
            warning = str(intervention_obj.get("warning", warning)).strip() or warning
            hint = str(intervention_obj.get("hint", hint)).strip() or hint
            model_counterexample = intervention_obj.get("counterexample", counterexample)
            counterexample = str(model_counterexample).strip() if isinstance(model_counterexample, str) and model_counterexample.strip() else counterexample
        else:
            reason = model_out.strip()

    return {
        "expected_approach": expected,
        "validation_result": {
            "status": status,
            "reason": reason,
            "confidence": float(round(confidence, 2)),
            "intervention": {
                "warning": warning,
                "hint": hint,
                "counterexample": counterexample,
            },
        },
    }
