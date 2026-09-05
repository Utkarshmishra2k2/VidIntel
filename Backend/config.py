"""
Application configuration.

All settings can be overridden via environment variables or a .env file.
This is the single source of truth for configuration — nothing else in the
app should read os.environ directly.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    # --- Ollama (local LLM) ---
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b-instruct-q4_K_M"

    # --- Embeddings / reranking ---
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # --- Storage ---
    FAISS_INDEX_PATH: str = "./storage/faiss_index"
    MAX_PLAYLIST_VIDEOS: int = 25  # keep playlist processing practical

    # --- Chunking ---
    CHUNK_MAX_CHARS: int = 1100
    CHUNK_OVERLAP_ENTRIES: int = 1  # how many transcript entries to re-include at the start of the next chunk

    # --- Retrieval ---
    RETRIEVE_TOP_K: int = 8
    RERANK_TOP_K: int = 4

    # --- Rate limiting (simple in-process limiter, no external services required) ---
    RATE_LIMIT_REQUESTS: int = 20
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # --- App / CORS ---
    PROD_MODE: bool = False
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


config = Config()
