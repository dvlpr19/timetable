"""Render notification texts in the recipient's language at creation time.

`params` hold language-neutral facts; translated names are passed as {"uz": .., "ru": .., "en": ..}.
"""

from django.utils import translation
from django.utils.translation import gettext as _
from django.utils.translation import gettext_noop

from apps.core.dates import format_when

from .models import NotificationKind


def localized(names: dict | str, lang: str) -> str:
    if isinstance(names, str):
        return names
    return names.get(lang) or names.get("uz") or ""


TITLES = {
    NotificationKind.ROOM_CHANGED: gettext_noop("Lesson moved to another room"),
    NotificationKind.TIME_CHANGED: gettext_noop("Lesson moved to another time"),
    NotificationKind.CANCELLED: gettext_noop("Lesson cancelled"),
    NotificationKind.TEACHER_CHANGED: gettext_noop("Teacher replaced"),
    NotificationKind.LESSON_ADDED: gettext_noop("New lesson added"),
    NotificationKind.LINK_CHANGED: gettext_noop("Online lesson link changed"),
    NotificationKind.SCHEDULE_PUBLISHED: gettext_noop("New timetable published"),
}


def _body(kind: str, p: dict, lang: str) -> str:
    subject = localized(p.get("subject", ""), lang)
    if kind == NotificationKind.SCHEDULE_PUBLISHED:
        return _("The timetable for %(semester)s is published. Check your lessons.") % {
            "semester": localized(p["semester"], lang)
        }
    common = {"day": format_when(p["when"]), "number": p.get("number"), "subject": subject}
    if kind == NotificationKind.ROOM_CHANGED:
        return _(
            "%(day)s, lesson %(number)s: %(subject)s moved from %(old_room)s to room %(new_room)s."
        ) % {**common, "old_room": p["old_room"], "new_room": p["new_room"]}
    if kind == NotificationKind.TIME_CHANGED:
        return _(
            "%(subject)s moved from %(day)s, lesson %(number)s "
            "to %(new_day)s, lesson %(new_number)s."
        ) % {**common, "new_day": format_when(p["new_when"]), "new_number": p["new_number"]}
    if kind == NotificationKind.CANCELLED:
        return _("%(day)s, lesson %(number)s: %(subject)s is cancelled.") % common
    if kind == NotificationKind.TEACHER_CHANGED:
        return _(
            "%(day)s, lesson %(number)s: %(subject)s will be taught by %(new_teacher)s "
            "instead of %(old_teacher)s."
        ) % {**common, "new_teacher": p["new_teacher"], "old_teacher": p["old_teacher"]}
    if kind == NotificationKind.LESSON_ADDED:
        return _("New lesson: %(subject)s, %(day)s, lesson %(number)s, %(room)s.") % {
            **common,
            "room": p["room"],
        }
    if kind == NotificationKind.LINK_CHANGED:
        return _(
            "%(subject)s (%(day)s, lesson %(number)s): the online lesson link has changed."
        ) % (common)
    raise ValueError(f"no template for {kind}")


def render(kind: str, params: dict, lang: str) -> tuple[str, str]:
    """(title, body) in `lang`."""
    with translation.override(lang):
        return _(TITLES[kind]), _body(kind, params, lang)
