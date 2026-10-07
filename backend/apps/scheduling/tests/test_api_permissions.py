"""Who may see and change what. Rules are enforced on the server, not only hidden in the UI."""

import pytest
from rest_framework.test import APIClient

from apps.academics.models import Group, Student, Teacher, TeacherAvailability
from apps.accounts.models import User
from apps.scheduling.models import Schedule
from apps.scheduling.services.editing import copy_schedule

pytestmark = pytest.mark.django_db


def client_for(username: str | None) -> APIClient:
    client = APIClient()
    if username:
        client.force_authenticate(User.objects.get(username=username))
    return client


@pytest.fixture
def draft(demo):
    return copy_schedule(Schedule.objects.get(status="published"), name="Qoralama")


@pytest.fixture
def ids(demo):
    return {
        "is301": Group.objects.get(name="IS-301").pk,
        "is302": Group.objects.get(name="IS-302").pk,
        "ru": Group.objects.get(name="IS-R-201").pk,
        "yusupov": Teacher.objects.get(last_name="Yusupov").pk,
        "karimov": Teacher.objects.get(last_name="Karimov").pk,  # same department as Yusupov
        "abdullayev": Teacher.objects.get(last_name="Abdullayev").pk,  # another department
    }


def test_anonymous_gets_nothing(demo):
    assert client_for(None).get("/api/rooms/").status_code == 401
    assert client_for(None).get("/api/timetable/?group=1").status_code == 401


# --- student -----------------------------------------------------------------------------


def test_student_reads_reference_data_but_cannot_change_it(demo):
    c = client_for("talaba")
    assert c.get("/api/rooms/").status_code == 200
    assert c.post("/api/rooms/", {"name": "X"}).status_code == 403
    assert c.get("/api/teachers/").status_code == 200
    assert "annual_load_hours" not in c.get("/api/teachers/").data["results"][0]


def test_student_cannot_see_personal_data_or_plans(demo):
    c = client_for("talaba")
    assert c.get("/api/students/").status_code == 403
    assert c.get("/api/curriculum/").status_code == 403
    assert c.get("/api/assignments/").status_code == 403
    assert c.get("/api/dashboard/").status_code == 403


def test_student_sees_only_the_published_timetable(draft, ids):
    c = client_for("talaba")
    listed = {s["id"] for s in c.get("/api/schedules/").data["results"]}
    assert draft.pk not in listed
    assert c.get(f"/api/schedules/{draft.pk}/").status_code == 404
    # neither another group's draft nor even the own group's draft
    assert c.get(f"/api/timetable/?group={ids['is302']}&schedule={draft.pk}").status_code == 403
    assert c.get(f"/api/timetable/?me=1&schedule={draft.pk}").status_code == 403
    assert c.get(f"/api/entries/?schedule={draft.pk}").status_code == 403
    assert c.get(f"/api/schedules/{draft.pk}/conflicts/").status_code == 403
    # published timetables of other groups are public (search)
    assert c.get(f"/api/timetable/?group={ids['is302']}").status_code == 200


def test_student_own_week_has_the_design_lessons(demo):
    data = client_for("talaba").get("/api/timetable/?me=1").data
    assert len(data["entries"]) == 17  # IS-301 week from the mobile design


def test_student_cannot_edit_the_timetable(demo, draft):
    c = client_for("talaba")
    entry = draft.entries.first()
    assert c.patch(f"/api/entries/{entry.pk}/", {"room": None}, format="json").status_code == 403
    assert c.post(f"/api/schedules/{draft.pk}/publish/").status_code == 403


# --- teacher -----------------------------------------------------------------------------


