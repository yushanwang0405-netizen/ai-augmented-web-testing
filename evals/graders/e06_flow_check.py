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


SYSTEM_PROMPT = """You are a senior QA automation engineer reviewing pytest + Playwright test code.
You will be given:
1. navigation_flows.yaml — the known navigation structure of the app
2. Generated test code to review

Check each test function for these 5 things:
1. CORRECT_PAGE: Does the test enter the right page first?
2. CORRECT_ORDER: Is the order navigate → interact → assert respected?
3. PAGE_RULES: Are page-specific rules followed (e.g. dismiss overlay before clicking on home page)?
4. CORRECT_FIXTURE: Does the function use the right fixture for the page it tests?
5. UNKNOWN_FLOW: Does the test exercise a flow not described in navigation_flows.yaml?

For UNKNOWN_FLOW: do NOT hard-fail. Score it 0.5 and set needs_human_review: true.
For all other violations: deduct from score.

Score = (functions with no violations) / (total functions). Round to 2 decimal places.

Return ONLY valid JSON:
{
  "score": 0.0 to 1.0,
  "flow_issues": [
    {
      "function": "<function name>",
      "violation": "CORRECT_PAGE | CORRECT_ORDER | PAGE_RULES | CORRECT_FIXTURE | UNKNOWN_FLOW",
      "detail": "<what is wrong>",
      "needs_human_review": true | false
    }
  ],
  "summary": "<one sentence>"
}"""


def run(generated_file_path: str, navigation_flows_path: str) -> EvalResult:
    AgentConfig.validate()
    client = OpenAI(api_key=AgentConfig.OPENAI_API_KEY)

    code = Path(generated_file_path).read_text(encoding="utf-8")
    flows = Path(navigation_flows_path).read_text(encoding="utf-8")

    response = client.chat.completions.create(
        model=AgentConfig.OPENAI_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"=== navigation_flows.yaml ===\n{flows}\n\n"
                f"=== Generated test code ===\n```python\n{code}\n```"
            )},
        ],
    )

    data = json.loads(response.choices[0].message.content)
    score = float(data.get("score", 0.0))
    passed = score >= 0.75

    issues = []
    for fi in data.get("flow_issues", []):
        prefix = "HUMAN REVIEW" if fi.get("needs_human_review") else fi["violation"]
        issues.append(f"[{fi['function']}] {prefix} — {fi['detail']}")

    return EvalResult(
        name="Flow Check",
        score=round(score, 2),
        passed=passed,
        reason=data.get("summary", ""),
        issues=issues,
    )
