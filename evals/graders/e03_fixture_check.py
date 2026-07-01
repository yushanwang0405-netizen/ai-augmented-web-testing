import ast
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
    """Return names of all @pytest.fixture-decorated functions in source."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return set()

    fixtures = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                target = dec.func if isinstance(dec, ast.Call) else dec
                is_fixture = (
                    (isinstance(target, ast.Name) and target.id == "fixture")
                    or (isinstance(target, ast.Attribute) and target.attr == "fixture")
                )
                if is_fixture:
                    fixtures.add(node.name)
    return fixtures


def _extract_used_fixtures(source_code: str) -> set:
    """Return all parameter names used in test functions (excluding self)."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return set()

    used = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                for arg in node.args.args:
                    if arg.arg != "self":
                        used.add(arg.arg)
    return used


def run(generated_file_path: str, conftest_path: str) -> EvalResult:
    generated_code = Path(generated_file_path).read_text(encoding="utf-8")
    conftest_code = Path(conftest_path).read_text(encoding="utf-8")

    known_fixtures = (
        _extract_defined_fixtures(conftest_code)
        | _extract_defined_fixtures(generated_code)
        | {"self", "request", "pytestconfig"}
    )
    used_fixtures = _extract_used_fixtures(generated_code)
    invented = used_fixtures - known_fixtures

    score = max(0.0, 1.0 - (len(invented) * 0.3))
    passed = len(invented) == 0

    issues = [f"Invented fixture: '{f}'" for f in sorted(invented)]
    reason = (
        "All fixtures are valid." if passed
        else f"{len(invented)} invented fixture(s) that don't exist in conftest.py."
    )

    return EvalResult(
        name="Fixture Check",
        score=round(score, 2),
        passed=passed,
        reason=reason,
        issues=issues,
    )
