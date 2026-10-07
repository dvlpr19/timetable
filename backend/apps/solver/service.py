"""Automatic timetabling runs: build the problem, solve, verify with the validator, save the
result as a new draft and explain what could not be placed."""

from __future__ import annotations

import logging
import threading
import time
from collections import Counter, defaultdict

from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from apps.academics.models import Group
from apps.scheduling.models import Schedule, ScheduleEntry, ScheduleStatus
from apps.scheduling.services.editing import copy_schedule
from apps.scheduling.services.occurrences import CalendarIndex, sync_occurrences
from apps.scheduling.validators import (
    DEFAULT_WEIGHTS,
    LINK_PLACEHOLDER,
    Code,
    Placement,
    ValidationContext,
    Validator,
    load_context,
    placements_from_entries,
    soft_report,
    validate,
)

from .base import SolveParams
from .cpsat import CpSatSolver
from .messages import Diagnostic
from .models import SolverRun, SolverStatus
from .problem import ROOMS_PER_UNIT, Problem, Slot, build_problem, kind_of, to_placement

log = logging.getLogger(__name__)

SOLVERS = {"cpsat": CpSatSolver}
MAX_TIME_LIMIT = 600
SAVE_RESERVE = 5  # seconds kept for verifying and saving the result


def base_schedule_for(semester) -> Schedule | None:
    return Schedule.objects.filter(semester=semester, status=ScheduleStatus.PUBLISHED).first()


def problem_for(run: SolverRun) -> tuple[Problem, list[Placement], ValidationContext]:
    ctx = load_context(run.semester)
    base = placements_from_entries(run.base_schedule.entries.all()) if run.base_schedule else []
    faculty_groups = None
    if run.faculty_id:
        faculty_groups = set(
            Group.objects.filter(program_form__program__faculty=run.faculty_id).values_list(
                "id", flat=True
            )
        )
    problem = build_problem(
        ctx,
        base,
        faculty_groups=faculty_groups,
        form_id=run.form_id,
        mode=run.params.get("mode", "rebuild"),
    )
    return problem, base, ctx


class _Reporter(threading.Thread):
    """Talks to the database for the solver: stores the latest progress and notices a
    cancellation. The search itself never waits on the database — its callbacks only touch
    memory, and every query here gives up after a short lock timeout."""

    INTERVAL = 1.0

    def __init__(self, run_id: int):
        super().__init__(daemon=True)
        self.run_id = run_id
        self.cancelled = False
        self._latest: dict | None = None
        self._lock = threading.Lock()
        self._done = threading.Event()

    def push(self, progress: dict) -> None:
        with self._lock:
            self._latest = progress

    def should_stop(self) -> bool:
        return self.cancelled

    def run(self) -> None:
        try:
            while not self._done.wait(self.INTERVAL):
                self._tick()
            self._tick()
        finally:
            connection.close()

    def finish(self) -> None:
        self._done.set()
        self.join(timeout=5)

    def _tick(self) -> None:
        with self._lock:
            progress, self._latest = self._latest, None
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL lock_timeout = '2s'")
                if progress is not None:
                    SolverRun.objects.filter(pk=self.run_id).update(progress=progress)
                self.cancelled = SolverRun.objects.filter(
                    pk=self.run_id, status=SolverStatus.CANCELLED
                ).exists()
        except DatabaseError:
            log.warning("solver run %s: progress not stored", self.run_id)


def execute(run_id: int) -> SolverRun:
    """Run one solver job (called by the Celery task, or directly in tests)."""
    run = SolverRun.objects.select_related("semester", "base_schedule").get(pk=run_id)
    if run.status != SolverStatus.QUEUED:
        return run
    run.status = SolverStatus.RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at"])
    try:
        _execute(run)
    except Exception as e:  # report instead of leaving the run "running" forever
        log.exception("solver run %s failed", run.pk)
        SolverRun.objects.filter(pk=run.pk).update(
            status=SolverStatus.FAILED,
            finished_at=timezone.now(),
            diagnostics=[
                {
                    "code": "error",
                    "severity": "error",
                    "message": dict.fromkeys(("uz", "ru", "en"), str(e)),
                }
            ],
        )
    run.refresh_from_db()
    return run


