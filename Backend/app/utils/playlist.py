"""
Expand a playlist ID into its member video IDs.

yt-dlp is used as the primary method because it is actively maintained
against YouTube's frequent internal changes; `pytube` (used in the original
code) is well known for breaking for weeks at a time when YouTube ships
changes, so it's kept only as a fallback.
"""
from typing import List

from tenacity import retry, stop_after_attempt, wait_exponential

from app.utils.logging import logger
from config import config


class PlaylistFetchError(Exception):
    pass


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=6), reraise=True)
def _fetch_with_ytdlp(playlist_id: str) -> List[str]:
    import yt_dlp

    url = f"https://www.youtube.com/playlist?list={playlist_id}"
    opts = {
        "extract_flat": True,
        "quiet": True,
        "skip_download": True,
        "playlistend": config.MAX_PLAYLIST_VIDEOS,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    entries = (info or {}).get("entries") or []
    video_ids = [e["id"] for e in entries if e and e.get("id")]
    return video_ids


def _fetch_with_pytube(playlist_id: str) -> List[str]:
    from pytube import Playlist

    url = f"https://www.youtube.com/playlist?list={playlist_id}"
    playlist = Playlist(url)
    video_ids = [u.split("v=")[1].split("&")[0] for u in playlist.video_urls]
    return video_ids[: config.MAX_PLAYLIST_VIDEOS]


def get_playlist_videos(playlist_id: str) -> List[str]:
    try:
        video_ids = _fetch_with_ytdlp(playlist_id)
        if video_ids:
            logger.info(f"Fetched {len(video_ids)} videos from playlist {playlist_id} (yt-dlp)")
            return video_ids
    except Exception as exc:
        logger.warning(f"yt-dlp playlist fetch failed for {playlist_id}: {exc}")

    try:
        video_ids = _fetch_with_pytube(playlist_id)
        if video_ids:
            logger.info(f"Fetched {len(video_ids)} videos from playlist {playlist_id} (pytube)")
            return video_ids
    except Exception as exc:
        logger.warning(f"pytube playlist fetch failed for {playlist_id}: {exc}")

    raise PlaylistFetchError(
        "Couldn't read that playlist. It may be private, empty, or YouTube's "
        "page structure may have changed. Try a public playlist or a single video URL."
    )
