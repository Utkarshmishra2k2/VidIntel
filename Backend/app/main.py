from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.documents import Document

from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ImportantMoment,
    QueryRequest,
    QueryResponse,
    SourceChunk,
    VideoMeta,
)
from app.utils.embedding import get_embedder
from app.utils.lang import detect_language_and_tone
from app.utils.logging import logger
from app.utils.playlist import PlaylistFetchError, get_playlist_videos
from app.utils.rag import generate_answer, retrieve_and_rerank
from app.utils.rate_limit import rate_limit
from app.utils.registry import get_resource, save_resource
from app.utils.resource import InvalidResourceError, parse_resource
from app.utils.summary import generate_analysis_extras
from app.utils.transcript import TranscriptUnavailableError, build_chunks, fetch_transcript
from app.utils.vector_store import get_vector_store, load_existing
from app.utils.youtube_meta import fetch_video_metadata, thumbnail_url
from config import config

app = FastAPI(
    title="YouTube RAG API",
    version="2.0.0",
    description="Ask questions about YouTube videos and playlists, grounded in their transcripts.",
    docs_url="/docs" if not config.PROD_MODE else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_ORIGIN] if config.PROD_MODE else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _format_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _snippet(text: str, max_len: int = 220) -> str:
    text = " ".join(text.split())
    return text if len(text) <= max_len else text[: max_len - 1].rstrip() + "…"


# ---------------------------------------------------------------------------
# POST /api/analyze
# ---------------------------------------------------------------------------

@app.post("/api/analyze", response_model=AnalyzeResponse, dependencies=[Depends(rate_limit)])
async def analyze_resource(request: AnalyzeRequest):
    """
    Paste a YouTube video/playlist URL or ID. Fetches metadata + transcripts,
    builds a searchable index, and generates a summary so the user has
    something useful to read immediately.
    """
    try:
        resource_type, resource_id = parse_resource(request.resource)
    except InvalidResourceError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    logger.info(f"Analyzing {resource_type} '{resource_id}'")

    if resource_type == "video":
        video_ids = [resource_id]
    else:
        try:
            video_ids = get_playlist_videos(resource_id)
        except PlaylistFetchError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    videos: List[VideoMeta] = []
    all_chunks: List[Document] = []
    warnings: List[str] = []

    for vid in video_ids:
        meta = fetch_video_metadata(vid)
        try:
            entries = fetch_transcript(vid)
            chunks = build_chunks(entries, vid)
            all_chunks.extend(chunks)
            videos.append(
                VideoMeta(
                    video_id=vid,
                    title=meta.title,
                    channel=meta.channel,
                    duration_seconds=meta.duration_seconds,
                    thumbnail_url=thumbnail_url(vid),
                    transcript_available=True,
                    chunk_count=len(chunks),
                )
            )
        except TranscriptUnavailableError as exc:
            warnings.append(f"{meta.title or vid}: {exc}")
            videos.append(
                VideoMeta(
                    video_id=vid,
                    title=meta.title,
                    channel=meta.channel,
                    duration_seconds=meta.duration_seconds,
                    thumbnail_url=thumbnail_url(vid),
                    transcript_available=False,
                    chunk_count=0,
                    error=str(exc),
                )
            )

    if not all_chunks:
        raise HTTPException(
            status_code=400,
            detail="Couldn't get a transcript for any video in this resource. "
            "It may have captions disabled, or be private/region-locked.",
        )

    embedder = get_embedder()
    try:
        get_vector_store(resource_id, all_chunks, embedder)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    save_resource(resource_id, resource_type, video_ids)

    extras = await generate_analysis_extras(all_chunks)

    logger.info(
        f"Analysis complete for {resource_id}: {len(all_chunks)} chunks, "
        f"{len(videos)} video(s), {len(warnings)} warning(s)"
    )

    return AnalyzeResponse(
        resource_id=resource_id,
        resource_type=resource_type,
        videos=videos,
        total_chunks=len(all_chunks),
        summary=extras["summary"] or None,
        key_takeaways=extras["key_takeaways"],
        suggested_questions=extras["suggested_questions"],
        important_moments=extras["important_moments"],
        status="ready" if not warnings else "partial",
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

@app.post("/api/query", response_model=QueryResponse, dependencies=[Depends(rate_limit)])
async def query_resource(request: QueryRequest):
    """Ask a question about an already-analyzed video/playlist."""
    record = get_resource(request.resource_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail="This video/playlist hasn't been analyzed yet. Please analyze it first.",
        )

    if request.video_id and request.video_id not in record["video_ids"]:
        raise HTTPException(status_code=400, detail="That video isn't part of this resource.")

    embedder = get_embedder()
    vector_store = load_existing(request.resource_id, embedder)
    if vector_store is None:
        raise HTTPException(
            status_code=404,
            detail="This resource's index is missing. Please analyze it again.",
        )

    try:
        lang_info = detect_language_and_tone(request.question)

        docs = retrieve_and_rerank(
            vector_store,
            request.question,
            current_time=request.current_time,
            video_id_filter=request.video_id,
        )
        if not docs:
            raise ValueError(
                "I couldn't find anything relevant to that question in this video's transcript."
            )

        history_str = (
            "\n".join(f"{m.role.capitalize()}: {m.content}" for m in (request.history or []))
            or "This is the beginning of the conversation."
        )
        context = "\n\n".join(
            f"[{d.metadata.get('video_id')} @ {_format_time(d.metadata.get('start', 0.0))}] {d.page_content}"
            for d in docs
        )

        answer = await generate_answer(lang_info, history_str, context, request.question)

        sources = [
            SourceChunk(
                video_id=d.metadata.get("video_id", ""),
                start=round(float(d.metadata.get("start", 0.0)), 2),
                end=round(float(d.metadata.get("end", 0.0)), 2),
                snippet=_snippet(d.page_content),
            )
            for d in docs
        ]

        return QueryResponse(answer=answer, sources=sources, resource_id=request.resource_id)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"Query failed for {request.resource_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Something went wrong answering that question. Please try again.")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}
