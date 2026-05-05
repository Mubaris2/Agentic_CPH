"""problem_analyzer.py

Placeholder agent that takes a raw Codeforces problem statement and splits it
into three clearly-structured sections:

  * description  – what the problem is asking (story + task)
  * constraints  – numerical bounds and limits, formatted as bullet points
  * examples     – each sample case with Input / Output / (optional) Explanation

When the LLM is available it uses call_reasoning_model to do the extraction.
If the model returns nothing (key not configured, quota exceeded, etc.) it
falls back to a lightweight heuristic that still produces a cleaner output
than the raw HTML-stripped text.
"""

from __future__ import annotations

import re
from typing import TypedDict

from state import State
from .common import ModelRegistry, call_reasoning_model, parse_json_object


# ---------------------------------------------------------------------------
# Public return type
# ---------------------------------------------------------------------------

class ParsedProblem(TypedDict, total=False):
    description: str
    constraints: str
    examples: str


# ---------------------------------------------------------------------------
# Heuristic fallback helpers
# ---------------------------------------------------------------------------

def _extract_constraints_heuristic(text: str) -> tuple[str, str]:
    """Split *text* into (description_part, constraints_part) heuristically."""
    # Common section headers found in CF statements
    constraint_header = re.compile(
        r"(constraints?|input\s+constraints?|limits?|bounds?)",
        re.IGNORECASE,
    )

    lines = text.splitlines()
    split_at = None
    for i, line in enumerate(lines):
        if constraint_header.search(line) and len(line.strip()) < 60:
            split_at = i
            break

    if split_at is not None:
        description = "\n".join(lines[:split_at]).strip()
        constraints_raw = "\n".join(lines[split_at + 1 :]).strip()
    else:
        # Try to detect the constraints block by the presence of inequalities
        # like "1 ≤ n ≤ 2·10^5" or "−10^9 ≤ a_i ≤ 10^9"
        constraint_line = re.compile(r"[0-9].*[≤<≥>].*[0-9]")
        first_constraint = next(
            (i for i, l in enumerate(lines) if constraint_line.search(l)), None
        )
        if first_constraint is not None:
            description = "\n".join(lines[:first_constraint]).strip()
            constraints_raw = "\n".join(lines[first_constraint:]).strip()
        else:
            description = text.strip()
            constraints_raw = ""

    # Format constraints as bullet points
    if constraints_raw:
        bullets = []
        for line in constraints_raw.splitlines():
            stripped = line.strip(" •-–—*")
            if stripped:
                bullets.append(f"• {stripped}")
        constraints_part = "\n".join(bullets) if bullets else constraints_raw
    else:
        constraints_part = "(constraints not found in statement)"

    return description, constraints_part


def _format_examples_heuristic(raw_examples: str | list) -> str:
    """Return a consistently formatted examples string."""
    if isinstance(raw_examples, list):
        parts = []
        for i, ex in enumerate(raw_examples, 1):
            inp = (ex.get("input") or "").strip()
            out = (ex.get("output") or "").strip()
            note = (ex.get("explanation") or ex.get("note") or "").strip()
            block = f"── Example {i} ──\nInput:\n{inp}\n\nOutput:\n{out}"
            if note:
                block += f"\n\nExplanation:\n{note}"
            parts.append(block)
        return "\n\n".join(parts) if parts else "(no examples)"

    # Already a string – normalize spacing
    return raw_examples.strip() if raw_examples else "(no examples)"


# ---------------------------------------------------------------------------
# Main agent node
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a competitive-programming assistant. "
    "Your job is to restructure a raw problem statement into three clearly "
    "separated sections that a contestant can read at a glance."
)

USER_PROMPT_TEMPLATE = """\
Below is a competitive-programming problem. Extract and rewrite it into the \
following three sections. Be concise but complete.

Return ONLY valid JSON with these exact keys:
{{
  "description": "<clear prose: what the problem is asking>",
  "constraints": "<bullet-point list, one constraint per line, using • as bullet>",
  "examples": "<all sample cases, each formatted as:\\n── Example N ──\\nInput:\\n...\\nOutput:\\n...\\nExplanation:\\n... (if present)>"
}}

--- PROBLEM TITLE ---
{title}

--- RAW STATEMENT ---
{statement}

--- RAW CONSTRAINTS (if separate) ---
{constraints}

--- RAW EXAMPLES ---
{examples}
"""


def problem_analyzer_node(state: State, models: ModelRegistry | None = None) -> dict:
    """LangGraph node: parse problem_context into structured parsed_problem."""
    ctx = state.get("problem_context") or {}

    title = str(ctx.get("title", "")).strip()
    statement = str(ctx.get("statement", "")).strip()
    constraints_raw = str(ctx.get("constraints", "")).strip()
    examples_raw = ctx.get("examples", "")

    parsed = _run_analysis(title, statement, constraints_raw, examples_raw, state, models)
    return {"parsed_problem": parsed}


def analyze_problem(
    title: str,
    statement: str,
    constraints: str,
    examples: str | list,
    state: State | None = None,
    models: ModelRegistry | None = None,
) -> ParsedProblem:
    """Public helper callable from the API endpoint (no LangGraph needed)."""
    return _run_analysis(title, statement, constraints, examples, state or {}, models)


# ---------------------------------------------------------------------------
# Internal implementation
# ---------------------------------------------------------------------------

def _run_analysis(
    title: str,
    statement: str,
    constraints_raw: str,
    examples_raw: str | list,
    state: State,
    models: ModelRegistry | None,
) -> ParsedProblem:
    examples_str = (
        _format_examples_heuristic(examples_raw)
        if isinstance(examples_raw, list)
        else (examples_raw or "")
    )

    prompt = USER_PROMPT_TEMPLATE.format(
        title=title or "(untitled)",
        statement=statement or "(no statement)",
        constraints=constraints_raw or "(none)",
        examples=examples_str or "(none)",
    )

    model_out = call_reasoning_model(prompt, state, models=models)

    if model_out:
        obj = parse_json_object(model_out)
        if obj and "description" in obj:
            return ParsedProblem(
                description=str(obj.get("description", "")).strip(),
                constraints=str(obj.get("constraints", "")).strip(),
                examples=str(obj.get("examples", "")).strip(),
            )

    # ---- heuristic fallback ----
    full_text = f"{statement}\n{constraints_raw}".strip()
    desc_heuristic, constr_heuristic = _extract_constraints_heuristic(full_text)

    # If we got a non-empty separate constraints field, prefer it
    if constraints_raw and constraints_raw not in ("None", "(none)"):
        bullets = []
        for line in constraints_raw.splitlines():
            stripped = line.strip(" •-–—*")
            if stripped:
                bullets.append(f"• {stripped}")
        constr_heuristic = "\n".join(bullets) if bullets else constraints_raw

    return ParsedProblem(
        description=desc_heuristic or statement or "(no description)",
        constraints=constr_heuristic or "(no constraints found)",
        examples=examples_str or "(no examples)",
    )
