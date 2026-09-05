"""
Embedding model + cross-encoder reranker.

Both are expensive to load, so they're cached process-wide with
`functools.lru_cache` instead of being re-instantiated on every request
(the original code re-created them per query, which was slow and wasteful).
"""
from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder

from app.utils.logging import logger
from config import config


@lru_cache(maxsize=1)
def get_embedder() -> HuggingFaceEmbeddings:
    logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
    return HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},  # set to "cuda" if a GPU is available
        encode_kwargs={"normalize_embeddings": True},
    )


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    logger.info(f"Loading reranker model: {config.RERANKER_MODEL}")
    return CrossEncoder(config.RERANKER_MODEL)
