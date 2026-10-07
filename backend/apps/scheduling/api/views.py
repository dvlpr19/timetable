"""Timetable API.

Visibility: students and teachers only ever see the published version. Drafts, conflicts,
history and statistics are for staff (admin, dekanat, kafedra_mudiri). Only the dispatcher
(admin) edits, publishes and undoes.
"""

from collections import defaultdict
from datetime import date

from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import Faculty, Group, Room, Semester, Teacher, TeachingAssignment
from apps.core.permissions import ADMIN_ONLY, ALL_ROLES, STAFF_ROLES, RolePermission, role_of

from ..exports import export
from ..models import EntryOccurrence, Schedule, ScheduleChange, ScheduleEntry, ScheduleStatus
from ..services.editing import (
    ConflictError,
    Editor,
    affected_people,
    copy_schedule,
    publish,
    snapshot,
    to_placement,
    undo_last,
)
from ..validators import (
    Code,
    Placement,
    ValidationReport,
    Validator,
    describe,
    load_context,
    placements_from_entries,
    plan_fulfilment,
    soft_report,
    validate,
)
from .serializers import (
    CancelSerializer,
    ChangeSerializer,
    EntryWriteSerializer,
    ScheduleSerializer,
    entry_payload,
)

ENTRY_RELATED = (
    "lesson_time",
    "room__building",
    "assignment__period__form",
    "assignment__subject",
    "assignment__lesson_type",
    "assignment__teacher",
    "assignment__group",
    "assignment__subgroup__group",
    "assignment__stream",
)


def current_semester() -> Semester:
    semester = Semester.objects.filter(is_current=True).first()
    if semester is None:
        raise NotFound(_("No current semester is set."))
    return semester


def published_schedule(semester: Semester | None = None) -> Schedule:
    schedule = Schedule.objects.filter(
        semester=semester or current_semester(), status=ScheduleStatus.PUBLISHED
    ).first()
    if schedule is None:
        raise NotFound(_("The timetable has not been published yet."))
    return schedule


def schedule_for(request, schedule_id=None) -> Schedule:
    """The version a user may look at: any version for staff, only published for others."""
    if schedule_id in (None, ""):
        return published_schedule()
    schedule = get_object_or_404(Schedule, pk=schedule_id)
    if schedule.status != ScheduleStatus.PUBLISHED and role_of(request.user) not in STAFF_ROLES:
        raise PermissionDenied(_("Only the published timetable is available."))
    return schedule


def violation_payload(v, ctx, placements) -> dict:
    return {
        "code": v.code,
        "constraint": v.constraint,
        "entries": [k for k in v.keys if isinstance(k, int)],
        "message": describe(v, ctx, placements),
    }


def entries_for(schedule: Schedule, *, group=None, teacher=None, room=None, student=None):
    qs = schedule.entries.select_related(*ENTRY_RELATED).prefetch_related(
        "assignment__stream__groups"
    )
    if student is not None:
        qs = qs.filter(
            Q(assignment__group=student.group_id)
            | Q(assignment__stream__groups=student.group_id)
            | Q(assignment__subgroup=student.subgroup_id)
        )
    if group is not None:
        qs = qs.filter(
            Q(assignment__group=group)
            | Q(assignment__stream__groups=group)
            | Q(assignment__subgroup__group=group)
        )
    if teacher is not None:
        qs = qs.filter(assignment__teacher=teacher)
    if room is not None:
        qs = qs.filter(room=room)
    return qs.distinct().order_by("date", "weekday", "lesson_time__number")


def _int(request, name):
    value = request.query_params.get(name)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except ValueError as e:
        raise ValidationError({name: _("Must be a number.")}) from e


def resolve_target(request):
    """group / teacher / room filter, or `me=1` for the signed-in student or teacher."""
    if request.query_params.get("me"):
        user = request.user
        if hasattr(user, "student") and user.student:
            return {"student": user.student}
        if hasattr(user, "teacher") and user.teacher:
            return {"teacher": user.teacher.pk}
        raise ValidationError({"me": _("Your account is not linked to a student or teacher.")})
    target = {k: _int(request, k) for k in ("group", "teacher", "room")}
    target = {k: v for k, v in target.items() if v is not None}
    if not target:
        raise ValidationError(_("Choose a group, a teacher or a room."))
    return target


