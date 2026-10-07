"""Editing, conflicts, history/undo, cancellations, publishing, grid options and exports."""

from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.academics.models import Group, LessonTime, Room, TeachingAssignment
from apps.accounts.models import User
from apps.scheduling.models import (
    EntryOccurrence,
    Schedule,
    ScheduleChange,
    ScheduleEntry,
    ScheduleStatus,
)
from apps.scheduling.services.editing import Editor, copy_schedule

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(demo):
    client = APIClient()
    client.force_authenticate(User.objects.get(username="admin"))
    return client


@pytest.fixture
def published(demo):
    return Schedule.objects.get(status="published")


@pytest.fixture
def draft(published):
    return copy_schedule(published, name="Qoralama")


def lt(number, form="kunduzgi"):
    return LessonTime.objects.get(form__code=form, number=number).pk


def room(name):
    return Room.objects.get(name=name).pk


def is302_seminar():
    return TeachingAssignment.objects.get(
        group__name="IS-302", subject__code="TAF", lesson_type__code="seminar"
    )


def test_copy_keeps_entries_and_cancellations(published, draft):
    assert draft.entries.count() == published.entries.count()
    assert draft.status == ScheduleStatus.DRAFT
    assert EntryOccurrence.objects.filter(schedule=draft, status="cancelled").count() == 1


@pytest.mark.parametrize(
    ("lang", "fragment"),
    [
        ("uz", "IS-302 guruhiga bir vaqtda ikkita dars qo'yilgan (Dushanba, 1-dars)"),
        ("ru", "У группы IS-302 два занятия одновременно (Понедельник, 1-я пара)"),
        ("en", "IS-302 has two lessons at the same time (Monday, lesson 1)"),
    ],
)
def test_conflicting_lesson_is_rejected_with_a_reason(admin, draft, lang, fragment):
    payload = {
        "schedule": draft.pk,
        "assignment": is302_seminar().pk,
        "lesson_time": lt(1),
        "weekday": 0,
        "room": room("B-201"),
    }
    response = admin.post("/api/entries/", payload, format="json", HTTP_ACCEPT_LANGUAGE=lang)
    assert response.status_code == 409
    messages = [v["message"] for v in response.data["violations"]]
    assert any(fragment in m for m in messages), messages
    assert not ScheduleEntry.objects.filter(schedule=draft, assignment=is302_seminar()).exists()


def test_place_move_and_undo(admin, draft):
    payload = {
        "schedule": draft.pk,
        "assignment": is302_seminar().pk,
        "lesson_time": lt(4),
        "weekday": 0,
        "room": room("B-201"),
    }
    created = admin.post("/api/entries/", payload, format="json")
    assert created.status_code == 201, created.data
    entry_id = created.data["id"]
    assert created.data["notify_students"] == 0  # drafts are not announced

    moved = admin.patch(f"/api/entries/{entry_id}/", {"lesson_time": lt(5)}, format="json")
    assert moved.status_code == 200
    assert moved.data["lesson_time"]["number"] == 5

    history = admin.get(f"/api/schedules/{draft.pk}/changes/").data
    assert [h["action"] for h in history[:2]] == ["update", "create"]

    assert admin.post(f"/api/schedules/{draft.pk}/undo/").status_code == 200
    assert ScheduleEntry.objects.get(pk=entry_id).lesson_time.number == 4
    assert admin.post(f"/api/schedules/{draft.pk}/undo/").status_code == 200
    assert not ScheduleEntry.objects.filter(pk=entry_id).exists()


def test_dry_run_counts_who_would_be_notified(admin, published):
    aqida = ScheduleEntry.objects.get(
        schedule=published, weekday=3, lesson_time__number=3, assignment__group__name="IS-301"
    )
    response = admin.patch(
        f"/api/entries/{aqida.pk}/", {"room": room("A-301"), "dry_run": True}, format="json"
    )
    assert response.status_code == 200
    assert response.data == {"ok": True, "notify_students": 27, "notify_teachers": 1}
    assert ScheduleEntry.objects.get(pk=aqida.pk).room.name == "A-115"  # nothing saved


