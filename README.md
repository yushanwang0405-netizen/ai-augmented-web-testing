# AI-Augmented Web Automation Testing Framework

基于 **Python + Pytest + Playwright** 的 AI 辅助 Web 自动化测试项目，在传统 Web 自动化测试框架基础上，引入 **LLM、RAG 与 Agent**，实现从自然语言测试需求到 Pytest 自动化脚本生成与执行的完整链路。

> 本项目基于开源项目 Astra AI Automation Agent 进行二次开发，重点扩展 Web 自动化测试实践，并针对 AI 测试生成过程中的代码幻觉、输出不稳定及生成质量问题进行了优化。

## 1. Project Overview

传统 Web 自动化测试通常需要测试人员根据需求手动分析测试场景、查找页面对象并编写测试脚本。

本项目在保留传统自动化测试能力的基础上，构建 AI 辅助测试生成流程：

**自然语言需求 → TestSpec → RAG 代码检索 → Agent 工具调用 → Pytest 脚本生成 → Quality Gate → Playwright 执行**

主要包含两部分：

- **传统 Web 自动化测试**
  - Pytest 测试组织
  - Playwright 浏览器自动化
  - Page Object / Component 封装
  - Fixture 环境与对象管理
  - 参数化测试与断言

- **AI 辅助测试生成**
  - LLM 需求解析
  - RAG 代码库语义检索
  - Agent Tool Calling
  - Pytest 脚本生成
  - AST 生成质量校验

---

## 2. Tech Stack

| Category | Technology |
| --- | --- |
| Language | Python |
| Test Framework | Pytest |
| Web Automation | Playwright |
| Design | Page Object / Component |
| LLM | OpenAI-compatible API / OpenRouter |
| RAG | ChromaDB + Embedding |
| AI Workflow | LLM + RAG + Agent Tool Calling |
| Validation | Python AST |
| Reporting | Allure |

---

## 3. Architecture

```text
Natural Language Requirement
            │
            ▼
┌─────────────────────────┐
│ Stage 1: Ticket Parser  │
│ Requirement → TestSpec  │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────────┐
│ Stage 2: Context Retrieval  │
│ RAG retrieves relevant      │
│ Pages / Components / Tests  │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────┐
│ Stage 3: Test Generator │
│ LLM + Agent Tool Calls  │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Generation Quality Gate │
│ Clean / Syntax / AST    │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Pytest + Playwright     │
│ Execute Generated Tests │
└─────────────────────────┘
```

---

## 4. Traditional Web Automation

The traditional automation layer is built with **Pytest + Playwright**.

Example test scenarios include:

- Search bar visibility
- Text input
- Input clearing
- Parameterized input validation
- Boundary and abnormal input scenarios

Reusable page operations are encapsulated in Page/Component objects, while Pytest Fixtures manage browser and page dependencies.

Example:

```python
@pytest.mark.parametrize("query", [
    "Accenture",
    "TCS",
    "A",
])
def test_search_bar_accepts_different_inputs(
        self, home_page, search_bar, query):

    search_bar.fill(query)

    assert search_bar.get_current_value() == query
```

This separates:

```text
Test        → What should be tested?
Fixture     → What environment/objects are required?
Page/Component → How should the browser interact with the page?
```

---

## 5. AI-Assisted Test Generation

### Stage 1 — Requirement Parsing

Natural-language testing requirements are converted into structured `TestSpec` objects.

Example input:

```text
Test that the search bar accepts user input and can be cleared
```

Instead of directly asking the LLM to generate arbitrary code, the structured TestSpec provides explicit testing context for subsequent stages.

### Stage 2 — RAG Context Retrieval

The project codebase, existing tests and testing knowledge are indexed into a vector database.

For each requirement, RAG retrieves relevant context such as:

- Page Objects
- Components
- Fixtures
- Existing tests
- Testing knowledge

This allows generated tests to reference the **actual project implementation** rather than relying only on the LLM's prior knowledge.

### Stage 3 — Agent-Based Generation

The Agent can inspect the existing framework through tools such as:

```text
get_fixtures
list_page_methods
read_file
```

Retrieved context and tool results are then used to generate Pytest tests compatible with the existing project structure.

---

## 6. Generation Quality Improvements

During implementation and testing, several common LLM generation problems were identified and addressed.

### 6.1 Page/Object Hallucination

Problem:

The LLM could infer nonexistent page objects from UI elements, for example treating a search bar as a separate `search_page`.

Solution:

Added grounding constraints to the requirement parser:

- Page names must follow existing codebase conventions
- Pages are included only when explicitly stated or clearly implied
- Unknown pages are not invented

### 6.2 Unstable LLM Output

Problem:

Some model responses contained explanatory prose or Markdown fences around Python code, causing generated files to fail syntax validation.

Solution:

Added output sanitization to extract valid Python code before validation and execution.

### 6.3 Incomplete Test Generation

Problem:

A response containing only imports such as:

```python
import pytest
import allure
```

is syntactically valid Python but is not a valid test case.

Solution:

Added an **AST-based quality gate** to validate that generated code contains:

- Valid Python syntax
- At least one `test_*` function
- At least one assertion

This prevents syntactically valid but functionally incomplete outputs from being treated as successful test generation.

---

## 7. Project Structure

```text
ai_agent/
├── stage1_ticket_parser/       # Requirement → TestSpec
├── stage2_context_retrieval/   # RAG indexing and retrieval
├── stage3_generator/           # Agent-based test generation
├── knowledge/                  # Testing knowledge base
└── cli.py

components/                     # Reusable UI components
core/                           # Browser / driver abstraction
pages/                          # Page Objects
tests/                          # Pytest test cases
utils/                          # Configuration and utilities
conftest.py                     # Shared Pytest fixtures
pytest.ini
```

---

## 8. Example Workflow

Generate tests from a natural-language requirement:

```bash
python -m ai_agent.cli \
  --text "Test that the search bar accepts user input and can be cleared" \
  --generate
```

The workflow performs:

```text
Requirement Parsing
        ↓
RAG Context Retrieval
        ↓
Agent Tool Calling
        ↓
Pytest Generation
        ↓
Syntax & Completeness Validation
        ↓
Generated Test File
```

Generated tests can then be executed with Pytest:

```bash
pytest tests/ambitionbox/test_text_input_generated.py -v
```

---

## 9. Key Improvements in This Fork

Compared with the upstream project, this fork focuses on improving **practical AI-assisted Web testing and generation reliability**, including:

- Added configurable LLM endpoint support for OpenAI-compatible APIs
- Extended traditional Pytest + Playwright search interaction tests
- Added reusable search input and clearing operations
- Improved requirement grounding to reduce page-object hallucination
- Added safeguards for empty LLM responses
- Improved generated-output sanitization
- Added AST-based generated-test completeness validation
- Improved syntax-error diagnostics
- Improved fixture teardown robustness when browser setup fails
- Validated the full requirement → retrieval → generation → execution workflow

---

## 10. Acknowledgements

This project is based on the open-source **Astra AI Automation Agent** project and has been extended for learning and practice in AI-assisted software testing.

Original project:

https://github.com/karishmakoul/astra-ai-automation-agent