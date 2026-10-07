"""Human-readable solver diagnostics. Runs happen in the worker, so each message is stored in
all three languages and the API returns the one the viewer reads."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from django.utils import translation
from django.utils.translation import gettext as _

from apps.scheduling.validators import ValidationContext, lesson_title

LANGS = ("uz", "ru", "en")

# error: the lesson cannot be placed until the data changes; warning: worth a look
SEVERITY = {
    "teacher_language": "error",
    "stream_language": "error",
    "no_room": "error",
    "no_time": "error",
    "fixed_conflicts": "warning",
    "teacher_overloaded": "warning",
    "group_overloaded": "warning",
    "unplaced": "error",
    "links_needed": "info",
    "assumption": "info",
}


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str
    message: dict  # {"uz": …, "ru": …, "en": …}
    assignment_id: int | None = None

    @classmethod
    def make(cls, code: str, ctx: ValidationContext, **params) -> Diagnostic:
        message = {}
        for lang in LANGS:
            with translation.override(lang):
                message[lang] = _render(code, ctx, lang, params)
        return cls(code, SEVERITY.get(code, "info"), message, params.get("assignment_id"))

    def as_dict(self) -> dict:
        return asdict(self)


def _render(code: str, ctx: ValidationContext, lang: str, p: dict) -> str:  # noqa: C901
    lesson = lesson_title(ctx, p["assignment_id"], lang) if "assignment_id" in p else ""
    teacher = ""
    if "assignment_id" in p:
        teacher = ctx.names.teachers.get(ctx.assignments[p["assignment_id"]].teacher_id, "")
    match code:
        case "teacher_language":
            return _(
                "%(lesson)s: %(teacher)s does not teach in the group's language. "
                "Choose another teacher in the workload."
            ) % {"lesson": lesson, "teacher": teacher}
        case "stream_language":
            return _("%(lesson)s: the stream joins groups with different teaching languages.") % {
                "lesson": lesson
            }
        case "no_room":
            return _(
                "%(lesson)s: no suitable room (%(students)s students, the biggest suitable "
                "room has %(biggest)s seats)."
            ) % {
                "lesson": lesson,
                "students": ctx.assignments[p["assignment_id"]].student_count,
                "biggest": p["biggest"],
            }
        case "no_time":
            return _(
                "%(lesson)s: no free time is left — study days, closed times and the "
                "teacher's unavailable times exclude everything."
            ) % {"lesson": lesson}
        case "fixed_conflicts":
            return _(
                "%(count)s conflicts are among the lessons that stay in place (pinned or "
                "outside the chosen scope). The solver works around them but cannot fix them."
            ) % {"count": p["count"]}
        case "teacher_overloaded":
            return _(
                "%(teacher)s has %(lessons)s lessons to place but only %(slots)s possible times."
            ) % {
                "teacher": ctx.names.teachers.get(p["teacher_id"], ""),
                "lessons": p["lessons"],
                "slots": p["slots"],
            }
        case "group_overloaded":
            return _(
                "%(group)s needs %(lessons)s lessons, but the daily limit allows only %(capacity)s."
            ) % {
                "group": ctx.groups[p["group_id"]].name,
                "lessons": p["lessons"],
                "capacity": p["capacity"],
            }
        case "unplaced":
            parts = []
            if p.get("teacher"):
                parts.append(_("teacher busy: %(n)s") % {"n": p["teacher"]})
            if p.get("group"):
                parts.append(_("group busy: %(n)s") % {"n": p["group"]})
            if p.get("daily"):
                parts.append(_("daily limit reached: %(n)s") % {"n": p["daily"]})
            if p.get("room"):
                parts.append(_("no free room: %(n)s") % {"n": p["room"]})
            return _(
                "%(lesson)s: %(missing)s lesson(s) not placed. All %(total)s possible times "
                "are taken (%(why)s)."
            ) % {
                "lesson": lesson,
                "missing": p["missing"],
                "total": p["total"],
                "why": ", ".join(parts) or "—",
            }
        case "links_needed":
            return _(
                "%(count)s distance lessons were placed without a link. Add the links in the "
                "editor before publishing."
            ) % {"count": p["count"]}
        case "assumption":
            return {
                "rooms": _(
                    "Each lesson may use the %(n)s smallest rooms that fit it; bigger rooms "
                    "are kept for bigger lessons."
                ),
                "weeks": _("Weekly forms are assumed to share week numbering (week 1 is odd)."),
                "soft": _(
                    "Building moves are reduced by keeping each group in few buildings; the "
                    "lecture-before-seminar order is scored after the search, not optimised."
                ),
            }[p["which"]] % p
    return code
