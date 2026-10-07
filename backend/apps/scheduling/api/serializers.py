from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.academics.choices import WeekParity

from ..models import RescheduleRequest, Schedule, ScheduleChange, ScheduleEntry


class ScheduleSerializer(serializers.ModelSerializer):
    entry_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Schedule
        fields = (
            "id",
            "semester",
            "name",
            "status",
            "based_on",
            "created_at",
            "published_at",
            "entry_count",
        )
        read_only_fields = ("status", "created_at", "published_at")


class EntryWriteSerializer(serializers.Serializer):
    """Input for creating/moving a lesson. Weekly forms: weekday + week_parity;
    sirtqi: date. Distance learning: online_url instead of room."""

    schedule = serializers.PrimaryKeyRelatedField(queryset=Schedule.objects.all(), required=False)
    assignment = serializers.IntegerField(required=False)
    lesson_time = serializers.IntegerField(required=False)
    weekday = serializers.IntegerField(min_value=0, max_value=6, required=False, allow_null=True)
    week_parity = serializers.ChoiceField(
        choices=WeekParity.choices, required=False, allow_null=True
    )
    date = serializers.DateField(required=False, allow_null=True)
    room = serializers.IntegerField(required=False, allow_null=True)
    online_url = serializers.URLField(required=False, allow_blank=True)
    is_locked = serializers.BooleanField(required=False)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)
    dry_run = serializers.BooleanField(required=False, default=False)

    MAP = {"assignment": "assignment_id", "lesson_time": "lesson_time_id", "room": "room_id"}

    def entry_data(self) -> dict:
        """Validated data in ScheduleEntry field names (only the fields that were sent)."""
        out = {}
        for key, value in self.validated_data.items():
            if key in ("schedule", "comment", "dry_run"):
                continue
            out[self.MAP.get(key, key)] = value
        if out.get("date"):
            out.setdefault("weekday", None)
            out.setdefault("week_parity", None)
        elif out.get("weekday") is not None:
            out.setdefault("week_parity", WeekParity.EVERY)
            out.setdefault("date", None)
        return out

    def validate(self, attrs):
        if self.context.get("creating"):
            missing = [f for f in ("schedule", "assignment", "lesson_time") if f not in attrs]
            if missing:
                raise serializers.ValidationError(
                    {f: _("This field is required.") for f in missing}
                )
            if attrs.get("date") is None and attrs.get("weekday") is None:
                raise serializers.ValidationError(_("Choose a weekday or a date."))
        return attrs


class CancelSerializer(serializers.Serializer):
    date = serializers.DateField()
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)
    restore = serializers.BooleanField(required=False, default=False)


class ChangeSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True, default="")
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = ScheduleChange
        fields = (
            "id",
            "entry",
            "batch",
            "reverts",
            "action",
            "action_display",
            "before",
            "after",
            "occurrence_date",
            "comment",
            "user_name",
            "created_at",
            "undone",
            "notified",
        )


class RescheduleRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RescheduleRequest
        fields = "__all__"
        read_only_fields = ("teacher", "status", "reviewed_by", "reviewed_at", "created_at")


def entry_payload(entry: ScheduleEntry) -> dict:
    """Read model for timetable views: everything a card needs, names in the request language."""
    a = entry.assignment
    lt = entry.lesson_time
    groups = a.target_groups()
    room = entry.room
    return {
        "id": entry.pk,
        "schedule": entry.schedule_id,
        "assignment": a.pk,
        "weekday": entry.weekday,
        "week_parity": entry.week_parity,
        "date": entry.date,
        "lesson_time": {
            "id": lt.pk,
            "number": lt.number,
            "start": lt.start.strftime("%H:%M"),
            "end": lt.end.strftime("%H:%M"),
            "shift": lt.shift,
        },
        "form": a.period.form.code,
        "subject": {"id": a.subject_id, "name": a.subject.name},
        "lesson_type": {"code": a.lesson_type.code, "name": a.lesson_type.name},
        "teacher": {
            "id": a.teacher_id,
            "short_name": a.teacher.short_name,
            "full_name": a.teacher.full_name,
        },
        "groups": [{"id": g.pk, "name": g.name} for g in groups],
        "subgroup": a.subgroup.number if a.subgroup_id else None,
        "stream": a.stream.name if a.stream_id else None,
        "student_count": a.student_count,
        "room": (
            {
                "id": room.pk,
                "name": room.name,
                "building": room.building.name,
                "floor": room.floor,
                "capacity": room.capacity,
            }
            if room
            else None
        ),
        "online_url": entry.online_url,
        "is_locked": entry.is_locked,
        "note": entry.note,
    }
