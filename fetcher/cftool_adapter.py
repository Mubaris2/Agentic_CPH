from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .cache import BASE_DIR


def _candidate_binaries(preferred_bin: Optional[str] = None) -> List[str]:
    configured = os.getenv("CFTOOL_BIN")
    out = []
    if preferred_bin:
        out.append(preferred_bin)
    if configured:
        out.append(configured)
    out.extend(["cftool", "cf", "/home/mubaris/go/bin/cftool", "/home/mubaris/go/bin/cf"])
    seen = set()
    deduped: List[str] = []
    for item in out:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _resolve_workdir(preferred_dir: Optional[str] = None) -> Path:
    if preferred_dir:
        raw = Path(preferred_dir).expanduser()
        workdir = raw if raw.is_absolute() else (BASE_DIR / raw)
    else:
        workdir = BASE_DIR / ".tmp_cftool_runtime"
    workdir.mkdir(parents=True, exist_ok=True)
    return workdir


async def _run_parse(binary: str, contest_id: int, index: str, workdir: Path) -> tuple[int, str, str]:
    spec = f"{contest_id}{str(index).upper()}"
    process = await asyncio.create_subprocess_exec(
        binary,
        "parse",
        spec,
        cwd=str(workdir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return process.returncode, stdout.decode("utf-8", errors="ignore"), stderr.decode("utf-8", errors="ignore")


def _parse_sample_files(problem_dir: Path) -> List[Dict[str, str]]:
    if not problem_dir.exists():
        return []

    files = sorted([p for p in problem_dir.iterdir() if p.is_file()])
    in_files: Dict[str, Path] = {}
    out_files: Dict[str, Path] = {}

    for f in files:
        name = f.name.lower()
        in_match = re.match(r"(?:in|input)(\d*)\.txt$", name)
        out_match = re.match(r"(?:out|output|ans|answer)(\d*)\.txt$", name)
        if in_match:
            in_files[in_match.group(1) or "1"] = f
        if out_match:
            out_files[out_match.group(1) or "1"] = f

    examples: List[Dict[str, str]] = []
    keys = sorted(set(in_files.keys()) | set(out_files.keys()), key=lambda x: int(x) if x.isdigit() else 0)
    for key in keys:
        in_text = in_files[key].read_text(encoding="utf-8", errors="ignore").strip() if key in in_files else ""
        out_text = out_files[key].read_text(encoding="utf-8", errors="ignore").strip() if key in out_files else ""
        if in_text or out_text:
            examples.append({"input": in_text, "output": out_text})
    return examples


async def parse_with_cftool(
    contest_id: int,
    index: str,
    workdir_path: Optional[str] = None,
    cftool_bin: Optional[str] = None,
) -> Dict[str, Any]:
    workdir = _resolve_workdir(workdir_path)

    errors = []
    for binary in _candidate_binaries(cftool_bin):
        try:
            code, stdout, stderr = await _run_parse(binary, contest_id, index, workdir)
        except FileNotFoundError:
            errors.append(f"{binary}: not found")
            continue
        except Exception as exc:
            errors.append(f"{binary}: {str(exc)}")
            continue

        if code != 0:
            errors.append(f"{binary}: exit={code} stderr={stderr.strip()[:200]}")
            continue

        problem_dir = workdir / "cf" / "contest" / str(contest_id) / str(index).lower()
        examples = _parse_sample_files(problem_dir)
        if examples:
            return {
                "ok": True,
                "examples": examples,
                "method": f"{binary} parse",
                "workdir": str(workdir),
                "stdout": stdout,
            }

        errors.append(f"{binary}: parse finished but no sample files were generated")

    return {
        "ok": False,
        "examples": [],
        "method": "",
        "workdir": str(workdir),
        "error": " | ".join(errors),
    }
