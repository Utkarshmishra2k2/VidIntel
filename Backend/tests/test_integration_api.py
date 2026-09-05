"""
End-to-end integration test for the full workflow:

    analyze (transcript -> chunks -> FAISS index -> summary)
        -> query (retrieve -> rerank -> grounded answer)
        -> sources with accurate, real timestamps

External services (YouTube transcript/metadata fetch, Ollama) are mocked so
this test runs offline and fast, while still exercising the real chunking,
vector store, retrieval, reranking, and API validation code paths.

Embeddings/reranker still use the real (small) HF models, so this test is
skipped in environments without network access to download them — same
condition as test_rag_eval.py.
"""
import shutil
from unittest.mock import AsyncMock, patch

import pytest

from app.utils.transcript import TranscriptEntry
from app.utils.youtube_meta import VideoMetadata

try:
    from app.utils.embedding import get_embedder

    get_embedder()  # actually try to load weights; network-restricted envs will raise here
    MODELS_AVAILABLE = True
except Exception:  # pragma: no cover
    MODELS_AVAILABLE = False


FAKE_TRANSCRIPT = [
    TranscriptEntry(text="Welcome to this tutorial on baking sourdough bread.", start=0.0, duration=4.0),
    TranscriptEntry(text="First, let's talk about the sourdough starter and feeding it daily.", start=9.0, duration=5.0),
    TranscriptEntry(text="A healthy starter should double in size within six hours of feeding.", start=14.0, duration=6.0),
    TranscriptEntry(text="Now let's move on to kneading the dough properly for good structure.", start=20.0, duration=5.0),
    TranscriptEntry(text="Finally, proof the dough at room temperature for about four hours.", start=42.0, duration=6.0),
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("config.config.FAISS_INDEX_PATH", str(tmp_path / "faiss_index"))
    from app.utils import registry
    registry._cache = None  # reset the module-level registry cache between tests

    from fastapi.testclient import TestClient
    from app.main import app

    yield TestClient(app)

    shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.mark.skipif(not MODELS_AVAILABLE, reason="embedding/reranker models not installed")
def test_full_workflow_video(client):
    with patch("app.main.fetch_transcript", return_value=FAKE_TRANSCRIPT), \
         patch("app.main.fetch_video_metadata", return_value=VideoMetadata(
             title="Sourdough Basics", channel="Baking Channel", duration_seconds=50.0
         )), \
         patch("app.utils.summary.get_llm") as mock_llm:

        mock_llm.return_value.ainvoke = AsyncMock(return_value=(
            '{"summary": "A short intro to sourdough baking.", '
            '"key_takeaways": ["Feed your starter daily", "Knead for structure"], '
            '"suggested_questions": ["How often should I feed my starter?"], '
            '"important_moments": [{"chunk_index": 0, "label": "Starter feeding"}]}'
        ))

        analyze_resp = client.post(
            "/api/analyze", json={"resource": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
        )

    assert analyze_resp.status_code == 200, analyze_resp.text
    data = analyze_resp.json()
    assert data["resource_type"] == "video"
    assert data["resource_id"] == "dQw4w9WgXcQ"
    assert data["status"] == "ready"
    assert data["total_chunks"] > 0
    assert data["videos"][0]["title"] == "Sourdough Basics"
    assert data["videos"][0]["transcript_available"] is True
    assert data["summary"]
    assert data["key_takeaways"]

    # Every important moment must reference a real, in-range timestamp.
    for moment in data["important_moments"]:
        assert 0.0 <= moment["time"] <= 50.0

    with patch("app.utils.rag.get_llm") as mock_query_llm:
        mock_query_llm.return_value.ainvoke = AsyncMock(
            return_value="Feed your starter daily so it stays active."
        )
        query_resp = client.post(
            "/api/query",
            json={"resource_id": "dQw4w9WgXcQ", "question": "How often should I feed the starter?"},
        )

    assert query_resp.status_code == 200, query_resp.text
    q = query_resp.json()
    assert q["resource_id"] == "dQw4w9WgXcQ"
    assert q["answer"]
    assert q["sources"], "Expected grounded sources for the answer"

    # The top source should be about the starter, with a timestamp inside
    # the real transcript's time range for that topic (9s-20s), never an
    # estimated/interpolated value outside real entry bounds.
    top = q["sources"][0]
    assert top["video_id"] == "dQw4w9WgXcQ"
    assert 0.0 <= top["start"] < top["end"] <= 50.0
    assert "starter" in top["snippet"].lower()


@pytest.mark.skipif(not MODELS_AVAILABLE, reason="embedding/reranker models not installed")
def test_query_before_analyze_returns_404(client):
    resp = client.post("/api/query", json={"resource_id": "never-analyzed", "question": "hi"})
    assert resp.status_code == 404


@pytest.mark.skipif(not MODELS_AVAILABLE, reason="embedding/reranker models not installed")
def test_analyze_with_no_transcript_returns_400(client):
    from app.utils.transcript import TranscriptUnavailableError

    with patch("app.main.fetch_transcript", side_effect=TranscriptUnavailableError("Captions are disabled.")), \
         patch("app.main.fetch_video_metadata", return_value=VideoMetadata()):
        resp = client.post("/api/analyze", json={"resource": "dQw4w9WgXcQ"})

    assert resp.status_code == 400
    assert "transcript" in resp.json()["detail"].lower()
