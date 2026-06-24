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
You are a senior QA engineer reviewing AI-generated pytest test code.
Your job is to evaluate every assertion in the test file.

AN ASSERTION IS WEAK if it can pass even when the feature is broken.
AN ASSERTION IS STRONG if a real bug in the application would cause it to fail.

WEAK assertion examples:
  - assert True
  - assert False
  - assert some_var where that variable was hardcoded to True above
  - assert count > -1 (count can never be negative)
  - assert result is not None (passes even if result is empty or wrong)
  - assert x (bare variable, no comparison)
  - assert page_loaded == True (comparing to literal True)

STRONG assertion examples:
  - assert "accenture" in url.lower()
  - assert 1.0 <= rating <= 5.0
  - assert len(results) > 0
  - assert before != after
  - assert "big-4" in current_url

Respond ONLY in this exact JSON format:
{
  "score": <float between 0.0 and 1.0>,
  "total_assertions": <integer>,
  "weak_count": <integer>,
  "weak_assertions": [{"line_hint": "<assertion code>", "reason": "<why weak>"}],
  "summary": "<one sentence>"
}
score = strong_count / total_assertions. If no assertions: score = 0.0
"""

def run(generated_file_path: str) -> EvalResult:
    path = Path(generated_file_path)
    if not path.exists():
        return EvalResult(name="Assertion Check", score=0.0, passed=False,
                         reason="File does not exist.", issues=[f"File not found: {generated_file_path}"])
    source_code = path.read_text(encoding="utf-8")
    if not source_code.strip():
        return EvalResult(name="Assertion Check", score=0.0, passed=False,
                         reason="File is empty.", issues=["Generated file has no content."])
    AgentConfig.validate()
    client = OpenAI(api_key=AgentConfig.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=AgentConfig.OPENAI_MODEL, temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Evaluate the assertions in this pytest test file:\n\n```python\n{source_code}\n```"}
        ]
    )
    data = json.loads(response.choices[0].message.content)
    score = float(data.get("score", 0.0))
    issues = [f"`{w['line_hint']}` — {w['reason']}" for w in data.get("weak_assertions", [])]
    return EvalResult(name="Assertion Check", score=round(score, 3),
                     passed=score >= 0.75, reason=data.get("summary", ""), issues=issues)
