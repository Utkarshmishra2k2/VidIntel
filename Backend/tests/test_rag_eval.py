"""
A small retrieval-accuracy evaluation.

This builds a real FAISS index (using the actual embedding + reranker models
configured in config.py) over the synthetic sourdough-bread transcript and
checks that each question in EVAL_DATASET retrieves a chunk:
  1. from the expected topic (keyword check), and
  2. whose timestamp falls inside the expected real time range.

This requires downloading the embedding/reranker models on first run (needs
network access to Hugging Face), so it's skipped automatically in
environments without them — it's meant to be run locally / in CI with
dependencies fully installed, e.g.:

    pytest tests/test_rag_eval.py -q
"""
import pytest

from app.utils.transcript import build_chunks

try:
    from app.utils.embedding import get_embedder, get_reranker
    from app.utils.rag import retrieve_and_rerank
    from langchain_community.vectorstores import FAISS

    MODELS_AVAILABLE = True
except Exception:  # pragma: no cover - environment-dependent
    MODELS_AVAILABLE = False


# (question, expected keyword in the retrieved chunk, expected [min_start, max_end] time range)
EVAL_DATASET = [
    ("How often should I feed my sourdough starter?", "starter", (9.0, 20.0)),
    ("What does kneading do to the dough?", "gluten", (20.0, 31.0)),
    ("How long should I proof the dough overnight?", "proof", (36.0, 48.0)),
]


@pytest.mark.skipif(not MODELS_AVAILABLE, reason="embedding/reranker models not installed")
def test_retrieval_returns_correct_topic_and_timestamp(sample_entries):
    chunks = build_chunks(sample_entries, video_id="bread101", max_chars=90)

    try:
        embedder = get_embedder()
    except Exception as exc:  # pragma: no cover - no network in this environment
        pytest.skip(f"Could not load embedding model (likely no network): {exc}")

    store = FAISS.from_documents(chunks, embedder)

    for question, keyword, (min_start, max_end) in EVAL_DATASET:
        results = retrieve_and_rerank(store, question, k_retrieve=6, k_final=1)
        assert results, f"No results for: {question}"
        top = results[0]

        assert keyword.lower() in top.page_content.lower(), (
            f"Expected keyword '{keyword}' in top result for '{question}', "
            f"got: {top.page_content!r}"
        )
        assert min_start <= top.metadata["start"] <= max_end, (
            f"Timestamp {top.metadata['start']} out of expected range "
            f"[{min_start}, {max_end}] for '{question}'"
        )
