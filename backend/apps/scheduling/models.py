"""Timetable versions, entries, their dated occurrences and change history."""

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import ArrayField, DateTimeRangeField, RangeOperators
from django.contrib.postgres.indexes import OpClass
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

from apps.academics.choices import Weekday, WeekParity
from apps.academics.models import LessonTime, Room, Semester, Teacher, TeachingAssignment


class ScheduleStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PUBLISHED = "published", _("Published")
    ARCHIVED = "archived", _("Archived")


class Schedule(models.Model):
    """A version of the whole academy timetable for a semester (all forms together)."""

    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name="schedules")
    name = models.CharField(_("name"), max_length=255)
    status = models.CharField(
        _("status"), max_length=10, choices=ScheduleStatus.choices, default=ScheduleStatus.DRAFT
    )
    based_on = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="derived"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("timetable version")
        verbose_name_plural = _("timetable versions")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["semester"],
                condition=Q(status=ScheduleStatus.PUBLISHED),
                name="schedule_single_published",
            ),
            models.CheckConstraint(
                condition=Q(status__in=ScheduleStatus.values), name="schedule_status_valid"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"


class ScheduleEntry(models.Model):
    """One placed lesson.

    Weekly forms: weekday + lesson time + week parity, repeated over the period.
    Session forms (sirtqi): a concrete date + lesson time.
    Distance learning: online_url instead of a room.
    """

    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name="entries")
    assignment = models.ForeignKey(
        TeachingAssignment, on_delete=models.CASCADE, related_name="entries"
    )
    lesson_time = models.ForeignKey(LessonTime, on_delete=models.PROTECT, related_name="+")
    weekday = models.PositiveSmallIntegerField(
        _("weekday"), choices=Weekday.choices, null=True, blank=True
    )
    # NULL (not "") marks a dated session entry; the check constraint relies on it.
    week_parity = models.CharField(  # noqa: DJ001
        _("weeks"), max_length=5, choices=WeekParity.choices, null=True, blank=True
    )
    date = models.DateField(_("date"), null=True, blank=True)
    room = models.ForeignKey(
        Room, on_delete=models.PROTECT, null=True, blank=True, related_name="entries"
    )
    online_url = models.URLField(_("online lesson link"), blank=True, default="")
    is_locked = models.BooleanField(
        _("pinned"), default=False, help_text=_("Pinned lessons are never moved by the solver.")
    )
    note = models.CharField(_("note"), max_length=255, blank=True)

    class Meta:
        verbose_name = _("timetable entry")
        verbose_name_plural = _("timetable entries")
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(date__isnull=True, weekday__isnull=False, week_parity__isnull=False)
                    | Q(date__isnull=False, weekday__isnull=True, week_parity__isnull=True)
                ),
                name="entry_weekly_or_dated",
            ),
            models.CheckConstraint(
                condition=Q(weekday__isnull=True) | (Q(weekday__gte=0) & Q(weekday__lte=6)),
                name="entry_weekday_range",
            ),
            models.CheckConstraint(
                condition=Q(room__isnull=False) | ~Q(online_url=""),
                name="entry_room_or_link",
            ),
        ]
        indexes = [models.Index(fields=["schedule", "weekday", "lesson_time"])]

    def __str__(self) -> str:
        when = self.date or self.get_weekday_display()
        return f"{when} · {self.lesson_time.number} · {self.assignment}"


class OccurrenceStatus(models.TextChoices):
    SCHEDULED = "scheduled", _("Scheduled")
    CANCELLED = "cancelled", _("Cancelled")
    NEEDS_RESCHEDULE = "reschedule", _("Needs rescheduling")


