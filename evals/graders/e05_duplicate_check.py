import ast
import textwrap
from pathlib import Path
from dataclasses import dataclass, field
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

@dataclass
class EvalResult:
    name: str
    score: float
    passed: bool
    reason: str
    issues: list = field(default_factory=list)

print("Loading embedding model...")
_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
DUPLICATE_THRESHOLD = 0.85

def _extract_test_functions(source_code: str, source_label: str) -> list:
    functions = []
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return functions
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            body = ast.get_source_segment(source_code, node) or ""
            body = textwrap.dedent(body)
            functions.append({"name": node.name, "body": body,
                             "combined": f"{node.name}\n{body}", "source": source_label})
    return functions

def _collect_all_functions(tests_dir: str) -> list:
    all_functions = []
    for py_file in Path(tests_dir).rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        source = py_file.read_text(encoding="utf-8")
        all_functions.extend(_extract_test_functions(source, str(py_file)))
    return all_functions

def run(generated_file_path: str, tests_dir: str) -> EvalResult:
    gen_path = Path(generated_file_path).resolve()
    if not gen_path.exists():
        return EvalResult(name="Duplicate Check", score=0.0, passed=False,
                         reason="Generated file does not exist.", issues=[f"File not found: {generated_file_path}"])
    generated_code = gen_path.read_text(encoding="utf-8")
    new_functions = _extract_test_functions(generated_code, str(gen_path))
    if not new_functions:
        return EvalResult(name="Duplicate Check", score=1.0, passed=True,
                         reason="No test functions found in generated file.")
    all_existing = _collect_all_functions(tests_dir)
    if not all_existing:
        return EvalResult(name="Duplicate Check", score=1.0, passed=True,
                         reason="No existing tests found to compare against.")
    issues = []
    duplicate_names = set()
    print(f"  Comparing {len(new_functions)} new functions against {len(all_existing)} total...")
    for new_fn in new_functions:
        pool = [fn for fn in all_existing
                if not (fn["name"] == new_fn["name"] and Path(fn["source"]).resolve() == gen_path)]
        if not pool:
            continue
        new_vector = _MODEL.encode([new_fn["combined"]])
        pool_vectors = _MODEL.encode([fn["combined"] for fn in pool], show_progress_bar=False)
        scores = cosine_similarity(new_vector, pool_vectors)[0]
        best_match_idx = scores.argmax()
        best_score = scores[best_match_idx]
        if best_score >= DUPLICATE_THRESHOLD:
            duplicate_names.add(new_fn["name"])
            match = pool[best_match_idx]
            match_location = ("same file" if Path(match["source"]).resolve() == gen_path
                             else Path(match["source"]).name)
            issues.append(f"'{new_fn['name']}' is {best_score:.0%} similar to "
                         f"'{match['name']}' ({match_location})")
    total = len(new_functions)
    unique = total - len(duplicate_names)
    return EvalResult(name="Duplicate Check", score=round(unique/total, 3),
                     passed=len(duplicate_names) == 0,
                     reason=f"{unique}/{total} generated functions are unique.", issues=issues)
