"""
Astra Eval Suite — orchestrator.

Usage:
  python -m evals.run_evals                                    # uses default hardcoded paths
  python -m evals.run_evals <generated_file> <user_story>     # CI passes these as args
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

# ── Config — overridden by CLI args when run from CI ──────────────────────
PROJECT_ROOT = Path(__file__).parent.parent

DEFAULT_GENERATED_FILE = str(PROJECT_ROOT / "tests/ambitionbox/test_home_page_generated.py")
DEFAULT_CONFTEST       = str(PROJECT_ROOT / "conftest.py")
DEFAULT_TESTS_DIR      = str(PROJECT_ROOT / "tests")
DEFAULT_NAV_FLOWS      = str(PROJECT_ROOT / "ai_agent/knowledge/navigation_flows.yaml")
DEFAULT_USER_STORY     = """
As a user visiting AmbitionBox home page,
I want to navigate to company pages, community links, and awards pages,
So that I can explore company information and community features.

Acceptance Criteria:
1. Clicking a company card navigates to that company's overview page.
2. Communities section links navigate to the correct community pages.
3. Clicking Login opens the login flow.
4. Unauthenticated users cannot access My Company tab content.
5. All navigation actions should work without JavaScript errors.
"""

# ── Parse CLI args ────────────────────────────────────────────────────────
if len(sys.argv) >= 3:
    GENERATED_FILE = sys.argv[1]
    USER_STORY     = sys.argv[2]
    print(f"[CI MODE] Evaluating: {GENERATED_FILE}")
else:
    GENERATED_FILE = DEFAULT_GENERATED_FILE
    USER_STORY     = DEFAULT_USER_STORY
    print(f"[LOCAL MODE] Evaluating: {GENERATED_FILE}")

CONFTEST  = DEFAULT_CONFTEST
TESTS_DIR = DEFAULT_TESTS_DIR
NAV_FLOWS = DEFAULT_NAV_FLOWS

# ── Run evals ─────────────────────────────────────────────────────────────
results = []

print("\n" + "=" * 60)
print("ASTRA EVAL SUITE")
print("=" * 60)

# E01 — fail fast
r1 = e01_syntax_check.run(GENERATED_FILE)
results.append(r1)
print(f"\n[E01] {r1.name}")
print(f"  Score : {r1.score}")
print(f"  Passed: {r1.passed}")
print(f"  Reason: {r1.reason}")
if not r1.passed:
    print("\n  FAIL FAST: syntax error — stopping all further evals.")
    print("\n" + "=" * 60)
    print("RESULT: FAIL (syntax error blocks all other checks)")
    print("=" * 60)
    sys.exit(1)

# E02
r2 = e02_todo_check.run(GENERATED_FILE)
results.append(r2)
print(f"\n[E02] {r2.name}")
print(f"  Score : {r2.score}")
print(f"  Passed: {r2.passed}")
print(f"  Reason: {r2.reason}")
for issue in r2.issues:
    print(f"    - {issue}")

# E03
r3 = e03_fixture_check.run(GENERATED_FILE, CONFTEST)
results.append(r3)
print(f"\n[E03] {r3.name}")
print(f"  Score : {r3.score}")
print(f"  Passed: {r3.passed}")
print(f"  Reason: {r3.reason}")
for issue in r3.issues:
    print(f"    - {issue}")

# E04
r4 = e04_assertion_check.run(GENERATED_FILE)
results.append(r4)
print(f"\n[E04] {r4.name}")
print(f"  Score : {r4.score}")
print(f"  Passed: {r4.passed}")
print(f"  Reason: {r4.reason}")
for issue in r4.issues:
    print(f"    - {issue}")

# E05
r5 = e05_duplicate_check.run(GENERATED_FILE, TESTS_DIR)
results.append(r5)
print(f"\n[E05] {r5.name}")
print(f"  Score : {r5.score}")
print(f"  Passed: {r5.passed}")
print(f"  Reason: {r5.reason}")
for issue in r5.issues:
    print(f"    - {issue}")

# E06
r6 = e06_flow_check.run(GENERATED_FILE, NAV_FLOWS)
results.append(r6)
print(f"\n[E06] {r6.name}")
print(f"  Score : {r6.score}")
print(f"  Passed: {r6.passed}")
print(f"  Reason: {r6.reason}")
for issue in r6.issues:
    print(f"    - {issue}")

# E07
r7 = e07_story_coverage.run(GENERATED_FILE, USER_STORY)
results.append(r7)
print(f"\n[E07] {r7.name}")
print(f"  Score : {r7.score}")
print(f"  Passed: {r7.passed}")
print(f"  Reason: {r7.reason}")
for issue in r7.issues:
    print(f"    - {issue}")

# ── Final report ──────────────────────────────────────────────────────────
passed_count = sum(1 for r in results if r.passed)
total_count  = len(results)
avg_score    = sum(r.score for r in results) / total_count

print("\n" + "=" * 60)
print(f"FINAL REPORT: {passed_count}/{total_count} evals passed  |  Avg score: {avg_score:.2f}")

if passed_count == total_count:
    print("OVERALL: PASS")
    sys.exit(0)
elif avg_score >= 0.6 and passed_count >= 5:
    print("OVERALL: NEEDS WORK — review issues above before merging")
    sys.exit(1)
else:
    print("OVERALL: FAIL — do not merge")
    sys.exit(1)
