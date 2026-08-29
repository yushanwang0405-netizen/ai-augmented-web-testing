"""
Generator Agent: orchestrates the full generation loop.

Flow:
  1. Build prompt from TestSpec + RetrievalResult
  2. Call GPT-4o with function-calling tools enabled
  3. GPT-4o calls tools (list_page_methods, get_fixtures, read_file, search_context)
     to ground itself before writing code
  4. GPT-4o outputs raw Python test code
  5. Extract and validate the generated code
  6. Return GenerationResult

The agentic loop continues until GPT-4o stops calling tools (finish_reason=stop).
Max 10 tool rounds to prevent infinite loops.
"""
import re
import ast
import json
from dataclasses import dataclass, field
from pathlib import Path

from openai import OpenAI

from ai_agent.config import AgentConfig
from ai_agent.models import TestSpec
from ai_agent.stage2_context_retrieval.retriever import RetrievalResult
from ai_agent.stage3_generator.prompt_builder import SYSTEM_PROMPT, build_user_message
from ai_agent.stage3_generator.tools import TOOL_SCHEMAS, dispatch_tool


MAX_TOOL_ROUNDS = 10
PROJECT_ROOT    = Path(__file__).parent.parent.parent


@dataclass
class GenerationResult:
    success:        bool
    code:           str                  = ""
    filepath:       str                  = ""
    tool_calls_made: list[str]           = field(default_factory=list)
    conflicts:      list[str]            = field(default_factory=list)
    warnings:       list[str]            = field(default_factory=list)
    error:          str                  = ""
    tokens_used:    int                  = 0

    def is_conflict(self) -> bool:
        return bool(self.conflicts)


class GeneratorAgent:

    def __init__(self):
        AgentConfig.validate()
        self.client = OpenAI(
            api_key=AgentConfig.OPENAI_API_KEY,
            base_url=AgentConfig.OPENAI_BASE_URL,
        )

    # ── Public API ─────────────────────────────────────────────────────────

    def generate(
        self,
        spec:      TestSpec,
        retrieval: RetrievalResult,
        dry_run:   bool = False,        # if True, don't write to disk
    ) -> GenerationResult:
        """
        Generate pytest test code for the given TestSpec using retrieved context.

        Args:
            spec:      Parsed ticket / excel / text test specification
            retrieval: Retrieved codebase context from Stage 2
            dry_run:   If True, return code without writing to file

        Returns:
            GenerationResult with generated code, file path, and metadata
        """
        # If conflicts were detected in retrieval, stop and report
        if retrieval.has_conflicts():
            return GenerationResult(
                success=False,
                conflicts=[
                    f"{c['topic']}: {c['source_a']} vs {c['source_b']} — {c['difference']}"
                    for c in retrieval.conflicts
                ],
                error="Conflicting context detected. Human review needed before generation.",
            )

        user_message  = build_user_message(spec, retrieval)
        messages      = [
            {"role": "system",  "content": SYSTEM_PROMPT},
            {"role": "user",    "content": user_message},
        ]
        tool_calls_made = []
        total_tokens    = 0
        raw_code        = ""

        # ── Agentic tool loop ──────────────────────────────────────────────
        for round_num in range(MAX_TOOL_ROUNDS):
            response = self.client.chat.completions.create(
                model=AgentConfig.OPENAI_MODEL,
                max_tokens=8096,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                messages=messages,
            )
            choice       = response.choices[0]
            total_tokens += response.usage.prompt_tokens + response.usage.completion_tokens

            # ── Done — no more tool calls ──────────────────────────────────
            if choice.finish_reason == "stop":
                raw_code = (choice.message.content or "").strip()
                break

            # ── Model wants to call tools ──────────────────────────────────
            elif choice.finish_reason == "tool_calls":
                # Append the assistant message (with tool_calls) to history
                messages.append(choice.message)

                # Execute each tool call and add tool-result messages
                for tc in choice.message.tool_calls:
                    tool_name   = tc.function.name
                    tool_inputs = json.loads(tc.function.arguments)
                    tool_calls_made.append(f"{tool_name}({tool_inputs})")

                    result = dispatch_tool(tool_name, tool_inputs)

                    messages.append({
                        "role":         "tool",
                        "tool_call_id": tc.id,
                        "content":      result,
                    })

            else:
                # length, content_filter, etc.
                break

        # ── Parse the generated code ───────────────────────────────────────
        if not raw_code:
            return GenerationResult(
                success=False,
                error="Model returned empty output after tool loop.",
                tool_calls_made=tool_calls_made,
                tokens_used=total_tokens,
            )

        # Detect conflict report
        if raw_code.strip().startswith("CONFLICT:"):
            conflict_lines = [l for l in raw_code.splitlines() if l.strip()]
            return GenerationResult(
                success=False,
                conflicts=conflict_lines,
                error="Model detected conflicts and stopped generation.",
                tool_calls_made=tool_calls_made,
                tokens_used=total_tokens,
            )

        # Clean up any accidental markdown fences
        code = _strip_markdown(raw_code)

        # Validate Python syntax
        syntax_error = _check_syntax(code)
        if syntax_error:
            preview = repr(code[:500])

            return GenerationResult(
                success=False,
                code=code,
                error=(
                    f"Syntax error in generated code: {syntax_error}\n"
                    f"Generated code preview: {preview}"
                ),
                tool_calls_made=tool_calls_made,
                tokens_used=total_tokens,
            )

        # Validate generated test completeness
        completeness_error = _check_test_completeness(code)
        if completeness_error:
            return GenerationResult(
                success=False,
                code=code,
                error=completeness_error,
                tool_calls_made=tool_calls_made,
                tokens_used=total_tokens,
            )

        # Determine output file path
        filepath = _determine_filepath(spec)

        # Write to disk unless dry_run
        if not dry_run:
            out = PROJECT_ROOT / filepath
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(code, encoding="utf-8")

        warnings = []
        if retrieval.stale_warnings:
            warnings.extend(retrieval.stale_warnings)

        return GenerationResult(
            success=True,
            code=code,
            filepath=filepath,
            tool_calls_made=tool_calls_made,
            warnings=warnings,
            tokens_used=total_tokens,
        )


