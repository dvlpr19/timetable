"""Automatic timetabling API. Staff read runs; only the dispatcher starts or cancels them."""

import csv
import io

from django.db import transaction
from django.http import HttpResponse
from django.utils.translation import gettext as _
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.dates import weekday_name
from apps.core.permissions import ADMIN_ONLY, STAFF_ROLES, RolePermission
from apps.scheduling.api.views import ENTRY_RELATED, current_semester
from apps.scheduling.models import ScheduleEntry

from .. import service
from ..models import SolverRun, SolverStatus
from ..tasks import run_solver
from .serializers import SolverRunSerializer, StartSerializer, localized


class SolverRunViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SolverRunSerializer
    permission_classes = [RolePermission]
    read_roles = STAFF_ROLES
    write_roles = ADMIN_ONLY
    action_roles = {"precheck": ADMIN_ONLY, "export": STAFF_ROLES, "entries": STAFF_ROLES}
    filterset_fields = ("semester", "status")
    queryset = SolverRun.objects.select_related(
        "faculty", "form", "base_schedule", "result_schedule", "created_by"
    )

    def in_scope(self, obj) -> bool:
        return True

    def _run_from(self, data) -> SolverRun:
        semester = current_semester()
        base = data.get("base_schedule") or service.base_schedule_for(semester)
        if base and base.semester_id != semester.pk:
            raise ValidationError({"base_schedule": _("Choose a version of the current semester.")})
        return SolverRun(
            semester=semester,
            faculty=data.get("faculty"),
            form=data.get("form"),
            base_schedule=base,
            params={
                "mode": data["mode"],
                "time_limit": data["time_limit"],
                "seed": data["seed"],
                "weights": data.get("weights", {}),
            },
            created_by=self.request.user,
        )

    def create(self, request):
        start = StartSerializer(data=request.data)
        start.is_valid(raise_exception=True)
        run = self._run_from(start.validated_data)
        run.save()

        def enqueue():
            task = run_solver.delay(run.pk)
            SolverRun.objects.filter(pk=run.pk).update(celery_task_id=task.id)

        transaction.on_commit(enqueue)
        return Response(SolverRunSerializer(run).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def precheck(self, request):
        """Check the data before starting: what cannot be placed and why (nothing is saved)."""
        start = StartSerializer(data=request.data)
        start.is_valid(raise_exception=True)
        run = self._run_from(start.validated_data)
        problem, _base, _ctx = service.problem_for(run)
        return Response(
            {
                "lessons": problem.lessons_total,
                "units": len(problem.units),
                "kept": len(problem.fixed),
                "replaced": len(problem.removed),
                "diagnostics": localized([d.as_dict() for d in problem.diagnostics]),
            }
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        run = self.get_object()
        if run.status not in (SolverStatus.QUEUED, SolverStatus.RUNNING):
            return Response({"detail": _("This run has already finished.")}, status=400)
        was_queued = run.status == SolverStatus.QUEUED
        run.status = SolverStatus.CANCELLED
        run.save(update_fields=["status"])
        if was_queued and run.celery_task_id:
            from config.celery import app

            app.control.revoke(run.celery_task_id)
        # A running job notices the flag within a second and stops.
        return Response(SolverRunSerializer(run).data)

    @action(detail=True)
    def compare(self, request, pk=None):
        run = self.get_object()
        if not run.result_schedule_id:
            return Response({"detail": _("This run has no result yet.")}, status=404)
        return Response(service.compare(run))

    @action(detail=False)
    def export(self, request):
        """All runs with their numbers (CSV) — for comparing settings and algorithms."""
        out = io.StringIO()
        writer = csv.writer(out)
        soft_codes = sorted(service.DEFAULT_WEIGHTS)
        writer.writerow(
            [
                "id", "created_at", "algorithm", "faculty", "form", "mode", "time_limit",
                "seed",
                "status", "seconds", "lessons_total", "lessons_placed", "hard_violations",
                "objective", "best_bound", "soft_score", *soft_codes, "variables", "constraints",
            ]
        )  # fmt: skip
        for run in self.filter_queryset(self.get_queryset()):
            seconds = (
                round((run.finished_at - run.started_at).total_seconds(), 1)
                if run.finished_at and run.started_at
                else ""
            )
            soft = run.soft_violations or {}
            writer.writerow(
                [
                    run.pk, run.created_at.isoformat(), run.algorithm,
                    run.faculty.code if run.faculty else "", run.form.code if run.form else "",
                    run.params.get("mode", ""), run.params.get("time_limit", ""),
                    run.params.get("seed", ""),
                    run.status, seconds, run.lessons_total, run.lessons_placed, run.hard_violations,
                    run.objective if run.objective is not None else "",
                    run.best_bound if run.best_bound is not None else "",
                    soft.get("score", ""), *(soft.get(c, "") for c in soft_codes),
                    run.model_stats.get("variables", ""), run.model_stats.get("constraints", ""),
                ]
            )  # fmt: skip
        return _csv(out.getvalue(), "solver-runs.csv")

    @action(detail=True)
    def entries(self, request, pk=None):
        """The resulting timetable as CSV (one row per lesson)."""
        run = self.get_object()
        if not run.result_schedule_id:
            return Response({"detail": _("This run has no result yet.")}, status=404)
        qs = (
            ScheduleEntry.objects.filter(schedule=run.result_schedule_id)
            .select_related(*ENTRY_RELATED)
            .prefetch_related("assignment__stream__groups")
            .order_by("assignment__period__form__order", "date", "weekday", "lesson_time__number")
        )
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(
            [_("Form"), _("Day"), _("Weeks"), _("Lesson"), _("Time"), _("Subject"),
             _("Lesson type"), _("Teacher"), _("Groups"), _("Room"), _("Pinned")]
        )  # fmt: skip
        for e in qs:
            a = e.assignment
            groups = ", ".join(g.name for g in a.target_groups())
            if a.subgroup_id:
                groups = f"{groups}/{a.subgroup.number}"
            writer.writerow(
                [
                    a.period.form.name,
                    e.date.isoformat() if e.date else weekday_name(e.weekday),
                    e.get_week_parity_display() if e.week_parity else "",
                    e.lesson_time.number,
                    f"{e.lesson_time.start:%H:%M}–{e.lesson_time.end:%H:%M}",
                    a.subject.name,
                    a.lesson_type.name,
                    a.teacher.short_name,
                    groups,
                    e.room.name if e.room else (e.online_url or ""),
                    "1" if e.is_locked else "",
                ]
            )
        return _csv(out.getvalue(), f"solver-run-{run.pk}.csv")


def _csv(text: str, filename: str) -> HttpResponse:
    # BOM so Excel opens UTF-8 (Cyrillic, o‘) correctly
    response = HttpResponse("﻿" + text, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