def test_published_change_waits_for_announcement(admin, published):
    aqida = ScheduleEntry.objects.get(
        schedule=published, weekday=3, lesson_time__number=3, assignment__group__name="IS-301"
    )
    response = admin.patch(
        f"/api/entries/{aqida.pk}/",
        {"room": room("A-301"), "comment": "Ta'mirlash"},
        format="json",
    )
    assert response.status_code == 200
    change = ScheduleChange.objects.filter(entry=aqida).latest("created_at")
    assert change.notified is False
    assert change.before["room_id"] == room("A-115") and change.after["room_id"] == room("A-301")
    assert change.comment == "Ta'mirlash"


def test_cancel_and_restore_one_date(admin, published):
    entry = ScheduleEntry.objects.get(
        schedule=published, weekday=1, lesson_time__number=2, assignment__group__name="IS-301"
    )
    day = date(2026, 4, 14)
    r = admin.post(f"/api/entries/{entry.pk}/cancel/", {"date": day, "comment": "Kasal"})
    assert r.status_code == 200
    assert EntryOccurrence.objects.get(entry=entry, date=day).status == "cancelled"
    admin.post(f"/api/entries/{entry.pk}/cancel/", {"date": day, "restore": True})
    assert EntryOccurrence.objects.get(entry=entry, date=day).status == "scheduled"
    bad = admin.post(f"/api/entries/{entry.pk}/cancel/", {"date": date(2026, 4, 15)})
    assert bad.status_code == 400  # not a Tuesday


def test_publish_requires_zero_conflicts(admin, draft, published):
    small = TeachingAssignment.objects.get(stream__name="IS-301 + IS-302", subject__code="TAF")
    entry = ScheduleEntry.objects.get(schedule=draft, assignment=small)
    Editor(draft).update(entry, {"room_id": room("A-105")}, force=True)  # 54 students, 30 seats
    response = admin.post(f"/api/schedules/{draft.pk}/publish/")
    assert response.status_code == 409
    assert response.data["conflicts"][0]["code"] == "capacity"

    Editor(draft).update(entry, {"room_id": room("Ma'ruza zali 1")})
    assert admin.post(f"/api/schedules/{draft.pk}/publish/").status_code == 200
    published.refresh_from_db()
    draft.refresh_from_db()
    assert (draft.status, published.status) == ("published", "archived")


def test_grid_options_mark_friday_prayer_and_busy_slots(admin, published):
    response = admin.get(
        f"/api/schedules/{published.pk}/options/?assignment={is302_seminar().pk}",
        HTTP_ACCEPT_LANGUAGE="uz",
    )
    cells = {(c["weekday"], c["number"]): c for c in response.data["cells"]}
    assert len(cells) == 36  # Monday–Saturday × 6 lessons
    assert not cells[(4, 3)]["ok"] and "Juma namozi" in cells[(4, 3)]["reasons"][0]
    assert not cells[(0, 1)]["ok"]  # IS-302 is in the stream lecture
    assert cells[(0, 4)]["ok"] and cells[(0, 4)]["room"]


def test_unplaced_and_dashboard(admin, published):
    group = Group.objects.get(name="IS-302").pk
    unplaced = admin.get(f"/api/schedules/{published.pk}/unplaced/?group={group}").data
    assert {u["target"] for u in unplaced} >= {"IS-302"}
    assert all(u["placed"] < u["required"] for u in unplaced)
    dashboard = admin.get("/api/dashboard/").data
    assert dashboard["conflict_count"] == 0
    assert dashboard["lessons_placed"] == 18
    assert dashboard["groups"] == 26
    assert dashboard["faculties"][0]["percent"] > 0


def test_student_day_view_shows_the_cancelled_lesson(demo):
    client = APIClient()
    client.force_authenticate(User.objects.get(username="talaba"))
    r = client.get("/api/timetable/occurrences/?me=1&date_from=2026-04-13")
    statuses = {(o["subject"]["name"], o["lesson_type"]["code"]): o["status"] for o in r.data}
    assert statuses[("Tafsir", "seminar")] == "cancelled"
    assert statuses[("Tafsir", "lecture")] == "scheduled"


@pytest.mark.parametrize(
    ("kind", "mime", "magic"),
    [
        ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", b"PK"),
        ("pdf", "application/pdf", b"%PDF"),
    ],
)
def test_exports(demo, kind, mime, magic):
    client = APIClient()
    client.force_authenticate(User.objects.get(username="talaba"))
    response = client.get(f"/api/export/?type={kind}&me=1&lang=ru")
    assert response.status_code == 200
    assert response["Content-Type"] == mime
    assert response.content.startswith(magic)
    assert 'filename="IS-301' in response["Content-Disposition"]
