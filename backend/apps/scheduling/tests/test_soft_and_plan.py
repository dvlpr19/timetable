from datetime import date

from apps.scheduling.validators import Soft, plan_fulfilment, soft_report

from .world import IS301, IS302, KARIMOV, YUSUPOV, asg, make_ctx, weekly


def report(placements, assignments, weights=None):
    return soft_report(placements, make_ctx(assignments), weights)


def test_student_gap_counts_free_lessons_between():
    a, b = asg(YUSUPOV, (IS301,)), asg(KARIMOV, (IS301,), subject=2)
    r = report([weekly(a, 0, 1), weekly(b, 0, 3, room="B-201")], [a, b])
    assert r.counts[Soft.STUDENT_GAPS] == 1


def test_friday_prayer_is_not_a_gap():
    a, b = asg(YUSUPOV, (IS301,)), asg(KARIMOV, (IS301,), subject=2)
    r = report([weekly(a, 4, 2), weekly(b, 4, 5)], [a, b])
    assert r.counts[Soft.STUDENT_GAPS] == 0  # lessons 3 and 4 are closed on Friday


def test_teacher_preference_and_gaps():
    a = asg(KARIMOV, (IS301,))
    b = asg(KARIMOV, (IS302,), subject=2)
    r = report([weekly(a, 0, 1), weekly(b, 0, 4, room="B-201")], [a, b])
    assert r.counts[Soft.TEACHER_GAPS] == 2
    assert r.counts[Soft.TEACHER_PREFERENCE] == 0  # Monday is a preferred day
    r = report([weekly(a, 3, 1)], [a])
    assert r.counts[Soft.TEACHER_PREFERENCE] == 1


def test_more_than_two_lessons_of_a_subject_a_day():
    lessons = [asg(YUSUPOV, (IS301,), subject=1) for _ in range(3)]
    placed = [weekly(a, 0, n + 1) for n, a in enumerate(lessons)]
    assert report(placed, lessons).counts[Soft.SUBJECT_CROWDING] == 1


def test_seminar_before_lecture():
    lec = asg(YUSUPOV, (IS301,), lesson_type="lecture")
    sem = asg(YUSUPOV, (IS301,), lesson_type="seminar")
    assert (
        report([weekly(lec, 2, 1), weekly(sem, 0, 1)], [lec, sem]).counts[Soft.LECTURE_ORDER] == 1
    )
    assert (
        report([weekly(lec, 0, 1), weekly(sem, 2, 1)], [lec, sem]).counts[Soft.LECTURE_ORDER] == 0
    )


def test_building_moves_and_shift_and_asr():
    a, b = asg(YUSUPOV, (IS301,)), asg(KARIMOV, (IS301,), subject=2)
    r = report([weekly(a, 0, 4, room="A-101"), weekly(b, 0, 5, room="B-201")], [a, b])
    assert r.counts[Soft.BUILDING_MOVES] == 1
    assert r.counts[Soft.BUILDING_SPREAD] == 1
    assert r.counts[Soft.SHIFT] == 2  # IS-301 studies in shift 1
    assert r.counts[Soft.SOFT_BLOCKED] == 1  # lesson 5 meets the asr break


def test_alternate_week_lessons_count_half():
    a = asg(YUSUPOV, (IS301,), weekly=0, alternating=1)
    r = report([weekly(a, 0, 4, parity="odd")], [a])
    assert r.counts[Soft.SHIFT] == 0.5


def test_score_is_weighted_sum():
    a, b = asg(YUSUPOV, (IS301,)), asg(KARIMOV, (IS301,), subject=2)
    lessons = [weekly(a, 0, 1), weekly(b, 0, 3, room="Ma'ruza zali")]  # same building
    r = report(lessons, [a, b], {Soft.STUDENT_GAPS: 7})
    assert r.score == 7


def test_plan_fulfilment_counts_holidays_as_lost():
    a = asg(YUSUPOV, (IS301,))
    # Saturdays: Navro'z (21 March) and 18 April are days off in the test calendar
    (row,) = plan_fulfilment([weekly(a, 5, 1)], make_ctx([a]))
    assert (row.planned, row.scheduled, row.lost) == (15, 13, 2)
    assert not row.matches


def test_cancelled_dates_are_lost_too():
    a = asg(YUSUPOV, (IS301,))
    p = weekly(a, 0, 1)
    p = type(p)(**{**p.__dict__, "cancelled_dates": frozenset({date(2026, 4, 13)})})
    (row,) = plan_fulfilment([p], make_ctx([a]))
    assert (row.scheduled, row.lost) == (14, 1)
