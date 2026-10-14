"""Verification helpers.

House rule, learned the hard way: a video id returned by `insert` is NOT evidence the
upload stuck. YouTube will happily return an id for an upload that later fails processing
or is rejected on length. Always re-fetch.
"""
from __future__ import annotations
import re
import time

_ISO = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def iso_to_seconds(duration: str) -> int:
    """'PT1H2M3S' -> 3723. Returns 0 on anything unparseable."""
    m = _ISO.match(duration or "")
    if not m:
        return 0
    h, mi, s = (int(g) if g else 0 for g in m.groups())
    return h * 3600 + mi * 60 + s


def wait_retrievable(yt, video_id: str, tries: int = 8, delay: float = 5.0) -> dict | None:
    """Poll until the video is retrievable. Returns the item, or None.

    YouTube's read-after-write is eventually consistent, and a brand-new upload can 404
    for a few seconds. Never conclude failure from a single miss.
    """
    for _ in range(tries):
        try:
            items = yt.videos().list(part="snippet,status,contentDetails,localizations",
                                     id=video_id).execute().get("items", [])
            if items:
                return items[0]
        except Exception:
            pass
        time.sleep(delay)
    return None


def present(yt, video_id: str) -> bool:
    """True only if videos().list returns the item. Playlist membership is not proof --
    an upload rejected for length can still appear in the uploads playlist as a ghost."""
    try:
        return bool(yt.videos().list(part="id", id=video_id).execute().get("items", []))
    except Exception:
        return False
