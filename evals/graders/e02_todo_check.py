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
    if not path.exists():
        return EvalResult(name="TODO Stub Check", score=0.0, passed=False,
                         reason="File does not exist.", issues=[f"File not found: {generated_file_path}"])
    source_code = path.read_text(encoding="utf-8")
    lines = source_code.splitlines()
    todo_lines = [
        f"Line {i+1}: {line.strip()}"
        for i, line in enumerate(lines)
        if re.search(r"\bTODO\b", line, re.IGNORECASE)
    ]
    todo_count = len(todo_lines)
    if todo_count == 0:
        score, reason = 1.0, "No TODO stubs found."
    elif todo_count == 1:
        score, reason = 0.5, "1 TODO stub found."
    elif todo_count == 2:
        score, reason = 0.25, "2 TODO stubs found."
    else:
        score, reason = 0.0, f"{todo_count} TODO stubs found. Test file is largely unimplemented."
    return EvalResult(name="TODO Stub Check", score=round(score, 3),
                     passed=todo_count == 0, reason=reason, issues=todo_lines)
