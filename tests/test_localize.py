"""Localization behaviour -- above all the `en` binding trap.

For a video with defaultLanguage='en', localizations['en'] IS snippet.description.
Writing localizations['en'] alone does nothing (observed in production), and omitting
'en' entirely can make the default description revert.
"""
import pytest

from ytmla.localize import apply, get
from tests.fake_yt import FakeYouTube

EN_TITLE, EN_DESC = "English Title", "English description body"
ES_TITLE, ES_DESC = "Titulo espanol", "Cuerpo en espanol"
PT_TITLE, PT_DESC = "Titulo portugues", "Corpo em portugues"


def _video():
    return {
        "VID1": {
            "snippet": {"title": EN_TITLE, "description": EN_DESC, "tags": ["a"],
                        "categoryId": "24", "defaultLanguage": "en",
                        "defaultAudioLanguage": "en"},
            "localizations": {"en": {"title": EN_TITLE, "description": EN_DESC},
                              "es": {"title": ES_TITLE, "description": ES_DESC}},
        }
    }


def test_english_goes_into_the_snippet_description():
    """The headline trap: en must be written to snippet.description, not just localizations."""
    yt = FakeYouTube(_video())
    new_en = "A NEW English description"
    res = apply(yt, "VID1", {"en": {"title": EN_TITLE, "description": new_en}}, sleep=0)
    assert res["snippet_ok"], res
    assert yt.state["VID1"]["snippet"]["description"] == new_en


def test_existing_languages_are_preserved_when_adding_a_new_one():
    yt = FakeYouTube(_video())
    res = apply(yt, "VID1", {"pt": {"title": PT_TITLE, "description": PT_DESC}}, sleep=0)
    assert res["all_ok"], res
    # the pre-existing Spanish must survive untouched
    assert yt.state["VID1"]["localizations"]["es"]["description"] == ES_DESC
    assert yt.state["VID1"]["localizations"]["pt"]["description"] == PT_DESC
    assert "es" in res["lanes"] and "pt" in res["lanes"] and "en" in res["lanes"]


def test_omitting_the_default_language_falls_back_to_the_snippet():
    """If the caller does not supply `en`, the video's own snippet becomes the `en` lane.

    Refusing would be wrong: the default description IS the default-language content.
    What matters is that the `en` lane ends up populated, because that is what stops the
    bound default description reverting.
    """
    yt = FakeYouTube({"VID1": {"snippet": {"title": EN_TITLE, "description": EN_DESC,
                                           "tags": [], "categoryId": "24",
                                           "defaultLanguage": "en"},
                               "localizations": {}}})
    res = apply(yt, "VID1", {"pt": {"title": PT_TITLE, "description": PT_DESC}}, sleep=0)
    assert res["all_ok"], res
    assert yt.state["VID1"]["localizations"]["en"]["description"] == EN_DESC
    assert yt.state["VID1"]["snippet"]["description"] == EN_DESC
    assert yt.state["VID1"]["localizations"]["pt"]["description"] == PT_DESC


def test_detects_an_update_that_did_not_stick():
    """An accepted call that does not persist must NOT be reported as success."""
    yt = FakeYouTube(_video(), fail_update=True)
    res = apply(yt, "VID1", {"pt": {"title": PT_TITLE, "description": PT_DESC}}, sleep=0)
    assert not res["all_ok"]
    assert res["verified"]["pt"] is False


def test_get_raises_for_an_unretrievable_video():
    with pytest.raises(RuntimeError):
        get(FakeYouTube({}), "MISSING")


def test_callers_own_languages_override_existing_ones():
    yt = FakeYouTube(_video())
    res = apply(yt, "VID1", {"es": {"title": "Nuevo", "description": "Nuevo cuerpo"}}, sleep=0)
    assert res["all_ok"], res
    assert yt.state["VID1"]["localizations"]["es"]["title"] == "Nuevo"
