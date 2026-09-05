"""
Transcript fetching and chunking.

Key fix vs. the original implementation: chunk start/end times are the
*actual* timestamps of the transcript entries that make up the chunk, not an
estimate derived from character-position ratio over total video duration.
Character-ratio estimates drift badly whenever speech rate is uneven (pauses,
music, fast talking), which made "jump to timestamp" inaccurate. Here, every
chunk's `start` is the start time of its first transcript entry and `end` is
`start + duration` of its last transcript entry — both taken directly from
YouTube's own caption timing.
"""
import re
from dataclasses import dataclass
from typing import Dict, List

from langchain_core.documents import Document
from tenacity import retry, stop_after_attempt, wait_exponential
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)

from app.utils.logging import logger
from config import config


class TranscriptUnavailableError(Exception):
    """Raised when a transcript genuinely cannot be fetched for a video."""


@dataclass
class TranscriptEntry:
    text: str
    start: float
    duration: float


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
def fetch_transcript(video_id: str) -> List[TranscriptEntry]:
    """Fetch the raw, timestamped transcript for a single video."""
    try:
        raw = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["en", "en-US", "en-GB", "hi", "hi-IN"]
        )
    except TranscriptsDisabled as exc:
        raise TranscriptUnavailableError("Captions are disabled for this video.") from exc
    except NoTranscriptFound as exc:
        raise TranscriptUnavailableError(
            "No English or Hindi transcript is available for this video."
        ) from exc

    if not raw:
        raise TranscriptUnavailableError("This video's transcript is empty.")

    entries = [
        TranscriptEntry(
            text=(e.get("text") or "").replace("\xa0", " ").strip(),
            start=float(e.get("start", 0.0)),
            duration=float(e.get("duration", 0.0)),
        )
        for e in raw
        if (e.get("text") or "").strip()
    ]
    if not entries:
        raise TranscriptUnavailableError("This video's transcript is empty.")

    logger.debug(f"Fetched transcript for {video_id}: {len(entries)} entries")
    return entries


_SENTENCE_END_RE = re.compile(r"[.!?]\s*$")


def build_chunks(
    entries: List[TranscriptEntry],
    video_id: str,
    max_chars: int | None = None,
    overlap_entries: int | None = None,
) -> List[Document]:
    """
    Group consecutive transcript entries into meaningful, readable chunks
    while keeping each chunk's start/end anchored to real caption timestamps.

    A chunk is closed when it reaches `max_chars`, preferring to close right
    after a sentence boundary so chunks read naturally rather than being cut
    mid-sentence. A small number of trailing entries are carried over into
    the next chunk (`overlap_entries`) so retrieval doesn't lose context at
    chunk boundaries — the overlapped entries keep their real timestamps, so
    accuracy is unaffected.
    """
    max_chars = max_chars or config.CHUNK_MAX_CHARS
    overlap_entries = overlap_entries if overlap_entries is not None else config.CHUNK_OVERLAP_ENTRIES

    chunks: List[Document] = []
    current: List[TranscriptEntry] = []
    current_len = 0

    def flush():
        if not current:
            return
        text = " ".join(e.text for e in current).strip()
        text = re.sub(r"\s+", " ", text)
        if not text:
            return
        start = current[0].start
        end = current[-1].start + current[-1].duration
        chunks.append(
            Document(
                page_content=text,
                metadata={"video_id": video_id, "start": round(start, 2), "end": round(end, 2)},
            )
        )

    last_index = len(entries) - 1
    for idx, entry in enumerate(entries):
        current.append(entry)
        current_len += len(entry.text) + 1

        at_sentence_end = bool(_SENTENCE_END_RE.search(entry.text))
        should_close = current_len >= max_chars and (at_sentence_end or current_len >= max_chars * 1.4)

        # Never close mid-loop on the very last entry — the flush() call
        # after the loop handles it. Without this check, the overlap
        # carry-over would re-emit the same final entry as a spurious
        # duplicate trailing chunk.
        if should_close and idx != last_index:
            flush()
            current = current[-overlap_entries:] if overlap_entries > 0 else []
            current_len = sum(len(e.text) + 1 for e in current)

    flush()

    if not chunks:
        raise TranscriptUnavailableError("Could not build any transcript chunks.")

    logger.debug(f"Built {len(chunks)} chunks for {video_id} (real timestamps preserved)")
    return chunks


def full_text(entries: List[TranscriptEntry]) -> str:
    return re.sub(r"\s+", " ", " ".join(e.text for e in entries)).strip()
