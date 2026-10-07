"""Timetable rules from section 3: hard-constraint validation and soft-constraint scoring.

One implementation serves manual editing (drag-and-drop checks), Excel import, solver
output verification, the seed and reports. The core works on plain dataclasses, so it is
fast and testable without a database; `load_context` / `placements_from_entries` adapt
Django models at the bottom of the module.

Hard constraints (numbers as in the spec):
 1 teacher in one place at a time (all forms, odd/even weeks, real dates)
 2 group in one place at a time (subgroups may run in parallel, never with the whole group)
 3 one lesson per physical room at a time (a stream lecture is one lesson)
 4 room capacity >= students
 5 room type matches the lesson; physical room for in-person forms, link for distance
 6 never in blocked times (Friday prayer) or on days off (dated lessons)
 7 within the form's bell schedule, study days and teaching period
 8 not in a teacher's "unavailable" time
 9 every planned lesson is placed (completeness)
10 at most N lessons per day for a student
11 teacher speaks the group's teaching language; a stream joins one language
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Hashable, Iterable
from dataclasses import dataclass, field
from datetime import date, time, timedelta
from enum import StrEnum

from django.utils import translation
from django.utils.translation import gettext as _

from apps.academics.choices import (
    MAX_SUBGROUPS,
    SLOTS_PER_GROUP,
    AvailabilityLevel,
    ScheduleMode,
    WeekParity,
)
from apps.core.dates import format_long_date, lesson_label, weekday_name

from .services.occurrences import CalendarIndex, lesson_dates, parity_matches

# --------------------------------------------------------------------------- codes


class Code(StrEnum):
    TEACHER_OVERLAP = "teacher_overlap"
    GROUP_OVERLAP = "group_overlap"
    ROOM_OVERLAP = "room_overlap"
    CAPACITY = "capacity"
    ROOM_TYPE = "room_type"
    ROOM_MISSING = "room_missing"
    LINK_MISSING = "link_missing"
    ROOM_INACTIVE = "room_inactive"
    BLOCKED_TIME = "blocked_time"
    HOLIDAY = "holiday"
    OUTSIDE_BELL = "outside_bell"
    OUTSIDE_PERIOD = "outside_period"
    TEACHER_UNAVAILABLE = "teacher_unavailable"
    PLAN_INCOMPLETE = "plan_incomplete"
    PLAN_EXCESS = "plan_excess"
    DAILY_LIMIT = "daily_limit"
    TEACHER_LANGUAGE = "teacher_language"
    STREAM_LANGUAGE = "stream_language"


CONSTRAINT_NUMBER = {
    Code.TEACHER_OVERLAP: 1,
    Code.GROUP_OVERLAP: 2,
    Code.ROOM_OVERLAP: 3,
    Code.CAPACITY: 4,
    Code.ROOM_TYPE: 5,
    Code.ROOM_MISSING: 5,
    Code.LINK_MISSING: 5,
    Code.ROOM_INACTIVE: 5,
    Code.BLOCKED_TIME: 6,
    Code.HOLIDAY: 6,
    Code.OUTSIDE_BELL: 7,
    Code.OUTSIDE_PERIOD: 7,
    Code.TEACHER_UNAVAILABLE: 8,
    Code.PLAN_INCOMPLETE: 9,
    Code.PLAN_EXCESS: 9,
    Code.DAILY_LIMIT: 10,
    Code.TEACHER_LANGUAGE: 11,
    Code.STREAM_LANGUAGE: 11,
}


class Soft(StrEnum):
    STUDENT_GAPS = "student_gaps"
    TEACHER_GAPS = "teacher_gaps"
    TEACHER_PREFERENCE = "teacher_preference"
    SUBJECT_CROWDING = "subject_crowding"
    LECTURE_ORDER = "lecture_order"
    BUILDING_MOVES = "building_moves"
    BUILDING_SPREAD = "building_spread"
    SHIFT = "shift"
    SOFT_BLOCKED = "soft_blocked"


DEFAULT_WEIGHTS: dict[str, float] = {
    Soft.STUDENT_GAPS: 10,
    Soft.TEACHER_GAPS: 3,
    Soft.TEACHER_PREFERENCE: 5,
    Soft.SUBJECT_CROWDING: 8,
    Soft.LECTURE_ORDER: 4,
    Soft.BUILDING_MOVES: 6,
    Soft.BUILDING_SPREAD: 2,
    Soft.SHIFT: 6,
    Soft.SOFT_BLOCKED: 1,
}

# --------------------------------------------------------------------------- input data


@dataclass(frozen=True)
class FormInfo:
    id: int
    code: str
    mode: str  # ScheduleMode
    requires_room: bool
    max_lessons_per_day: int
    study_weekdays: frozenset[int]
    name: dict = field(default_factory=dict, compare=False)


@dataclass(frozen=True)
class PeriodInfo:
    id: int
    form_id: int
    start_date: date
    end_date: date
    weeks_count: int | None = None

    @property
    def first_monday(self) -> date:
        return self.start_date - timedelta(days=self.start_date.weekday())

    def week_number(self, day: date) -> int:
        return (day - self.first_monday).days // 7 + 1

    def dates(self):
        day = self.start_date
        while day <= self.end_date:
            yield day
            day += timedelta(days=1)


@dataclass(frozen=True)
class LessonTimeInfo:
    id: int
    form_id: int
    number: int
    start: time
    end: time
    shift: int = 1


@dataclass(frozen=True)
class RoomInfo:
    id: int
    name: str
    building_id: int
    type_id: int
    capacity: int
    is_active: bool = True


@dataclass(frozen=True)
class BlockedInfo:
    weekday: int | None
    start: time
    end: time
    form_id: int | None = None
    is_hard: bool = True
    name: dict = field(default_factory=dict, compare=False)

    def hits(self, weekday: int, form_id: int, lt: LessonTimeInfo) -> bool:
        return (
            (self.weekday is None or self.weekday == weekday)
            and (self.form_id is None or self.form_id == form_id)
            and lt.start < self.end
            and self.start < lt.end
        )


@dataclass(frozen=True)
class GroupInfo:
    id: int
    name: str
    form_id: int
    language: str
    shift: int = 1
    student_count: int = 0


@dataclass(frozen=True)
class AssignmentInfo:
    id: int
    period_id: int
    teacher_id: int
    subject_id: int
    lesson_type_code: str  # lecture / practice / seminar / lab
    group_ids: tuple[int, ...]
    student_count: int
    language: str
    subgroup_number: int | None = None
    stream_id: int | None = None
    required_room_type_id: int | None = None
    weekly_lessons: int = 0
    alternating_lessons: int = 0
    total_lessons: int = 0

    @property
    def slot_keys(self) -> frozenset[int]:
        if self.subgroup_number:
            return frozenset({self.group_ids[0] * SLOTS_PER_GROUP + self.subgroup_number})
        return frozenset(
            g * SLOTS_PER_GROUP + k for g in self.group_ids for k in range(1, MAX_SUBGROUPS + 1)
        )


@dataclass(frozen=True)
class Placement:
    """One placed lesson: weekly (weekday + parity) or dated."""

    key: Hashable
    assignment_id: int
    lesson_time_id: int
    weekday: int | None = None
    week_parity: str | None = None
    date: date | None = None
    room_id: int | None = None
    online_url: str = ""
    is_locked: bool = False
    cancelled_dates: frozenset[date] = frozenset()

    @property
    def is_dated(self) -> bool:
        return self.date is not None


@dataclass
class Names:
    """Display names for messages. Translatable ones are {"uz":…, "ru":…, "en":…}."""

    teachers: dict[int, str] = field(default_factory=dict)
    subjects: dict[int, dict] = field(default_factory=dict)
    lesson_types: dict[str, dict] = field(default_factory=dict)
    room_types: dict[int, dict] = field(default_factory=dict)
    streams: dict[int, str] = field(default_factory=dict)
    languages: dict[str, dict] = field(default_factory=dict)


@dataclass
class ValidationContext:
    forms: dict[int, FormInfo]
    periods: dict[int, PeriodInfo]
    lesson_times: dict[int, LessonTimeInfo]
    rooms: dict[int, RoomInfo]
    groups: dict[int, GroupInfo]
    assignments: dict[int, AssignmentInfo]
    blocked: list[BlockedInfo] = field(default_factory=list)
    calendar: CalendarIndex = field(default_factory=CalendarIndex)
    holiday_names: dict[date, dict] = field(default_factory=dict)
    teacher_languages: dict[int, frozenset[str]] = field(default_factory=dict)
    # teacher availability: (weekday, lesson_time_id or None for the whole day)
    unavailable: dict[int, set[tuple[int, int | None]]] = field(default_factory=dict)
    preferred: dict[int, set[tuple[int, int | None]]] = field(default_factory=dict)
    names: Names = field(default_factory=Names)

    def form_of(self, a: AssignmentInfo) -> FormInfo:
        return self.forms[self.periods[a.period_id].form_id]


# --------------------------------------------------------------------------- results


@dataclass(frozen=True)
class Violation:
    code: Code
    keys: tuple[Hashable, ...]
    params: dict = field(default_factory=dict, compare=False, hash=False)

    @property
    def constraint(self) -> int:
        return CONSTRAINT_NUMBER[self.code]

    @property
    def is_completeness(self) -> bool:
        return self.code == Code.PLAN_INCOMPLETE


@dataclass
class ValidationReport:
    violations: list[Violation]

    @property
    def conflicts(self) -> list[Violation]:
        """Everything except "not yet placed" — a partial draft can still be conflict-free."""
        return [v for v in self.violations if not v.is_completeness]

    @property
    def ok(self) -> bool:
        return not self.violations

    def by_constraint(self) -> dict[int, int]:
        counts: dict[int, int] = defaultdict(int)
        for v in self.violations:
            counts[v.constraint] += 1
        return dict(sorted(counts.items()))

    def for_key(self, key: Hashable) -> list[Violation]:
        return [v for v in self.violations if key in v.keys]


# --------------------------------------------------------------------------- core


@dataclass(frozen=True)
class _Occ:
    key: Hashable
    day: date
    start: time
    end: time


class Validator:
    """Holds an index of placed lessons; checks the whole timetable or one candidate."""

    def __init__(self, ctx: ValidationContext, placements: Iterable[Placement] = ()):
        self.ctx = ctx
        self.placements: dict[Hashable, Placement] = {}
        # (resource, day) -> occurrences; resource = ("t", id) | ("r", id) | ("s", slot)
        self._busy: dict[tuple, list[_Occ]] = defaultdict(list)
        # (slot, day) -> keys, for the daily limit
        self._per_day: dict[tuple[int, date], list[Hashable]] = defaultdict(list)
        for p in placements:
            self.add(p)

    # -- indexing
    def occurrences(self, p: Placement) -> list[date]:
        a = self.ctx.assignments[p.assignment_id]
        period = self.ctx.periods[a.period_id]
        return [
            d
            for d, status in lesson_dates(p, period, self.ctx.calendar)
            if status == "scheduled" and d not in p.cancelled_dates
        ]

    def _resources(self, p: Placement) -> list[tuple]:
        a = self.ctx.assignments[p.assignment_id]
        res = [("t", a.teacher_id)]
        if p.room_id is not None:
            res.append(("r", p.room_id))
        res.extend(("s", s) for s in a.slot_keys)
        return res

    def add(self, p: Placement) -> None:
        if p.key in self.placements:
            self.remove(p.key)
        self.placements[p.key] = p
        lt = self.ctx.lesson_times[p.lesson_time_id]
        slots = self.ctx.assignments[p.assignment_id].slot_keys
        for day in self.occurrences(p):
            occ = _Occ(p.key, day, lt.start, lt.end)
            for res in self._resources(p):
                self._busy[(res, day)].append(occ)
            for s in slots:
                self._per_day[(s, day)].append(p.key)

    def remove(self, key: Hashable) -> None:
        p = self.placements.pop(key, None)
        if p is None:
            return
        for bucket in self._busy.values():
            bucket[:] = [o for o in bucket if o.key != key]
        for bucket in self._per_day.values():
            bucket[:] = [k for k in bucket if k != key]

    # -- checks
    def check(self, p: Placement) -> list[Violation]:
        """Violations a placement would cause against the indexed timetable (itself excluded).

        Used for drag-and-drop: green cell = empty list.
        """
        return self._single(p) + self._overlaps(p, exclude={p.key}) + self._daily(p)

    def validate(self, *, completeness: bool = True) -> ValidationReport:
        found: dict[tuple, Violation] = {}
        for p in self.placements.values():
            for v in self._single(p) + self._overlaps(p, exclude={p.key}) + self._daily(p):
                found.setdefault((v.code, frozenset(v.keys), _param_key(v)), v)
        found.update({(v.code, v.keys, ()): v for v in self._stream_languages()})
        found.update({(v.code, v.keys, ()): v for v in self._plan(completeness)})
        return ValidationReport(list(found.values()))

    # constraint 1-3
    def _overlaps(self, p: Placement, exclude: set) -> list[Violation]:
        ctx = self.ctx
        lt = ctx.lesson_times[p.lesson_time_id]
        hits: dict[tuple[Code, Hashable], list[date]] = defaultdict(list)
        resource_code = {"t": Code.TEACHER_OVERLAP, "r": Code.ROOM_OVERLAP, "s": Code.GROUP_OVERLAP}
        for day in self.occurrences(p):
            for res in self._resources(p):
                for o in self._busy.get((res, day), ()):
                    if o.key in exclude or not (lt.start < o.end and o.start < lt.end):
                        continue
                    code = resource_code[res[0]]
                    days = hits[(code, o.key)]
                    if not days or days[-1] != day:
                        days.append(day)
        result = []
        for (code, other_key), days in hits.items():
            other = self.placements[other_key]
            params = {"day": days[0], "dates": len(days)}
            if code == Code.GROUP_OVERLAP:
                shared = _shared_groups(ctx, p, other)
                params["group_id"] = shared[0] if shared else None
            result.append(Violation(code, _pair(p.key, other_key), params))
        return result

    # constraints 4-8, 11 (teacher language)
    def _single(self, p: Placement) -> list[Violation]:
        ctx = self.ctx
        a = ctx.assignments[p.assignment_id]
        period = ctx.periods[a.period_id]
        form = ctx.forms[period.form_id]
        lt = ctx.lesson_times[p.lesson_time_id]
        out: list[Violation] = []

        def add(code: Code, **params):
            out.append(Violation(code, (p.key,), params))

        # 5: room or link
        if form.requires_room:
            if p.room_id is None:
                add(Code.ROOM_MISSING)
        elif p.room_id is None and not p.online_url:
            add(Code.LINK_MISSING)
        room = ctx.rooms.get(p.room_id) if p.room_id is not None else None
        if room:
            if not room.is_active:
                add(Code.ROOM_INACTIVE, room_id=room.id)
            if room.capacity < a.student_count:  # 4
                add(Code.CAPACITY, room_id=room.id, students=a.student_count)
            if a.required_room_type_id and room.type_id != a.required_room_type_id:
                add(Code.ROOM_TYPE, room_id=room.id, required=a.required_room_type_id)

        # 7: bell schedule, study days, period and mode
        if lt.form_id != form.id:
            add(Code.OUTSIDE_BELL, reason="lesson_time")
        if (form.mode == ScheduleMode.SESSION) != p.is_dated:
            add(Code.OUTSIDE_BELL, reason="mode")
        weekday = p.date.weekday() if p.is_dated else p.weekday
        if weekday not in form.study_weekdays:
            add(Code.OUTSIDE_BELL, reason="weekday")
        if p.is_dated and not (period.start_date <= p.date <= period.end_date):
            add(Code.OUTSIDE_PERIOD)

        # 6: blocked times and days off
        for b in ctx.blocked:
            if b.is_hard and b.hits(weekday, form.id, lt):
                add(Code.BLOCKED_TIME, name=b.name)
        if p.is_dated and p.date in ctx.calendar.days_off:
            add(Code.HOLIDAY, name=ctx.holiday_names.get(p.date, {}))

        # 8: teacher availability
        unavailable = ctx.unavailable.get(a.teacher_id, ())
        if (weekday, None) in unavailable or (weekday, lt.id) in unavailable:
            add(Code.TEACHER_UNAVAILABLE)

        # 11: teacher language
        if a.language not in ctx.teacher_languages.get(a.teacher_id, ()):
            add(Code.TEACHER_LANGUAGE, language=a.language)
        return out

    # constraint 10
    def _daily(self, p: Placement) -> list[Violation]:
        ctx = self.ctx
        a = ctx.assignments[p.assignment_id]
        limit = ctx.form_of(a).max_lessons_per_day
        result: dict[int, Violation] = {}
        for day in self.occurrences(p):
            for slot in a.slot_keys:
                keys = {k for k in self._per_day.get((slot, day), ()) if k != p.key} | {p.key}
                group_id = slot // SLOTS_PER_GROUP
                if len(keys) > limit and group_id not in result:
                    result[group_id] = Violation(
                        Code.DAILY_LIMIT,
                        tuple(sorted(keys, key=str)),
                        {"group_id": group_id, "day": day, "count": len(keys), "limit": limit},
                    )
        return list(result.values())

    # constraint 11 (streams)
    def _stream_languages(self) -> list[Violation]:
        out = []
        seen = set()
        for p in self.placements.values():
            a = self.ctx.assignments[p.assignment_id]
            if a.stream_id is None or a.stream_id in seen:
                continue
            seen.add(a.stream_id)
            langs = {self.ctx.groups[g].language for g in a.group_ids}
            if len(langs) > 1 or a.language not in langs:
                out.append(Violation(Code.STREAM_LANGUAGE, (p.key,), {"stream_id": a.stream_id}))
        return out

    # constraint 9
    def _plan(self, completeness: bool) -> list[Violation]:
        placed: dict[int, list[Placement]] = defaultdict(list)
        for p in self.placements.values():
            placed[p.assignment_id].append(p)
        out = []
        for a in self.ctx.assignments.values():
            ps = placed.get(a.id, [])
            if self.ctx.periods[a.period_id].weeks_count:
                every = sum(1 for p in ps if p.week_parity == WeekParity.EVERY)
                alt = sum(1 for p in ps if p.week_parity in (WeekParity.ODD, WeekParity.EVEN))
                pairs = [(every, a.weekly_lessons), (alt, a.alternating_lessons)]
            else:
                pairs = [(sum(1 for p in ps if p.is_dated), a.total_lessons)]
            keys = tuple(p.key for p in ps)
            placed_n = sum(x for x, _ in pairs)
            required_n = sum(r for _, r in pairs)
            params = {"assignment_id": a.id, "placed": placed_n, "required": required_n}
            if any(x > r for x, r in pairs):
                out.append(Violation(Code.PLAN_EXCESS, keys, params))
            elif completeness and any(x < r for x, r in pairs):
                out.append(Violation(Code.PLAN_INCOMPLETE, keys or (("assignment", a.id),), params))
        return out


def _pair(a: Hashable, b: Hashable) -> tuple:
    return tuple(sorted((a, b), key=str))


def _param_key(v: Violation) -> tuple:
    return tuple(sorted((k, str(val)) for k, val in v.params.items() if k != "dates"))


def _shared_groups(ctx: ValidationContext, p: Placement, q: Placement) -> list[int]:
    a = ctx.assignments[p.assignment_id]
    b = ctx.assignments[q.assignment_id]
    shared = a.slot_keys & b.slot_keys
    return sorted({s // SLOTS_PER_GROUP for s in shared})


def validate(
    placements: Iterable[Placement], ctx: ValidationContext, *, completeness: bool = True
) -> ValidationReport:
    return Validator(ctx, placements).validate(completeness=completeness)


# --------------------------------------------------------------------------- soft scoring


@dataclass
class SoftReport:
    counts: dict[str, float]
    weights: dict[str, float]

    @property
    def score(self) -> float:
        return sum(self.weights.get(code, 0) * n for code, n in self.counts.items())


def soft_report(
    placements: Iterable[Placement],
    ctx: ValidationContext,
    weights: dict[str, float] | None = None,
) -> SoftReport:
    """Soft-constraint counts. Weekly lessons are evaluated over one odd and one even week
    and averaged, so the numbers read as "per week"; session lessons count per date."""
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    counts: dict[str, float] = defaultdict(float)
    placements = list(placements)

    # day key -> weight: ("w", weekday, odd/even) counts 0.5, ("d", date) counts 1
    def day_keys(p: Placement) -> list[tuple[tuple, float]]:
        if p.is_dated:
            return [(("d", p.date), 1.0)]
        weeks = [n for n in (1, 2) if parity_matches(p.week_parity, n)]
        return [(("w", p.weekday, n), 0.5) for n in weeks]

    lts = ctx.lesson_times
    by_group_day: dict[tuple[int, tuple], list[tuple[Placement, int]]] = defaultdict(list)
    by_teacher_day: dict[tuple[int, tuple], list[int]] = defaultdict(list)
    day_weight: dict[tuple, float] = {}
    subgroups_used: dict[int, set[int]] = defaultdict(set)
    group_buildings: dict[tuple[int, str], set[int]] = defaultdict(set)

    for p in placements:
        a = ctx.assignments[p.assignment_id]
        lt = lts[p.lesson_time_id]
        form = ctx.forms[ctx.periods[a.period_id].form_id]
        weekday = p.date.weekday() if p.is_dated else p.weekday
        for dk, w in day_keys(p):
            day_weight[dk] = w
            by_teacher_day[(a.teacher_id, dk)].append(lt.number)
            for g in a.group_ids:
                by_group_day[(g, dk)].append((p, a.subgroup_number or 0))
                if p.room_id is not None:
                    week = dk[2] if dk[0] == "w" else dk[1].isocalendar()[1]
                    group_buildings[(g, str(week))].add(ctx.rooms[p.room_id].building_id)
        for g in a.group_ids:
            if a.subgroup_number:
                subgroups_used[g].add(a.subgroup_number)
            group = ctx.groups[g]
            if form.code == "kunduzgi" and lt.shift != group.shift:
                counts[Soft.SHIFT] += _weekly_factor(p)
        prefs = ctx.preferred.get(a.teacher_id)
        if prefs and (weekday, None) not in prefs and (weekday, lt.id) not in prefs:
            counts[Soft.TEACHER_PREFERENCE] += _weekly_factor(p)
        if any(not b.is_hard and b.hits(weekday, form.id, lt) for b in ctx.blocked):
            counts[Soft.SOFT_BLOCKED] += _weekly_factor(p)

    blocked_numbers = _blocked_numbers(ctx)
    for (g, dk), items in by_group_day.items():
        w = day_weight[dk]
        group = ctx.groups[g]
        weekday = dk[1] if dk[0] == "w" else dk[1].weekday()
        closed = blocked_numbers.get((group.form_id, weekday), set())
        perspectives = sorted(subgroups_used.get(g) or {1})
        gaps = 0
        for k in perspectives:
            numbers = [lts[p.lesson_time_id].number for p, sg in items if sg in (0, k)]
            gaps += _gaps(numbers, closed)
        counts[Soft.STUDENT_GAPS] += w * gaps / len(perspectives)
        per_subject: dict[int, int] = defaultdict(int)
        for p, sg in items:
            if sg in (0, perspectives[0]):
                per_subject[ctx.assignments[p.assignment_id].subject_id] += 1
        counts[Soft.SUBJECT_CROWDING] += w * sum(max(0, n - 2) for n in per_subject.values())
        ordered = sorted(
            (p for p, sg in items if p.room_id is not None and sg in (0, perspectives[0])),
            key=lambda p: lts[p.lesson_time_id].number,
        )
        moves = sum(
            1
            for x, y in zip(ordered, ordered[1:], strict=False)
            if ctx.rooms[x.room_id].building_id != ctx.rooms[y.room_id].building_id
        )
        counts[Soft.BUILDING_MOVES] += w * moves
    for (_teacher, dk), numbers in by_teacher_day.items():
        counts[Soft.TEACHER_GAPS] += day_weight[dk] * _gaps(numbers, set())
    weeks_per_group: dict[int, int] = defaultdict(int)
    spread: dict[int, int] = defaultdict(int)
    for (g, _week), buildings in group_buildings.items():
        weeks_per_group[g] += 1
        spread[g] += len(buildings) - 1
    counts[Soft.BUILDING_SPREAD] = sum(spread[g] / weeks_per_group[g] for g in spread)
    counts[Soft.LECTURE_ORDER] = _lecture_order(placements, ctx)
    return SoftReport({code: round(counts.get(code, 0.0), 2) for code in Soft}, weights)


def _weekly_factor(p: Placement) -> float:
    if p.is_dated or p.week_parity == WeekParity.EVERY:
        return 1.0
    return 0.5


def _gaps(numbers: list[int], closed: set[int]) -> int:
    """Free lessons between the first and last lesson of a day (blocked ones excluded)."""
    if len(numbers) < 2:
        return 0
    lo, hi = min(numbers), max(numbers)
    return sum(1 for n in range(lo, hi + 1) if n not in numbers and n not in closed)


def _blocked_numbers(ctx: ValidationContext) -> dict[tuple[int, int], set[int]]:
    out: dict[tuple[int, int], set[int]] = defaultdict(set)
    for lt in ctx.lesson_times.values():
        for weekday in range(7):
            if any(b.is_hard and b.hits(weekday, lt.form_id, lt) for b in ctx.blocked):
                out[(lt.form_id, weekday)].add(lt.number)
    return out


def _lecture_order(placements: list[Placement], ctx: ValidationContext) -> float:
    """Groups whose first seminar/practice of a subject comes before its first lecture."""
    first: dict[tuple[int, int, bool], tuple] = {}
    for p in placements:
        a = ctx.assignments[p.assignment_id]
        if a.lesson_type_code == "lab":
            continue
        moment = (p.date or date.min, p.weekday or 0, ctx.lesson_times[p.lesson_time_id].number)
        is_lecture = a.lesson_type_code == "lecture"
        for g in a.group_ids:
            k = (g, a.subject_id, is_lecture)
            if k not in first or moment < first[k]:
                first[k] = moment
    return float(
        sum(
            1
            for (g, subj, is_lecture), moment in first.items()
            if not is_lecture and (g, subj, True) in first and moment < first[(g, subj, True)]
        )
    )


# --------------------------------------------------------------------------- plan fulfilment


@dataclass(frozen=True)
class PlanRow:
    assignment_id: int
    planned: int  # lessons the plan requires in the period
    scheduled: int  # dated lessons that will actually take place
    lost: int  # lessons falling on days off or cancelled

    @property
    def matches(self) -> bool:
        return self.planned == self.scheduled


def plan_fulfilment(placements: Iterable[Placement], ctx: ValidationContext) -> list[PlanRow]:
    """Planned vs scheduled lessons per assignment (section 2.5 "reja bajarilishi")."""
    scheduled: dict[int, int] = defaultdict(int)
    lost: dict[int, int] = defaultdict(int)
    for p in placements:
        a = ctx.assignments[p.assignment_id]
        for day, status in lesson_dates(p, ctx.periods[a.period_id], ctx.calendar):
            if status == "scheduled" and day not in p.cancelled_dates:
                scheduled[a.id] += 1
            else:
                lost[a.id] += 1
    return [
        PlanRow(a.id, a.total_lessons, scheduled[a.id], lost[a.id])
        for a in ctx.assignments.values()
    ]


# --------------------------------------------------------------------------- messages


def lesson_title(ctx: ValidationContext, assignment_id: int, lang: str) -> str:
    a = ctx.assignments[assignment_id]
    subject = _tr(ctx.names.subjects.get(a.subject_id, {}), lang)
    lesson_type = _tr(ctx.names.lesson_types.get(a.lesson_type_code, {}), lang)
    if a.stream_id is not None:
        target = " + ".join(ctx.groups[g].name for g in a.group_ids)
    else:
        target = ctx.groups[a.group_ids[0]].name
        if a.subgroup_number:
            target = f"{target}/{a.subgroup_number}"
    return f"{subject} ({lesson_type.lower()}), {target}"


def when_label(ctx: ValidationContext, p: Placement, day: date | None = None) -> str:
    number = ctx.lesson_times[p.lesson_time_id].number
    if p.is_dated or (day is not None and p.week_parity is None):
        return lesson_label(format_long_date(p.date or day), number)
    return lesson_label(weekday_name(p.weekday), number)


def describe(v: Violation, ctx: ValidationContext, placements: dict[Hashable, Placement]) -> str:
    """Human-readable reason in the active language (used in tooltips and reports)."""
    lang = translation.get_language() or "uz"
    ps = [placements[k] for k in v.keys if k in placements]
    titles = [lesson_title(ctx, p.assignment_id, lang) for p in ps]
    first = ps[0] if ps else None
    a = ctx.assignments[first.assignment_id] if first else None
    pr = v.params

    def when() -> str:
        if not first:
            return ""
        both_weekly = all(not p.is_dated for p in ps)
        if both_weekly:
            return when_label(ctx, first)
        dated = next(p for p in ps if p.is_dated) if any(p.is_dated for p in ps) else first
        number = ctx.lesson_times[dated.lesson_time_id].number
        return lesson_label(format_long_date(pr.get("day") or dated.date), number)

    other = titles[1] if len(titles) > 1 else ""
    match v.code:
        case Code.TEACHER_OVERLAP:
            return _(
                "%(teacher)s has two lessons at the same time (%(when)s): %(a)s and %(b)s."
            ) % {
                "teacher": ctx.names.teachers.get(a.teacher_id, ""),
                "when": when(),
                "a": titles[0],
                "b": other,
            }
        case Code.GROUP_OVERLAP:
            return _("%(group)s has two lessons at the same time (%(when)s): %(a)s and %(b)s.") % {
                "group": ctx.groups[pr["group_id"]].name if pr.get("group_id") else "",
                "when": when(),
                "a": titles[0],
                "b": other,
            }
        case Code.ROOM_OVERLAP:
            return _("Room %(room)s is taken twice (%(when)s): %(a)s and %(b)s.") % {
                "room": ctx.rooms[first.room_id].name,
                "when": when(),
                "a": titles[0],
                "b": other,
            }
        case Code.CAPACITY:
            room = ctx.rooms[pr["room_id"]]
            return _(
                "Room %(room)s has %(seats)s seats, but %(lesson)s has %(students)s students."
            ) % {
                "room": room.name,
                "seats": room.capacity,
                "lesson": titles[0],
                "students": pr["students"],
            }
        case Code.ROOM_TYPE:
            room = ctx.rooms[pr["room_id"]]
            return _(
                "%(lesson)s needs a room of type “%(required)s”, %(room)s is “%(actual)s”."
            ) % {
                "lesson": titles[0],
                "required": _tr(ctx.names.room_types.get(pr["required"], {}), lang),
                "room": room.name,
                "actual": _tr(ctx.names.room_types.get(room.type_id, {}), lang),
            }
        case Code.ROOM_MISSING:
            return _("%(lesson)s needs a room.") % {"lesson": titles[0]}
        case Code.LINK_MISSING:
            return _("Online lesson %(lesson)s needs a link.") % {"lesson": titles[0]}
        case Code.ROOM_INACTIVE:
            return _("Room %(room)s is not in use.") % {"room": ctx.rooms[pr["room_id"]].name}
        case Code.BLOCKED_TIME:
            return _("%(when)s is closed for lessons (%(reason)s): %(lesson)s.") % {
                "when": when_label(ctx, first),
                "reason": _tr(pr.get("name", {}), lang),
                "lesson": titles[0],
            }
        case Code.HOLIDAY:
            return _("%(when)s is a day off (%(reason)s): %(lesson)s.") % {
                "when": when_label(ctx, first),
                "reason": _tr(pr.get("name", {}), lang),
                "lesson": titles[0],
            }
        case Code.OUTSIDE_BELL:
            return _("%(lesson)s is outside the %(form)s timetable (%(when)s).") % {
                "lesson": titles[0],
                "form": _tr(ctx.form_of(a).name, lang).lower(),
                "when": when_label(ctx, first),
            }
        case Code.OUTSIDE_PERIOD:
            return _("%(lesson)s: %(when)s is outside the teaching period.") % {
                "lesson": titles[0],
                "when": when_label(ctx, first),
            }
        case Code.TEACHER_UNAVAILABLE:
            return _("%(teacher)s is not available at %(when)s (%(lesson)s).") % {
                "teacher": ctx.names.teachers.get(a.teacher_id, ""),
                "when": when_label(ctx, first),
                "lesson": titles[0],
            }
        case Code.PLAN_INCOMPLETE | Code.PLAN_EXCESS:
            msg = (
                _("%(lesson)s: %(placed)s of %(required)s lessons are placed.")
                if v.code == Code.PLAN_INCOMPLETE
                else _("%(lesson)s: %(placed)s lessons are placed, the plan has %(required)s.")
            )
            return msg % {
                "lesson": lesson_title(ctx, pr["assignment_id"], lang),
                "placed": pr["placed"],
                "required": pr["required"],
            }
        case Code.DAILY_LIMIT:
            return _("%(group)s has %(count)s lessons on %(day)s (at most %(limit)s).") % {
                "group": ctx.groups[pr["group_id"]].name,
                "count": pr["count"],
                "day": format_long_date(pr["day"])
                if ctx.forms[ctx.groups[pr["group_id"]].form_id].mode == ScheduleMode.SESSION
                else weekday_name(pr["day"].weekday()),
                "limit": pr["limit"],
            }
        case Code.TEACHER_LANGUAGE:
            return _("%(teacher)s does not teach in %(language)s (%(lesson)s).") % {
                "teacher": ctx.names.teachers.get(a.teacher_id, ""),
                "language": _tr(ctx.names.languages.get(pr["language"], {}), lang).lower(),
                "lesson": titles[0],
            }
        case Code.STREAM_LANGUAGE:
            return _("Stream %(stream)s joins groups with different teaching languages.") % {
                "stream": ctx.names.streams.get(pr["stream_id"], "")
            }
    return str(v.code)


def _tr(names: dict, lang: str) -> str:
    return names.get(lang) or names.get("uz") or ""


# --------------------------------------------------------------------------- database adapters


def load_context(semester, *, assignments=None) -> ValidationContext:
    """Build a ValidationContext from the database for one semester."""
    from apps.academics.choices import TeachingLanguage
    from apps.academics.models import (
        AcademicCalendarDay,
        BlockedPeriod,
        EducationForm,
        Group,
        LessonTime,
        LessonType,
        Room,
        RoomType,
        Stream,
        Subject,
        Teacher,
        TeacherAvailability,
        TeachingAssignment,
        TeachingPeriod,
    )

    def tr(obj) -> dict:
        return {lang: getattr(obj, f"name_{lang}") or "" for lang in ("uz", "ru", "en")}

    periods = {
        p.id: PeriodInfo(p.id, p.form_id, p.start_date, p.end_date, p.weeks_count)
        for p in TeachingPeriod.objects.filter(semester=semester)
    }
    forms = {
        f.id: FormInfo(
            f.id,
            f.code,
            f.schedule_mode,
            f.requires_room,
            f.max_lessons_per_day,
            frozenset(f.study_weekdays),
            tr(f),
        )
        for f in EducationForm.objects.all()
    }
    lesson_times = {
        lt.id: LessonTimeInfo(lt.id, lt.form_id, lt.number, lt.start, lt.end, lt.shift)
        for lt in LessonTime.objects.all()
    }
    rooms = {
        r.id: RoomInfo(r.id, r.name, r.building_id, r.room_type_id, r.capacity, r.is_active)
        for r in Room.objects.all()
    }
    groups = {
        g.id: GroupInfo(
            g.id, g.name, g.program_form.form_id, g.teaching_language, g.shift, g.student_count
        )
        for g in Group.objects.select_related("program_form")
    }
    stream_groups: dict[int, list[int]] = defaultdict(list)
    for stream_id, group_id in Stream.groups.through.objects.values_list("stream_id", "group_id"):
        stream_groups[stream_id].append(group_id)
    streams = {s.id: s for s in Stream.objects.all()}

    qs = assignments
    if qs is None:
        qs = TeachingAssignment.objects.filter(period__semester=semester)
    qs = qs.select_related("lesson_type", "subgroup", "group", "stream")
    infos = {}
    for a in qs:
        if a.stream_id:
            group_ids = tuple(sorted(stream_groups[a.stream_id]))
            language = streams[a.stream_id].teaching_language
            count = sum(groups[g].student_count for g in group_ids)
        elif a.subgroup_id:
            group_ids = (a.subgroup.group_id,)
            language = groups[a.subgroup.group_id].language
            count = a.subgroup.student_count
        else:
            group_ids = (a.group_id,)
            language = a.group.teaching_language
            count = a.group.student_count
        infos[a.id] = AssignmentInfo(
            id=a.id,
            period_id=a.period_id,
            teacher_id=a.teacher_id,
            subject_id=a.subject_id,
            lesson_type_code=a.lesson_type.code,
            group_ids=group_ids,
            student_count=count,
            language=language,
            subgroup_number=a.subgroup.number if a.subgroup_id else None,
            stream_id=a.stream_id,
            required_room_type_id=a.required_room_type_id,
            weekly_lessons=a.weekly_lessons,
            alternating_lessons=a.alternating_lessons,
            total_lessons=a.total_lessons,
        )

    calendar = CalendarIndex.load()
    unavailable: dict[int, set] = defaultdict(set)
    preferred: dict[int, set] = defaultdict(set)
    for av in TeacherAvailability.objects.all():
        target = unavailable if av.level == AvailabilityLevel.UNAVAILABLE else None
        if av.level == AvailabilityLevel.PREFERRED:
            target = preferred
        if target is not None:
            target[av.teacher_id].add((av.weekday, av.lesson_time_id))

    teachers = list(Teacher.objects.all())
    names = Names(
        teachers={t.id: t.short_name for t in teachers},
        subjects={s.id: tr(s) for s in Subject.objects.all()},
        lesson_types={lt.code: tr(lt) for lt in LessonType.objects.all()},
        room_types={rt.id: tr(rt) for rt in RoomType.objects.all()},
        streams={s.id: s.name for s in streams.values()},
        languages={
            code: {lang: _label_in(label, lang) for lang in ("uz", "ru", "en")}
            for code, label in TeachingLanguage.choices
        },
    )
    return ValidationContext(
        forms=forms,
        periods=periods,
        lesson_times=lesson_times,
        rooms=rooms,
        groups=groups,
        assignments=infos,
        blocked=[
            BlockedInfo(b.weekday, b.start, b.end, b.form_id, b.is_hard, tr(b))
            for b in BlockedPeriod.objects.all()
        ],
        calendar=calendar,
        holiday_names={d.date: tr(d) for d in AcademicCalendarDay.objects.all()},
        teacher_languages={t.id: frozenset(t.teaching_languages) for t in teachers},
        unavailable=dict(unavailable),
        preferred=dict(preferred),
        names=names,
    )


def _label_in(label, lang: str) -> str:
    with translation.override(lang):
        return str(label)


def placements_from_entries(entries) -> list[Placement]:
    from .models import OccurrenceStatus

    entries = entries.prefetch_related("occurrences")
    return [
        Placement(
            key=e.pk,
            assignment_id=e.assignment_id,
            lesson_time_id=e.lesson_time_id,
            weekday=e.weekday,
            week_parity=e.week_parity,
            date=e.date,
            room_id=e.room_id,
            online_url=e.online_url,
            is_locked=e.is_locked,
            cancelled_dates=frozenset(
                o.date for o in e.occurrences.all() if o.status == OccurrenceStatus.CANCELLED
            ),
        )
        for e in entries
    ]


def validate_schedule(schedule, *, completeness: bool = True):
    """(report, context, placements by key) for a stored timetable version."""
    ctx = load_context(schedule.semester)
    placements = placements_from_entries(schedule.entries.all())
    report = validate(placements, ctx, completeness=completeness)
    return report, ctx, {p.key: p for p in placements}


__all__ = [
    "DEFAULT_WEIGHTS",
    "Code",
    "Placement",
    "Soft",
    "ValidationContext",
    "ValidationReport",
    "Validator",
    "Violation",
    "describe",
    "load_context",
    "plan_fulfilment",
    "placements_from_entries",
    "soft_report",
    "validate",
    "validate_schedule",
]
