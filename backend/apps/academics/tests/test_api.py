"""Reference-data API details the admin panel relies on."""

import pytest
from django.db.models import Sum
from rest_framework.test import APIClient

from apps.academics.models import Academy, Faculty, Teacher, TeachingAssignment
from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def admin_client() -> APIClient:
    client = APIClient()
    client.force_authenticate(User.objects.get(username="admin"))
    return client


def test_teacher_list_shows_weekly_load_of_the_current_semester(demo):
    teacher = Teacher.objects.get(last_name="Yusupov")
    expected = TeachingAssignment.objects.filter(
        teacher=teacher, period__semester__is_current=True
    ).aggregate(n=Sum("weekly_lessons"))["n"]
    rows = admin_client().get("/api/teachers/?search=Yusupov").data["results"]
    row = next(r for r in rows if r["id"] == teacher.pk)
    assert expected and row["weekly_lessons"] == expected


def test_faculty_can_be_created_without_choosing_the_academy(demo):
    resp = admin_client().post(
        "/api/faculties/",
        {"code": "TST", "name_uz": "Sinov fakulteti", "teaching_language": "uz"},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert Faculty.objects.get(code="TST").academy == Academy.objects.first()