# ── Helpers ──────────────────────────────────────────────────────────────────

def _strip_markdown(text: str) -> str:
    """Extract Python code from an LLM response and discard surrounding prose."""
    text = text.strip()

    # Case 1: Python fenced code block, possibly surrounded by prose.
    if "```python" in text:
        code = text.split("```python", 1)[1]
        code = code.split("```", 1)[0]
        return code.strip()

    # Case 2: Generic fenced code block.
    if "```" in text:
        code = text.split("```", 1)[1]
        code = code.split("```", 1)[0]
        return code.strip()

    # Case 3: Plain Python preceded by explanatory prose.
    common_python_starts = [
        "import pytest",
        "import allure",
        "from ",
        "import ",
    ]

    positions = [
        text.find(marker)
        for marker in common_python_starts
        if text.find(marker) != -1
    ]

    if positions:
        return text[min(positions):].strip()

    # Fall back to the original response.
    return text

def _check_syntax(code: str) -> str | None:
    """Return a syntax error message, or None if code is valid Python."""
    try:
        ast.parse(code)
        return None
    except SyntaxError as e:
        return f"Line {e.lineno}: {e.msg}"

def _check_test_completeness(code: str) -> str | None:
    """Validate that generated code contains a pytest test and assertion."""
    tree = ast.parse(code)

    test_functions = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]

    if not test_functions:
        return "Generated code contains no pytest test function."

    has_assert = any(
        isinstance(node, ast.Assert)
        for func in test_functions
        for node in ast.walk(func)
    )

    if not has_assert:
        return "Generated test contains no assertion."

    return None


def _determine_filepath(spec: TestSpec) -> str:
    """
    Determine where to write the generated test file.
    Uses affected_pages[0] to name the file.
    """
    from ai_agent.models import InputSource

    if spec.affected_pages:
        page = spec.affected_pages[0].lower().replace(" ", "_")
        # Don't overwrite existing test files — add _generated suffix
        base = f"tests/ambitionbox/test_{page}_generated.py"
    elif spec.source == InputSource.EXCEL:
        base = "tests/ambitionbox/test_generated_from_excel.py"
    else:
        safe_id = re.sub(r"[^a-z0-9_]", "_", spec.source_id.lower())
        base = f"tests/ambitionbox/test_{safe_id}_generated.py"

    return base
