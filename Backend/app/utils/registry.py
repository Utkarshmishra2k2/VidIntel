"""
Tiny persisted registry recording which resource_ids have been analyzed,
what type they are, and which video_ids they contain. This lets /api/query
validate a resource without re-fetching transcripts, and survives server
restarts (the FAISS index on disk would otherwise be orphaned).
"""
import json
import os
from typing import Optional, TypedDict

from config import config

_REGISTRY_PATH = os.path.join(config.FAISS_INDEX_PATH, "registry.json")
_cache: Optional[dict] = None


class ResourceRecord(TypedDict):
    resource_type: str
    video_ids: list[str]


def _load() -> dict:
    global _cache
    if _cache is None:
        if os.path.exists(_REGISTRY_PATH):
            try:
                with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
                    _cache = json.load(f)
            except (json.JSONDecodeError, OSError):
                _cache = {}
        else:
            _cache = {}
    return _cache


def _save() -> None:
    os.makedirs(config.FAISS_INDEX_PATH, exist_ok=True)
    with open(_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(_load(), f)


def save_resource(resource_id: str, resource_type: str, video_ids: list[str]) -> None:
    reg = _load()
    reg[resource_id] = {"resource_type": resource_type, "video_ids": video_ids}
    _save()


def get_resource(resource_id: str) -> Optional[ResourceRecord]:
    return _load().get(resource_id)
