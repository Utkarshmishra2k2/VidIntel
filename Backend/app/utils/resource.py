"""
Turn whatever the user pastes (a full URL, a shortened URL, or a raw ID)
into a definitive (resource_type, resource_id) pair.

This replaces the old, fragile heuristic in main.py
(`len(resource_id) == 11 and not resource_id.startswith("PL")`) which
misclassified any 11-character video ID that happened to start with "PL".
URL structure is checked first and is authoritative; length-based guessing
is only used as a last resort for bare IDs.
"""
import re
from typing import Literal
from urllib.parse import parse_qs, urlparse

ResourceType = Literal["video", "playlist"]

_VIDEO_ID_RE = re.compile(r"^[0-9A-Za-z_-]{11}$")
# Bare playlist IDs are alphanumeric (plus - and _) and longer than a video ID;
# this is only used as a last-resort guess when there's no URL structure to
# read `list=` from directly.
_PLAYLIST_ID_RE = re.compile(r"^[0-9A-Za-z_-]{12,64}$")
# Known YouTube playlist ID prefixes (uploads, likes, watch-later, mixes, user playlists, etc.)
_PLAYLIST_PREFIXES = ("PL", "UU", "LL", "FL", "RD", "OL", "WL")


class InvalidResourceError(ValueError):
    pass


def parse_resource(raw: str) -> tuple[ResourceType, str]:
    raw = raw.strip()
    if not raw:
        raise InvalidResourceError("Please paste a YouTube video or playlist URL.")

    # Bare ID (no scheme, no slashes) — decide by shape.
    if "://" not in raw and "/" not in raw and "?" not in raw:
        if _VIDEO_ID_RE.match(raw) and not raw.startswith(_PLAYLIST_PREFIXES):
            return "video", raw
        if _PLAYLIST_ID_RE.match(raw):
            return "playlist", raw
        if _VIDEO_ID_RE.match(raw):
            return "video", raw
        raise InvalidResourceError(
            "That doesn't look like a valid YouTube video or playlist ID."
        )

    # Full / shortened URL.
    try:
        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    except ValueError as exc:
        raise InvalidResourceError(f"Could not parse URL: {exc}") from exc

    host = (parsed.netloc or "").lower().replace("www.", "").replace("m.", "")
    query = parse_qs(parsed.query)

    # A `list=` query param means the user wants the whole playlist,
    # even if the URL also contains a `v=` (e.g. a video played from inside a playlist).
    if "list" in query and query["list"][0]:
        return "playlist", query["list"][0]

    if host in ("youtube.com", "youtube-nocookie.com", "music.youtube.com"):
        if parsed.path == "/watch" and "v" in query:
            return "video", query["v"][0]
        for prefix in ("/embed/", "/shorts/", "/live/"):
            if parsed.path.startswith(prefix):
                candidate = parsed.path[len(prefix):].split("/")[0]
                if _VIDEO_ID_RE.match(candidate):
                    return "video", candidate
        if parsed.path == "/playlist" and "list" in query:
            return "playlist", query["list"][0]

    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/")[0]
        if _VIDEO_ID_RE.match(candidate):
            return "video", candidate

    raise InvalidResourceError(
        "Couldn't find a video or playlist in that link. "
        "Try pasting the full YouTube URL, or just the video/playlist ID."
    )
