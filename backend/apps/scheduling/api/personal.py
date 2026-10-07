"""Endpoints of the student and teacher apps: calendar file, free rooms, reschedule requests."""

from datetime import date, datetime

from django.db.backends.postgresql.psycopg_any import DateTimeTZRange
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import LessonTime, Room
from apps.accounts.models import Role
from apps.core.permissions import ADMIN_ONLY, STAFF_ROLES, RolePermission, role_of

from ..ics import build_calendar
from ..models import (
    EntryOccurrence,
    OccurrenceStatus,
    RequestStatus,
    RescheduleRequest,
    ScheduleEntry,
)
from .serializers import entry_payload
from .views import ENTRY_RELATED, entries_for, resolve_target, schedule_for


class IcsView(APIView):
    """GET /api/export/ics/?me=1 | group= | teacher= | room= — the whole period as .ics."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        schedule = schedule_for(request, request.query_params.get("schedule"))
        target = resolve_target(request)
        entries = {e.pk: entry_payload(e) for e in entries_for(schedule, **target)}
        occurrences = EntryOccurrence.objects.filter(entry__in=entries.keys()).order_by("during")
        name = _("Timetable")
        body = build_calendar(occurrences, entries, f"{name} — {schedule.name}")
        response = HttpResponse(body, content_type="text/calendar; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="dars-jadvali.ics"'
        return response


class FreeRoomsView(APIView):
    """GET /api/free-rooms/?date=YYYY-MM-DD&lesson_time=ID[&capacity=N]

    Rooms not used by the published timetable at that time (for teachers and staff)."""

    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES | {Role.OQITUVCHI}
    write_roles = frozenset()

    def get(self, request):
        try:
            day = date.fromisoformat(request.query_params["date"])
            lt = LessonTime.objects.get(pk=int(request.query_params["lesson_time"]))
            capacity = int(request.query_params.get("capacity") or 0)
        except (KeyError, ValueError, LessonTime.DoesNotExist) as e:
            raise ValidationError(_("Choose a date and a lesson time.")) from e
        schedule = schedule_for(request, None)
        tz = timezone.get_current_timezone()
        during = DateTimeTZRange(
            timezone.make_aware(datetime.combine(day, lt.start), tz),
            timezone.make_aware(datetime.combine(day, lt.end), tz),
            "[)",
        )
        busy = (
            EntryOccurrence.objects.filter(
                schedule=schedule, date=day, during__overlap=during, room__isnull=False
            )
            .exclude(status=OccurrenceStatus.CANCELLED)
            .values_list("room_id", flat=True)
        )
        rooms = (
            Room.objects.filter(is_active=True, capacity__gte=capacity)
            .exclude(pk__in=busy)
            .select_related("building", "room_type")
            .order_by("building__name", "floor", "name")
        )
        return Response(
            [
                {
                    "id": r.pk,
                    "name": r.name,
                    "building": r.building.name,
                    "floor": r.floor,
                    "capacity": r.capacity,
                    "room_type": r.room_type.name,
                    "has_projector": r.has_projector,
                    "computer_count": r.computer_count,
                }
                for r in rooms
            ]
        )


class RescheduleRequestSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.short_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    lesson = serializers.SerializerMethodField()
    desired_lesson_number = serializers.IntegerField(
        source="desired_lesson_time.number", read_only=True, default=None
    )

    class Meta:
        model = RescheduleRequest
        fields = (
            "id",
            "teacher",
            "teacher_name",
            "entry",
            "lesson",
            "occurrence_date",
            "reason",
            "desired_weekday",
            "desired_date",
            "desired_lesson_time",
            "desired_lesson_number",
            "desired_note",
            "status",
            "status_display",
            "review_comment",
            "created_at",
            "reviewed_at",
        )
        read_only_fields = (
            "teacher",
            "status",
            "review_comment",
            "created_at",
            "reviewed_at",
        )

    def get_lesson(self, obj) -> dict:
        return entry_payload(obj.entry)

    def validate(self, attrs):
        if not attrs.get("reason", "").strip():
            raise ValidationError({"reason": gettext_lazy("Write the reason.")})
        return attrs


class RescheduleRequestViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Teachers ask to move their lessons; the dispatcher approves or rejects (and moves the
    lesson in the editor). Staff can read all requests, a teacher only their own."""

    serializer_class = RescheduleRequestSerializer
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES | {Role.OQITUVCHI}
    write_roles = frozenset({Role.OQITUVCHI})
    action_roles = {"review": ADMIN_ONLY}
    filterset_fields = ("status", "teacher")
    pagination_class = None

    def get_queryset(self):
        qs = RescheduleRequest.objects.select_related(
            "teacher", "desired_lesson_time", *(f"entry__{r}" for r in ENTRY_RELATED)
        ).prefetch_related("entry__assignment__stream__groups")
        if role_of(self.request.user) == Role.OQITUVCHI:
            qs = qs.filter(teacher__user=self.request.user)
        return qs

    def in_scope(self, obj) -> bool:
        return obj.teacher.user_id == self.request.user.id

    def perform_create(self, serializer):
        teacher = getattr(self.request.user, "teacher", None)
        entry: ScheduleEntry = serializer.validated_data["entry"]
        if teacher is None or entry.assignment.teacher_id != teacher.pk:
            raise PermissionDenied(_("You can only ask to move your own lessons."))
        if entry.schedule.status != "published":
            raise ValidationError({"entry": _("Only lessons of the published timetable.")})
        serializer.save(teacher=teacher)

    def perform_destroy(self, instance):
        if instance.status != RequestStatus.PENDING:
            raise ValidationError(_("Only a pending request can be withdrawn."))
        instance.delete()

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        obj = get_object_or_404(self.get_queryset(), pk=pk)
        decision = request.data.get("status")
        if decision not in (RequestStatus.APPROVED, RequestStatus.REJECTED):
            raise ValidationError({"status": _("Choose approved or rejected.")})
        obj.status = decision
        obj.review_comment = str(request.data.get("comment", ""))[:500]
        obj.reviewed_by = request.user
        obj.reviewed_at = timezone.now()
        obj.save(update_fields=["status", "review_comment", "reviewed_by", "reviewed_at"])
        return Response(RescheduleRequestSerializer(obj).data)
