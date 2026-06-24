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

KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "ai_agent" / "knowledge"

SYSTEM_PROMPT = """
You are a senior QA engineer reviewing AI-generated pytest test code.
You have deep knowledge of the application's navigation flows, provided in CONTEXT.

CHECK THESE 5 THINGS FOR EACH TEST FUNCTION:

1. CORRECT PAGE ENTERED FIRST — right fixture or URL used before anything else
2. CORRECT ORDER — navigate → interact → assert. Never assert before navigating.
3. PAGE-SPECIFIC RULES (check CONTEXT carefully):
   - Home page: overlay must be dismissed before any interaction
   - Salary page: salary figures require login — must handle login wall
   - Companies page: search/open must happen before applying filters
   - Reviews page: extra 2s wait needed after page load
4. RIGHT FIXTURE FOR THE PAGE — each page has a designated fixture in CONTEXT
5. UNKNOWN FLOW DETECTION — if test navigates to page/section not in CONTEXT yaml,
   flag as UNVERIFIABLE (score 0.5, needs_human_review: true)

SCORING:
  1.0  = all checks pass
  0.75 = 1 minor violation
  0.5  = 1 major violation OR unverifiable flow found
  0.25 = multiple major violations
  0.0  = completely wrong flow

Respond ONLY in this JSON format:
{
  "score": <float 0.0 to 1.0>,
  "flow_issues": [
    {"function": "<name>", "violation": "<ORDER/PAGE/RULES/FIXTURE/UNKNOWN_FLOW>",
     "detail": "<what is wrong>", "needs_human_review": <true/false>}
  ],
  "summary": "<one sentence>"
}
"""

def run(generated_file_path: str) -> EvalResult:
    path = Path(generated_file_path)
    if not path.exists():
        return EvalResult(name="Flow Check", score=0.0, passed=False,
                         reason="File does not exist.", issues=[f"File not found: {generated_file_path}"])
    generated_code = path.read_text(encoding="utf-8")
    nav_flows_path = KNOWLEDGE_DIR / "navigation_flows.yaml"
    if not nav_flows_path.exists():
        return EvalResult(name="Flow Check", score=0.0, passed=False,
                         reason="navigation_flows.yaml not found.",
                         issues=["Cannot evaluate flow without navigation knowledge."])
    navigation_context = nav_flows_path.read_text(encoding="utf-8")
    AgentConfig.validate()
    client = OpenAI(api_key=AgentConfig.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=AgentConfig.OPENAI_MODEL, temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"CONTEXT — Application Navigation Flows:\n```yaml\n{navigation_context}\n```\n\n"
                f"TEST CODE TO EVALUATE:\n```python\n{generated_code}\n```\n\n"
                f"Evaluate the navigation flow of each test function."
            )}
        ]
    )
    data = json.loads(response.choices[0].message.content)
    score = float(data.get("score", 0.0))
    issues = []
    for item in data.get("flow_issues", []):
        prefix = "⚠ HUMAN REVIEW" if item.get("needs_human_review") else "✗"
        issues.append(f"{prefix} [{item['function']}] {item['violation']} — {item['detail']}")
    return EvalResult(name="Flow Check", score=round(score, 3),
                     passed=score >= 0.75, reason=data.get("summary", ""), issues=issues)
