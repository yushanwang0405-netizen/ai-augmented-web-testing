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


SYSTEM_PROMPT = """You are a senior QA engineer checking whether a generated test file adequately covers a user story.

You will be given:
1. A user story with acceptance criteria (ACs)
2. Generated test code

Check for:
1. AC_COVERAGE: Is every AC covered by at least one test?
2. CORRECT_OUTCOMES: Do assertions verify what the AC says should happen?
3. NEGATIVE_CASES: Are error states / edge cases tested if the story mentions them?
4. SCOPE_CREEP: Does the test cover things the story never asked for?

Severity for gaps: MAJOR (AC completely untested) or MINOR (partially tested or weak).

score = acs_covered / total_acs_found. Round to 2 decimal places.

Return ONLY valid JSON:
{
  "score": 0.0 to 1.0,
  "total_acs_found": <int>,
  "acs_covered": <int>,
  "coverage_gaps": [
    {"ac": "<AC text>", "severity": "MAJOR | MINOR", "detail": "<what is missing>"}
  ],
  "out_of_scope": ["<description of extra thing tested>"],
  "summary": "<one sentence>"
}"""


def run(generated_file_path: str, user_story: str) -> EvalResult:
    AgentConfig.validate()
    client = OpenAI(api_key=AgentConfig.OPENAI_API_KEY)

    code = Path(generated_file_path).read_text(encoding="utf-8")

    response = client.chat.completions.create(
        model=AgentConfig.OPENAI_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"=== User Story ===\n{user_story}\n\n"
                f"=== Generated Test Code ===\n```python\n{code}\n```"
            )},
        ],
    )

    data = json.loads(response.choices[0].message.content)
    score = float(data.get("score", 0.0))
    passed = score >= 0.75

    issues = []
    for gap in data.get("coverage_gaps", []):
        issues.append(f"{gap['severity']} GAP — {gap['ac']}: {gap['detail']}")
    for oos in data.get("out_of_scope", []):
        issues.append(f"OUT OF SCOPE — {oos}")

    total = data.get("total_acs_found", 0)
    covered = data.get("acs_covered", 0)
    reason = f"ACs covered: {covered}/{total}. {data.get('summary', '')}"

    return EvalResult(
        name="Story Coverage",
        score=round(score, 2),
        passed=passed,
        reason=reason,
        issues=issues,
    )
