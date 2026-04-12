from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from time import perf_counter
from typing import Any


LANGUAGE_CONFIG = {
    "python": {
        "source": "main.py",
        "compile": None,
        "run": ["python3", "main.py"],
    },
    "cpp": {
        "source": "main.cpp",
        "compile": ["g++", "-std=c++17", "-O2", "main.cpp", "-o", "main"],
        "run": ["./main"],
    },
    "java": {
        "source": "Main.java",
        "compile": ["javac", "Main.java"],
        "run": ["java", "Main"],
    },
}


def _normalize_output(value: str) -> str:
    return value.replace("\r\n", "\n").strip()


def _run_subprocess(command: list[str], cwd: Path, input_text: str, timeout_seconds: int) -> tuple[int, str, str, float]:
    started = perf_counter()
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    elapsed_ms = (perf_counter() - started) * 1000
    return completed.returncode, completed.stdout, completed.stderr, elapsed_ms


def run_code(language: str, code: str, test_cases: list[dict[str, Any]], timeout_seconds: int = 2) -> dict[str, Any]:
    lang = (language or "").strip().lower()
    if lang not in LANGUAGE_CONFIG:
        return {"error": f"Unsupported language: {language}", "cases": []}

    config = LANGUAGE_CONFIG[lang]

    with tempfile.TemporaryDirectory(prefix="cp_runner_") as tmpdir:
        workdir = Path(tmpdir)
        source_path = workdir / config["source"]
        source_path.write_text(code or "", encoding="utf-8")

        if config["compile"] is not None:
            try:
                compile_code, _, compile_err, _ = _run_subprocess(
                    command=config["compile"],
                    cwd=workdir,
                    input_text="",
                    timeout_seconds=max(timeout_seconds, 5),
                )
            except FileNotFoundError:
                return {
                    "error": f"Compiler not found for language '{lang}'. Install required toolchain.",
                    "cases": [],
                }
            except subprocess.TimeoutExpired:
                return {
                    "error": "Compilation timed out.",
                    "cases": [],
                }

            if compile_code != 0:
                return {
                    "error": "Compilation failed.",
                    "compile_error": compile_err.strip(),
                    "cases": [],
                }

        results: list[dict[str, Any]] = []
        for index, case in enumerate(test_cases, start=1):
            case_input = str(case.get("input", ""))
            expected = str(case.get("expected", ""))
            try:
                exit_code, stdout, stderr, elapsed_ms = _run_subprocess(
                    command=config["run"],
                    cwd=workdir,
                    input_text=case_input,
                    timeout_seconds=timeout_seconds,
                )
            except FileNotFoundError:
                return {
                    "error": f"Runtime not found for language '{lang}'.",
                    "cases": [],
                }
            except subprocess.TimeoutExpired:
                results.append(
                    {
                        "id": case.get("id", index),
                        "output": "",
                        "error": "Execution timed out",
                        "status": "Failed",
                        "runtime_ms": timeout_seconds * 1000,
                    }
                )
                continue

            output = _normalize_output(stdout)
            expected_norm = _normalize_output(expected)
            if exit_code != 0:
                status = "Failed"
                error_text = _normalize_output(stderr) or f"Non-zero exit code: {exit_code}"
            else:
                status = "Passed" if output == expected_norm else "Failed"
                error_text = _normalize_output(stderr)

            results.append(
                {
                    "id": case.get("id", index),
                    "output": output,
                    "error": error_text,
                    "status": status,
                    "runtime_ms": round(elapsed_ms, 2),
                }
            )

        overall = "Accepted" if results and all(case["status"] == "Passed" for case in results) else "Wrong Answer"
        if not results:
            overall = "Error: No test cases"

        return {
            "error": "",
            "compile_error": "",
            "status": overall,
            "cases": results,
        }
