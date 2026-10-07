"""Expand timetable entries into dated occurrences (the shared time axis of all forms)."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime

from django.db import transaction
from django.db.backends.postgresql.psycopg_any import DateTimeTZRange
from django.utils import timezone

from apps.academics.choices import CalendarDayKind, WeekParity
from apps.academics.models import AcademicCalendarDay, TeachingPeriod

from ..models import EntryOccurrence, OccurrenceStatus, ScheduleEntry


@dataclass
class CalendarIndex:
    """Holidays/day-offs and transferred working days, keyed by date."""

    days_off: set[date] = field(default_factory=set)
    workday_as: dict[date, int] = field(default_factory=dict)

    @classmethod
    def load(cls, start: date | None = None, end: date | None = None) -> "CalendarIndex":
        qs = AcademicCalendarDay.objects.all()
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        index = cls()
        for day in qs:
            if day.kind == CalendarDayKind.WORKDAY:
                index.workday_as[day.date] = day.works_as_weekday
            else:
                index.days_off.add(day.date)
        return index

    def effective_weekday(self, day: date) -> int:
        return self.workday_as.get(day, day.weekday())


def parity_matches(parity: str, week_number: int) -> bool:
    if parity == WeekParity.EVERY:
        return True
    return (week_number % 2 == 1) == (parity == WeekParity.ODD)


def lesson_dates(
    entry: ScheduleEntry, period: TeachingPeriod, calendar: CalendarIndex
) -> list[tuple[date, str]]:
    """(date, status) pairs for an entry. Lessons on days off need rescheduling."""
    if entry.date is not None:
        status = (
            OccurrenceStatus.NEEDS_RESCHEDULE
            if entry.date in calendar.days_off
            else OccurrenceStatus.SCHEDULED
        )
        return [(entry.date, status)]

    result = []
    for day in period.dates():
        if not parity_matches(entry.week_parity, period.week_number(day)):
            continue
        if day in calendar.days_off:
            if day.weekday() == entry.weekday:
                result.append((day, OccurrenceStatus.NEEDS_RESCHEDULE))
        elif calendar.effective_weekday(day) == entry.weekday:
            result.append((day, OccurrenceStatus.SCHEDULED))
    return result


def time_range(day: date, entry: ScheduleEntry) -> DateTimeTZRange:
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, entry.lesson_time.start), tz)
    end = timezone.make_aware(datetime.combine(day, entry.lesson_time.end), tz)
    return DateTimeTZRange(start, end, "[)")


def build_occurrences(entry: ScheduleEntry, calendar: CalendarIndex) -> list[EntryOccurrence]:
    assignment = entry.assignment
    slots = assignment.slot_keys()
    return [
        EntryOccurrence(
            entry=entry,
            schedule_id=entry.schedule_id,
            date=day,
            during=time_range(day, entry),
            teacher_id=assignment.teacher_id,
            room_id=entry.room_id,
            slot_keys=slots,
            status=status,
        )
        for day, status in lesson_dates(entry, assignment.period, calendar)
    ]


@transaction.atomic
def sync_occurrences(
    entries: Iterable[ScheduleEntry], calendar: CalendarIndex | None = None
) -> int:
    """Regenerate occurrences of the given entries. Raises IntegrityError on a conflict."""
    entries = list(entries)
    calendar = calendar or CalendarIndex.load()
    EntryOccurrence.objects.filter(entry__in=entries).delete()
    rows = [occ for entry in entries for occ in build_occurrences(entry, calendar)]
    EntryOccurrence.objects.bulk_create(rows, batch_size=2000)
    return len(rows)