# --------------------------------------------------------------------------- versions


class ScheduleViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ScheduleSerializer
    permission_classes = [RolePermission]
    read_roles = ALL_ROLES
    write_roles = ADMIN_ONLY
    action_roles = {
        "conflicts": STAFF_ROLES,
        "unplaced": STAFF_ROLES,
        "stats": STAFF_ROLES,
        "changes": STAFF_ROLES,
        "options": ADMIN_ONLY,
        "check": ADMIN_ONLY,
    }
    filterset_fields = ("semester", "status")

    def in_scope(self, obj) -> bool:
        return True

    def get_queryset(self):
        # Meta.ordering is not applied to GROUP BY queries, so order explicitly.
        qs = Schedule.objects.annotate(entry_count=Count("entries")).order_by("-created_at")
        if role_of(self.request.user) not in STAFF_ROLES:
            qs = qs.filter(status=ScheduleStatus.PUBLISHED)
        return qs

    def perform_create(self, serializer):
        source = serializer.validated_data.get("based_on")
        if source:
            draft = copy_schedule(
                source, name=serializer.validated_data["name"], user=self.request.user
            )
            serializer.instance = Schedule.objects.annotate(entry_count=Count("entries")).get(
                pk=draft.pk
            )
        else:
            serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        if instance.status == ScheduleStatus.PUBLISHED:
            raise ValidationError(_("The published timetable cannot be deleted."))
        instance.delete()

    def _validated(self, schedule):
        ctx = load_context(schedule.semester)
        placements = placements_from_entries(schedule.entries.all())
        return ctx, placements, validate(placements, ctx)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        schedule = self.get_object()
        ctx, placements, report = self._validated(schedule)
        if report.conflicts:
            by_key = {p.key: p for p in placements}
            return Response(
                {
                    "detail": _("The timetable has conflicts and cannot be published."),
                    "conflicts": [violation_payload(v, ctx, by_key) for v in report.conflicts],
                },
                status=status.HTTP_409_CONFLICT,
            )
        publish(schedule)
        return Response(ScheduleSerializer(self.get_queryset().get(pk=schedule.pk)).data)

    @action(detail=True, methods=["post"])
    def undo(self, request, pk=None):
        schedule = self.get_object()
        changes = undo_last(schedule, request.user)
        if not changes:
            return Response({"detail": _("There is nothing to undo.")}, status=400)
        return Response(ChangeSerializer(changes, many=True).data)

    @action(detail=True)
    def conflicts(self, request, pk=None):
        schedule = self.get_object()
        ctx, placements, report = self._validated(schedule)
        by_key = {p.key: p for p in placements}
        return Response(
            {
                "count": len(report.conflicts),
                "by_constraint": ValidationReport(report.conflicts).by_constraint(),
                "items": [violation_payload(v, ctx, by_key) for v in report.conflicts],
            }
        )

    @action(detail=True)
    def unplaced(self, request, pk=None):
        """Assignments that still miss lessons (the side panel of the editor)."""
        schedule = self.get_object()
        ctx, placements, report = self._validated(schedule)
        missing = {
            v.params["assignment_id"]: v.params
            for v in report.violations
            if v.code == Code.PLAN_INCOMPLETE
        }
        qs = (
            TeachingAssignment.objects.filter(pk__in=missing)
            .select_related(
                "subject",
                "lesson_type",
                "teacher",
                "group",
                "subgroup__group",
                "stream",
                "period__form",
            )
            .prefetch_related("stream__groups")
        )
        group = _int(request, "group")
        teacher = _int(request, "teacher")
        if group:
            qs = qs.filter(
                Q(group=group) | Q(stream__groups=group) | Q(subgroup__group=group)
            ).distinct()
        if teacher:
            qs = qs.filter(teacher=teacher)
        if form := request.query_params.get("form"):
            qs = qs.filter(period__form__code=form)
        return Response(
            [
                {
                    "assignment": a.pk,
                    "subject": a.subject.name,
                    "lesson_type": {"code": a.lesson_type.code, "name": a.lesson_type.name},
                    "teacher": a.teacher.short_name,
                    "target": a.target_name,
                    "form": a.period.form.code,
                    "student_count": a.student_count,
                    "placed": missing[a.pk]["placed"],
                    "required": missing[a.pk]["required"],
                }
                for a in qs
            ]
        )

    @action(detail=True)
    def stats(self, request, pk=None):
        schedule = self.get_object()
        ctx, placements, report = self._validated(schedule)
        soft = soft_report(placements, ctx)
        rows = plan_fulfilment(placements, ctx)
        placed = [r for r in rows if r.scheduled]
        return Response(
            {
                "hard_conflicts": len(report.conflicts),
                "soft": soft.counts,
                "soft_score": soft.score,
                "plan": {
                    "assignments": len(rows),
                    "with_lessons": len(placed),
                    "matching_plan": sum(1 for r in placed if r.matches),
                    "lessons_planned": sum(r.planned for r in rows),
                    "lessons_scheduled": sum(r.scheduled for r in rows),
                    "lessons_lost": sum(r.lost for r in rows),
                },
            }
        )

    @action(detail=True)
    def changes(self, request, pk=None):
        schedule = self.get_object()
        qs = ScheduleChange.objects.filter(schedule=schedule).select_related("user")[:200]
        return Response(ChangeSerializer(qs, many=True).data)

    @action(detail=True)
    def options(self, request, pk=None):
        """For drag-and-drop: every cell of the grid with ok / reasons and free rooms.

        ?entry=ID (move an existing lesson) or ?assignment=ID (place a new one).
        """
        schedule = self.get_object()
        entry_id, assignment_id = _int(request, "entry"), _int(request, "assignment")
        ctx = load_context(schedule.semester)
        placements = placements_from_entries(schedule.entries.all())
        by_key = {p.key: p for p in placements}
        if entry_id:
            base = by_key.get(entry_id)
            if base is None:
                raise NotFound()
        elif assignment_id and assignment_id in ctx.assignments:
            base = Placement(key="new", assignment_id=assignment_id, lesson_time_id=0)
        else:
            raise ValidationError(_("Choose a lesson."))
        validator = Validator(ctx, placements)
        a = ctx.assignments[base.assignment_id]
        period = ctx.periods[a.period_id]
        form = ctx.forms[period.form_id]
        times = sorted(
            (lt for lt in ctx.lesson_times.values() if lt.form_id == form.id),
            key=lambda lt: lt.number,
        )
        if form.mode == "session":
            days = [{"date": d} for d in period.dates() if d.weekday() in form.study_weekdays]
        else:
            days = [{"weekday": wd} for wd in sorted(form.study_weekdays)]
        parity = base.week_parity or "every"
        cells = []
        for day in days:
            for lt in times:
                candidate = Placement(
                    key=base.key,
                    assignment_id=base.assignment_id,
                    lesson_time_id=lt.id,
                    weekday=day.get("weekday"),
                    week_parity=None if "date" in day else parity,
                    date=day.get("date"),
                    room_id=None,
                    online_url=base.online_url or ("-" if not form.requires_room else ""),
                )
                problems = [
                    v
                    for v in validator.check(candidate)
                    if v.code not in (Code.ROOM_MISSING, Code.LINK_MISSING)
                ]
                rooms = _free_rooms(validator, candidate) if form.requires_room else []
                keep = base.room_id if base.room_id in rooms else None
                ok = not problems and (bool(rooms) or not form.requires_room)
                cells.append(
                    {
                        **{k: v for k, v in day.items()},
                        "lesson_time": lt.id,
                        "number": lt.number,
                        "ok": ok,
                        "room": keep or (rooms[0] if rooms else None),
                        "free_rooms": rooms[:20],
                        "reasons": [
                            describe(v, ctx, {**by_key, candidate.key: candidate}) for v in problems
                        ]
                        or ([] if ok else [_("No suitable room is free at this time.")]),
                    }
                )
        return Response({"assignment": base.assignment_id, "cells": cells})

    @action(detail=True, methods=["post"])
    def check(self, request, pk=None):
        """Validate a would-be change without saving it (and count who would be notified)."""
        schedule = self.get_object()
        serializer = EntryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry_id = request.data.get("entry")
        editor = Editor(schedule, user=request.user)
        data = serializer.entry_data()
        if entry_id:
            entry = get_object_or_404(ScheduleEntry, pk=entry_id, schedule=schedule)
            data = {**snapshot(entry), **data}
            key = entry.pk
        else:
            key = "candidate"
        violations = editor.check(data, key=key)
        by_key = {**editor.validator.placements, key: to_placement(data, key)}
        return Response(
            {
                "ok": not violations,
                "violations": [violation_payload(v, editor.ctx, by_key) for v in violations],
                **_audience(schedule, {data["assignment_id"]}),
            }
        )