def test_teacher_manages_only_own_availability(ids):
    c = client_for("oqituvchi")  # Yusupov
    rows = c.get("/api/teacher-availability/").data
    assert rows and {r["teacher"] for r in rows} == {ids["yusupov"]}
    own = {"teacher": ids["yusupov"], "weekday": 5, "lesson_time": None, "level": "unavailable"}
    assert c.post("/api/teacher-availability/", own, format="json").status_code == 201
    other = {**own, "teacher": ids["karimov"]}
    assert c.post("/api/teacher-availability/", other, format="json").status_code == 403
    replace = c.put(
        "/api/teacher-availability/replace/",
        {"teacher": ids["yusupov"], "rows": [{"weekday": 0, "level": "preferred"}]},
        format="json",
    )
    assert replace.status_code == 200
    assert TeacherAvailability.objects.filter(teacher_id=ids["yusupov"]).count() == 1
    assert (
        c.put(
            "/api/teacher-availability/replace/",
            {"teacher": ids["karimov"], "rows": []},
            format="json",
        ).status_code
        == 403
    )


def test_teacher_sees_only_own_assignments_and_no_drafts(ids, draft):
    c = client_for("oqituvchi")
    teachers = {a["teacher"] for a in c.get("/api/assignments/?page_size=500").data["results"]}
    assert teachers == {ids["yusupov"]}
    assert c.get(f"/api/timetable/?me=1&schedule={draft.pk}").status_code == 403
    assert len(c.get("/api/timetable/?me=1").data["entries"]) == 2  # Tafsir lecture + seminar
    assert c.patch(f"/api/groups/{ids['is301']}/", {"student_count": 1}).status_code == 403


# --- dean's office -----------------------------------------------------------------------


def test_dekanat_edits_only_its_faculty(ids):
    c = client_for("dekanat")  # Islomshunoslik
    assert c.patch(f"/api/groups/{ids['is301']}/", {"shift": 2}).status_code == 200
    assert c.patch(f"/api/groups/{ids['ru']}/", {"shift": 1}).status_code == 403
    assert c.patch(f"/api/teachers/{ids['yusupov']}/", {"max_weekly_lessons": 3}).status_code == 403


def test_dekanat_sees_only_its_students(demo):
    c = client_for("dekanat")
    data = c.get("/api/students/?page_size=1000").data
    own = Student.objects.filter(group__program_form__program__faculty__code="ISL").count()
    assert data["count"] == own
    assert all(not s["group_name"].startswith("IS-R") for s in data["results"])


def test_dekanat_reads_drafts_but_does_not_edit_them(draft):
    c = client_for("dekanat")
    assert c.get(f"/api/schedules/{draft.pk}/conflicts/").status_code == 200
    entry = draft.entries.first()
    assert c.patch(f"/api/entries/{entry.pk}/", {"note": "x"}, format="json").status_code == 403


def test_dekanat_cannot_move_a_group_into_another_faculty(ids, demo):
    c = client_for("dekanat")
    ru_program_form = Group.objects.get(pk=ids["ru"]).program_form_id
    response = c.patch(f"/api/groups/{ids['is301']}/", {"program_form": ru_program_form})
    assert response.status_code == 403
    assert Group.objects.get(pk=ids["is301"]).program_form_id != ru_program_form


# --- head of department ------------------------------------------------------------------


def test_kafedra_edits_only_its_teachers(ids):
    c = client_for("kafedra")  # Qur'onshunoslik va hadisshunoslik
    assert (
        c.patch(f"/api/teachers/{ids['karimov']}/", {"max_weekly_lessons": 14}).status_code == 200
    )
    assert (
        c.patch(f"/api/teachers/{ids['abdullayev']}/", {"max_weekly_lessons": 14}).status_code
        == 403
    )
    assert c.get("/api/students/").status_code == 403
    assert "annual_load_hours" in c.get(f"/api/teachers/{ids['karimov']}/").data


# --- dispatcher --------------------------------------------------------------------------


def test_admin_has_full_access(ids, draft):
    c = client_for("admin")
    assert c.get("/api/students/").status_code == 200
    assert c.patch(f"/api/groups/{ids['ru']}/", {"shift": 1}).status_code == 200
    assert c.get("/api/dashboard/").status_code == 200
    assert c.delete(f"/api/schedules/{draft.pk}/").status_code == 204
    published = Schedule.objects.get(status="published")
    assert c.delete(f"/api/schedules/{published.pk}/").status_code == 400
