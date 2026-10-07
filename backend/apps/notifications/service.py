"""Who gets which message.

Every message is created once per person (unique dedup key), in that person's language,
honouring their settings (cancellations and time changes cannot be switched off).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import timedelta

from django.db import transaction
from django.db.models import Q

from apps.academics.models import LessonTime, Room, Teacher, TeachingAssignment
from apps.accounts.models import User
from apps.core import clock
from apps.scheduling.models import (
    ChangeAction,
    EntryOccurrence,
    OccurrenceStatus,
    Schedule,
    ScheduleChange,
    ScheduleStatus,
)
from apps.scheduling.services.editing import affected_people

from .channels import CHANNELS
from .models import Notification, NotificationKind, NotificationPreference
from .rendering import render

log = logging.getLogger(__name__)

TIME_FIELDS = ("weekday", "week_parity", "date", "lesson_time_id")


def _names(obj) -> dict:
    return {lang: getattr(obj, f"name_{lang}") or "" for lang in ("uz", "ru", "en")}


# --------------------------------------------------------------------------- creating


def notify(
    users,
    kind: str,
    params: dict,
    *,
    key: str,
    entry=None,
    change=None,
    comment: str = "",
) -> list[Notification]:
    """Create the message for everyone who wants it; return the new rows (then pushed)."""
    users = [u for u in {u.pk: u for u in users}.values() if u.is_active]
    if not users:
        return []
    already = set(
        Notification.objects.filter(dedup_key=key, recipient__in=users).values_list(
            "recipient_id", flat=True
        )
    )
    users = [u for u in users if u.pk not in already]
    prefs = {p.user_id: p for p in NotificationPreference.objects.filter(user__in=users)}
    rows = []
    for user in users:
        pref = prefs.get(user.pk)
        if pref and not pref.allows(kind):
            continue
        lang = user.language or "uz"
        title, body = render(kind, params, lang)
        rows.append(
            Notification(
                recipient=user,
                kind=kind,
                params=params,
                language=lang,
                title=title,
                body=body,
                comment=comment,
                entry=entry,
                change=change,
                dedup_key=key,
            )
        )
    # ignore_conflicts: a parallel worker may have created some of them a moment ago
    Notification.objects.bulk_create(rows, ignore_conflicts=True)
    return list(
        Notification.objects.filter(
            dedup_key=key, recipient__in=[r.recipient_id for r in rows], pushed_at__isnull=True
        )
    )


def deliver(notifications: list[Notification]) -> None:
    for channel in CHANNELS:
        try:
            channel.send(notifications)
        except Exception:  # a broken channel must not block the others
            log.exception("channel %s failed", channel.name)


def users_for(assignment_ids: set[int], extra_teachers: set[int] = frozenset()) -> list[User]:
    students, teacher_ids = affected_people(assignment_ids, set(extra_teachers))
    return list(
        User.objects.filter(
            Q(student__in=students) | Q(teacher__in=Teacher.objects.filter(pk__in=teacher_ids))
        ).distinct()
    )


# --------------------------------------------------------------------------- timetable changes


def _when(snap: dict) -> dict:
    return {"date": snap["date"]} if snap.get("date") else {"weekday": snap["weekday"]}


def describe_change(change: ScheduleChange) -> tuple[str, dict, set[int], set[int]] | None:
    """(kind, params, assignment ids, extra teacher ids) — or None for silent edits
    (pinning, notes)."""
    before, after = change.before or {}, change.after or {}
    snap = after or before
    entry = change.entry
    if change.occurrence_date:  # one date cancelled or restored
        e = entry
        params = {
            "when": {"date": change.occurrence_date.isoformat()},
            "number": e.lesson_time.number,
            "subject": _names(e.assignment.subject),
        }
        kind = (
            NotificationKind.CANCELLED
            if (after or {}).get("status") == OccurrenceStatus.CANCELLED
            else NotificationKind.LESSON_ADDED
        )
        if kind == NotificationKind.LESSON_ADDED:
            params["room"] = e.room.name if e.room_id else e.online_url
        return kind, params, {e.assignment_id}, set()

    assignment = TeachingAssignment.objects.select_related("subject", "teacher").get(
        pk=snap["assignment_id"]
    )
    number = LessonTime.objects.get(pk=snap["lesson_time_id"]).number
    base = {"when": _when(snap), "number": number, "subject": _names(assignment.subject)}
    if change.action == ChangeAction.CREATE:
        room = Room.objects.filter(pk=after.get("room_id")).first()
        return (
            NotificationKind.LESSON_ADDED,
            {**base, "room": room.name if room else after.get("online_url", "")},
            {assignment.pk},
            set(),
        )
    if change.action == ChangeAction.DELETE:
        return NotificationKind.CANCELLED, base, {assignment.pk}, set()

    # update: what changed decides the message
    old_number = LessonTime.objects.get(pk=before["lesson_time_id"]).number
    old = {**base, "when": _when(before), "number": old_number}
    ids = {before["assignment_id"], after["assignment_id"]}
    if any(before.get(f) != after.get(f) for f in TIME_FIELDS):
        return (
            NotificationKind.TIME_CHANGED,
            {**old, "new_when": _when(after), "new_number": number},
            ids,
            set(),
        )
    if before.get("room_id") != after.get("room_id"):
        rooms = Room.objects.in_bulk([before.get("room_id"), after.get("room_id")])
        name = lambda pk: rooms[pk].name if pk in rooms else "—"  # noqa: E731
        return (
            NotificationKind.ROOM_CHANGED,
            {
                **old,
                "old_room": name(before.get("room_id")),
                "new_room": name(after.get("room_id")),
            },
            ids,
            set(),
        )
    if before["assignment_id"] != after["assignment_id"]:
        old_a = TeachingAssignment.objects.select_related("teacher").get(pk=before["assignment_id"])
        if old_a.teacher_id != assignment.teacher_id:
            return (
                NotificationKind.TEACHER_CHANGED,
                {
                    **old,
                    "old_teacher": old_a.teacher.short_name,
                    "new_teacher": assignment.teacher.short_name,
                },
                ids,
                {old_a.teacher_id},
            )
    if (before.get("online_url") or "") != (after.get("online_url") or ""):
        return NotificationKind.LINK_CHANGED, old, ids, set()
    return None


def announce_changes(schedule_id: int) -> int:
    """Turn not yet announced edits of the published timetable into messages."""
    created_total: list[Notification] = []
    with transaction.atomic():
        pending = list(
            ScheduleChange.objects.select_for_update(skip_locked=True, of=("self",))
            .filter(
                schedule_id=schedule_id,
                schedule__status=ScheduleStatus.PUBLISHED,
                notified=False,
            )
            .select_related("entry__lesson_time", "entry__assignment__subject", "entry__room")
            .order_by("created_at", "pk")
        )
        skipped_batches = set()
        for change in pending:
            # an edit undone before anyone heard of it, and its undo, stay silent
            if change.undone or (change.reverts and change.reverts in skipped_batches):
                skipped_batches.add(change.batch)
                continue
            described = describe_change(change)
            if described is None:
                continue
            kind, params, assignment_ids, extra = described
            created_total += notify(
                users_for(assignment_ids, extra),
                kind,
                params,
                key=f"change:{change.pk}",
                entry=change.entry,
                change=change,
                comment=change.comment,
            )
        ScheduleChange.objects.filter(pk__in=[c.pk for c in pending]).update(notified=True)
    deliver(created_total)
    return len(created_total)


def announce_publication(schedule_id: int) -> int:
    schedule = Schedule.objects.select_related("semester__year").get(pk=schedule_id)
    users = list(
        User.objects.filter(
            Q(student__isnull=False) | Q(teacher__assignments__entries__schedule=schedule)
        ).distinct()
    )
    semester = schedule.semester
    names = {lang: str(semester) for lang in ("uz", "ru", "en")}
    created = notify(
        users,
        NotificationKind.SCHEDULE_PUBLISHED,
        {"semester": names},
        key=f"published:{schedule.pk}",
    )
    deliver(created)
    return len(created)


def announce_request_answer(request) -> int:
    entry = request.entry
    params = {
        "when": {"date": request.occurrence_date.isoformat()}
        if request.occurrence_date
        else _when({"weekday": entry.weekday, "date": entry.date and entry.date.isoformat()}),
        "number": entry.lesson_time.number,
        "subject": _names(entry.assignment.subject),
        "status": request.status,
    }
    user = request.teacher.user
    if user is None:
        return 0
    created = notify(
        [user],
        NotificationKind.REQUEST_ANSWERED,
        params,
        key=f"request:{request.pk}:{request.status}",
        entry=entry,
        comment=request.review_comment,
    )
    deliver(created)
    return len(created)


# --------------------------------------------------------------------------- reminders & digest


def _published_occurrences():
    return EntryOccurrence.objects.filter(
        schedule__status=ScheduleStatus.PUBLISHED, status=OccurrenceStatus.SCHEDULED
    ).select_related("entry__lesson_time", "entry__room", "entry__assignment__subject", "entry")


def send_reminders() -> int:
    """Every minute: "your lesson starts in N minutes" for people who asked for it."""
    now = clock.now()
    by_minutes: dict[int, set[int]] = defaultdict(set)
    for pref in NotificationPreference.objects.filter(reminder_enabled=True):
        by_minutes[pref.reminder_minutes].add(pref.user_id)
    created: list[Notification] = []
    for minutes, user_ids in by_minutes.items():
        start = now + timedelta(minutes=minutes)
        window = _published_occurrences().filter(
            during__startswith__gte=start.replace(second=0, microsecond=0),
            during__startswith__lt=start.replace(second=0, microsecond=0) + timedelta(minutes=1),
        )
        for occ in window:
            e = occ.entry
            users = [u for u in users_for({e.assignment_id}) if u.pk in user_ids]
            created += notify(
                users,
                NotificationKind.REMINDER,
                {
                    "subject": _names(e.assignment.subject),
                    "time": e.lesson_time.start.strftime("%H:%M"),
                    "room": e.room.name if e.room_id else "",
                    "minutes": minutes,
                },
                key=f"reminder:{occ.pk}",
                entry=e,
            )
    deliver(created)
    return len(created)


def send_daily_digest() -> int:
    """20:00: tomorrow's lessons in one message (only for people with lessons)."""
    tomorrow = clock.today() + timedelta(days=1)
    wanted = set(
        NotificationPreference.objects.filter(daily_digest_enabled=True).values_list(
            "user_id", flat=True
        )
    )
    if not wanted:
        return 0
    per_user: dict[int, list] = defaultdict(list)
    cache: dict[int, list[User]] = {}
    for occ in _published_occurrences().filter(date=tomorrow).order_by("during"):
        aid = occ.entry.assignment_id
        if aid not in cache:
            cache[aid] = users_for({aid})
        for user in cache[aid]:
            if user.pk in wanted:
                per_user[user.pk].append(occ)
    created: list[Notification] = []
    users = User.objects.in_bulk(per_user.keys())
    for user_id, occs in per_user.items():
        first = occs[0].entry
        created += notify(
            [users[user_id]],
            NotificationKind.DAILY_DIGEST,
            {
                "date": tomorrow.isoformat(),
                "count": len(occs),
                "subject": _names(first.assignment.subject),
                "time": first.lesson_time.start.strftime("%H:%M"),
            },
            key=f"digest:{tomorrow.isoformat()}",
        )
    deliver(created)
    return len(created)


__all__ = [
    "announce_changes",
    "announce_publication",
    "announce_request_answer",
    "describe_change",
    "deliver",
    "notify",
    "send_daily_digest",
    "send_reminders",
]
