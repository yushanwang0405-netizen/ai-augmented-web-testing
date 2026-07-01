import ast
from pathlib import Path
from dataclasses import dataclass, field
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
DUPLICATE_THRESHOLD = 0.85


@dataclass
class EvalResult:
    name: str
    score: float
    passed: bool
    reason: str
    issues: list = field(default_factory=list)


def _extract_functions(source_code: str, source_file: str) -> list[dict]:
    """Extract all function defs as {name, body, source_file}."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []

    funcs = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            try:
                body = ast.unparse(node)
            except Exception:
                body = node.name
            funcs.append({"name": node.name, "body": body, "source_file": source_file})
    return funcs


def run(generated_file_path: str, tests_dir: str) -> EvalResult:
    gen_path = Path(generated_file_path)
    gen_code = gen_path.read_text(encoding="utf-8")
    new_functions = _extract_functions(gen_code, str(gen_path))

    if not new_functions:
        return EvalResult(
            name="Duplicate Check",
            score=1.0,
            passed=True,
            reason="No functions found in generated file.",
        )

    # Build corpus of ALL functions from entire tests dir
    all_functions = []
    for py_file in Path(tests_dir).rglob("*.py"):
        try:
            code = py_file.read_text(encoding="utf-8")
            all_functions.extend(_extract_functions(code, str(py_file)))
        except Exception:
            continue

    duplicates = []
    for new_fn in new_functions:
        new_combined = new_fn["name"] + "\n" + new_fn["body"]
        new_vector = _MODEL.encode([new_combined])

        # Pool = all functions EXCEPT itself (same name + same source file)
        pool = [
            f for f in all_functions
            if not (f["name"] == new_fn["name"] and f["source_file"] == new_fn["source_file"])
        ]

        if not pool:
            continue

        pool_texts = [f["name"] + "\n" + f["body"] for f in pool]
        pool_vectors = _MODEL.encode(pool_texts)
        scores = cosine_similarity(new_vector, pool_vectors)[0]
        best_idx = scores.argmax()
        best_score = scores[best_idx]

        if best_score >= DUPLICATE_THRESHOLD:
            match = pool[best_idx]
            duplicates.append(
                f"'{new_fn['name']}' is {best_score:.0%} similar to "
                f"'{match['name']}' in {Path(match['source_file']).name}"
            )

    total = len(new_functions)
    unique = total - len(duplicates)
    score = unique / total if total > 0 else 1.0
    passed = len(duplicates) == 0

    reason = (
        f"{unique}/{total} generated functions are unique."
        if passed
        else f"{len(duplicates)} duplicate(s) found among {total} generated functions."
    )

    return EvalResult(
        name="Duplicate Check",
        score=round(score, 2),
        passed=passed,
        reason=reason,
        issues=duplicates,
    )
