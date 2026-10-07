"""The validator on the real demo data, and its messages in all three languages."""

import pytest
from django.utils import translation

from apps.scheduling.models import Schedule
from apps.scheduling.validators import Code, Placement, Validator, describe, validate_schedule

pytestmark = pytest.mark.django_db


@pytest.fixture
def checked(demo):
    return validate_schedule(Schedule.objects.get(status="published"))


def test_seed_has_no_hard_conflicts(checked, demo):
    report, _ctx, _placements = checked
    assert report.conflicts == []
    assert demo["hard conflicts (validator)"] == 0
    # The rest of the academy is not placed yet: that is reported, not a conflict.
    assert {v.code for v in report.violations} == {Code.PLAN_INCOMPLETE}
    assert demo["lessons not yet placed"] > 0


def test_is301_plan_is_fully_placed(checked):
    """All 14 IS-301 assignments (17 weekly lessons) are placed exactly as planned."""
    report, ctx, _placements = checked
    is301 = next(g.id for g in ctx.groups.values() if g.name == "IS-301")
    incomplete = {v.params["assignment_id"] for v in report.violations}
    own = [a for a in ctx.assignments.values() if is301 in a.group_ids]
    assert len(own) == 14
    assert sum(a.weekly_lessons for a in own) == 17
    assert not [a.id for a in own if a.id in incomplete]


def moved(placement: Placement, **changes) -> Placement:
    return Placement(**{**placement.__dict__, **changes})


@pytest.mark.parametrize(
    ("lang", "expected"),
    [
        ("uz", "Yusupov S. bir vaqtda ikkita darsga qo'yilgan (Dushanba, 1-dars)"),
        ("ru", "У Yusupov S. два занятия одновременно (Понедельник, 1-я пара)"),
        ("en", "Yusupov S. has two lessons at the same time (Monday, lesson 1)"),
    ],
)
def test_conflict_message_in_each_language(checked, lang, expected):
    report, ctx, placements = checked
    v = Validator(ctx, placements.values())
    # Move the Tafsir seminar (Monday 2) onto the Tafsir lecture (Monday 1).
    seminar = next(
        p
        for p in placements.values()
        if p.weekday == 0 and ctx.lesson_times[p.lesson_time_id].number == 2
    )
    lecture_time = next(
        p.lesson_time_id
        for p in placements.values()
        if p.weekday == 0 and ctx.lesson_times[p.lesson_time_id].number == 1
    )
    candidate = moved(seminar, lesson_time_id=lecture_time, room_id=None)
    violations = v.check(candidate)
    teacher = next(x for x in violations if x.code == Code.TEACHER_OVERLAP)
    with translation.override(lang):
        text = describe(teacher, ctx, {**placements, candidate.key: candidate})
    assert text.startswith(expected), text
