"""Turn a semester into a solver problem: lessons to place ("units"), their candidate times
and rooms, and the lessons that stay where they are.

Pre-filtering removes every option a hard constraint already rules out on its own
(blocked time, day off, teacher unavailable, wrong study day, room too small or of the
wrong type, resource already taken by a kept lesson). Lessons left without options are
reported with a reason before any search starts.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from apps.academics.choices import ScheduleMode, WeekParity
from apps.scheduling.services.occurrences import parity_matches
from apps.scheduling.validators import (
    AssignmentInfo,
    Code,
    Placement,
    ValidationContext,
    Validator,
)

from .messages import Diagnostic

# Rooms kept per lesson: the smallest ones that fit. Bigger rooms stay free for big lessons
# and the model stays small; see ASSUMPTIONS.md.
ROOMS_PER_UNIT = 8


@dataclass(frozen=True)
class Slot:
    """A time choice: weekly (weekday + parity) or dated."""

    lesson_time_id: int
    weekday: int | None = None
    week_parity: str | None = None
    date: date | None = None

    @property
    def order(self) -> tuple:
        return (
            self.date or date.min,
            self.weekday or 0,
            self.week_parity or "",
            self.lesson_time_id,
        )


@dataclass
class Unit:
    """One lesson to place."""

    key: str
    assignment_id: int
    slots: list[Slot]
    rooms: list[int]  # empty for distance learning (no room, link instead)
    needs_room: bool
    group: str  # units of one assignment with the same kind are interchangeable


@dataclass
class Problem:
    ctx: ValidationContext
    units: list[Unit]
    fixed: list[Placement]  # lessons that are kept as they are
    removed: list[int] = field(default_factory=list)  # base entry ids replaced by the solver
    diagnostics: list[Diagnostic] = field(default_factory=list)
    skipped: dict[int, int] = field(default_factory=dict)  # assignment -> lessons not attempted

    @property
    def lessons_total(self) -> int:
        return len(self.units) + sum(self.skipped.values())


def in_scope(ctx: ValidationContext, a: AssignmentInfo, faculty_groups, form_id) -> bool:
    if form_id and ctx.periods[a.period_id].form_id != form_id:
        return False
    return faculty_groups is None or bool(set(a.group_ids) & faculty_groups)


def required_by_kind(ctx: ValidationContext, a: AssignmentInfo) -> dict[str, int]:
    """How many lessons the plan needs: per week (every / alternating) or dated in total."""
    if ctx.periods[a.period_id].weeks_count:
        return {"every": a.weekly_lessons, "alt": a.alternating_lessons}
    return {"dated": a.total_lessons}


def kind_of(p: Placement) -> str:
    if p.is_dated:
        return "dated"
    return "every" if p.week_parity == WeekParity.EVERY else "alt"


def build_problem(
    ctx: ValidationContext,
    base: list[Placement],
    *,
    faculty_groups: set[int] | None = None,
    form_id: int | None = None,
    mode: str = "rebuild",
    rooms_per_unit: int = ROOMS_PER_UNIT,
) -> Problem:
    """`mode`: "rebuild" keeps only pinned lessons in scope, "fill" keeps all of them and
    places only what is missing. Lessons outside the scope are always kept."""
    scope = {a.id for a in ctx.assignments.values() if in_scope(ctx, a, faculty_groups, form_id)}
    fixed, removed = [], []
    for p in base:
        keep = p.assignment_id not in scope or p.is_locked or mode == "fill"
        (fixed if keep else removed).append(p)

    problem = Problem(ctx=ctx, units=[], fixed=fixed, removed=[p.key for p in removed])
    _fixed_conflicts(problem)
    validator = Validator(ctx, fixed)
    kept: dict[tuple[int, str], int] = defaultdict(int)
    for p in fixed:
        kept[(p.assignment_id, kind_of(p))] += 1

    for aid in sorted(scope):
        a = ctx.assignments[aid]
        need = {kind: max(0, n - kept[(aid, kind)]) for kind, n in required_by_kind(ctx, a).items()}
        if not sum(need.values()):
            continue
        reason = _blocking_reason(ctx, a)
        rooms, room_reason = _candidate_rooms(ctx, a, rooms_per_unit)
        reason = reason or room_reason
        slots_by_kind = {kind: _candidate_slots(ctx, a, kind, validator) for kind in need}
        if not reason and not any(slots_by_kind[k] for k, n in need.items() if n):
            reason = Diagnostic.make("no_time", ctx, assignment_id=aid)
        if reason:
            problem.diagnostics.append(reason)
            problem.skipped[aid] = sum(need.values())
            continue
        form = ctx.form_of(a)
        for kind, n in need.items():
            for i in range(n):
                problem.units.append(
                    Unit(
                        key=f"a{aid}:{kind}:{i}",
                        assignment_id=aid,
                        slots=slots_by_kind[kind],
                        rooms=rooms,
                        needs_room=form.requires_room,
                        group=f"{aid}:{kind}",
                    )
                )
    _capacity_warnings(problem, validator)
    return problem


# --------------------------------------------------------------------------- filters


def _blocking_reason(ctx: ValidationContext, a: AssignmentInfo) -> Diagnostic | None:
    """Problems no timetable can fix: the data has to change first."""
    if a.language not in ctx.teacher_languages.get(a.teacher_id, ()):
        return Diagnostic.make("teacher_language", ctx, assignment_id=a.id)
    if a.stream_id is not None:
        langs = {ctx.groups[g].language for g in a.group_ids}
        if len(langs) > 1 or a.language not in langs:
            return Diagnostic.make("stream_language", ctx, assignment_id=a.id)
    return None


def _candidate_rooms(
    ctx: ValidationContext, a: AssignmentInfo, limit: int
) -> tuple[list[int], Diagnostic | None]:
    if not ctx.form_of(a).requires_room:
        return [], None
    fitting = sorted(
        (
            r
            for r in ctx.rooms.values()
            if r.is_active
            and r.capacity >= a.student_count
            and (not a.required_room_type_id or r.type_id == a.required_room_type_id)
        ),
        key=lambda r: (r.capacity, r.name),
    )
    if fitting:
        return [r.id for r in fitting[:limit]], None
    typed = [
        r
        for r in ctx.rooms.values()
        if r.is_active and (not a.required_room_type_id or r.type_id == a.required_room_type_id)
    ]
    biggest = max((r.capacity for r in typed), default=0)
    return [], Diagnostic.make("no_room", ctx, assignment_id=a.id, biggest=biggest)


def _candidate_slots(
    ctx: ValidationContext, a: AssignmentInfo, kind: str, fixed: Validator
) -> list[Slot]:
    period = ctx.periods[a.period_id]
    form = ctx.forms[period.form_id]
    times = sorted(
        (lt for lt in ctx.lesson_times.values() if lt.form_id == form.id), key=lambda lt: lt.number
    )
    unavailable = ctx.unavailable.get(a.teacher_id, set())
    if kind == "dated":
        if form.mode != ScheduleMode.SESSION:
            return []
        days = [
            (d.weekday(), d)
            for d in period.dates()
            if d.weekday() in form.study_weekdays and d not in ctx.calendar.days_off
        ]
        parities = [None]
    else:
        days = [(wd, None) for wd in sorted(form.study_weekdays)]
        parities = [WeekParity.EVERY] if kind == "every" else [WeekParity.ODD, WeekParity.EVEN]

    out = []
    for weekday, day in days:
        if (weekday, None) in unavailable:
            continue
        for lt in times:
            if (weekday, lt.id) in unavailable:
                continue
            if any(b.is_hard and b.hits(weekday, form.id, lt) for b in ctx.blocked):
                continue
            for parity in parities:
                slot = Slot(lt.id, None if day else weekday, parity, day)
                if _taken_by_kept(fixed, a, slot):
                    continue
                out.append(slot)
    return out


def _taken_by_kept(fixed: Validator, a: AssignmentInfo, slot: Slot) -> bool:
    """Teacher or group already busy because of a lesson that stays."""
    teachers, slots = _kept_resources(fixed)
    if a.teacher_id not in teachers and not a.slot_keys & slots:
        return False
    probe = to_placement("probe", a.id, slot, room_id=None)
    return any(v.code in (Code.TEACHER_OVERLAP, Code.GROUP_OVERLAP) for v in fixed.check(probe))


def _kept_resources(fixed: Validator) -> tuple[set[int], set[int]]:
    cached = getattr(fixed, "_kept_resources", None)
    if cached is None:
        teachers, slots = set(), set()
        for p in fixed.placements.values():
            a = fixed.ctx.assignments[p.assignment_id]
            teachers.add(a.teacher_id)
            slots |= a.slot_keys
        cached = fixed._kept_resources = (teachers, slots)
    return cached


def to_placement(key, assignment_id: int, slot: Slot, room_id: int | None) -> Placement:
    return Placement(
        key=key,
        assignment_id=assignment_id,
        lesson_time_id=slot.lesson_time_id,
        weekday=slot.weekday,
        week_parity=slot.week_parity,
        date=slot.date,
        room_id=room_id,
    )


# --------------------------------------------------------------------------- warnings


def _fixed_conflicts(problem: Problem) -> None:
    """Kept lessons that already clash: the solver works around them but cannot fix them."""
    report = Validator(problem.ctx, problem.fixed).validate(completeness=False)
    real = [v for v in report.conflicts if v.code not in (Code.LINK_MISSING, Code.PLAN_EXCESS)]
    if real:
        problem.diagnostics.append(Diagnostic.make("fixed_conflicts", problem.ctx, count=len(real)))


def _capacity_warnings(problem: Problem, validator: Validator) -> None:
    """Simple counting checks that explain an incomplete result in advance."""
    ctx = problem.ctx
    per_teacher: dict[int, list[Unit]] = defaultdict(list)
    per_group: dict[tuple[int, str], int] = defaultdict(int)
    for u in problem.units:
        a = ctx.assignments[u.assignment_id]
        per_teacher[a.teacher_id].append(u)
        for g in a.group_ids:
            per_group[(g, "dated" if u.slots and u.slots[0].date else "weekly")] += 1
    for teacher_id, units in per_teacher.items():
        distinct = {(s.date, s.weekday, s.lesson_time_id) for u in units for s in u.slots}
        if len(units) > len(distinct):
            problem.diagnostics.append(
                Diagnostic.make(
                    "teacher_overloaded",
                    ctx,
                    teacher_id=teacher_id,
                    lessons=len(units),
                    slots=len(distinct),
                )
            )
    for (group_id, kind), count in per_group.items():
        group = ctx.groups[group_id]
        form = ctx.forms[group.form_id]
        if kind == "weekly":
            capacity = len(form.study_weekdays) * form.max_lessons_per_day
        else:
            period = next(
                (p for p in ctx.periods.values() if p.form_id == form.id and not p.weeks_count),
                None,
            )
            days = (
                sum(
                    1
                    for d in period.dates()
                    if d.weekday() in form.study_weekdays and d not in ctx.calendar.days_off
                )
                if period
                else 0
            )
            capacity = days * form.max_lessons_per_day
        if count > capacity:
            problem.diagnostics.append(
                Diagnostic.make(
                    "group_overloaded", ctx, group_id=group_id, lessons=count, capacity=capacity
                )
            )


def weekly_dates(
    ctx: ValidationContext, period_id: int, slot: Slot, dates: list[date]
) -> list[date]:
    """Dates (among `dates`) on which a weekly lesson really takes place."""
    period = ctx.periods[period_id]
    return [
        d
        for d in dates
        if period.start_date <= d <= period.end_date
        and d not in ctx.calendar.days_off
        and ctx.calendar.effective_weekday(d) == slot.weekday
        and parity_matches(slot.week_parity, period.week_number(d))
    ]
