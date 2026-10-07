from datetime import date

import pytest
from django.utils import translation

from apps.core.dates import format_long_date, lesson_label, weekday_name


@pytest.mark.parametrize(
    ("lang", "expected"),
    [
        ("uz", "9-aprel, payshanba"),
        ("ru", "9 апреля, четверг"),
        ("en", "Thursday, 9 April"),
    ],
)
def test_long_date(lang, expected):
    with translation.override(lang):
        assert format_long_date(date(2026, 4, 9)) == expected


@pytest.mark.parametrize(
    ("lang", "expected"),
    [("uz", "Payshanba, 3-dars"), ("ru", "Четверг, 3-я пара"), ("en", "Thursday, lesson 3")],
)
def test_lesson_label(lang, expected):
    with translation.override(lang):
        assert lesson_label(weekday_name(3), 3) == expected
