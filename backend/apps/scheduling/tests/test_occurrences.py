"""Expansion of entries into dated lessons (pure, no database)."""

from datetime import date, time

from apps.academics.models import LessonTime, TeachingPeriod
from apps.scheduling.models import OccurrenceStatus, ScheduleEntry
from apps.scheduling.services.occurrences import CalendarIndex, lesson_dates

# 15 teaching weeks: Mon 23 Feb – Sat 6 Jun 2026 (6–11 April is week 7)
PERIOD = TeachingPeriod(start_date=date(2026, 2, 23), end_date=date(2026, 6, 6), weeks_count=15)
LT = LessonTime(number=1, start=time(8, 30), end=time(9, 50))


def weekly(weekday: int, parity: str = "every") -> ScheduleEntry:
    return ScheduleEntry(weekday=weekday, week_parity=parity, lesson_time=LT)


def dates(entry, calendar=None):
    return lesson_dates(entry, PERIOD, calendar or CalendarIndex())


def test_week_numbering_matches_design():
    assert PERIOD.week_number(date(2026, 4, 6)) == 7
    assert PERIOD.week_number(date(2026, 4, 11)) == 7
    assert PERIOD.week_number(date(2026, 2, 23)) == 1


def test_every_week_gives_one_lesson_per_week():
    result = dates(weekly(0))
    assert len(result) == 15
    assert all(d.weekday() == 0 for d, _ in result)


def test_odd_and_even_weeks_split_and_never_meet():
    odd = {d for d, _ in dates(weekly(2, "odd"))}
    even = {d for d, _ in dates(weekly(2, "even"))}
    assert len(odd) == 8 and len(even) == 7
    assert not odd & even
    assert date(2026, 2, 25) in odd  # week 1


def test_holiday_marks_lesson_for_rescheduling():
    calendar = CalendarIndex(days_off={date(2026, 3, 21)})
    result = dict(dates(weekly(5), calendar))
    assert result[date(2026, 3, 21)] == OccurrenceStatus.NEEDS_RESCHEDULE
    assert result[date(2026, 3, 28)] == OccurrenceStatus.SCHEDULED


def test_transferred_working_day_follows_another_weekday():
    sunday = date(2026, 4, 12)
    calendar = CalendarIndex(workday_as={sunday: 0})
    result = dict(dates(weekly(0), calendar))
    assert result[sunday] == OccurrenceStatus.SCHEDULED
    assert len(result) == 16


def test_session_entry_is_its_own_date():
    entry = ScheduleEntry(date=date(2026, 4, 15), lesson_time=LT)
    assert dates(entry) == [(date(2026, 4, 15), OccurrenceStatus.SCHEDULED)]
