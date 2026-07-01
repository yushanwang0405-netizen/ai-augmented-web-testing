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


SYSTEM_PROMPT = """You are a senior QA engineer reviewing pytest test code for assertion quality.

A WEAK assertion is one that cannot actually fail meaningfully:
- Asserting a hardcoded True/False literal: assert True, assert login_modal_visible = True then assert login_modal_visible
- Asserting a variable that was never set from the UI/DOM
- assert len(items) >= 0  (always true)
- assert result is not None  without ever checking the value

A STRONG assertion is one that verifies real UI state:
- assert "accenture" in driver.current_url
- assert company_name in page_title
- assert len(results) > 0
- assert error_message.is_displayed()

Return ONLY valid JSON in this format:
{
  "score": 0.0 to 1.0,
  "total_assertions": <int>,
  "weak_count": <int>,
  "weak_assertions": [
    {"line_hint": "<short snippet>", "reason": "<why it is weak>"}
  ],
  "summary": "<one sentence>"
}

score = (total_assertions - weak_count) / total_assertions. If no assertions found, score = 0.0."""


def run(generated_file_path: str) -> EvalResult:
    AgentConfig.validate()
    client = OpenAI(api_key=AgentConfig.OPENAI_API_KEY)

    code = Path(generated_file_path).read_text(encoding="utf-8")

    response = client.chat.completions.create(
        model=AgentConfig.OPENAI_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Review the assertions in this test file:\n\n```python\n{code}\n```"},
        ],
    )

    data = json.loads(response.choices[0].message.content)
    score = float(data.get("score", 0.0))
    passed = score >= 0.75

    issues = [
        f"Line hint: {w['line_hint']} — {w['reason']}"
        for w in data.get("weak_assertions", [])
    ]

    return EvalResult(
        name="Assertion Check",
        score=round(score, 2),
        passed=passed,
        reason=data.get("summary", ""),
        issues=issues,
    )
