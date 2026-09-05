"""
Best-effort video metadata (title, channel, duration).

The thumbnail URL never requires a network call — YouTube serves thumbnails
from a predictable, stable path for every video ID. Title/channel/duration
require actually reading the video's page (via yt-dlp), which can fail for
private/region-locked videos; when it does, we degrade gracefully instead
of failing the whole analysis.
"""
from dataclasses import dataclass
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from app.utils.logging import logger


@dataclass
class VideoMetadata:
    title: Optional[str] = None
    channel: Optional[str] = None
    duration_seconds: Optional[float] = None


def thumbnail_url(video_id: str) -> str:
    return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5), reraise=True)
def fetch_video_metadata(video_id: str) -> VideoMetadata:
    try:
        import yt_dlp

        opts = {"quiet": True, "skip_download": True, "noplaylist": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", download=False
            )
        return VideoMetadata(
            title=info.get("title"),
            channel=info.get("uploader") or info.get("channel"),
            duration_seconds=float(info["duration"]) if info.get("duration") else None,
        )
    except Exception as exc:
        logger.warning(f"Metadata fetch failed for {video_id}: {exc}")
        return VideoMetadata()
