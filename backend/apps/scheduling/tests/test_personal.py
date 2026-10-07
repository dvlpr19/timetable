"""Student and teacher app endpoints: demo clock, .ics, free rooms, reschedule requests."""

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.academics.models import LessonTime
from apps.accounts.models import User
from apps.core import clock
from apps.scheduling.models import EntryOccurrence, RescheduleRequest, Schedule

pytestmark = pytest.mark.django_db


def client_for(username: str | None) -> APIClient:
    client = APIClient()
    if username:
        client.force_authenticate(User.objects.get(username=username))
    return client


@override_settings(DEMO_NOW="2026-04-08")
def test_demo_clock_pins_the_date_but_keeps_the_time_of_day():
    assert clock.today().isoformat() == "2026-04-08"
    data = client_for(None).get("/api/meta/").data
    assert data["today"] == "2026-04-08" and data["demo_date"] is True


@override_settings(DEMO_NOW="")
def test_without_demo_date_the_clock_is_real():
    assert client_for(None).get("/api/meta/").data["demo_date"] is False


def test_ics_has_one_event_per_dated_lesson(demo):
    resp = client_for("talaba").get("/api/export/ics/?me=1")
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/calendar")
    body = resp.content.decode()
    published = Schedule.objects.get(status="published")
    student = User.objects.get(username="talaba").student
    expected = EntryOccurrence.objects.filter(
        schedule=published, slot_keys__overlap=[student.group_id * 10 + k for k in range(1, 4)]
    ).count()
    assert body.count("BEGIN:VEVENT") == expected > 0
    assert body.startswith("BEGIN:VCALENDAR\r\n") and body.endswith("END:VCALENDAR\r\n")
    assert all(len(line.encode()) <= 75 for line in body.split("\r\n"))
    # holidays stay in the file but are marked as not taking place
    if EntryOccurrence.objects.filter(schedule=published).exclude(status="scheduled").exists():
        assert "STATUS:CANCELLED" in body


def test_free_rooms_exclude_rooms_in_use(demo):
    occ = (
        EntryOccurrence.objects.filter(schedule__status="published", room__isnull=False)
        .select_related("entry__lesson_time")
        .first()
    )
    url = f"/api/free-rooms/?date={occ.date}&lesson_time={occ.entry.lesson_time_id}"
    free = client_for("oqituvchi").get(url)
    assert free.status_code == 200
    ids = {r["id"] for r in free.data}
    assert occ.room_id not in ids and ids
    big = client_for("oqituvchi").get(url + "&capacity=100").data
    assert all(r["capacity"] >= 100 for r in big)
    assert client_for("talaba").get(url).status_code == 403
    assert client_for("oqituvchi").get("/api/free-rooms/?date=x").status_code == 400


def test_teacher_asks_to_move_own_lesson_and_dispatcher_answers(demo):
    teacher = client_for("oqituvchi")
    own = teacher.get("/api/timetable/?me=1").data["entries"][0]
    lt = LessonTime.objects.filter(form__code="kunduzgi", number=5).first()
    resp = teacher.post(
        "/api/reschedule-requests/",
        {
            "entry": own["id"],
            "reason": "Konferensiya",
            "desired_weekday": 3,
            "desired_lesson_time": lt.pk,
        },
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["status"] == "pending" and resp.data["lesson"]["id"] == own["id"]
    req_id = resp.data["id"]

    # someone else's lesson is refused, and so is an empty reason
    other = (
        Schedule.objects.get(status="published")
        .entries.exclude(assignment__teacher__user__username="oqituvchi")
        .first()
    )
    assert (
        teacher.post(
            "/api/reschedule-requests/", {"entry": other.pk, "reason": "x"}, format="json"
        ).status_code
        == 403
    )
    assert (
        teacher.post(
            "/api/reschedule-requests/", {"entry": own["id"], "reason": " "}, format="json"
        ).status_code
        == 400
    )

    # students cannot see requests; staff can; only the dispatcher answers
    assert client_for("talaba").get("/api/reschedule-requests/").status_code == 403
    assert len(client_for("dekanat").get("/api/reschedule-requests/").data) == 1
    assert (
        client_for("dekanat")
        .post(f"/api/reschedule-requests/{req_id}/review/", {"status": "approved"})
        .status_code
        == 403
    )
    review = client_for("admin").post(
        f"/api/reschedule-requests/{req_id}/review/",
        {"status": "rejected", "comment": "Xona yo'q"},
        format="json",
    )
    assert review.status_code == 200 and review.data["status"] == "rejected"
    # an answered request can no longer be withdrawn
    assert teacher.delete(f"/api/reschedule-requests/{req_id}/").status_code == 400
    assert RescheduleRequest.objects.get(pk=req_id).review_comment == "Xona yo'q"
