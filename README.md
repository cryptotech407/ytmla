# ytmla

[![PyPI](https://img.shields.io/pypi/v/ytmla.svg)](https://pypi.org/project/ytmla/)
[![Python](https://img.shields.io/pypi/pyversions/ytmla.svg)](https://pypi.org/project/ytmla/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/cryptotech407/ytmla/actions/workflows/publish.yml/badge.svg)](https://github.com/cryptotech407/ytmla/actions/workflows/publish.yml)

Tooling for putting **multi-language audio tracks** on YouTube videos — the API half, plus
the Studio half the API doesn't cover.

Built out of a real production run: 3 languages × 6 episodes × long-form and Shorts, all
uploaded, dubbed and verified.

## The honest status of each half

**The API half is proven.** Upload, localization, duration fitting and verification were
used end to end against a live channel.

**The Studio half (`ytmla/studio.py`) is NOT proven.** See "The API cannot do this" below.

| Command | Status |
|---|---|
| `auth` | proven |
| `upload` | proven |
| `localize` | proven |
| `dub` | proven |
| `check` | proven |
| `studio` | **unverified selectors — expect to fix them** |

## Install

```bash
pip install -r requirements.txt
playwright install chromium        # only for the studio command
```

## The API cannot do this

Multi-language audio has **no Data API endpoint**. I checked the v3 discovery document
directly: there is no audio/localization write part on `videos.insert` or `videos.update`.
The only audio-related schema is `VideoFileDetailsAudioStream`, which is read-only metadata.

So the audio track itself has to be attached through the Studio UI. `ytmla/studio.py` drives
that with Playwright. **Studio's DOM changes without notice, so treat the `SELECTORS` map as
a starting point.** Run `--dry-run --headed` first; every failure screenshots into
`studio-shots/`.

The *metadata* for those languages **is** available via the API — titles and descriptions in
any language, which is what `ytmla/localize.py` does. That part is reliable; lean on it.

## Quickstart

```bash
# 1. one-time consent (needs force-ssl, not just upload)
python -m ytmla auth --client-secret client_secret.json --creds token.json

# 2. upload and PROVE it landed
python -m ytmla upload ep01.mp4 --title "..." --description-file desc_en.txt --privacy private

# 3. localized titles + descriptions for every language, in one call
python -m ytmla localize VIDEO_ID translations.json      # {lang: {title, description}}

# 4. fit a dub to the video's exact length (this is what prevents the upload error)
python -m ytmla dub narration_es.wav out_es.m4a --video ep01.mp4 --bed music.wav

# 5. preflight BEFORE uploading -- catches the mismatch that costs an upload cycle
python -m ytmla check out_es.m4a ep01.mp4

# 6. attach it (Studio UI; unverified selectors)
python -m ytmla studio --video-id VIDEO_ID --lang es --audio out_es.m4a --headed --dry-run
```

## Three traps this encodes

These each cost a real failed upload. They're the reason this exists rather than a snippet.

### 1 · Audio tracks must match video length

```
Processing failed — Audio tracks must match video length.
```

A track fitted to the **wrong** video fails by exactly the difference. If you dub Spanish to
the English picture (18:02) and attach it to the Spanish video (19:08), it fails — and then
fails again with a *generic* "unknown error" that sends you hunting in the wrong place.

`ytmla check` before every upload. `ytmla dub --video <the video you will attach to>` derives
the target length from that file, never from a hardcoded number.

### 2 · The `en` localization is bound to `snippet.description`

For a video with `defaultLanguage: en`, `localizations['en']` **is** the default description.

* Writing `localizations['en']` alone does nothing — the English text must go to
  `snippet.description`. (Observed: `es` and `pt` stored fine while `en` silently kept the
  old text.)
* Sending `localizations` *without* `en` can make the default description revert.

`localize.apply()` re-fetches immediately before updating, carries every existing language
through byte-for-byte, and always includes the default language. It then sleeps and
re-reads, comparing strings — not trusting that the call returned.

### 3 · A returned video id is not evidence the upload stuck

`videos().insert` will hand you an id for an upload that later fails processing or is
rejected on length. It can even leave a ghost entry in the uploads playlist while
`videos().list(id=...)` returns nothing.

`upload.resumable_upload` re-fetches and raises if the video isn't retrievable. Also check
`channels().list(part='status').longUploadsStatus == 'allowed'` — `eligible` caps you at
15 minutes.

## Also worth knowing

**AAC overshoots peaks.** A source peaking at -4 dBFS came out of the encoder at -0.3 dBFS.
`dub()` applies a default -1.5 dB headroom, because a track that clips on decode is worse
than one that's slightly quiet.

**64000bps is not enough** for a 45-minute documentary with music. The default here is 192k.

**Publishing is not automatic.** Everything defaults to `private`. Add audio tracks, check
playback, then publish.

## What this deliberately does not do

* Nothing that a human isn't permitted to do in their own Studio account. It clicks the same
  buttons faster.
* No auto-dubbing. YouTube's Gemini auto-dub has been measured at a **4–5× drop in average
  view duration** versus professional dubbing, and poor retention on a dubbed track drags
  the *whole channel* down. Bring real audio.
* No creation of separate language channels. That's a strategy decision, not a scripting one.

## Licence

MIT.