def _free_rooms(validator: Validator, candidate: Placement) -> list[int]:
    ctx = validator.ctx
    a = ctx.assignments[candidate.assignment_id]
    out = []
    for room in sorted(ctx.rooms.values(), key=lambda r: (r.capacity, r.name)):
        if not room.is_active or room.capacity < a.student_count:
            continue
        if a.required_room_type_id and room.type_id != a.required_room_type_id:
            continue
        probe = Placement(**{**candidate.__dict__, "room_id": room.id, "online_url": ""})
        if not any(v.code == Code.ROOM_OVERLAP for v in validator.check(probe)):
            out.append(room.id)
    return out


def _audience(schedule: Schedule, assignment_ids: set[int], extra_teachers=frozenset()) -> dict:
    """Who would be told about a change — only meaningful for the published version."""
    if schedule.status != ScheduleStatus.PUBLISHED:
        return {"notify_students": 0, "notify_teachers": 0}
    students, teachers = affected_people(assignment_ids, set(extra_teachers))
    return {"notify_students": students.count(), "notify_teachers": len(teachers)}


# --------------------------------------------------------------------------- entries


class EntryViewSet(viewsets.ViewSet):
    """Lessons of a timetable version. Reads follow version visibility; writes: admin."""

    permission_classes = [RolePermission]
    read_roles = ALL_ROLES
    write_roles = ADMIN_ONLY

    def in_scope(self, obj) -> bool:
        return True

    def list(self, request):
        schedule = schedule_for(request, request.query_params.get("schedule"))
        target = {k: _int(request, k) for k in ("group", "teacher", "room")}
        qs = entries_for(schedule, **{k: v for k, v in target.items() if v})
        return Response([entry_payload(e) for e in qs])

    def retrieve(self, request, pk=None):
        entry = get_object_or_404(ScheduleEntry.objects.select_related(*ENTRY_RELATED), pk=pk)
        schedule_for(request, entry.schedule_id)
        return Response(entry_payload(entry))

    def _respond(self, request, schedule, data, entry=None):
        comment = request.data.get("comment", "")
        dry_run = str(request.data.get("dry_run", "")).lower() in ("1", "true")
        editor = Editor(schedule, user=request.user, comment=comment)
        old_teacher = {entry.assignment.teacher_id} if entry else set()
        key = entry.pk if entry else "candidate"
        merged = {**snapshot(entry), **data} if entry else data
        try:
            if dry_run:
                violations = editor.check(merged, key=key)
                if violations:
                    raise ConflictError(violations, editor.validator)
                return Response(
                    {"ok": True, **_audience(schedule, {merged["assignment_id"]}, old_teacher)}
                )
            result = editor.update(entry, data) if entry else editor.create(data)
        except ConflictError as e:
            by_key = {**e.validator.placements, key: to_placement(merged, key)}
            return Response(
                {
                    "detail": _("This change would create a conflict."),
                    "violations": [violation_payload(v, editor.ctx, by_key) for v in e.violations]
                    or [{"code": "database", "message": _("This time is already taken.")}],
                },
                status=status.HTTP_409_CONFLICT,
            )
        result = ScheduleEntry.objects.select_related(*ENTRY_RELATED).get(pk=result.pk)
        return Response(
            {**entry_payload(result), **_audience(schedule, {result.assignment_id}, old_teacher)},
            status=status.HTTP_200_OK if entry else status.HTTP_201_CREATED,
        )

    def create(self, request):
        serializer = EntryWriteSerializer(data=request.data, context={"creating": True})
        serializer.is_valid(raise_exception=True)
        schedule = serializer.validated_data["schedule"]
        return self._respond(request, schedule, serializer.entry_data())

    def partial_update(self, request, pk=None):
        entry = get_object_or_404(
            ScheduleEntry.objects.select_related("schedule", "assignment"), pk=pk
        )
        serializer = EntryWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return self._respond(request, entry.schedule, serializer.entry_data(), entry)

    def destroy(self, request, pk=None):
        entry = get_object_or_404(ScheduleEntry.objects.select_related("schedule"), pk=pk)
        audience = _audience(entry.schedule, {entry.assignment_id})
        Editor(entry.schedule, user=request.user, comment=request.data.get("comment", "")).delete(
            entry
        )
        return Response(audience)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel or restore the lesson on one date (holiday, illness)."""
        entry = get_object_or_404(ScheduleEntry.objects.select_related("schedule"), pk=pk)
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not EntryOccurrence.objects.filter(
            entry=entry, date=serializer.validated_data["date"]
        ).exists():
            raise ValidationError({"date": _("There is no such lesson on this date.")})
        editor = Editor(
            entry.schedule, user=request.user, comment=serializer.validated_data.get("comment", "")
        )
        try:
            editor.cancel_occurrence(
                entry,
                serializer.validated_data["date"],
                restore=serializer.validated_data["restore"],
            )
        except ConflictError:
            return Response(
                {"detail": _("This time is already taken.")}, status=status.HTTP_409_CONFLICT
            )
        return Response({"ok": True, **_audience(entry.schedule, {entry.assignment_id})})


# --------------------------------------------------------------------------- read views


class TimetableView(APIView):
    """Weekly/session timetable of a group, teacher, room or `me` (published by default)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        schedule = schedule_for(request, request.query_params.get("schedule"))
        target = resolve_target(request)
        entries = entries_for(schedule, **target)
        return Response(
            {
                "schedule": {"id": schedule.pk, "name": schedule.name, "status": schedule.status},
                "entries": [entry_payload(e) for e in entries],
            }
        )


