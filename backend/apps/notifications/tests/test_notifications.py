"""Timetable changes become messages for exactly the right people, once, in their language."""

from datetime import datetime, timedelta
from unittest import mock

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.notifications import service
from apps.notifications.models import Notification, NotificationPreference, PushSubscription
from apps.scheduling.models import EntryOccurrence, Schedule, ScheduleEntry
from apps.scheduling.services.editing import Editor, undo_last

pytestmark = pytest.mark.django_db


def client_for(username: str) -> APIClient:
    client = APIClient()
    client.force_authenticate(User.objects.get(username=username))
    return client


@pytest.fixture
def published(demo):
    return Schedule.objects.get(status="published")


@pytest.fixture
def arab(published):
    """IS-301's Arabic practice: a whole-group lesson (no stream)."""
    return published.entries.get(
        assignment__group__name="IS-301",
        assignment__lesson_type__code="practice",
        lesson_time__number=1,
        weekday=2,
    )


def free_room_for(entry: ScheduleEntry):
    editor = Editor(entry.schedule)
    for room in editor.ctx.rooms.values():
        data = {**{"room_id": room.id}}
        from apps.scheduling.services.editing import snapshot

        if room.id != entry.room_id and not editor.check({**snapshot(entry), **data}, key=entry.pk):
            return room.id
    raise AssertionError("no free room")


def new_messages(user, kind=None):
    qs = Notification.objects.filter(recipient=user, dedup_key__startswith="change:").exclude(
        change__created_at__lt=datetime(2026, 9, 1).astimezone()
    )
    return qs.filter(kind=kind) if kind else qs


def test_room_change_reaches_the_group_and_the_teacher_only(
    published, arab, django_capture_on_commit_callbacks
):
    room = free_room_for(arab)
    with django_capture_on_commit_callbacks(execute=True):
        resp = client_for("admin").patch(
            f"/api/entries/{arab.pk}/", {"room": room, "comment": "Ta'mir"}, format="json"
        )
    assert resp.status_code == 200, resp.data
    talaba = User.objects.get(username="talaba")  # IS-301
    msg = new_messages(talaba).get()
    assert msg.kind == "room_changed" and msg.language == "uz"
    assert msg.title == "Dars boshqa xonaga ko'chirildi"
    assert msg.comment == "Ta'mir" and msg.entry_id == arab.pk
    teacher_user = arab.assignment.teacher.user
    assert teacher_user is None or new_messages(teacher_user).count() == 1
    # another group's student hears nothing
    assert not new_messages(User.objects.get(username="talaba_ru")).exists()
    # everyone in IS-301 got exactly one message
    group_users = User.objects.filter(student__group__name="IS-301")
    assert all(new_messages(u).count() == 1 for u in group_users)
    # the change is marked as announced: running again creates nothing
    assert service.announce_changes(published.pk) == 0


def test_messages_are_rendered_in_each_persons_language(
    published, arab, django_capture_on_commit_callbacks
):
    student = User.objects.get(username="talaba")
    student.language = "ru"
    student.save()
    with django_capture_on_commit_callbacks(execute=True):
        client_for("admin").patch(
            f"/api/entries/{arab.pk}/", {"room": free_room_for(arab)}, format="json"
        )
    msg = new_messages(student).get()
    assert msg.language == "ru" and msg.title == "Занятие перенесено в другую аудиторию"


def test_settings_switch_off_room_changes_but_never_time_changes(
    published, arab, django_capture_on_commit_callbacks
):
    student = User.objects.get(username="talaba")
    NotificationPreference.objects.create(user=student, disabled_kinds=["room_changed"])
    with django_capture_on_commit_callbacks(execute=True):
        client_for("admin").patch(
            f"/api/entries/{arab.pk}/", {"room": free_room_for(arab)}, format="json"
        )
    assert not new_messages(student).exists()

    editor = Editor(published)
    # a free time for the lesson: try weekly cells until one passes the validator
    from apps.scheduling.services.editing import snapshot

    arab.refresh_from_db()
    target = None
    for lt in editor.ctx.lesson_times.values():
        if lt.form_id != arab.lesson_time.form_id:
            continue
        for wd in range(6):
            data = {**snapshot(arab), "weekday": wd, "lesson_time_id": lt.id}
            if (wd, lt.id) != (arab.weekday, arab.lesson_time_id) and not editor.check(
                data, key=arab.pk
            ):
                target = {"weekday": wd, "lesson_time": lt.id}
                break
        if target:
            break
    with django_capture_on_commit_callbacks(execute=True):
        resp = client_for("admin").patch(f"/api/entries/{arab.pk}/", target, format="json")
    assert resp.status_code == 200, resp.data
    msg = new_messages(student, "time_changed").get()
    assert msg.params["new_when"] == {"weekday": target["weekday"]}


