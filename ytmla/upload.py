"""Upload a video and prove it landed."""
from __future__ import annotations
from pathlib import Path

from googleapiclient.http import MediaFileUpload

from .verify import wait_retrievable


def resumable_upload(yt, path: str | Path, *, title: str, description: str,
                     tags: list[str] | None = None, category_id: str = "24",
                     privacy: str = "private", publish_at: str | None = None,
                     default_language: str = "en", made_for_kids: bool = False,
                     chunk_size: int = 8 * 1024 * 1024, progress=print) -> str:
    """Upload, then VERIFY retrievability. Returns the video id.

    Raises RuntimeError if the upload appears to succeed but the video is not retrievable
    -- which happens when an upload is rejected (e.g. longer than the channel's
    longUploadsStatus allows) and leaves a ghost entry in the uploads playlist.
    """
    status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": made_for_kids}
    if publish_at:
        status["publishAt"] = publish_at
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": (tags or [])[:500],
            "categoryId": category_id,
            "defaultLanguage": default_language,
            "defaultAudioLanguage": default_language,
        },
        "status": status,
    }
    media = MediaFileUpload(str(path), chunksize=chunk_size, resumable=True,
                            mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        chunk, response = req.next_chunk()
        if chunk:
            progress(f"  upload {int(chunk.progress() * 100)}%")

    vid = response["id"]
    progress(f"  returned id {vid} -- verifying")

    item = wait_retrievable(yt, vid)
    if not item:
        raise RuntimeError(
            f"upload of {path} returned id {vid} but the video is NOT retrievable. "
            "This is the ghost-entry failure -- usually a length limit. Check "
            "channels().list(part='status').longUploadsStatus == 'allowed'.")
    progress(f"  verified {vid}  ({item['status']['privacyStatus']})")
    return vid
