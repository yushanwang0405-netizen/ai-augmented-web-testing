import json
from pathlib import Path
from dataclasses import dataclass, field
from openai import OpenAI
from ai_agent.config import AgentConfig

@dataclass
class EvalResult:
    name: str
    score: float
    passed: bool
    reason: str
    issues: list = field(default_factory=list)

SYSTEM_PROMPT = """
You are a senior QA engineer reviewing AI-generated pytest tests against a user story.

CHECK THESE 4 THINGS:

1. ACCEPTANCE CRITERIA COVERAGE
   - Identify every AC in the user story
   - Check if each AC has at least one test that covers it with correct assertions
   - Flag any AC with no corresponding test as a COVERAGE GAP

2. CORRECT EXPECTED OUTCOMES
   - Story says what should happen — do assertions verify exactly that?
   - Flag any test where assertion doesn't match story's expected outcome

3. NEGATIVE AND EDGE CASES
   - Does story mention errors, empty states, invalid inputs, boundary conditions?
   - If yes — are those tested? Flag missing negative/edge case tests.

4. SCOPE CREEP
   - Did agent write tests for things the story never mentioned?
   - Flag out-of-scope tests for review.

SCORING:
  1.0  = all ACs covered, correct outcomes, edge cases covered
  0.75 = 1 minor gap (missing edge case, slightly wrong assertion)
  0.5  = 1 major gap (missing AC entirely) or multiple minor gaps
  0.25 = multiple ACs missing
  0.0  = tests don't match story at all

Respond ONLY in this JSON format:
{
  "score": <float 0.0 to 1.0>,
  "total_acs_found": <integer>,
  "acs_covered": <integer>,
  "coverage_gaps": [{"missing": "<what is not tested>", "severity": "<MAJOR or MINOR>"}],
  "out_of_scope": ["<function name>"],
  "summary": "<one sentence>"
}
"""

def run(generated_file_path: str, user_story: str) -> EvalResult:
    path = Path(generated_file_path)
    if not path.exists():
        return EvalResult(name="Story Coverage", score=0.0, passed=False,
                         reason="File does not exist.", issues=[f"File not found: {generated_file_path}"])
    if not user_story or not user_story.strip():
        return EvalResult(name="Story Coverage", score=0.0, passed=False,
                         reason="No user story provided.",
                         issues=["User story is empty — provide the original story text."])
    generated_code = path.read_text(encoding="utf-8")
    AgentConfig.validate()
    client = OpenAI(api_key=AgentConfig.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=AgentConfig.OPENAI_MODEL, temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"USER STORY:\n```\n{user_story}\n```\n\n"
                f"GENERATED TESTS:\n```python\n{generated_code}\n```\n\n"
                f"Evaluate whether the generated tests fully cover the user story."
            )}
        ]
    )
    data = json.loads(response.choices[0].message.content)
    score = float(data.get("score", 0.0))
    issues = [f"ACs covered: {data.get('acs_covered', 0)}/{data.get('total_acs_found', 0)}"]
    for gap in data.get("coverage_gaps", []):
        prefix = "✗ MAJOR" if gap.get("severity") == "MAJOR" else "! MINOR"
        issues.append(f"{prefix} GAP — {gap['missing']}")
    for fn in data.get("out_of_scope", []):
        issues.append(f"? OUT OF SCOPE — {fn}")
    return EvalResult(name="Story Coverage", score=round(score, 3),
                     passed=score >= 0.75, reason=data.get("summary", ""), issues=issues)
