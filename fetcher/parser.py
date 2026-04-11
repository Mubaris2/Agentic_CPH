from __future__ import annotations

import re
from typing import Any, Dict, List

from bs4 import BeautifulSoup


def _clean(text: str) -> str:
    text = text.replace("\r", "")
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def _extract_text(node) -> str:
    if node is None:
        return ""
    return _clean(node.get_text("\n", strip=False))


def _extract_statement_body(problem_statement: BeautifulSoup) -> str:
    chunks: List[str] = []
    for child in problem_statement.find_all(recursive=False):
        classes = child.get("class", [])
        if "header" in classes:
            continue
        if child.name == "div" and "input-spec" in classes:
            break
        if child.name == "div" and "output-spec" in classes:
            break
        if child.name == "div" and "sample-tests" in classes:
            break
        text = _extract_text(child)
        if text:
            chunks.append(text)
    return _clean("\n\n".join(chunks))


def _extract_examples(problem_statement: BeautifulSoup) -> List[Dict[str, str]]:
    sample_tests = problem_statement.select_one(".sample-tests")
    if sample_tests is None:
        return []

    examples: List[Dict[str, str]] = []
    tests = sample_tests.select(".sample-test")
    if tests:
        for test in tests:
            input_node = test.select_one(".input pre")
            output_node = test.select_one(".output pre")
            examples.append(
                {
                    "input": _extract_text(input_node),
                    "output": _extract_text(output_node),
                }
            )
        return examples

    input_blocks = sample_tests.select(".input")
    output_blocks = sample_tests.select(".output")
    for input_node, output_node in zip(input_blocks, output_blocks):
        examples.append(
            {
                "input": _extract_text(input_node),
                "output": _extract_text(output_node),
            }
        )
    return examples


def parse_problem_html(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    problem_statement = soup.select_one(".problem-statement")
    if problem_statement is None:
        raise ValueError("Could not locate .problem-statement in HTML")

    title = _extract_text(problem_statement.select_one(".title"))
    time_limit = _extract_text(problem_statement.select_one(".time-limit"))
    memory_limit = _extract_text(problem_statement.select_one(".memory-limit"))
    statement = _extract_statement_body(problem_statement)
    input_spec = _extract_text(problem_statement.select_one(".input-spec"))
    output_spec = _extract_text(problem_statement.select_one(".output-spec"))
    examples = _extract_examples(problem_statement)

    return {
        "title": title,
        "time_limit": time_limit,
        "memory_limit": memory_limit,
        "statement": statement,
        "input": input_spec,
        "output": output_spec,
        "examples": examples,
    }
