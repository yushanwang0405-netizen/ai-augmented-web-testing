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

def _extract_defined_fixtures(source_code: str) -> set:
    matches = re.findall(r"@pytest\.fixture[^\n]*\ndef (\w+)", source_code)
    return set(matches)

def _extract_used_fixtures(source_code: str) -> set:
    used = set()
    param_strings = re.findall(r"def test_\w+\(self,([^)]+)\)", source_code)
    for param_string in param_strings:
        for param in param_string.split(","):
            name = param.strip().split(":")[0].strip()
            if name:
                used.add(name)
    return used

def run(generated_file_path: str, conftest_path: str) -> EvalResult:
    gen_path = Path(generated_file_path)
    conftest = Path(conftest_path)
    if not gen_path.exists():
        return EvalResult(name="Fixture Check", score=0.0, passed=False,
                         reason="Generated file does not exist.", issues=[f"File not found: {generated_file_path}"])
    if not conftest.exists():
        return EvalResult(name="Fixture Check", score=0.0, passed=False,
                         reason="conftest.py not found.", issues=[f"conftest not found: {conftest_path}"])
    conftest_code = conftest.read_text(encoding="utf-8")
    known_fixtures = _extract_defined_fixtures(conftest_code)
    generated_code = gen_path.read_text(encoding="utf-8")
    inline_fixtures = _extract_defined_fixtures(generated_code)
    known_fixtures = known_fixtures | inline_fixtures | {"self", "request", "pytestconfig"}
    used_fixtures = _extract_used_fixtures(generated_code)
    invented = used_fixtures - known_fixtures
    if not invented:
        return EvalResult(name="Fixture Check", score=1.0, passed=True,
                         reason=f"All {len(used_fixtures)} fixtures are valid.")
    score = max(0.0, 1.0 - (len(invented) * 0.3))
    issues = [f"Invented fixture (does not exist anywhere): '{f}'" for f in sorted(invented)]
    return EvalResult(name="Fixture Check", score=round(score, 3), passed=False,
                     reason=f"{len(invented)} invented fixture(s) found.", issues=issues)