class OccurrencesView(APIView):
    """Dated lessons in a range, including cancelled ones (for "Bugun" and calendars)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        schedule = schedule_for(request, request.query_params.get("schedule"))
        target = resolve_target(request)
        try:
            start = date.fromisoformat(request.query_params["date_from"])
            end = date.fromisoformat(
                request.query_params.get("date_to") or request.query_params["date_from"]
            )
        except (KeyError, ValueError) as e:
            raise ValidationError({"date_from": _("Enter a date (YYYY-MM-DD).")}) from e
        if (end - start).days > 62:
            raise ValidationError({"date_to": _("Choose at most two months.")})
        entries = {e.pk: e for e in entries_for(schedule, **target)}
        occurrences = EntryOccurrence.objects.filter(
            entry__in=entries.keys(), date__gte=start, date__lte=end
        ).order_by("date", "during")
        return Response(
            [
                {**entry_payload(entries[o.entry_id]), "date": o.date, "status": o.status}
                for o in occurrences
            ]
        )


class DashboardView(APIView):
    """Numbers for the dispatcher's home page."""

    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES
    write_roles = frozenset()

    def get(self, request):
        schedule_id = request.query_params.get("schedule")
        schedule = (
            get_object_or_404(Schedule, pk=schedule_id) if schedule_id else published_schedule()
        )
        form = request.query_params.get("form")
        ctx = load_context(schedule.semester)
        placements = placements_from_entries(schedule.entries.all())
        report = validate(placements, ctx)
        by_key = {p.key: p for p in placements}

        def form_ok(a) -> bool:
            return not form or ctx.forms[ctx.periods[a.period_id].form_id].code == form

        assignments = [a for a in ctx.assignments.values() if form_ok(a)]
        missing = {
            v.params["assignment_id"]: v.params["required"] - v.params["placed"]
            for v in report.violations
            if v.code == Code.PLAN_INCOMPLETE
        }
        required = {
            a.id: (a.weekly_lessons + a.alternating_lessons) or a.total_lessons for a in assignments
        }
        faculty_of = {
            g.id: g.program_form.program.faculty_id
            for g in Group.objects.select_related("program_form__program")
        }
        per_faculty: dict[int, list[int]] = defaultdict(lambda: [0, 0])
        for a in assignments:
            fac = faculty_of[a.group_ids[0]]
            per_faculty[fac][0] += required[a.id] - missing.get(a.id, 0)
            per_faculty[fac][1] += required[a.id]
        conflicts = [
            v
            for v in report.conflicts
            if any(
                k in by_key and form_ok(ctx.assignments[by_key[k].assignment_id]) for k in v.keys
            )
        ]
        groups = Group.objects.all()
        if form:
            groups = groups.filter(program_form__form__code=form)
        total_required = sum(required.values())
        total_missing = sum(missing.get(a.id, 0) for a in assignments)
        return Response(
            {
                "schedule": {"id": schedule.pk, "name": schedule.name, "status": schedule.status},
                "groups": groups.count(),
                "teachers": len({a.teacher_id for a in assignments})
                if form
                else Teacher.objects.count(),
                "rooms": Room.objects.filter(is_active=True).count(),
                "lessons_placed": total_required - total_missing,
                "lessons_unplaced": total_missing,
                "conflicts": [violation_payload(v, ctx, by_key) for v in conflicts[:50]],
                "conflict_count": len(conflicts),
                "faculties": [
                    {
                        "id": f.pk,
                        "name": f.name,
                        "placed": per_faculty[f.pk][0],
                        "required": per_faculty[f.pk][1],
                        "percent": round(100 * per_faculty[f.pk][0] / per_faculty[f.pk][1])
                        if per_faculty[f.pk][1]
                        else 0,
                    }
                    for f in Faculty.objects.all()
                ],
            }
        )


