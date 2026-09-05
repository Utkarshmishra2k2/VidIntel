"""
FAISS vector store, cached per resource_id both in-process and on disk.

Fix vs. the original: the old code cached an index on disk forever with no
way to tell it was stale. Here we also persist a small signature file
(the sorted list of video_ids + chunk count that produced the index). If a
later request for the same resource_id resolves to a different set of
videos or chunk count (e.g. a playlist changed, or a transcript that
previously failed now succeeds), the index is rebuilt instead of silently
serving stale content.

For a single self-hosted user, FAISS-on-disk is a fine choice; the comment
in the original code about migrating to a hosted vector DB for large-scale
multi-tenant deployments still applies but isn't needed here.
"""
import json
import os
import shutil
from typing import List

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.utils.logging import logger
from config import config

_MEMORY_CACHE: dict[str, FAISS] = {}


def _signature(documents: List[Document]) -> dict:
    video_ids = sorted({d.metadata.get("video_id", "") for d in documents})
    return {"video_ids": video_ids, "chunk_count": len(documents)}


def _index_dir(resource_id: str) -> str:
    return os.path.join(config.FAISS_INDEX_PATH, resource_id)


def get_vector_store(resource_id: str, documents: List[Document], embedder) -> FAISS:
    if not documents:
        raise ValueError("No transcript content to index.")

    sig = _signature(documents)
    index_dir = _index_dir(resource_id)
    sig_path = os.path.join(index_dir, "signature.json")

    if resource_id in _MEMORY_CACHE:
        logger.debug(f"Vector store cache hit (memory) for {resource_id}")
        return _MEMORY_CACHE[resource_id]

    if os.path.exists(index_dir) and os.path.exists(sig_path):
        try:
            with open(sig_path, "r", encoding="utf-8") as f:
                cached_sig = json.load(f)
        except (json.JSONDecodeError, OSError):
            cached_sig = None

        if cached_sig == sig:
            logger.debug(f"Vector store cache hit (disk) for {resource_id}")
            store = FAISS.load_local(
                index_dir,
                embeddings=embedder,
                allow_dangerous_deserialization=True,  # index is written by this app, not user-uploaded
            )
            _MEMORY_CACHE[resource_id] = store
            return store

        logger.info(f"Vector store stale for {resource_id}, rebuilding")
        shutil.rmtree(index_dir, ignore_errors=True)

    logger.info(f"Building new vector store for {resource_id} ({len(documents)} chunks)")
    os.makedirs(index_dir, exist_ok=True)
    store = FAISS.from_documents(documents, embedder)
    store.save_local(index_dir)
    with open(sig_path, "w", encoding="utf-8") as f:
        json.dump(sig, f)

    _MEMORY_CACHE[resource_id] = store
    return store


def has_vector_store(resource_id: str) -> bool:
    return resource_id in _MEMORY_CACHE or os.path.exists(_index_dir(resource_id))


def load_existing(resource_id: str, embedder) -> "FAISS | None":
    """Load a previously-built index without needing the source documents
    (used at query time, when we already know analysis succeeded)."""
    if resource_id in _MEMORY_CACHE:
        return _MEMORY_CACHE[resource_id]

    index_dir = _index_dir(resource_id)
    if not os.path.exists(index_dir):
        return None

    store = FAISS.load_local(index_dir, embeddings=embedder, allow_dangerous_deserialization=True)
    _MEMORY_CACHE[resource_id] = store
    return store
