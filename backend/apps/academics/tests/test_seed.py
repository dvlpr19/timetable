"""`seed_demo` must produce the documented dataset."""

import pytest
from django.db.models import Sum

from apps.academics.models import (
    CurriculumItem,
    Group,
    Room,
    Stream,
    Student,
    Teacher,
    TeachingAssignment,
)
from apps.accounts.models import Role, User
from apps.notifications.models import Notification
from apps.scheduling.models import EntryOccurrence, OccurrenceStatus, ScheduleEntry

pytestmark = pytest.mark.django_db


def test_counts(demo):
    assert demo["faculties"] == 2
    assert 20 <= Group.objects.filter(program_form__program__faculty__code="ISL").count() <= 22
    assert Group.objects.filter(teaching_language="ru").count() == 6
    assert demo["streams"] >= 3
    assert 28 <= demo["teachers"] <= 35
    assert demo["rooms"] == 28
    assert 550 <= demo["students"] <= 650


def test_students_match_group_sizes(demo):
    for group in Group.objects.all():
        assert group.students.count() == group.student_count, group.name
        assert group.subgroups.aggregate(n=Sum("student_count"))["n"] == group.student_count


def test_design_names_exist(demo):
    for last in (
        "Yusupov",
        "Karimov",
        "Rahimov",
        "Abdullayev",
        "Nazarova",
        "Toshmatov",
        "Mirzayev",
        "Qodirov",
        "Saidov",
    ):
        assert Teacher.objects.filter(last_name=last).exists(), last
    for room in (
        "Ma'ruza zali 1",
        "Ma'ruza zali 2",
        "Ma'ruza zali 3",
        "A-115",
        "A-204",
        "A-210",
        "B-112",
        "B-305",
        "Kompyuter xona 2",
    ):
        assert Room.objects.filter(name=room).exists(), room
    assert Student.objects.filter(
        group__name="IS-301", first_name="Aziza", last_name="Karimova"
    ).exists()


def test_every_plan_item_has_assignments(demo):
    for group in Group.objects.select_related("program_form__program", "program_form__form"):
        sem = group.study_semester("spring")
        plan = CurriculumItem.objects.filter(
            program=group.program_form.program, form=group.program_form.form, study_semester=sem
        )
        specific = plan.filter(teaching_language=group.teaching_language)
        plan = specific if specific.exists() else plan.filter(teaching_language="")
        assert plan.exists(), group.name
        for item in plan:
            assert any(group in a.target_groups() for a in item.assignments.all()), (
                group.name,
                item.subject.code,
            )


def test_teachers_speak_the_group_language_and_stay_within_load(demo):
    for teacher in Teacher.objects.prefetch_related("assignments"):
        weekly = sum(a.weekly_lessons for a in teacher.assignments.all())
        hours = sum(a.total_lessons * 2 for a in teacher.assignments.all())
        assert weekly <= teacher.max_weekly_lessons, teacher
        assert hours <= teacher.annual_load_hours / 2, teacher
        for a in teacher.assignments.all():
            assert teacher.can_teach_in(a.teaching_language), (teacher, a)


def test_some_teachers_teach_both_faculties_and_languages(demo):
    both = [
        t
        for t in Teacher.objects.all()
        if {a.teaching_language for a in t.assignments.all()} == {"uz", "ru"}
    ]
    assert both


def test_streams_join_groups_of_one_language(demo):
    for stream in Stream.objects.all():
        assert {g.teaching_language for g in stream.groups.all()} == {stream.teaching_language}


def test_is301_week_matches_design(demo):
    entries = ScheduleEntry.objects.filter(
        assignment__group__name="IS-301"
    ) | ScheduleEntry.objects.filter(assignment__stream__groups__name="IS-301")
    assert entries.distinct().count() == 17
    assert all(e.is_locked for e in entries)
    aqida = entries.get(weekday=3, lesson_time__number=3)
    assert aqida.assignment.subject.name_uz == "Aqida"
    assert aqida.room.name == "A-115"
    friday = entries.filter(weekday=4).values_list("lesson_time__number", flat=True)
    assert sorted(friday) == [1, 2]  # 3rd/4th lessons are Friday prayer


def test_holiday_lessons_need_rescheduling(demo):
    navruz = EntryOccurrence.objects.filter(date="2026-03-21")
    assert navruz.exists()
    assert set(navruz.values_list("status", flat=True)) == {OccurrenceStatus.NEEDS_RESCHEDULE}


def test_demo_users(demo):
    roles = {
        "admin": Role.ADMIN,
        "dekanat": Role.DEKANAT,
        "kafedra": Role.KAFEDRA_MUDIRI,
        "oqituvchi": Role.OQITUVCHI,
        "talaba": Role.TALABA,
        "talaba_ru": Role.TALABA,
    }
    for username, role in roles.items():
        user = User.objects.get(username=username)
        assert user.role == role
        assert user.check_password(f"{username.split('_')[0]}123")
    assert User.objects.get(username="oqituvchi").teacher.last_name == "Yusupov"
    assert User.objects.get(username="talaba").student.group.name == "IS-301"
    ru = User.objects.get(username="talaba_ru")
    assert ru.language == "ru" and ru.student.group.teaching_language == "ru"


def test_sample_notifications_are_rendered_in_user_language(demo):
    talaba = Notification.objects.filter(recipient__username="talaba")
    assert talaba.count() == 4
    assert talaba.filter(is_read=False).count() == 2
    assert talaba.filter(
        body="Payshanba, 3-dars: Aqida darsi Ma'ruza zali 2 dan A-115 xonasiga ko'chirildi."
    ).exists()
    teacher = Notification.objects.filter(recipient__username="oqituvchi")
    assert teacher.count() == 3


def test_assignments_target_exactly_one(demo):
    for a in TeachingAssignment.objects.all():
        assert sum(x is not None for x in (a.group_id, a.stream_id, a.subgroup_id)) == 1