def test_pinning_is_silent(published, arab, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        client_for("admin").patch(
            f"/api/entries/{arab.pk}/", {"is_locked": not arab.is_locked}, format="json"
        )
    assert not Notification.objects.filter(
        change__entry=arab, change__created_at__gte=datetime(2026, 9, 1).astimezone()
    ).exists()


def test_an_edit_undone_before_announcement_stays_silent(published, arab):
    # no on_commit execution: the announcement has not run yet
    editor = Editor(published)
    editor.update(arab, {"room_id": free_room_for(arab)})
    undo_last(published)
    assert service.announce_changes(published.pk) == 0


def test_bell_api_counts_lists_and_marks_read(published, arab, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        client_for("admin").patch(
            f"/api/entries/{arab.pk}/", {"room": free_room_for(arab)}, format="json"
        )
    c = client_for("talaba")
    before = c.get("/api/notifications/unread-count/").data["count"]
    assert before >= 1
    items = c.get("/api/notifications/?unread=1").data["results"]
    newest = items[0]
    assert newest["kind"] == "room_changed" and newest["was"] and newest["now"]
    assert c.post(f"/api/notifications/{newest['id']}/read/").data["updated"] == 1
    assert c.get("/api/notifications/unread-count/").data["count"] == before - 1
    c.post("/api/notifications/read-all/")
    assert c.get("/api/notifications/unread-count/").data["count"] == 0
    # nobody reads someone else's messages
    assert (
        client_for("talaba_ru").post(f"/api/notifications/{newest['id']}/read/").data["updated"]
        == 0
    )


def test_preferences_validate_choices(demo):
    c = client_for("talaba")
    assert c.get("/api/notifications/preferences/").data["reminder_enabled"] is False
    assert (
        c.patch(
            "/api/notifications/preferences/", {"disabled_kinds": ["cancelled"]}, format="json"
        ).status_code
        == 400
    )
    assert (
        c.patch(
            "/api/notifications/preferences/", {"reminder_minutes": 7}, format="json"
        ).status_code
        == 400
    )
    ok = c.patch(
        "/api/notifications/preferences/",
        {"reminder_enabled": True, "reminder_minutes": 15, "disabled_kinds": ["link_changed"]},
        format="json",
    )
    assert ok.status_code == 200 and ok.data["reminder_minutes"] == 15


def _first_occurrence_of(user):
    student = user.student
    return (
        EntryOccurrence.objects.filter(
            schedule__status="published",
            status="scheduled",
            slot_keys__overlap=[student.group_id * 10 + k for k in (1, 2, 3)],
        )
        .order_by("during")
        .first()
    )


def test_reminder_comes_once_n_minutes_before(published):
    talaba = User.objects.get(username="talaba")
    NotificationPreference.objects.create(user=talaba, reminder_enabled=True, reminder_minutes=10)
    occ = _first_occurrence_of(talaba)
    start = occ.during.lower.astimezone()
    demo_now = (start - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M")
    with override_settings(DEMO_NOW=demo_now):
        assert service.send_reminders() >= 1
        assert service.send_reminders() == 0  # no duplicates
    msg = Notification.objects.get(recipient=talaba, dedup_key=f"reminder:{occ.pk}")
    assert msg.kind == "reminder" and occ.entry.lesson_time.start.strftime("%H:%M") in msg.body


def test_evening_summary_lists_tomorrow(published):
    talaba = User.objects.get(username="talaba")
    NotificationPreference.objects.create(user=talaba, daily_digest_enabled=True)
    occ = _first_occurrence_of(talaba)
    evening = (occ.date - timedelta(days=1)).isoformat() + "T20:00"
    with override_settings(DEMO_NOW=evening):
        assert service.send_daily_digest() == 1
    msg = Notification.objects.get(recipient=talaba, kind="daily_digest")
    tomorrow = EntryOccurrence.objects.filter(
        date=occ.date, schedule__status="published", status="scheduled",
        slot_keys__overlap=[talaba.student.group_id * 10 + k for k in (1, 2, 3)],
    ).count()  # fmt: skip
    assert msg.params["count"] == tomorrow


def test_answered_request_is_announced_to_the_teacher(demo, django_capture_on_commit_callbacks):
    teacher = client_for("oqituvchi")
    own = teacher.get("/api/timetable/?me=1").data["entries"][0]
    req = teacher.post(
        "/api/reschedule-requests/", {"entry": own["id"], "reason": "x"}, format="json"
    ).data
    with django_capture_on_commit_callbacks(execute=True):
        client_for("admin").post(
            f"/api/reschedule-requests/{req['id']}/review/", {"status": "approved"}, format="json"
        )
    msg = Notification.objects.get(recipient__username="oqituvchi", kind="request_answered")
    assert "approved" in msg.params["status"]


@override_settings(VAPID_PUBLIC_KEY="pub", VAPID_PRIVATE_KEY="priv", VAPID_CLAIM_EMAIL="a@b.uz")
def test_web_push_is_sent_and_dead_subscriptions_are_dropped(
    published, arab, django_capture_on_commit_callbacks
):
    from pywebpush import WebPushException

    talaba = User.objects.get(username="talaba")
    c = client_for("talaba")
    assert c.get("/api/notifications/push/").data["enabled"] is True
    c.post(
        "/api/notifications/push/",
        {"endpoint": "https://push.example/alive", "keys": {"p256dh": "k", "auth": "a"}},
        format="json",
    )
    c.post(
        "/api/notifications/push/",
        {"endpoint": "https://push.example/dead", "keys": {"p256dh": "k", "auth": "a"}},
        format="json",
    )

    def fake_push(subscription_info, **kwargs):
        if subscription_info["endpoint"].endswith("dead"):
            raise WebPushException("gone", response=mock.Mock(status_code=410))

    room = free_room_for(arab)
    with (
        mock.patch("pywebpush.webpush", side_effect=fake_push) as push,
        django_capture_on_commit_callbacks(execute=True),
    ):
        client_for("admin").patch(f"/api/entries/{arab.pk}/", {"room": room}, format="json")
    sent_to_talaba = [
        call
        for call in push.call_args_list
        if call.kwargs["subscription_info"]["endpoint"].startswith("https://push.example")
    ]
    assert len(sent_to_talaba) == 2
    assert list(
        PushSubscription.objects.filter(user=talaba).values_list("endpoint", flat=True)
    ) == ["https://push.example/alive"]
    assert new_messages(talaba).get().pushed_at is not None
