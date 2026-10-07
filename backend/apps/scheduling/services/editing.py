"""Timetable editing: every change is validated, expanded into dated lessons and recorded
in ScheduleChange so it can be undone and announced (notifications, stage 8)."""

import uuid
from dataclasses import dataclass, field
from datetime import date

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.academics.models import Student, TeachingAssignment

from ..models import (
    ChangeAction,
    EntryOccurrence,
    OccurrenceStatus,
    Schedule,
    ScheduleChange,
    ScheduleEntry,
    ScheduleStatus,
)
from ..validators import (
    Placement,
    ValidationContext,
    Validator,
    Violation,
    load_context,
    placements_from_entries,
)
from .occurrences import CalendarIndex, sync_occurrences

ENTRY_FIELDS = (
    "assignment_id",
    "lesson_time_id",
    "weekday",
    "week_parity",
    "date",
    "room_id",
    "online_url",
    "is_locked",
    "note",
)


class ConflictError(Exception):
    """The change breaks hard constraints; `violations` explain why."""

    def __init__(self, violations: list[Violation], validator: Validator):
        super().__init__("conflicts")
        self.violations = violations
        self.validator = validator


def snapshot(entry: ScheduleEntry) -> dict:
    data = {f: getattr(entry, f) for f in ENTRY_FIELDS}
    data["date"] = data["date"].isoformat() if data["date"] else None
    return data


def to_placement(data: dict, key) -> Placement:
    return Placement(
        key=key,
        assignment_id=data["assignment_id"],
        lesson_time_id=data["lesson_time_id"],
        weekday=data.get("weekday"),
        week_parity=data.get("week_parity"),
        date=date.fromisoformat(data["date"])
        if isinstance(data.get("date"), str)
        else data.get("date"),
        room_id=data.get("room_id"),
        online_url=data.get("online_url") or "",
        is_locked=bool(data.get("is_locked")),
    )


@dataclass
class Editor:
    """Applies a batch of edits to one timetable version atomically."""

    schedule: Schedule
    user: object = None
    comment: str = ""
    batch: uuid.UUID = field(default_factory=uuid.uuid4)
    reverts: uuid.UUID | None = None

    def __post_init__(self):
        self.ctx: ValidationContext = load_context(self.schedule.semester)
        self.validator = Validator(self.ctx, placements_from_entries(self.schedule.entries.all()))
        self.changes: list[ScheduleChange] = []
        self._announcing = False

    # -- checks
    def check(self, data: dict, key="candidate") -> list[Violation]:
        return [v for v in self.validator.check(to_placement(data, key)) if not v.is_completeness]

    # -- edits
    def create(self, data: dict, *, force: bool = False) -> ScheduleEntry:
        violations = self.check(data)
        if violations and not force:
            raise ConflictError(violations, self.validator)
        entry = ScheduleEntry(schedule=self.schedule, **_model_kwargs(data))
        self._save(entry)
        self._record(entry, ChangeAction.CREATE, None, snapshot(entry))
        return entry

    def update(self, entry: ScheduleEntry, data: dict, *, force: bool = False) -> ScheduleEntry:
        before = snapshot(entry)
        after = {**before, **data}
        violations = self.check(after, key=entry.pk)
        if violations and not force:
            raise ConflictError(violations, self.validator)
        for name, value in _model_kwargs(after).items():
            setattr(entry, name, value)
        self._save(entry)
        self._record(entry, ChangeAction.UPDATE, before, snapshot(entry))
        return entry

    def delete(self, entry: ScheduleEntry) -> None:
        before = snapshot(entry)
        self.validator.remove(entry.pk)
        self._record(entry, ChangeAction.DELETE, before, None)
        entry.delete()

    def cancel_occurrence(self, entry: ScheduleEntry, day: date, *, restore: bool = False):
        """Cancel (or restore) one dated lesson, e.g. "teacher is ill on 13 April"."""
        occ = EntryOccurrence.objects.get(entry=entry, date=day)
        new = OccurrenceStatus.SCHEDULED if restore else OccurrenceStatus.CANCELLED
        old = occ.status
        occ.status = new
        try:
            with transaction.atomic():
                occ.save(update_fields=["status"])
        except IntegrityError as e:  # restoring onto a slot that is now taken
            raise ConflictError([], self.validator) from e
        self._record(
            entry,
            ChangeAction.CANCEL if not restore else ChangeAction.UPDATE,
            {"status": old},
            {"status": new},
            occurrence_date=day,
        )

    # -- internals
    def _save(self, entry: ScheduleEntry) -> None:
        try:
            with transaction.atomic():
                entry.save()
                entry = ScheduleEntry.objects.select_related(
                    "lesson_time",
                    "assignment__period",
                    "assignment__group",
                    "assignment__stream",
                    "assignment__subgroup__group",
                ).get(pk=entry.pk)
                sync_occurrences([entry], CalendarIndex.load())
        except IntegrityError as e:
            # The database caught a conflict the validator could not see (e.g. a concurrent
            # edit). Report it the same way.
            raise ConflictError([], self.validator) from e
        self.validator.add(placements_from_entries(ScheduleEntry.objects.filter(pk=entry.pk))[0])

    def _record(self, entry, action, before, after, occurrence_date=None) -> None:
        self.changes.append(
            ScheduleChange.objects.create(
                schedule=self.schedule,
                entry=entry if action != ChangeAction.DELETE else None,
                batch=self.batch,
                reverts=self.reverts,
                action=action,
                before=before,
                after=after,
                occurrence_date=occurrence_date,
                comment=self.comment,
                user=self.user if getattr(self.user, "is_authenticated", False) else None,
                # Drafts are nobody's business yet; published changes wait for announcement.
                notified=self.schedule.status != ScheduleStatus.PUBLISHED,
            )
        )
        if self.schedule.status == ScheduleStatus.PUBLISHED and not self._announcing:
            from apps.notifications.tasks import after_commit, announce_changes

            self._announcing = True  # one announcement per batch of edits
            after_commit(announce_changes, self.schedule.pk)


