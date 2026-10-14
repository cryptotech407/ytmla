"""Command line entry points.  `python -m ytmla <command>`."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path


def _svc(a):
    from .auth import service
    return service(a.creds, a.client_secret)


def cmd_auth(a):
    from .auth import authorize
    authorize(a.client_secret, a.creds, port=a.port)
    print(f"token written to {a.creds}")


def cmd_upload(a):
    from .upload import resumable_upload
    yt = _svc(a)
    desc = Path(a.description_file).read_text() if a.description_file else (a.description or "")
    vid = resumable_upload(
        yt, a.video, title=a.title, description=desc,
        tags=(a.tags.split(",") if a.tags else []),
        category_id=a.category, privacy=a.privacy, publish_at=a.publish_at,
        default_language=a.default_language)
    print(vid)


def cmd_localize(a):
    from .localize import apply
    yt = _svc(a)
    translations = json.loads(Path(a.translations).read_text())
    res = apply(yt, a.video_id, translations, default_language=a.default_language)
    print(json.dumps(res, indent=1))
    sys.exit(0 if res["all_ok"] else 1)


def cmd_dub(a):
    from .dub import fit, duration
    target = a.target_seconds or duration(a.video)
    res = fit(a.audio, a.out, target, bed=a.bed, headroom_db=a.headroom)
    print(json.dumps(res, indent=1))
    sys.exit(0 if res["ok"] else 1)


def cmd_check(a):
    from .dub import check_track
    res = check_track(a.audio, a.video)
    print(json.dumps(res, indent=1))
    if not res["ok"]:
        print("FAIL: YouTube will reject this track -- "
              "'Audio tracks must match video length'", file=sys.stderr)
    sys.exit(0 if res["ok"] else 1)


def cmd_studio(a):
    from .studio import add_audio_track
    res = add_audio_track(a.video_id, a.lang, a.audio, profile_dir=a.profile,
                          headed=a.headed, dry_run=a.dry_run, shots=a.shots)
    print(json.dumps(res, indent=1))


def build_parser():
    p = argparse.ArgumentParser(prog="ytmla", description=__doc__)
    p.add_argument("--creds", default="token.json")
    p.add_argument("--client-secret", default="client_secret.json")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("auth", help="one-time interactive OAuth consent")
    s.add_argument("--port", type=int, default=0)
    s.set_defaults(func=cmd_auth)

    s = sub.add_parser("upload", help="upload a video and verify it landed")
    s.add_argument("video")
    s.add_argument("--title", required=True)
    s.add_argument("--description")
    s.add_argument("--description-file")
    s.add_argument("--tags", default="")
    s.add_argument("--category", default="24")
    s.add_argument("--privacy", default="private", choices=["private", "public", "unlisted"])
    s.add_argument("--publish-at", default=None, help="RFC3339, e.g. 2026-11-01T19:00:00Z")
    s.add_argument("--default-language", default="en")
    s.set_defaults(func=cmd_upload)

    s = sub.add_parser("localize", help="apply localized titles/descriptions")
    s.add_argument("video_id")
    s.add_argument("translations", help="JSON: {lang: {title, description}}")
    s.add_argument("--default-language", default="en")
    s.set_defaults(func=cmd_localize)

    s = sub.add_parser("dub", help="fit an audio track to a video's exact length")
    s.add_argument("audio")
    s.add_argument("out")
    s.add_argument("--video", help="target length comes from this file")
    s.add_argument("--target-seconds", type=float)
    s.add_argument("--bed", help="optional music bed to mix under")
    s.add_argument("--headroom", type=float, default=-1.5)
    s.set_defaults(func=cmd_dub)

    s = sub.add_parser("check", help="preflight: will YouTube accept this track?")
    s.add_argument("audio")
    s.add_argument("video")
    s.set_defaults(func=cmd_check)

    s = sub.add_parser("studio", help="attach an audio track via Studio (Playwright)")
    s.add_argument("--video-id", required=True)
    s.add_argument("--lang", required=True)
    s.add_argument("--audio", required=True)
    s.add_argument("--profile", default="~/.ytmla-profile")
    s.add_argument("--shots", default="studio-shots")
    s.add_argument("--headed", action="store_true")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_studio)
    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
