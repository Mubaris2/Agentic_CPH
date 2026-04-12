from __future__ import annotations

from state import State


def response_aggregator_node(state: State) -> State:
    validation = state.get("validation_result") or {}
    status = validation.get("status")
    intervention = validation.get("intervention") or {}
    trainer_profile = state.get("trainer_profile") or "Supportive personal CP trainer"
    coaching_goal = state.get("coaching_goal") or "Improve one concept and one implementation habit in each session."
    memory_notes = state.get("memory_notes") or []
    user_input = state.get("user_input") or ""

    blocks: list[str] = []

    blocks.append(f"Coach Mode: {trainer_profile}")
    blocks.append(f"Session Goal: {coaching_goal}")

    if status == "mismatch":
        warning = intervention.get("warning", "Approach mismatch detected.")
        reason = validation.get("reason", "")
        hint = intervention.get("hint", "")
        counterexample = intervention.get("counterexample")
        blocks.append(f"⚠️ Validation Warning: {warning}")
        if reason:
            blocks.append(f"Reason: {reason}")
        if hint:
            blocks.append(f"Direction: {hint}")
        if counterexample:
            blocks.append(f"Counterexample idea: {counterexample}")

    analysis = state.get("analysis_result")
    if analysis:
        blocks.append("Code Analysis:\n" + analysis)

    hints = state.get("hints") or []
    if hints:
        hint_text = "\n".join(f"- {h}" for h in hints)
        blocks.append("Progressive Hints:\n" + hint_text)

    strategy = state.get("strategy")
    if strategy:
        blocks.append("Strategy:\n" + strategy)

    if memory_notes:
        recent = "\n".join(f"- {note}" for note in memory_notes[-3:])
        blocks.append("What I remember about your progress:\n" + recent)

    next_step = "Implement one small improvement and run sample + one edge case test."
    if status == "mismatch":
        next_step = "Refactor toward the suggested approach, then validate complexity against constraints."
    elif not state.get("analysis_result") and not state.get("strategy") and not state.get("hints"):
        next_step = "Share either your current code or ask for strategy/hints for this specific problem."

    blocks.append(f"Next step: {next_step}")

    if not blocks:
        blocks.append("I did not detect enough signals. Share the problem statement and your current code for a precise response.")

    if user_input and len(user_input) < 6:
        blocks.append("Tip: add one sentence about where you are stuck (logic, complexity, or bug).")

    return {"final_response": "\n\n".join(blocks)}
