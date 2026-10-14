"""Localized titles/descriptions -- the part of multi-language the API DOES support.

THE TRAP: for a video whose `defaultLanguage` is `en`, the `en` localization IS the
video's default description. Two consequences:

  1. Writing `localizations['en']` alone does nothing. The English text has to go into
     `snippet.description`. (Observed: es and pt stored fine on the first attempt while
     `en` silently kept the old text.)
  2. If you send `localizations` WITHOUT `en`, the default description can revert.

So `apply()` always writes the full set. Everything is re-fetched immediately before the
update and carried through byte-for-byte, so nothing is destroyed.
"""
from __future__ import annotations

from .verify import wait_retrievable


def get(yt, video_id: str) -> dict:
    items = yt.videos().list(part="snippet,localizations", id=video_id).execute().get("items", [])
    if not items:
        raise RuntimeError(f"{video_id} not retrievable")
    return items[0]


def apply(yt, video_id: str, translations: dict[str, dict],
          default_language: str = "en", sleep: float = 12.0) -> dict:
    """Apply translations {lang: {'title':..., 'description':...}} and verify.

    `translations` must include `default_language`. Any localization already on the video
    that you do not supply is preserved untouched.

    Returns {'lanes': [...], 'verified': {lang: bool}, 'snippet_ok': bool}.
    """
    import time

    cur = get(yt, video_id)
    snippet = cur["snippet"]
    existing = cur.get("localizations") or {}

    # carry every pre-existing localization through unless the caller overrides it
    merged = {lang: {"title": v.get("title", ""), "description": v.get("description", "")}
              for lang, v in existing.items()}
    for lang, v in translations.items():
        merged[lang] = {"title": v["title"], "description": v["description"]}

    if default_language not in merged:
        raise ValueError(
            f"translations must include '{default_language}': its localization is bound to "
            "snippet.description, and omitting it lets the default description revert.")

    default_text = merged[default_language]["description"]

    body = {
        "id": video_id,
        "snippet": {
            "title": merged[default_language]["title"],
            "description": default_text,
            "tags": snippet.get("tags", []),
            "categoryId": snippet.get("categoryId", "24"),
            "defaultLanguage": default_language,
            "defaultAudioLanguage": snippet.get("defaultAudioLanguage", default_language),
        },
        "localizations": merged,
    }
    yt.videos().update(part="snippet,localizations", body=body).execute()

    time.sleep(sleep)  # read-after-write is eventually consistent
    after = get(yt, video_id)
    got = after.get("localizations") or {}

    verified = {
        lang: (got.get(lang, {}).get("description", "").strip()
               == merged[lang]["description"].strip()
               and got.get(lang, {}).get("title", "") == merged[lang]["title"])
        for lang in merged
    }
    return {
        "lanes": sorted(merged),
        "snippet_ok": after["snippet"]["description"].strip() == default_text.strip(),
        "verified": verified,
        "all_ok": all(verified.values())
                  and after["snippet"]["description"].strip() == default_text.strip(),
    }
