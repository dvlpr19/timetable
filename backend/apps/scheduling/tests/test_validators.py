"""Hard constraints: at least one "violated" and one "satisfied" case each, plus the
cross-form, odd/even and session-date-vs-weekday cases."""

from datetime import date

import pytest

from apps.scheduling.validators import Code, Validator, validate

from .world import (
    AHMEDOV,
    BUSY,
    COMPUTER,
    IS301,
    IS302,
    IS_M101,
    IS_S201,
    KARIMOV,
    ONLINE,
    RU201,
    SESSION,
    YUSUPOV,
    asg,
    dated,
    make_ctx,
    weekly,
)


def codes(placements, assignments, completeness=False):
    report = validate(placements, make_ctx(assignments), completeness=completeness)
    return sorted(v.code for v in report.violations)


# --- 1. teacher -------------------------------------------------------------------------


def test_1_teacher_in_two_groups_at_once():
    a, b = asg(YUSUPOV, (IS301,)), asg(YUSUPOV, (IS302,))
    assert codes([weekly(a, 0, 1), weekly(b, 0, 1, room="B-201")], [a, b]) == [Code.TEACHER_OVERLAP]


def test_1_teacher_in_consecutive_lessons_is_fine():
    a, b = asg(YUSUPOV, (IS301,)), asg(YUSUPOV, (IS302,))
    assert codes([weekly(a, 0, 1), weekly(b, 0, 2, room="B-201")], [a, b]) == []


def test_1_teacher_conflict_across_forms_session_date_vs_weekday():
    """Sirtqi 14 April (Tuesday) 10:00 vs the same teacher's weekly Tuesday lesson 2."""
    day = asg(YUSUPOV, (IS301,))
    ses = asg(YUSUPOV, (IS_S201,), period=SESSION, weekly=0, total=1)
    clash = [weekly(day, 1, 2), dated(ses, date(2026, 4, 14), 2, room="B-201")]
    assert codes(clash, [day, ses]) == [Code.TEACHER_OVERLAP]
    fine = [weekly(day, 1, 2), dated(ses, date(2026, 4, 14), 3, room="B-201")]
    assert codes(fine, [day, ses]) == []


def test_1_session_date_vs_odd_week_lesson_depends_on_the_week():
    """14 April is in week 8 (even): an odd-week lesson that Tuesday is not a conflict,
    but 7 April (week 7, odd) is."""
    day = asg(YUSUPOV, (IS301,), weekly=0, alternating=1, total=8)
    ses = asg(YUSUPOV, (IS_S201,), period=SESSION, weekly=0, total=1)
    odd = weekly(day, 1, 2, parity="odd")
    assert codes([odd, dated(ses, date(2026, 4, 14), 2, room="B-201")], [day, ses]) == []
    assert codes([odd, dated(ses, date(2026, 4, 7), 2, room="B-201")], [day, ses]) == [
        Code.TEACHER_OVERLAP
    ]


def test_1_odd_and_even_weeks_share_a_slot_but_not_with_every_week():
    a = asg(YUSUPOV, (IS301,), weekly=0, alternating=1)
    b = asg(YUSUPOV, (IS302,), weekly=0, alternating=1)
    c = asg(YUSUPOV, (RU201,), language="ru")
    odd, even = weekly(a, 2, 1, parity="odd"), weekly(b, 2, 1, parity="even", room="B-201")
    assert Code.TEACHER_OVERLAP not in codes([odd, even], [a, b])
    every = weekly(c, 2, 1, room="Ma'ruza zali")
    assert codes([odd, even, every], [a, b, c]).count(Code.TEACHER_OVERLAP) == 2


def test_1_session_saturday_vs_weekly_saturday():
    """A session lesson on Saturday 11 April meets the teacher's weekly Saturday lesson."""
    day = asg(YUSUPOV, (IS301,))
    ses = asg(YUSUPOV, (IS_S201,), period=SESSION, weekly=0, total=1)
    assert codes(
        [weekly(day, 5, 1), dated(ses, date(2026, 4, 11), 1, room="B-201")], [day, ses]
    ) == [Code.TEACHER_OVERLAP]


