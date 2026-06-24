"""
Eval Runner
===========
Runs all 7 evals against a generated test file.
Fails fast on E01 — if syntax is broken, no point running the rest.
Prints a clean report with scores and issues.
"""

import sys
from pathlib import Path
from evals.graders import (
    e01_syntax_check,
    e02_todo_check,
    e03_fixture_check,
    e04_assertion_check,
    e05_duplicate_check,
    e06_flow_check,
    e07_story_coverage,
)

# ── Config — change these paths to match what you're evaluating ────────────
GENERATED_FILE = "tests/ambitionbox/test_home_page_generated.py"
CONFTEST_FILE  = "conftest.py"
TESTS_DIR      = "tests/"

USER_STORY = """
As a user on the AmbitionBox home page, I want to:
1. Click on a company card and be taken to that company overview page
2. Navigate to community sections from the home page
3. Click Login and see the login flow open
4. Navigate to ABECA Awards page from the home page nav

Acceptance Criteria:
- Clicking a company card navigates to that company URL
- Community section links work and take user to correct pages
- Login button opens login modal for unauthenticated users
- ABECA Awards nav link opens the awards page
- All navigation should work without errors
"""

# ── Separator line for readability ─────────────────────────────────────────
SEP = "─" * 60


def print_result(result, index):
    icon   = "✅" if result.passed else "❌"
    status = "PASS" if result.passed else "FAIL"
    print(f"\n{icon}  E0{index} {result.name:<25} Score: {result.score:.2f}  [{status}]")
    print(f"   {result.reason}")
    for issue in result.issues:
        print(f"   → {issue}")


def run():
    print(f"\n{'═' * 60}")
    print(f"  EVAL SUITE — {Path(GENERATED_FILE).name}")
    print(f"{'═' * 60}")

    results = []

    # ── E01: Syntax Check — FAIL FAST ─────────────────────────────────────
    print(f"\n{SEP}")
    print("Running E01 — Syntax Check...")
    r1 = e01_syntax_check.run(GENERATED_FILE)
    print_result(r1, 1)
    results.append(r1)

    if not r1.passed:
        print(f"\n{'═' * 60}")
        print("  ⛔ STOPPED — File has syntax errors. Fix before running other evals.")
        print(f"{'═' * 60}\n")
        sys.exit(1)

    # ── E02: TODO Check ────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("Running E02 — TODO Stub Check...")
    r2 = e02_todo_check.run(GENERATED_FILE)
    print_result(r2, 2)
    results.append(r2)

    # ── E03: Fixture Check ─────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("Running E03 — Fixture Check...")
    r3 = e03_fixture_check.run(GENERATED_FILE, CONFTEST_FILE)
    print_result(r3, 3)
    results.append(r3)

    # ── E04: Assertion Check ───────────────────────────────────────────────
    print(f"\n{SEP}")
    print("Running E04 — Assertion Check (calling LLM)...")
    r4 = e04_assertion_check.run(GENERATED_FILE)
    print_result(r4, 4)
    results.append(r4)

    # ── E05: Duplicate Check ───────────────────────────────────────────────
    print(f"\n{SEP}")
    print("Running E05 — Duplicate Check...")
    r5 = e05_duplicate_check.run(GENERATED_FILE, TESTS_DIR)
    print_result(r5, 5)
    results.append(r5)

    # ── E06: Flow Check ────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("Running E06 — Flow Check (calling LLM)...")
    r6 = e06_flow_check.run(GENERATED_FILE)
    print_result(r6, 6)
    results.append(r6)

    # ── E07: Story Coverage ────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("Running E07 — Story Coverage (calling LLM)...")
    r7 = e07_story_coverage.run(GENERATED_FILE, USER_STORY)
    print_result(r7, 7)
    results.append(r7)

    # ── Final Report ───────────────────────────────────────────────────────
    passed = sum(1 for r in results if r.passed)
    total  = len(results)
    avg    = sum(r.score for r in results) / total

    print(f"\n{'═' * 60}")
    print(f"  FINAL REPORT")
    print(f"{'═' * 60}")
    print(f"  Evals passed : {passed}/{total}")
    print(f"  Average score: {avg:.2f}")

    if passed == total:
        print(f"\n  ✅ OVERALL: PASS — Agent output is good quality.")
    elif passed >= total * 0.7:
        print(f"\n  ⚠️  OVERALL: NEEDS WORK — Some issues to fix before merging.")
    else:
        print(f"\n  ❌ OVERALL: FAIL — Too many issues. Agent output needs significant revision.")

    print(f"{'═' * 60}\n")

    return passed == total


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
