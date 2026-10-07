from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.scheduling.models import ScheduleChange, ScheduleEntry


class NotificationKind(models.TextChoices):
    ROOM_CHANGED = "room_changed", _("Lesson moved to another room")
    TIME_CHANGED = "time_changed", _("Lesson moved to another time")
    CANCELLED = "cancelled", _("Lesson cancelled")
    TEACHER_CHANGED = "teacher_changed", _("Teacher replaced")
    LESSON_ADDED = "lesson_added", _("New lesson added")
    LINK_CHANGED = "link_changed", _("Online lesson link changed")
    SCHEDULE_PUBLISHED = "schedule_published", _("New timetable published")
    REMINDER = "reminder", _("Lesson reminder")
    DAILY_DIGEST = "daily_digest", _("Tomorrow's lessons")
    REQUEST_ANSWERED = "request_answered", _("Reschedule request answered")


# Students must always learn about these; they cannot be switched off.
MANDATORY_KINDS = frozenset({NotificationKind.CANCELLED, NotificationKind.TIME_CHANGED})


class Notification(models.Model):
    """In-app message. `params` keep the raw facts; title/body are rendered in the
    recipient's language when the message is created."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=30, choices=NotificationKind.choices)
    params = models.JSONField(default=dict)
    language = models.CharField(max_length=2)
    title = models.CharField(max_length=255)
    body = models.TextField()
    comment = models.CharField(_("dispatcher comment"), max_length=500, blank=True)
    entry = models.ForeignKey(
        ScheduleEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    change = models.ForeignKey(
        ScheduleChange, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    dedup_key = models.CharField(max_length=100)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    pushed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read", "-created_at"])]
        constraints = [
            # The same change never produces two messages for one person.
            models.UniqueConstraint(fields=["recipient", "dedup_key"], name="notification_dedup"),
        ]

    def __str__(self) -> str:
        return self.title


class PushSubscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions"
    )
    endpoint = models.URLField(max_length=1000, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_success_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("push subscription")
        verbose_name_plural = _("push subscriptions")

    def __str__(self) -> str:
        return f"{self.user} · {self.user_agent[:40]}"


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preference"
    )
    disabled_kinds = models.JSONField(default=list, blank=True)
    reminder_enabled = models.BooleanField(_("remind before lessons"), default=False)
    reminder_minutes = models.PositiveSmallIntegerField(_("minutes before"), default=10)
    daily_digest_enabled = models.BooleanField(_("evening summary"), default=False)

    class Meta:
        verbose_name = _("notification settings")
        verbose_name_plural = _("notification settings")

    def __str__(self) -> str:
        return str(self.user)

    def allows(self, kind: str) -> bool:
        return kind in MANDATORY_KINDS or kind not in self.disabled_kinds