def _model_kwargs(data: dict) -> dict:
    kwargs = {f: data.get(f) for f in ENTRY_FIELDS if f in data}
    if isinstance(kwargs.get("date"), str):
        kwargs["date"] = date.fromisoformat(kwargs["date"])
    kwargs["online_url"] = kwargs.get("online_url") or ""
    kwargs["note"] = kwargs.get("note") or ""
    kwargs["is_locked"] = bool(kwargs.get("is_locked"))
    return kwargs


@transaction.atomic
def undo_last(schedule: Schedule, user=None) -> list[ScheduleChange]:
    """Revert the most recent batch that is not undone yet. Returns the reverting changes."""
    last = (
        ScheduleChange.objects.filter(schedule=schedule, undone=False, reverts__isnull=True)
        .order_by("-created_at", "-pk")
        .first()
    )
    if last is None:
        return []
    batch = list(
        ScheduleChange.objects.filter(batch=last.batch).order_by("-pk").select_related("entry")
    )
    editor = Editor(schedule, user=user, comment=last.comment, reverts=last.batch)
    for change in batch:
        entry = change.entry
        if change.occurrence_date:
            editor.cancel_occurrence(
                entry, change.occurrence_date, restore=change.after["status"] == "cancelled"
            )
        elif change.action == ChangeAction.CREATE and entry:
            editor.delete(entry)
        elif change.action == ChangeAction.DELETE:
            editor.create(change.before, force=True)
        elif change.action == ChangeAction.UPDATE and entry:
            editor.update(entry, change.before, force=True)
    ScheduleChange.objects.filter(batch=last.batch).update(undone=True)
    return editor.changes


def affected_people(assignment_ids: set[int], extra_teacher_ids: set[int] = frozenset()):
    """(students, teachers) who must hear about a change to these lessons."""
    assignments = TeachingAssignment.objects.filter(pk__in=assignment_ids).select_related(
        "subgroup"
    )
    students = Student.objects.none()
    teacher_ids = set(extra_teacher_ids)
    for a in assignments:
        teacher_ids.add(a.teacher_id)
        if a.subgroup_id:
            students = students | Student.objects.filter(subgroup_id=a.subgroup_id)
        else:
            students = students | Student.objects.filter(
                group__in=[g.pk for g in a.target_groups()]
            )
    return students.distinct(), teacher_ids


def publish(schedule: Schedule) -> None:
    with transaction.atomic():
        Schedule.objects.filter(
            semester=schedule.semester, status=ScheduleStatus.PUBLISHED
        ).exclude(pk=schedule.pk).update(status=ScheduleStatus.ARCHIVED)
        schedule.status = ScheduleStatus.PUBLISHED
        schedule.published_at = timezone.now()
        schedule.save(update_fields=["status", "published_at"])
        from apps.notifications.tasks import after_commit, announce_publication

        after_commit(announce_publication, schedule.pk)


@transaction.atomic
def copy_schedule(source: Schedule, *, name: str, user=None, exclude=()) -> Schedule:
    """A new draft with the same entries and cancellations (minus `exclude` entry ids)."""
    draft = Schedule.objects.create(
        semester=source.semester, name=name, based_on=source, created_by=user
    )
    entries = list(source.entries.exclude(pk__in=exclude))
    old_pks = [e.pk for e in entries]
    for entry in entries:
        entry.pk = None
        entry.schedule = draft
    ScheduleEntry.objects.bulk_create(entries, batch_size=1000)
    mapping = dict(zip(old_pks, entries, strict=True))
    occurrences = []
    for occ in EntryOccurrence.objects.filter(schedule=source, entry__in=old_pks):
        occ.pk = None
        occ.schedule = draft
        occ.entry = mapping[occ.entry_id]
        occurrences.append(occ)
    EntryOccurrence.objects.bulk_create(occurrences, batch_size=2000)
    return draft
