"""Translation catalogue checks: every language must define every message."""

from pathlib import Path

import polib
import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient

LANGS = [code for code, _name in settings.LANGUAGES]


def load_catalog(lang: str) -> polib.POFile:
    path = Path(settings.LOCALE_PATHS[0]) / lang / "LC_MESSAGES" / "django.po"
    assert path.exists(), f"missing catalogue: {path}"
    return polib.pofile(str(path))


def active_ids(po: polib.POFile) -> set[str]:
    return {entry.msgid for entry in po if not entry.obsolete}


def test_catalogues_have_identical_keys():
    reference = active_ids(load_catalog(LANGS[0]))
    for lang in LANGS[1:]:
        ids = active_ids(load_catalog(lang))
        assert ids == reference, (
            f"{lang}: missing={sorted(reference - ids)} extra={sorted(ids - reference)}"
        )


@pytest.mark.parametrize("lang", LANGS)
def test_catalogue_fully_translated(lang):
    po = load_catalog(lang)
    untranslated = [e.msgid for e in po.untranslated_entries()]
    fuzzy = [e.msgid for e in po.fuzzy_entries()]
    assert not untranslated, f"{lang}: untranslated {untranslated}"
    assert not fuzzy, f"{lang}: fuzzy {fuzzy}"


@pytest.mark.parametrize(
    ("lang", "app_name"),
    [("uz", "Dars jadvali"), ("ru", "Расписание занятий"), ("en", "Timetable")],
)
def test_meta_follows_accept_language(lang, app_name):
    resp = APIClient().get(reverse("meta"), HTTP_ACCEPT_LANGUAGE=lang)
    assert resp.status_code == 200
    assert resp.data["app_name"] == app_name
    assert resp.data["language"] == lang


def test_unknown_language_falls_back_to_uzbek():
    resp = APIClient().get(reverse("meta"), HTTP_ACCEPT_LANGUAGE="de")
    assert resp.data["language"] == "uz"
