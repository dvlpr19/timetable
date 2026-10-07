"""Database-level protection: exclusion and check constraints reject bad rows even when
application code is bypassed (manual inserts, bugs)."""

from datetime import date

import pytest
from django.db import IntegrityError, transaction

from apps.academics.models import (
    CurriculumItem,
    Group,
    LessonTime,
    LessonType,
    Room,
    Subject,
    Teacher,
    TeachingAssignment,
    TeachingPeriod,
)
from apps.scheduling.models import Schedule, ScheduleEntry
from apps.scheduling.services.occurrences import sync_occurrences

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx(demo):
    return {
        "schedule": Schedule.objects.get(status="published"),
        "daytime": TeachingPeriod.objects.get(form__code="kunduzgi"),
        "session": TeachingPeriod.objects.get(form__code="sirtqi"),
        "lt": {n: LessonTime.objects.get(form__code="kunduzgi", number=n) for n in range(1, 7)},
        "lecture": LessonType.objects.get(code="lecture"),
        "subject": Subject.objects.get(code="TAF"),
    }


def assignment(ctx, teacher, period=None, **target):
    return TeachingAssignment.objects.create(
        period=period or ctx["daytime"],
        teacher=Teacher.objects.get(last_name=teacher),
        subject=ctx["subject"],
        lesson_type=ctx["lecture"],
        total_lessons=15,
        weekly_lessons=1,
        **target,
    )


def place(ctx, a, *, weekday=None, number=1, parity="every", day=None, room=None, url=""):
    entry = ScheduleEntry.objects.create(
        schedule=ctx["schedule"],
        assignment=a,
        lesson_time=ctx["lt"][number],
        weekday=None if day else weekday,
        week_parity=None if day else parity,
        date=day,
        room=Room.objects.get(name=room) if room else None,
        online_url=url,
    )
    sync_occurrences([entry])
    return entry


def rejected(fn, *args, **kwargs):
    with pytest.raises(IntegrityError), transaction.atomic():
        fn(*args, **kwargs)
    return True


# Yusupov teaches IS-301/302 Tafsir lecture on Monday, lesson 1, in Ma'ruza zali 1.


def test_teacher_cannot_be_in_two_places(ctx):
    a = assignment(ctx, "Yusupov", group=Group.objects.get(name="IS-201"))
    assert rejected(place, ctx, a, weekday=0, number=1, room="A-301")


def test_room_cannot_host_two_lessons(ctx):
    a = assignment(ctx, "Olimov", group=Group.objects.get(name="IS-201"))
    assert rejected(place, ctx, a, weekday=0, number=1, room="Ma'ruza zali 1")


def test_group_cannot_attend_two_lessons(ctx):
    a = assignment(ctx, "Olimov", group=Group.objects.get(name="IS-302"))  # in the stream
    assert rejected(place, ctx, a, weekday=0, number=1, room="A-301")


def test_session_date_conflicts_with_weekly_lesson_of_another_form(ctx):
    """Sirtqi 6 April (Monday) 08:30 vs Yusupov's weekly Monday lesson 1 (kunduzgi)."""
    a = assignment(ctx, "Yusupov", ctx["session"], group=Group.objects.get(name="IS-S-201"))
    assert rejected(place, ctx, a, day=date(2026, 4, 6), number=1, room="A-301")
    place(ctx, a, day=date(2026, 4, 6), number=3, room="A-301")  # lesson 3 is free


def test_odd_and_even_weeks_share_a_slot(ctx):
    g = Group.objects.get(name="IS-201")
    odd = assignment(ctx, "Olimov", group=g)
    even = assignment(ctx, "Olimov", group=g)
    place(ctx, odd, weekday=6, number=6, parity="odd", room="A-301")
    place(ctx, even, weekday=6, number=6, parity="even", room="A-301")
    every = assignment(ctx, "Olimov", group=g)
    assert rejected(place, ctx, every, weekday=6, number=6, parity="every", room="A-304")


def test_subgroups_run_in_parallel_but_not_with_the_whole_group(ctx):
    g = Group.objects.get(name="IS-101")
    sg1, sg2 = g.subgroups.order_by("number")
    place(ctx, assignment(ctx, "Olimov", subgroup=sg1), weekday=6, number=5, room="A-301")
    place(ctx, assignment(ctx, "Sultonova", subgroup=sg2), weekday=6, number=5, room="A-304")
    whole = assignment(ctx, "Xolmatov", group=g)
    assert rejected(place, ctx, whole, weekday=6, number=5, room="B-308")
    same_sub = assignment(ctx, "Xolmatov", subgroup=sg1)
    assert rejected(place, ctx, same_sub, weekday=6, number=5, room="B-308")


def test_online_lessons_do_not_occupy_rooms_but_still_need_free_teacher(ctx):
    m1, m2 = Group.objects.get(name="IS-M-101"), Group.objects.get(name="IS-M-201")
    place(
        ctx,
        assignment(ctx, "Olimov", group=m1),
        weekday=0,
        number=6,
        url="https://meet.example.com/a",
    )
    place(
        ctx,
        assignment(ctx, "Sultonova", group=m2),
        weekday=0,
        number=6,
        url="https://meet.example.com/b",
    )
    # Yusupov has the Tafsir seminar on Monday, lesson 2: online does not make him free.
    busy = assignment(ctx, "Yusupov", group=m1)
    assert rejected(place, ctx, busy, weekday=0, number=2, url="https://meet.example.com/c")


def test_cancelled_lesson_frees_the_slot(ctx):
    """Yusupov's Tafsir seminar on 13 April (lesson 2) is cancelled in the demo data."""
    a = assignment(ctx, "Yusupov", ctx["session"], group=Group.objects.get(name="IS-S-201"))
    place(ctx, a, day=date(2026, 4, 13), number=2, room="A-301")


def test_entry_is_weekly_or_dated_not_both(ctx):
    a = assignment(ctx, "Olimov", group=Group.objects.get(name="IS-201"))
    assert rejected(
        ScheduleEntry.objects.create,
        schedule=ctx["schedule"],
        assignment=a,
        lesson_time=ctx["lt"][1],
        weekday=6,
        week_parity="every",
        date=date(2026, 4, 12),
        room=Room.objects.get(name="A-301"),
    )


def test_entry_needs_room_or_link(ctx):
    a = assignment(ctx, "Olimov", group=Group.objects.get(name="IS-201"))
    assert rejected(
        ScheduleEntry.objects.create,
        schedule=ctx["schedule"],
        assignment=a,
        lesson_time=ctx["lt"][1],
        weekday=6,
        week_parity="every",
    )


def test_assignment_has_exactly_one_target(ctx):
    g = Group.objects.get(name="IS-201")
    assert rejected(assignment, ctx, "Olimov", group=g, subgroup=g.subgroups.first())


def test_credit_hours_must_add_up(ctx):
    item = CurriculumItem.objects.first()
    item.hours_independent += 2
    assert rejected(item.save)