class EntryOccurrence(models.Model):
    """A dated instance of an entry. Generated from ScheduleEntry; never edited by hand.

    Every lesson becomes a real time range here, so weekly and session lessons are compared on
    one axis. The exclusion constraints make teacher, room and group double-booking impossible
    within a timetable version, across all education forms and odd/even weeks.
    """

    entry = models.ForeignKey(ScheduleEntry, on_delete=models.CASCADE, related_name="occurrences")
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name="+")
    date = models.DateField()
    during = DateTimeRangeField()
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="+")
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    # group_id * 10 + subgroup number; a whole group covers all of its subgroup slots
    slot_keys = ArrayField(models.IntegerField())
    status = models.CharField(
        max_length=10, choices=OccurrenceStatus.choices, default=OccurrenceStatus.SCHEDULED
    )

    class Meta:
        verbose_name = _("lesson occurrence")
        verbose_name_plural = _("lesson occurrences")
        indexes = [models.Index(fields=["schedule", "date"])]
        constraints = [
            models.UniqueConstraint(fields=["entry", "date"], name="occurrence_unique_date"),
            ExclusionConstraint(
                name="occurrence_no_teacher_overlap",
                expressions=[
                    ("schedule", RangeOperators.EQUAL),
                    ("teacher", RangeOperators.EQUAL),
                    ("during", RangeOperators.OVERLAPS),
                ],
                condition=Q(status=OccurrenceStatus.SCHEDULED),
            ),
            ExclusionConstraint(
                name="occurrence_no_room_overlap",
                expressions=[
                    ("schedule", RangeOperators.EQUAL),
                    ("room", RangeOperators.EQUAL),
                    ("during", RangeOperators.OVERLAPS),
                ],
                condition=Q(status=OccurrenceStatus.SCHEDULED, room__isnull=False),
            ),
            ExclusionConstraint(
                name="occurrence_no_group_overlap",
                expressions=[
                    ("schedule", RangeOperators.EQUAL),
                    (OpClass(F("slot_keys"), name="gist__int_ops"), RangeOperators.OVERLAPS),
                    ("during", RangeOperators.OVERLAPS),
                ],
                condition=Q(status=OccurrenceStatus.SCHEDULED),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.date} · {self.entry_id} · {self.status}"


class ChangeAction(models.TextChoices):
    CREATE = "create", _("Lesson added")
    UPDATE = "update", _("Lesson changed")
    DELETE = "delete", _("Lesson removed")
    CANCEL = "cancel", _("Lesson cancelled")


class ScheduleChange(models.Model):
    """History of edits (for undo and notifications). `before`/`after` are entry snapshots."""

    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name="changes")
    entry = models.ForeignKey(
        ScheduleEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name="changes"
    )
    batch = models.UUIDField(_("change batch"), db_index=True)
    action = models.CharField(max_length=10, choices=ChangeAction.choices)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    occurrence_date = models.DateField(
        null=True, blank=True, help_text=_("Set when only one dated lesson is affected.")
    )
    comment = models.CharField(_("comment"), max_length=500, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    undone = models.BooleanField(default=False)
    notified = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("timetable change")
        verbose_name_plural = _("timetable changes")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_action_display()} · {self.created_at:%Y-%m-%d %H:%M}"


class RequestStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")


class RescheduleRequest(models.Model):
    """A teacher asks the dispatcher to move a lesson."""

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="requests")
    entry = models.ForeignKey(ScheduleEntry, on_delete=models.CASCADE, related_name="requests")
    occurrence_date = models.DateField(
        null=True, blank=True, help_text=_("Empty means the lesson every week.")
    )
    reason = models.TextField(_("reason"))
    desired_weekday = models.PositiveSmallIntegerField(
        choices=Weekday.choices, null=True, blank=True
    )
    desired_date = models.DateField(null=True, blank=True)
    desired_lesson_time = models.ForeignKey(
        LessonTime, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    desired_note = models.CharField(_("preferred time"), max_length=255, blank=True)
    status = models.CharField(
        max_length=10, choices=RequestStatus.choices, default=RequestStatus.PENDING
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    review_comment = models.CharField(_("answer"), max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("reschedule request")
        verbose_name_plural = _("reschedule requests")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.teacher} · {self.get_status_display()}"
