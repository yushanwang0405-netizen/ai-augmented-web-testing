"""
R01 — RAGAS Eval for Astra's RAG pipeline.

Tests two things:
  1. Is Stage 2 (retriever) fetching the RIGHT context?
  2. Is Stage 3 (generator) staying FAITHFUL to that context?

Run: python -m evals.rag.r01_ragas_eval
"""

# ── Imports ───────────────────────────────────────────────────────────────────

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# datasets is a HuggingFace library — ragas 0.1.x uses it as its data container
from datasets import Dataset

# ragas 0.1.x: metrics are imported as pre-built instances (lowercase)
# NOT as classes like Faithfulness() — that's the 0.4.x API
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
)

# Astra's own modules
from ai_agent.models import TestSpec, InputSource
from ai_agent.stage2_context_retrieval.retriever import Retriever
from ai_agent.stage3_generator.generator_agent import GeneratorAgent

# ── Environment ───────────────────────────────────────────────────────────────

# Load .env so OPENAI_API_KEY is available
# RAGAS uses OpenAI internally as its judge — same key Astra already uses
load_dotenv(Path(__file__).parent.parent.parent / "ai_agent" / ".env")

# ── Ground Truth (Reference) ──────────────────────────────────────────────────

# This is the IDEAL test we would want Astra to generate.
# We write this once by hand. RAGAS uses it to measure Context Recall:
# "Did the retriever fetch everything needed to produce THIS test?"
REFERENCE = """
def test_search_returns_results(page, home_page):
    home_page.navigate()
    home_page.search("Accenture")
    results = home_page.get_search_results()
    assert len(results) > 0

def test_search_empty_query(page, home_page):
    home_page.navigate()
    home_page.search("")
    results = home_page.get_search_results()
    assert results == [] or home_page.is_empty_state_visible()
""".strip()

# ── User Story ────────────────────────────────────────────────────────────────

USER_STORY = """
As a user I want to search for companies on the home page.

Acceptance Criteria:
1. Searching for a company name returns relevant results.
2. Searching with an empty query shows an empty state or no results.
3. The search bar is visible on the home page without scrolling.
"""


def build_spec() -> TestSpec:
    """Build a TestSpec from the user story above."""
    return TestSpec(
        source=InputSource.TEXT,
        source_id="RAGAS-EVAL-001",
        title="Search for companies",
        description=USER_STORY,
        acceptance_criteria=[
            "Searching for a company name returns relevant results.",
            "Searching with an empty query shows an empty state or no results.",
            "The search bar is visible on the home page without scrolling.",
        ],
        affected_pages=["home_page"],
        raw_content=USER_STORY,
    )


def run_eval():
    print("=" * 60)
    print("R01 — RAGAS Eval: Astra RAG Pipeline")
    print("=" * 60)

    # ── Step 1: Build the input ───────────────────────────────────────────────
    spec = build_spec()
    print(f"\n[1] User story: {spec.title}")

    # ── Step 2: Run Stage 2 — Retriever ──────────────────────────────────────
    print("\n[2] Running Stage 2 retriever...")
    retriever = Retriever()
    retrieval = retriever.retrieve(
        query=spec.description,
        affected_pages=spec.affected_pages,
    )

    # retrieval.all_chunks() = page_object_methods + similar_tests + knowledge
    # .text gives us the raw string content of each chunk
    # We build a LIST OF STRINGS — one string per chunk
    retrieved_contexts = [chunk.text for chunk in retrieval.all_chunks()]

    print(f"    Retrieved {len(retrieved_contexts)} chunks:")
    for i, chunk in enumerate(retrieval.all_chunks()):
        print(f"      [{i+1}] {chunk.short_label()} ({chunk.collection})")

    # ── Step 3: Run Stage 3 — Generator ──────────────────────────────────────
    print("\n[3] Running Stage 3 generator (dry_run=True)...")
    generator = GeneratorAgent()
    result = generator.generate(spec, retrieval, dry_run=True)

    if not result.success:
        print(f"    Generation failed: {result.error}")
        sys.exit(1)

    generated_code = result.code
    print(f"    Generated {len(generated_code.splitlines())} lines of code")

    # ── Step 4: Build the RAGAS dataset ──────────────────────────────────────
    # ragas 0.1.x uses a HuggingFace Dataset, not SingleTurnSample.
    # Each key maps to a LIST — one item per sample.
    # We have one sample, so every list has exactly one element.
    #
    # CRITICAL: contexts must be a list of LISTS.
    # Wrong:   "contexts": ["chunk1", "chunk2"]          ← flat list
    # Correct: "contexts": [["chunk1", "chunk2"]]        ← list of lists
    #
    # Why? Because you might have multiple samples (questions).
    # Each sample gets its own list of chunks.
    # We have 1 sample → 1 outer list → [our_chunks_list]
    print("\n[4] Building RAGAS dataset...")
    dataset = Dataset.from_dict({
        "question":     [USER_STORY],
        "answer":       [generated_code],
        "contexts":     [retrieved_contexts],   # list of lists — [[chunk1, chunk2, ...]]
        "ground_truth": [REFERENCE],
    })

    print(f"    Dataset: 1 sample, {len(retrieved_contexts)} context chunks")

    # ── Step 5: Run RAGAS ─────────────────────────────────────────────────────
    # evaluate() calls OpenAI internally as the judge.
    # It scores each metric and returns a Result object with a .to_pandas() method.
    print("\n[5] Running RAGAS evaluation (calls OpenAI as judge)...")
    print("    This may take 30-60 seconds...")

    scores = evaluate(
        dataset,
        metrics=[
            faithfulness,        # did generator stay honest to context?
            answer_relevancy,    # did generator answer the right question?
            context_recall,      # did retriever fetch everything needed?
            context_precision,   # was everything retrieved actually useful?
        ],
    )

    # ── Step 6: Print results ─────────────────────────────────────────────────
    df = scores.to_pandas()

    f  = df["faithfulness"].iloc[0]
    ar = df["answer_relevancy"].iloc[0]
    cr = df["context_recall"].iloc[0]
    cp = df["context_precision"].iloc[0]

    print("\n" + "=" * 60)
    print("RAGAS SCORES")
    print("=" * 60)
    print(f"\n  Faithfulness      : {f:.2f}  (Stage 3 honest to retrieved context?)")
    print(f"  Answer Relevancy  : {ar:.2f}  (Stage 3 answered the right question?)")
    print(f"  Context Recall    : {cr:.2f}  (Stage 2 fetched everything needed?)")
    print(f"  Context Precision : {cp:.2f}  (Stage 2 fetched without noise?)")

    print("\nDIAGNOSIS:")
    issues = []
    if f  < 0.8: issues.append("  ⚠ Faithfulness low    → Stage 3 hallucinating beyond context")
    if ar < 0.8: issues.append("  ⚠ Answer Relevancy low → Stage 3 generating off-topic code")
    if cr < 0.8: issues.append("  ⚠ Context Recall low   → Stage 2 missing needed chunks")
    if cp < 0.8: issues.append("  ⚠ Context Precision low → Stage 2 fetching noisy chunks")
    if issues:
        for issue in issues: print(issue)
    else:
        print("  ✓ All metrics above 0.8 — RAG pipeline is healthy")

    print("=" * 60)


if __name__ == "__main__":
    run_eval()
