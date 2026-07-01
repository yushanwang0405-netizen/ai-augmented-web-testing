import re
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class EvalResult:
    name: str
    score: float
    passed: bool
    reason: str
    issues: list = field(default_factory=list)


def run(generated_file_path: str) -> EvalResult:
    path = Path(generated_file_path)
    source_code = path.read_text(encoding="utf-8")
    lines = source_code.splitlines()

    todo_lines = [
        f"Line {i+1}: {line.strip()}"
        for i, line in enumerate(lines)
        if re.search(r"\bTODO\b", line, re.IGNORECASE)
    ]
    count = len(todo_lines)

    if count == 0:
        score = 1.0
    elif count == 1:
        score = 0.5
    elif count == 2:
        score = 0.25
    else:
        score = 0.0

    passed = score >= 0.5
    reason = (
        f"No TODO stubs found." if count == 0
        else f"{count} TODO stub(s) found — agent left unfinished placeholders."
    )

    return EvalResult(
        name="TODO Stub Check",
        score=score,
        passed=passed,
        reason=reason,
        issues=todo_lines,
    )
