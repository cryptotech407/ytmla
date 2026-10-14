"""Fit a dubbed audio track to a video's exact length.

WHY THIS EXISTS: YouTube rejects an audio track with
    "Processing failed -- Audio tracks must match video length."
This is the single most common failure when attaching dubs. A track fitted to the wrong
picture (e.g. a Spanish dub fitted to the English video, then attached to the longer
Spanish video) fails by exactly the length difference.

So: always derive the target length from THE VIDEO YOU ARE ATTACHING TO, and assert
before you upload.
"""
from __future__ import annotations
import subprocess
from pathlib import Path


def duration(path: str | Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True).stdout.strip()
    return float(out or 0.0)


def fit(src: str | Path, out: str | Path, target_seconds: float,
        bed: str | Path | None = None, bed_gain: float = 0.055,
        bitrate: str = "192k", headroom_db: float = -1.5) -> dict:
    """Stretch `src` to exactly `target_seconds`, optionally mixing a music bed.

    Uses atempo so pitch is preserved. Speed ratios beyond ~1.10 start to sound rushed;
    prefer re-recording over stretching further.

    `headroom_db` matters: AAC encoding overshoots peaks. A source peaking at -4 dBFS can
    come out of the encoder at -0.3 dBFS and clip on some decoders. -1.5 dB is a sane floor.

    Returns a dict with the real measured result -- check it, do not assume.
    """
    src_d = duration(src)
    if src_d <= 0:
        raise ValueError(f"cannot read duration of {src}")
    ratio = src_d / target_seconds

    if bed:
        fc = (f"[0:a]atempo={ratio:.6f},aresample=48000[vo];"
              f"[1:a]volume={bed_gain},aresample=48000[bed];"
              f"[vo][bed]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[m];"
              f"[m]volume={headroom_db}dB,apad,atrim=0:{target_seconds:.3f}[out]")
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src),
               "-stream_loop", "-1", "-i", str(bed),
               "-filter_complex", fc, "-map", "[out]"]
    else:
        fc = (f"[0:a]atempo={ratio:.6f},aresample=48000,"
              f"volume={headroom_db}dB,apad,atrim=0:{target_seconds:.3f}[out]")
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src),
               "-filter_complex", fc, "-map", "[out]"]

    cmd += ["-c:a", "aac", "-b:a", bitrate, "-ar", "48000", "-ac", "2", str(out)]
    subprocess.run(cmd, check=True)

    got = duration(out)
    return {
        "source_seconds": round(src_d, 3),
        "target_seconds": round(target_seconds, 3),
        "output_seconds": round(got, 3),
        "atempo": round(ratio, 5),
        "delta": round(got - target_seconds, 3),
        "ok": abs(got - target_seconds) < 0.5,
    }


def check_track(track: str | Path, video: str | Path, tolerance: float = 0.5) -> dict:
    """Pre-flight: will YouTube accept this track on this video?

    Run this BEFORE uploading. It catches the mismatch that otherwise costs you an upload
    cycle and a confusing 'unknown error' in Studio.
    """
    t, v = duration(track), duration(video)
    return {
        "track_seconds": round(t, 3),
        "video_seconds": round(v, 3),
        "delta": round(t - v, 3),
        "ok": abs(t - v) <= tolerance,
    }