__all__ = [
    "DashboardView",
    "EntryViewSet",
    "ExportView",
    "OccurrencesView",
    "ScheduleViewSet",
    "TimetableView",
]


class ExportView(APIView):
    """GET /api/export/?type=xlsx|pdf&group=ID|teacher=ID|room=ID|me=1&lang=uz|ru|en

    (`format` is reserved by DRF for content negotiation, hence `type`.)"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        schedule = schedule_for(request, request.query_params.get("schedule"))
        target = resolve_target(request)
        fmt = request.query_params.get("type", "xlsx")
        if fmt not in ("xlsx", "pdf"):
            raise ValidationError({"type": _("Choose xlsx or pdf.")})
        lang = request.query_params.get("lang") or request.LANGUAGE_CODE
        if lang not in ("uz", "ru", "en"):
            raise ValidationError({"lang": _("Choose uz, ru or en.")})
        if "student" in target:
            view, name = "group", target["student"].group.name
        elif "group" in target:
            view, name = "group", get_object_or_404(Group, pk=target["group"]).name
        elif "teacher" in target:
            view, name = "teacher", get_object_or_404(Teacher, pk=target["teacher"]).short_name
        else:
            view, name = "room", get_object_or_404(Room, pk=target["room"]).name
        content, mime = export(schedule, entries_for(schedule, **target), view, name, fmt, lang)
        response = HttpResponse(content, content_type=mime)
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)
        response["Content-Disposition"] = f'attachment; filename="{safe}.{fmt}"'
        return response
