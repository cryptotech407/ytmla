"""Duration fitting -- the code that prevents
'Processing failed -- Audio tracks must match video length.'"""
import shutil
import subprocess

import pytest

from ytmla.dub import check_track, duration, fit

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _tone(path, seconds, freq=440):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                    "-i", f"sine=frequency={freq}:duration={seconds}",
                    "-ar", "48000", "-ac", "2", str(path)], check=True)
    return path


def test_fit_stretches_to_exact_target(tmp_path):
    src = _tone(tmp_path / "vo.wav", 10.0)
    out = tmp_path / "vo_fit.m4a"
    res = fit(src, out, target_seconds=9.0)
    assert res["ok"], res
    assert abs(res["output_seconds"] - 9.0) < 0.5
    # 10s squeezed into 9s => atempo > 1
    assert res["atempo"] > 1.0
    assert abs(res["delta"]) < 0.5


def test_fit_with_music_bed(tmp_path):
    src = _tone(tmp_path / "vo.wav", 5.0)
    bed = _tone(tmp_path / "bed.wav", 5.0, freq=110)
    out = tmp_path / "mixed.m4a"
    res = fit(src, out, target_seconds=5.0, bed=bed)
    assert res["ok"], res
    assert duration(out) > 0


def test_check_track_accepts_a_match(tmp_path):
    v = _tone(tmp_path / "video.mp4".replace(".mp4", ".wav"), 20.0)
    t = _tone(tmp_path / "track.wav", 20.0, freq=200)
    res = check_track(t, v)
    assert res["ok"], res
    assert abs(res["delta"]) < 0.5


def test_check_track_rejects_the_mismatch_that_cost_a_real_upload(tmp_path):
    """18:02 track against a 19:08 video -- exactly the failure seen in production."""
    track = _tone(tmp_path / "track.wav", 18 * 60 + 2)
    video = _tone(tmp_path / "video.wav", 19 * 60 + 8)
    res = check_track(track, video)
    assert not res["ok"]
    assert res["delta"] < -60  # ~66s short


def test_fit_rejects_unreadable_source(tmp_path):
    with pytest.raises(ValueError):
        fit(tmp_path / "nope.wav", tmp_path / "out.m4a", target_seconds=10.0)