def _execute(run: SolverRun) -> None:
    started = time.monotonic()
    limit = min(float(run.params.get("time_limit", 90)), MAX_TIME_LIMIT)
    problem, base, ctx = problem_for(run)
    params = SolveParams(
        # the limit is the whole run, so the search gets what loading left over
        time_limit=max(5.0, limit - (time.monotonic() - started) - SAVE_RESERVE),
        workers=int(run.params.get("workers", 8)),
        seed=int(run.params.get("seed", 0)),
        weights={**DEFAULT_WEIGHTS, **run.params.get("weights", {})},
    )

    reporter = _Reporter(run.pk)
    reporter.start()
    try:
        result = SOLVERS[run.algorithm]().solve(
            problem,
            params,
            hints=_hints(problem, base),
            progress=reporter.push,
            should_stop=reporter.should_stop,
        )
    finally:
        reporter.finish()
    run.refresh_from_db(fields=["status"])
    if run.status == SolverStatus.CANCELLED or result.status == "cancelled":
        SolverRun.objects.filter(pk=run.pk).update(
            status=SolverStatus.CANCELLED,
            finished_at=timezone.now(),
            model_stats=result.model_stats,
        )
        return

    placements = result.placements
    everything = problem.fixed + placements
    report = validate(everything, ctx)
    new_keys = {p.key for p in placements}
    links = sum(
        1 for v in report.conflicts if v.code == Code.LINK_MISSING and v.keys[0] in new_keys
    )
    hard = [v for v in report.conflicts if v.code != Code.LINK_MISSING]

    diagnostics = list(problem.diagnostics)
    diagnostics += _explain_unplaced(problem, placements)
    if links:
        diagnostics.append(Diagnostic.make("links_needed", ctx, count=links))
    diagnostics += [
        Diagnostic.make("assumption", ctx, which="rooms", n=ROOMS_PER_UNIT),
        Diagnostic.make("assumption", ctx, which="weeks"),
        Diagnostic.make("assumption", ctx, which="soft"),
    ]

    draft = None
    if placements or problem.removed:
        draft = _save_draft(run, problem, placements)
    soft = soft_report(everything, ctx, params.weights)
    SolverRun.objects.filter(pk=run.pk).update(
        status=SolverStatus.SUCCEEDED
        if result.status in ("optimal", "feasible") or not problem.units
        else SolverStatus.INFEASIBLE,
        finished_at=timezone.now(),
        result_schedule=draft,
        objective=result.objective,
        best_bound=result.best_bound,
        lessons_total=problem.lessons_total,
        lessons_placed=len(placements),
        hard_violations=len(hard),
        soft_violations={**soft.counts, "score": round(soft.score, 1)},
        diagnostics=[d.as_dict() for d in diagnostics],
        model_stats={
            **result.model_stats,
            "status": result.status,
            "wall_time": round(result.wall_time, 1),
        },
    )


def _hints(problem: Problem, base: list[Placement]) -> dict[str, tuple]:
    """Warm start from the lessons the solver replaces: same assignment, same kind."""
    removed = set(problem.removed)
    queues: dict[str, list[Placement]] = defaultdict(list)
    for p in base:
        if p.key in removed:
            queues[f"{p.assignment_id}:{kind_of(p)}"].append(p)
    hints = {}
    for u in problem.units:
        queue = queues.get(u.group)
        if queue:
            p = queue.pop(0)
            hints[u.key] = (Slot(p.lesson_time_id, p.weekday, p.week_parity, p.date), p.room_id)
    return hints