# --- 2. group ---------------------------------------------------------------------------


def test_2_group_in_two_lessons_at_once():
    a, b = asg(YUSUPOV, (IS301,)), asg(KARIMOV, (IS301,), subject=2)
    assert codes([weekly(a, 0, 1), weekly(b, 0, 1, room="B-201")], [a, b]) == [Code.GROUP_OVERLAP]


def test_2_subgroups_in_parallel_are_fine():
    a = asg(YUSUPOV, (IS301,), subgroup=1, lesson_type="practice", subject=3)
    b = asg(KARIMOV, (IS301,), subgroup=2, lesson_type="practice", subject=3)
    assert codes([weekly(a, 0, 1), weekly(b, 0, 1, room="B-201")], [a, b]) == []


def test_2_subgroup_and_whole_group_clash():
    a = asg(YUSUPOV, (IS301,), subgroup=1, lesson_type="practice", subject=3)
    whole = asg(KARIMOV, (IS301,), subject=2)
    assert codes([weekly(a, 0, 1), weekly(whole, 0, 1, room="B-201")], [a, whole]) == [
        Code.GROUP_OVERLAP
    ]


def test_2_stream_lecture_blocks_each_member_group():
    stream = asg(YUSUPOV, (IS301, IS302), stream=7)
    seminar = asg(KARIMOV, (IS302,), lesson_type="seminar", subject=2)
    lessons = [weekly(stream, 0, 1, room="Ma'ruza zali"), weekly(seminar, 0, 1, room="B-201")]
    assert codes(lessons, [stream, seminar]) == [Code.GROUP_OVERLAP]


# --- 3. room ----------------------------------------------------------------------------


def test_3_room_taken_twice():
    a, b = asg(YUSUPOV, (IS301,)), asg(KARIMOV, (IS302,))
    assert codes([weekly(a, 0, 1), weekly(b, 0, 1)], [a, b]) == [Code.ROOM_OVERLAP]


def test_3_stream_is_one_lesson_in_one_room():
    stream = asg(YUSUPOV, (IS301, IS302), stream=7)
    assert codes([weekly(stream, 0, 1, room="Ma'ruza zali")], [stream]) == []


def test_3_online_lessons_need_no_room():
    a = asg(YUSUPOV, (IS_M101,), period=ONLINE)
    b = asg(KARIMOV, (IS_M101,), period=ONLINE, subject=2)
    lessons = [
        weekly(a, 0, 1, room=None, form=ONLINE, url="https://meet.example/a"),
        weekly(b, 0, 2, room=None, form=ONLINE, url="https://meet.example/b"),
    ]
    assert codes(lessons, [a, b]) == []


# --- 4. capacity ------------------------------------------------------------------------


def test_4_stream_does_not_fit_small_room():
    stream = asg(YUSUPOV, (IS301, IS302), stream=7)  # 54 students
    assert codes([weekly(stream, 0, 1, room="A-101")], [stream]) == [Code.CAPACITY]
    assert codes([weekly(stream, 0, 1, room="Ma'ruza zali")], [stream]) == []


# --- 5. room type, room/link presence ---------------------------------------------------


def test_5_lab_needs_computer_room():
    lab = asg(KARIMOV, (IS301,), subgroup=1, lesson_type="lab", subject=2, room_type=COMPUTER)
    assert codes([weekly(lab, 2, 3, room="A-101")], [lab]) == [Code.ROOM_TYPE]
    assert codes([weekly(lab, 2, 3, room="Kompyuter")], [lab]) == []


def test_5_in_person_lesson_needs_room():
    a = asg(YUSUPOV, (IS301,))
    assert codes([weekly(a, 0, 1, room=None)], [a]) == [Code.ROOM_MISSING]


def test_5_online_lesson_needs_link():
    a = asg(YUSUPOV, (IS_M101,), period=ONLINE)
    assert codes([weekly(a, 0, 1, room=None, form=ONLINE)], [a]) == [Code.LINK_MISSING]
    assert codes([weekly(a, 0, 1, room=None, form=ONLINE, url="https://x.example")], [a]) == []


