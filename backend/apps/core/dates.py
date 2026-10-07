"""Language-aware date and weekday labels (active Django language)."""

from datetime import date

from django.utils import translation
from django.utils.translation import gettext as _
from django.utils.translation import gettext_noop, pgettext

WEEKDAYS = [
    gettext_noop("Monday"),
    gettext_noop("Tuesday"),
    gettext_noop("Wednesday"),
    gettext_noop("Thursday"),
    gettext_noop("Friday"),
    gettext_noop("Saturday"),
    gettext_noop("Sunday"),
]


def month_genitive(month: int) -> str:
    names = {
        1: pgettext("genitive month", "January"),
        2: pgettext("genitive month", "February"),
        3: pgettext("genitive month", "March"),
        4: pgettext("genitive month", "April"),
        5: pgettext("genitive month", "May"),
        6: pgettext("genitive month", "June"),
        7: pgettext("genitive month", "July"),
        8: pgettext("genitive month", "August"),
        9: pgettext("genitive month", "September"),
        10: pgettext("genitive month", "October"),
        11: pgettext("genitive month", "November"),
        12: pgettext("genitive month", "December"),
    }
    return names[month]


def weekday_name(weekday: int) -> str:
    return _(WEEKDAYS[weekday])


def format_long_date(day: date) -> str:
    """9-aprel, payshanba / 9 апреля, четверг / Thursday, 9 April (active language)."""
    return _("%(day)s %(month)s, %(weekday)s") % {
        "day": day.day,
        "month": month_genitive(day.month),
        "weekday": weekday_name(day.weekday()).lower()
        if translation.get_language() != "en"
        else weekday_name(day.weekday()),
    }


def format_when(when: dict) -> str:
    """`when` is {"date": "2026-04-09"} or {"weekday": 3}."""
    if when.get("date"):
        return format_long_date(date.fromisoformat(when["date"]))
    return weekday_name(when["weekday"])


def lesson_label(day: str, number: int) -> str:
    """ "Payshanba, 3-dars" / "Четверг, 3-я пара" / "Thursday, lesson 3"."""
    return _("%(day)s, lesson %(number)s") % {"day": day, "number": number}