def _explain_unplaced(problem: Problem, placements: list[Placement]) -> list[Diagnostic]:
    """For every lesson left out: why each of its possible times did not work."""
    placed = Counter(p.assignment_id for p in placements)
    wanted = Counter(u.assignment_id for u in problem.units)
    missing = {aid: n - placed[aid] for aid, n in wanted.items() if n > placed[aid]}
    if not missing:
        return []
    ctx = problem.ctx
    validator = Validator(ctx, problem.fixed + placements)
    out = []
    for aid, count in missing.items():
        unit = next(u for u in problem.units if u.assignment_id == aid)
        why = Counter()
        for slot in unit.slots:
            probe = to_placement("probe", aid, slot, None)
            codes = {v.code for v in validator.check(probe)}
            if Code.TEACHER_OVERLAP in codes:
                why["teacher"] += 1
            elif Code.GROUP_OVERLAP in codes:
                why["group"] += 1
            elif Code.DAILY_LIMIT in codes:
                why["daily"] += 1
            elif unit.needs_room:
                free = any(
                    not any(
                        v.code == Code.ROOM_OVERLAP
                        for v in validator.check(to_placement("probe", aid, slot, r))
                    )
                    for r in unit.rooms
                )
                if not free:
                    why["room"] += 1
        out.append(
            Diagnostic.make(
                "unplaced", ctx, assignment_id=aid, missing=count, total=len(unit.slots), **why
            )
        )
    return out


@transaction.atomic
def _save_draft(run: SolverRun, problem: Problem, placements: list[Placement]) -> Schedule:
    name = f"Avtomatik #{run.pk} · {timezone.localtime().strftime('%d.%m.%Y %H:%M')}"
    if run.base_schedule:
        draft = copy_schedule(
            run.base_schedule, name=name, user=run.created_by, exclude=problem.removed
        )
    else:
        draft = Schedule.objects.create(semester=run.semester, name=name, created_by=run.created_by)
    entries = ScheduleEntry.objects.bulk_create(
        [
            ScheduleEntry(
                schedule=draft,
                assignment_id=p.assignment_id,
                lesson_time_id=p.lesson_time_id,
                weekday=p.weekday,
                week_parity=p.week_parity,
                date=p.date,
                room_id=p.room_id,
                online_url="" if p.room_id else f"{LINK_PLACEHOLDER}{p.assignment_id}",
            )
            for p in placements
        ],
        batch_size=1000,
    )
    fresh = ScheduleEntry.objects.filter(pk__in=[e.pk for e in entries]).select_related(
        "lesson_time",
        "assignment__period",
        "assignment__group",
        "assignment__stream",
        "assignment__subgroup__group",
    )
    sync_occurrences(fresh, CalendarIndex.load())
    return draft


# --------------------------------------------------------------------------- comparison


def _positions(placements) -> Counter:
    return Counter(
        (p.assignment_id, p.lesson_time_id, p.weekday, p.week_parity, p.date, p.room_id)
        for p in placements
    )


def summary(schedule: Schedule, ctx: ValidationContext) -> tuple[dict, list[Placement]]:
    placements = placements_from_entries(schedule.entries.all())
    report = validate(placements, ctx)
    soft = soft_report(placements, ctx)
    missing = sum(
        v.params["required"] - v.params["placed"]
        for v in report.violations
        if v.code == Code.PLAN_INCOMPLETE
    )
    return (
        {
            "id": schedule.pk,
            "name": schedule.name,
            "lessons": len(placements),
            "missing": missing,
            "hard_conflicts": len([v for v in report.conflicts if v.code != Code.LINK_MISSING]),
            "links_missing": len([v for v in report.conflicts if v.code == Code.LINK_MISSING]),
            "soft": soft.counts,
            "soft_score": round(soft.score, 1),
        },
        placements,
    )


def compare(run: SolverRun) -> dict:
    """The result next to the version it started from: quality and how much moved."""
    ctx = load_context(run.semester)
    result, new = summary(run.result_schedule, ctx)
    out = {"result": result, "base": None, "kept": len(new), "added": len(new), "removed": 0}
    if run.base_schedule:
        base, old = summary(run.base_schedule, ctx)
        a, b = _positions(old), _positions(new)
        kept = sum((a & b).values())
        out.update(
            base=base, kept=kept, added=sum(b.values()) - kept, removed=sum(a.values()) - kept
        )
    return out