def test_5_room_out_of_use():
    a = asg(YUSUPOV, (IS301,))
    assert codes([weekly(a, 0, 1, room="Yopiq")], [a]) == [Code.ROOM_INACTIVE]


# --- 6. blocked times and days off ------------------------------------------------------


@pytest.mark.parametrize(("number", "blocked"), [(2, False), (3, True), (4, True), (5, False)])
def test_6_friday_prayer(number, blocked):
    a = asg(YUSUPOV, (IS301,))
    assert (codes([weekly(a, 4, number)], [a]) == [Code.BLOCKED_TIME]) is blocked


def test_6_friday_prayer_applies_to_session_dates_too():
    ses = asg(YUSUPOV, (IS_S201,), period=SESSION, weekly=0, total=1)
    assert codes([dated(ses, date(2026, 4, 10), 3)], [ses]) == [Code.BLOCKED_TIME]
    assert codes([dated(ses, date(2026, 4, 10), 2)], [ses]) == []


def test_6_session_lesson_on_a_day_off():
    ses = asg(YUSUPOV, (IS_S201,), period=SESSION, weekly=0, total=1)
    assert codes([dated(ses, date(2026, 4, 18), 1)], [ses]) == [Code.HOLIDAY]


# --- 7. bell schedule, study days, period -----------------------------------------------


def test_7_sunday_is_not_a_study_day():
    a = asg(YUSUPOV, (IS301,))
    assert codes([weekly(a, 6, 1)], [a]) == [Code.OUTSIDE_BELL]


def test_7_lesson_time_of_another_form():
    a = asg(YUSUPOV, (IS301,))
    assert codes([weekly(a, 0, 1, form=ONLINE)], [a]) == [Code.OUTSIDE_BELL]


def test_7_session_form_needs_dates_not_weekdays():
    ses = asg(YUSUPOV, (IS_S201,), period=SESSION, weekly=0, total=1)
    assert codes([weekly(ses, 0, 1, form=SESSION)], [ses]) == [Code.OUTSIDE_BELL]


def test_7_session_date_outside_the_session():
    ses = asg(YUSUPOV, (IS_S201,), period=SESSION, weekly=0, total=1)
    assert codes([dated(ses, date(2026, 5, 4), 1)], [ses]) == [Code.OUTSIDE_PERIOD]
    assert codes([dated(ses, date(2026, 4, 20), 1)], [ses]) == []


# --- 8. teacher availability ------------------------------------------------------------


def test_8_teacher_unavailable_whole_day_and_single_lesson():
    a = asg(BUSY, (IS301,))
    assert codes([weekly(a, 0, 3)], [a]) == [Code.TEACHER_UNAVAILABLE]  # all Monday
    assert codes([weekly(a, 1, 1)], [a]) == [Code.TEACHER_UNAVAILABLE]  # Tuesday lesson 1
    assert codes([weekly(a, 1, 2)], [a]) == []


# --- 9. completeness --------------------------------------------------------------------


def test_9_missing_lessons_are_reported_but_are_not_conflicts():
    a = asg(YUSUPOV, (IS301,), weekly=2, total=30)
    report = validate([weekly(a, 0, 1)], make_ctx([a]))
    assert [v.code for v in report.violations] == [Code.PLAN_INCOMPLETE]
    assert report.violations[0].params["placed"] == 1
    assert report.conflicts == []


def test_9_too_many_lessons_is_a_conflict():
    a = asg(YUSUPOV, (IS301,))
    assert codes([weekly(a, 0, 1), weekly(a, 1, 1)], [a]) == [Code.PLAN_EXCESS]


def test_9_weekly_plus_alternating_and_session_totals():
    a = asg(YUSUPOV, (IS301,), weekly=1, alternating=1, total=23)
    ses = asg(KARIMOV, (IS_S201,), period=SESSION, weekly=0, total=2, subject=2)
    placed = [
        weekly(a, 0, 1),
        weekly(a, 2, 1, parity="odd"),
        dated(ses, date(2026, 4, 6), 1, room="B-201"),  # A-101 is busy on Mondays
        dated(ses, date(2026, 4, 7), 1, room="B-201"),
    ]
    assert codes(placed, [a, ses], completeness=True) == []


