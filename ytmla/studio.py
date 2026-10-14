"""Attach multi-language AUDIO tracks through YouTube Studio, via Playwright.

>>> SELECTORS IN THIS FILE ARE UNVERIFIED. <<<

The Data API has no audio-track endpoint (checked against the v3 discovery document: there
is no audio/localization write part on videos.insert or videos.update -- only
`VideoFileDetailsAudioStream`, which is read-only metadata). So this step has to go through
the Studio UI, and Studio's DOM changes without notice.

What that means concretely:
  * Treat the selector maps below as a STARTING POINT, not as truth.
  * Run `--dry-run --headed` first and watch what happens.
  * Every step screenshots on failure into ./studio-shots/ so you can see the DOM you got.
  * When a selector breaks, fix it in the SELECTORS map only.

Prerequisites: `pip install playwright && playwright install chromium`, and a Google
account already signed in. Use a persistent profile so you stay signed in:

    ytmla studio --video-id X --lang es --audio out.m4a --profile ~/.ytmla-profile --headed

Do NOT use this to work around a platform limit -- only to do a thing a human is permitted
to do in their own account, faster.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

SELECTORS = {
    # each entry is a list of candidates, tried in order
    "add_language": [
        'button:has-text("Add language")',
        'ytcp-button:has-text("Add language")',
        'button:has-text("Add")',
    ],
    "language_search": [
        'input[aria-label*="language" i]',
        'ytcp-form-input-container input',
        'input[type="text"]',
    ],
    "language_option": [
        'ytcp-ve:has-text("{lang}")',
        'mat-option:has-text("{lang}")',
        '[role="option"]:has-text("{lang}")',
    ],
    "audio_add": [
        'button:has-text("Add")',
        'ytcp-button:has-text("Add")',
    ],
    "file_input": ['input[type="file"]'],
    "publish": [
        'button:has-text("Publish")',
        'ytcp-button:has-text("Publish")',
        'button:has-text("Save")',
    ],
    "row_menu": [
        'ytcp-icon-button[aria-label*="more" i]',
        'button[aria-label*="more" i]',
    ],
    "delete": [
        'tp-yt-paper-item:has-text("Delete")',
        '[role="menuitem"]:has-text("Delete")',
    ],
}

LANG_NAMES = {"en": "English", "es": "Spanish", "pt": "Portuguese (Brazil)", "pt-BR": "Portuguese (Brazil)"}


def _first(page, key: str, timeout: int = 8000, **fmt):
    """Try each candidate selector for `key`; return the first that resolves."""
    last = None
    for sel in SELECTORS[key]:
        sel = sel.format(**fmt) if fmt else sel
        try:
            el = page.wait_for_selector(sel, timeout=timeout, state="visible")
            if el:
                return el
        except Exception as e:  # noqa: BLE001 - we want to try the next candidate
            last = e
    raise RuntimeError(f"no selector matched for '{key}'. Last error: {last}")


def _shot(page, name: str, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    try:
        page.screenshot(path=str(outdir / f"{name}.png"), full_page=True)
    except Exception:
        pass


def add_audio_track(video_id: str, lang: str, audio_path: str | Path, *,
                    profile_dir: str | Path = "~/.ytmla-profile",
                    headed: bool = False, dry_run: bool = False,
                    channel_handle: str | None = None,
                    shots: str | Path = "studio-shots") -> dict:
    """Attach one audio track to one video. Returns a result dict; raises on hard failure."""
    from playwright.sync_api import sync_playwright

    audio = Path(audio_path).expanduser().resolve()
    if not audio.exists():
        raise FileNotFoundError(audio)
    shots = Path(shots)
    name = LANG_NAMES.get(lang, lang)
    result = {"video_id": video_id, "lang": lang, "audio": str(audio),
              "steps": [], "ok": False, "dry_run": dry_run}

    def step(msg):
        result["steps"].append(msg)
        print(f"  [{lang}] {msg}", flush=True)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(Path(profile_dir).expanduser()), headless=not headed,
            accept_downloads=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            url = f"https://studio.youtube.com/video/{video_id}/translations"
            step(f"navigate {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)

            if "accounts.google.com" in page.url:
                step("NOT SIGNED IN -- run once with --headed and sign in")
                _shot(page, f"{video_id}-{lang}-signin", shots)
                raise RuntimeError("not signed in; the persistent profile has no session")

            if dry_run:
                step("dry run: stopping before any click")
                _shot(page, f"{video_id}-{lang}-dryrun", shots)
                result["ok"] = True
                return result

            step("click Add language")
            _first(page, "add_language").click()
            page.wait_for_timeout(1500)

            step(f"choose {name}")
            box = _first(page, "language_search")
            box.click()
            box.fill(name)
            page.wait_for_timeout(1500)
            _first(page, "language_option", lang=name).click()
            page.wait_for_timeout(2500)

            step("upload audio file")
            inp = page.query_selector(SELECTORS["file_input"][0])
            if inp is None:
                # the input may be created only after clicking the Add control
                _first(page, "audio_add").click()
                page.wait_for_timeout(1000)
                inp = page.query_selector(SELECTORS["file_input"][0])
            if inp is None:
                _shot(page, f"{video_id}-{lang}-no-file-input", shots)
                raise RuntimeError("no file input found for the audio upload")
            inp.set_input_files(str(audio))
            page.wait_for_timeout(3000)

            step("publish")
            _first(page, "publish").click()
            page.wait_for_timeout(5000)

            _shot(page, f"{video_id}-{lang}-after-publish", shots)
            result["ok"] = True
            step("done (verify in Studio -- processing is asynchronous)")
            return result
        except Exception:
            _shot(page, f"{video_id}-{lang}-error", shots)
            raise
        finally:
            ctx.close()


def remove_existing_dub(video_id: str, lang: str, **kw) -> dict:
    """Delete an auto-dub already published for `lang`, so a custom track can take its place."""
    # Deliberately left as a thin wrapper: the row-menu -> Delete path is the most
    # DOM-brittle part of Studio and I have not validated it. Implement against a real
    # session with --headed before trusting it.
    raise NotImplementedError(
        "Not implemented: deleting an existing auto-dub is the most brittle Studio path "
        "(row three-dot menu -> Delete). Verify the DOM in a headed session first.")
