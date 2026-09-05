"""
Shared, cached Ollama LLM client. Every part of the app (query answering,
summary generation) uses this one instance instead of constructing a new
client per call.
"""
from functools import lru_cache

from langchain_ollama import OllamaLLM

from app.utils.logging import logger
from config import config


@lru_cache(maxsize=1)
def get_llm() -> OllamaLLM:
    logger.info(f"Using Ollama model '{config.OLLAMA_MODEL}' at {config.OLLAMA_HOST}")
    return OllamaLLM(base_url=config.OLLAMA_HOST, model=config.OLLAMA_MODEL, temperature=0.2)