# --- 10. daily limit --------------------------------------------------------------------


def test_10_five_lessons_a_day_is_too_many():
    lessons = [asg(YUSUPOV + (n % 2), (IS301,), subject=n) for n in range(5)]
    rooms = ["A-101", "B-201"]
    placed = [weekly(a, 0, n + 1, room=rooms[n % 2]) for n, a in enumerate(lessons)]
    assert codes(placed, lessons) == [Code.DAILY_LIMIT]
    assert codes(placed[:4], lessons[:4]) == []


def test_10_subgroup_lessons_count_per_student():
    """3 whole-group lessons + one lesson for each subgroup = 4 per student, not 5."""
    whole = [asg(YUSUPOV + (n % 2), (IS301,), subject=n) for n in range(3)]
    sg1 = asg(YUSUPOV, (IS301,), subgroup=1, lesson_type="practice", subject=3)
    sg2 = asg(KARIMOV, (IS301,), subgroup=2, lesson_type="practice", subject=3)
    placed = [weekly(a, 0, n + 1, room=["A-101", "B-201"][n % 2]) for n, a in enumerate(whole)]
    placed += [weekly(sg1, 0, 4), weekly(sg2, 0, 4, room="B-201")]
    assert codes(placed, [*whole, sg1, sg2]) == []


def test_10_distance_learning_limit_is_two():
    a = asg(YUSUPOV, (IS_M101,), period=ONLINE)
    b = asg(KARIMOV, (IS_M101,), period=ONLINE, subject=2)
    c = asg(YUSUPOV, (IS_M101,), period=ONLINE, subject=3)
    placed = [
        weekly(a, 0, 1, room=None, form=ONLINE, url="https://x.example/1"),
        weekly(b, 0, 2, room=None, form=ONLINE, url="https://x.example/2"),
        weekly(c, 1, 1, room=None, form=ONLINE, url="https://x.example/3"),
    ]
    assert codes(placed, [a, b, c]) == []
    placed[2] = weekly(c, 0, 1, room=None, form=ONLINE, url="https://x.example/3")
    assert Code.DAILY_LIMIT in codes(placed, [a, b, c])


# --- 11. teaching language --------------------------------------------------------------


def test_11_teacher_must_speak_the_group_language():
    wrong = asg(KARIMOV, (RU201,), language="ru")
    right = asg(AHMEDOV, (RU201,), language="ru")
    assert codes([weekly(wrong, 0, 1)], [wrong]) == [Code.TEACHER_LANGUAGE]
    assert codes([weekly(right, 0, 1)], [right]) == []


def test_11_stream_cannot_mix_languages():
    mixed = asg(YUSUPOV, (IS301, RU201), stream=8, language="uz")
    assert Code.STREAM_LANGUAGE in codes([weekly(mixed, 0, 1, room="Ma'ruza zali")], [mixed])


# --- incremental checks (drag-and-drop) -------------------------------------------------


def test_candidate_check_ignores_its_own_old_position():
    a, b = asg(YUSUPOV, (IS301,)), asg(KARIMOV, (IS302,), subject=2)
    v = Validator(make_ctx([a, b]), [weekly(a, 0, 1, key="a"), weekly(b, 0, 2, key="b")])
    assert v.check(weekly(a, 0, 1, key="a")) == []  # dropped back where it was
    moved = v.check(weekly(a, 0, 2, key="a"))  # onto b's room and time
    assert [x.code for x in moved] == [Code.ROOM_OVERLAP]
    assert v.check(weekly(a, 0, 3, key="a")) == []


def test_removed_lesson_no_longer_blocks():
    a, b = asg(YUSUPOV, (IS301,)), asg(KARIMOV, (IS302,), subject=2)
    v = Validator(make_ctx([a, b]), [weekly(a, 0, 1, key="a")])
    assert v.check(weekly(b, 0, 1, key="b"))
    v.remove("a")
    assert v.check(weekly(b, 0, 1, key="b")) == []
