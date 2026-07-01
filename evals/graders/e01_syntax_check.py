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
        return EvalResult(
            name="Syntax Check",
            score=0.0,
            passed=False,
            reason=f"File not found: {generated_file_path}",
            issues=[f"File not found: {generated_file_path}"],
        )

    source_code = path.read_text(encoding="utf-8")

    if not source_code.strip():
        return EvalResult(
            name="Syntax Check",
            score=0.0,
            passed=False,
            reason="File is empty.",
            issues=["File is empty."],
        )

    try:
        compile(source_code, str(path), "exec")
        return EvalResult(
            name="Syntax Check",
            score=1.0,
            passed=True,
            reason="File is valid Python.",
        )
    except SyntaxError as e:
        error_detail = f"Line {e.lineno}: {e.msg}"
        return EvalResult(
            name="Syntax Check",
            score=0.0,
            passed=False,
            reason=f"SyntaxError: {error_detail}",
            issues=[error_detail],
        )
