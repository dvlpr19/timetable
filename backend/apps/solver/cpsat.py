"""CP-SAT model.

Variables: y[u, t] — unit u is held at time t; z[u, t, r] — in room r (in-person forms only,
sum_r z[u, t, r] = y[u, t]). Each unit is placed at most once; the search first places as many
units as possible and only then optimises soft constraints, so the result is always a valid
(possibly partial) timetable with reasons for what is missing.

Time is unified across forms the same way the validator does it: a weekly lesson occupies
"week keys" (weekday x odd/even week) and, for every session date it really falls on, a
"date key"; session lessons occupy their date key. Lesson times of different forms overlap
by clock time, so each key is split into elementary clock intervals and every resource
(teacher, physical room, group slot) may be used at most once per interval.

Hard constraints 1–8, 10 and 11 hold by construction (pre-filtering + the capacity rows
below); 9 (completeness) is the objective's first priority. Soft constraints optimised:
student and teacher gaps, teacher preferences, subject crowding, shifts, soft-blocked times,
and the number of buildings a group uses (spread, which also cuts building moves).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass

from ortools.sat.python import cp_model

from apps.academics.choices import SLOTS_PER_GROUP, WeekParity
from apps.scheduling.services.occurrences import parity_matches
from apps.scheduling.validators import Placement, Soft

from .base import BaseSolver, Progress, ShouldStop, SolveParams, SolveResult
from .problem import Problem, Slot, to_placement, weekly_dates

STATUS = {
    cp_model.OPTIMAL: "optimal",
    cp_model.FEASIBLE: "feasible",
    cp_model.INFEASIBLE: "infeasible",
    cp_model.MODEL_INVALID: "unknown",
    cp_model.UNKNOWN: "unknown",
}


class _Callback(cp_model.CpSolverSolutionCallback):
    def __init__(self, placed_vars, progress: Progress | None, total: int, phase: str, t0: float):
        super().__init__()
        self.placed_vars = placed_vars
        self.progress = progress
        self.total = total
        self.phase = phase
        self.t0 = t0
        self.solutions = 0
        self.last = 0.0

    def on_solution_callback(self):
        self.solutions += 1
        now = time.monotonic()
        if self.progress and (now - self.last >= 1.0 or self.solutions == 1):
            self.last = now
            self.progress(
                {
                    "phase": self.phase,
                    "elapsed": round(now - self.t0, 1),
                    "objective": self.ObjectiveValue(),
                    "bound": self.BestObjectiveBound(),
                    "placed": sum(self.Value(v) for v in self.placed_vars),
                    "total": self.total,
                    "solutions": self.solutions,
                }
            )


class CpSatSolver(BaseSolver):
    """Two phases on one model (lexicographic optimisation):
    1. place as many lessons as possible (soft constraints ignored) — finds a complete
       timetable fast;
    2. keep at least that many placed and minimise the soft penalty, starting from phase 1.
    """

    name = "cpsat"
    PHASE1_SHARE = 0.4  # of the time limit

    def solve(
        self,
        problem: Problem,
        params: SolveParams,
        *,
        hints: dict[str, tuple] | None = None,
        progress: Progress | None = None,
        should_stop: ShouldStop | None = None,
    ) -> SolveResult:
        t0 = time.monotonic()
        builder = _ModelBuilder(problem, params.weights)
        builder.build()
        model = builder.model
        total = len(problem.units)
        stats = {"units": total, "build_seconds": round(time.monotonic() - t0, 1)}
        if not total:
            return SolveResult("optimal", [], 0.0, 0.0, 0.0, stats)

        if hints:
            builder.add_hints(hints)
        model.minimize(sum(1 - p for p in builder.placed_vars))
        budget = max(1.0, float(params.time_limit) - (time.monotonic() - t0))
        first = self._run(
            builder, params, budget * self.PHASE1_SHARE, "placing", progress, should_stop, t0
        )
        stats["phase1"] = first.stats
        if first.cancelled or not first.has_solution:
            return self._result(builder, first, stats, t0)

        placed = round(sum(first.solver.value(v) for v in builder.placed_vars))
        values = builder.snapshot(first.solver)
        model.clear_hints()
        for var, value in values:
            model.add_hint(var, value)
        model.add(sum(builder.placed_vars) >= placed)
        model.minimize(sum(builder.soft))
        budget = max(1.0, float(params.time_limit) - (time.monotonic() - t0))
        second = self._run(builder, params, budget, "improving", progress, should_stop, t0)
        stats["phase2"] = second.stats
        if not second.has_solution and not second.cancelled:
            return self._result(builder, first, stats, t0)  # keep phase 1
        return self._result(builder, second, stats, t0)

    def _run(self, builder, params, seconds, phase, progress, should_stop, t0) -> _Run:
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = seconds
        solver.parameters.num_workers = int(params.workers)
        solver.parameters.random_seed = int(params.seed)
        callback = _Callback(builder.placed_vars, progress, len(builder.p.units), phase, t0)
        done = threading.Event()
        cancelled = threading.Event()

        def watchdog():
            while not done.wait(1.0):
                if should_stop and should_stop():
                    cancelled.set()
                    solver.stop_search()
                    return

        watcher = threading.Thread(target=watchdog, daemon=True)
        watcher.start()
        try:
            code = solver.solve(builder.model, callback)
        finally:
            done.set()
            watcher.join(timeout=2)
        return _Run(solver, code, cancelled.is_set(), callback.solutions)

    @staticmethod
    def _result(builder, run: _Run, stats: dict, t0: float) -> SolveResult:
        proto = builder.model.Proto()
        stats.update(
            variables=len(proto.variables),
            constraints=len(proto.constraints),
            solver_status=run.solver.status_name(run.code),
        )
        status = "cancelled" if run.cancelled else STATUS.get(run.code, "unknown")
        if not run.has_solution:
            return SolveResult(status, [], wall_time=time.monotonic() - t0, model_stats=stats)
        return SolveResult(
            status=status,
            placements=builder.extract(run.solver),
            objective=run.solver.objective_value,
            best_bound=run.solver.best_objective_bound,
            wall_time=time.monotonic() - t0,
            model_stats=stats,
        )


@dataclass
class _Run:
    solver: cp_model.CpSolver
    code: int
    cancelled: bool
    solutions: int

    @property
    def has_solution(self) -> bool:
        return self.code in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    @property
    def stats(self) -> dict:
        s = self.solver
        return {
            "status": s.status_name(self.code),
            "seconds": round(s.wall_time, 1),
            "solutions": self.solutions,
            "objective": s.objective_value if self.has_solution else None,
            "bound": s.best_objective_bound if self.has_solution else None,
            "conflicts": s.num_conflicts,
            "branches": s.num_branches,
        }


class _ModelBuilder:
    def __init__(self, problem: Problem, weights: dict[str, float]):
        self.p = problem
        self.ctx = problem.ctx
        self.w = {k: int(round(v)) for k, v in weights.items()}
        self.model = cp_model.CpModel()
        self.y: dict[tuple[int, int], cp_model.IntVar] = {}
        self.z: dict[tuple[int, int, int], cp_model.IntVar] = {}
        self.placed_vars: list[cp_model.IntVar] = []
        self.unit_y: dict[int, list[tuple[int, cp_model.IntVar]]] = defaultdict(list)
        self.soft: list = []  # weighted soft-constraint terms

        lts = self.ctx.lesson_times.values()
        self.bounds = sorted({t for lt in lts for t in (lt.start, lt.end)})
        self._iv: dict[int, list[int]] = {}
        self._keys: dict[tuple, list[tuple]] = {}
        self.session_dates = sorted(
            {s.date for u in problem.units for s in u.slots if s.date}
            | {f.date for f in problem.fixed if f.is_dated}
        )
        self.closed = self._closed_numbers()

    # ------------------------------------------------------------------ time keys
    def intervals(self, lesson_time_id: int) -> list[int]:
        if lesson_time_id not in self._iv:
            lt = self.ctx.lesson_times[lesson_time_id]
            b = self.bounds
            self._iv[lesson_time_id] = [
                i for i in range(len(b) - 1) if b[i] >= lt.start and b[i + 1] <= lt.end
            ]
        return self._iv[lesson_time_id]

    def day_keys(self, period_id: int, slot: Slot) -> list[tuple]:
        """Every day key the lesson occupies (for overlaps)."""
        cache_key = (period_id, slot.weekday, slot.week_parity, slot.date)
        if cache_key not in self._keys:
            if slot.date:
                keys = [("d", slot.date)]
            else:
                keys = [
                    ("w", slot.weekday, n) for n in (1, 2) if parity_matches(slot.week_parity, n)
                ]
                keys += [
                    ("d", d) for d in weekly_dates(self.ctx, period_id, slot, self.session_dates)
                ]
            self._keys[cache_key] = keys
        return self._keys[cache_key]

    @staticmethod
    def native_keys(slot: Slot) -> list[tuple]:
        """Day keys of the lesson's own form (daily limit, gaps, crowding)."""
        if slot.date:
            return [("d", slot.date)]
        return [("w", slot.weekday, n) for n in (1, 2) if parity_matches(slot.week_parity, n)]

    def cells(self, period_id: int, slot: Slot) -> list[tuple]:
        ivs = self.intervals(slot.lesson_time_id)
        return [(dk, iv) for dk in self.day_keys(period_id, slot) for iv in ivs]

    @staticmethod
    def factor(slot: Slot) -> int:
        """Weight of one occurrence: weekly every-week and session lessons 2, odd/even 1
        (matches soft_report, which averages an odd and an even week)."""
        if slot.date or slot.week_parity == WeekParity.EVERY:
            return 2
        return 1

    @staticmethod
    def key_factor(dk: tuple) -> int:
        return 1 if dk[0] == "w" else 2

    def _closed_numbers(self) -> dict[tuple[int, int], set[int]]:
        out: dict[tuple[int, int], set[int]] = defaultdict(set)
        for lt in self.ctx.lesson_times.values():
            for weekday in range(7):
                if any(b.is_hard and b.hits(weekday, lt.form_id, lt) for b in self.ctx.blocked):
                    out[(lt.form_id, weekday)].add(lt.number)
        return out

    # ------------------------------------------------------------------ model
    def build(self) -> None:
        ctx, m = self.ctx, self.model
        busy: dict[tuple, list] = defaultdict(list)  # (resource, day key, interval) -> vars
        daily: dict[tuple, list] = defaultdict(list)  # (group slot, native day key) -> vars
        fixed_busy: dict[tuple, int] = defaultdict(int)
        fixed_daily: dict[tuple, int] = defaultdict(int)
        # gap / crowding bookkeeping: (entity, day key) -> {lesson number: [vars]}
        occ: dict[tuple, dict[int, list]] = defaultdict(lambda: defaultdict(list))
        occ_fixed: dict[tuple, set[int]] = defaultdict(set)
        crowd: dict[tuple, list] = defaultdict(list)
        crowd_fixed: dict[tuple, int] = defaultdict(int)
        in_building: dict[tuple[int, int], list] = defaultdict(list)  # (unit, building) -> z
        fixed_buildings: dict[int, set[int]] = defaultdict(set)  # group -> buildings

        for f in self.p.fixed:
            a = ctx.assignments[f.assignment_id]
            slot = Slot(f.lesson_time_id, f.weekday, f.week_parity, f.date)
            number = ctx.lesson_times[f.lesson_time_id].number
            if f.room_id is not None:
                for g in a.group_ids:
                    fixed_buildings[g].add(ctx.rooms[f.room_id].building_id)
            for cell in self.cells(a.period_id, slot):
                fixed_busy[(("t", a.teacher_id), *cell)] += 1
                if f.room_id is not None:
                    fixed_busy[(("r", f.room_id), *cell)] += 1
                for s in a.slot_keys:
                    fixed_busy[(("s", s), *cell)] += 1
            for dk in self.native_keys(slot):
                for s in a.slot_keys:
                    fixed_daily[(s, dk)] += 1
                occ_fixed[(("t", a.teacher_id), dk)].add(number)
                for g in self._perspective_groups(a):
                    occ_fixed[(("g", g), dk)].add(number)
                    crowd_fixed[(g, dk, a.subject_id)] += 1

        for ui, u in enumerate(self.p.units):
            a = ctx.assignments[u.assignment_id]
            form = ctx.form_of(a)
            unit_vars = []
            for si, slot in enumerate(u.slots):
                cells = self.cells(a.period_id, slot)
                rooms = []
                if u.needs_room:
                    rooms = [
                        r
                        for r in u.rooms
                        if not any(fixed_busy.get((("r", r), *c), 0) for c in cells)
                    ]
                    if not rooms:
                        continue
                y = m.new_bool_var(f"y{ui}_{si}")
                self.y[(ui, si)] = y
                self.unit_y[ui].append((si, y))
                unit_vars.append(y)
                for cell in cells:
                    busy[(("t", a.teacher_id), *cell)].append(y)
                    for s in a.slot_keys:
                        busy[(("s", s), *cell)].append(y)
                if u.needs_room:
                    zs = []
                    for r in rooms:
                        z = m.new_bool_var(f"z{ui}_{si}_{r}")
                        self.z[(ui, si, r)] = z
                        zs.append(z)
                        in_building[(ui, ctx.rooms[r].building_id)].append(z)
                        for cell in cells:
                            busy[(("r", r), *cell)].append(z)
                    m.add(sum(zs) == y)
                number = ctx.lesson_times[slot.lesson_time_id].number
                for dk in self.native_keys(slot):
                    for s in a.slot_keys:
                        daily[(s, dk)].append(y)
                    occ[(("t", a.teacher_id), dk)][number].append(y)
                    for g in self._perspective_groups(a):
                        occ[(("g", g), dk)][number].append(y)
                        crowd[(g, dk, a.subject_id)].append(y)
                cost = self._linear_cost(a, form, slot)
                if cost:
                    self.soft.append(cost * y)

            placed = m.new_bool_var(f"placed{ui}")
            m.add(sum(unit_vars) == placed)
            self.placed_vars.append(placed)

        # constraints 1–3: one lesson per teacher / room / group slot at a time
        for key, terms in busy.items():
            cap = 1 - fixed_busy.get(key, 0)
            if cap <= 0:
                for v in terms:
                    m.add(v == 0)
            elif len(terms) > cap:
                m.add(sum(terms) <= cap)
        # constraint 10: daily limit per group slot
        for (s, dk), terms in daily.items():
            form = ctx.forms[ctx.groups[s // SLOTS_PER_GROUP].form_id]
            cap = form.max_lessons_per_day - fixed_daily.get((s, dk), 0)
            if len(terms) > cap:
                m.add(sum(terms) <= max(cap, 0))

        self._symmetry()
        self._gaps(occ, occ_fixed)
        self._crowding(crowd, crowd_fixed)
        self._buildings(in_building, fixed_buildings)

    def _perspective_groups(self, a) -> list[int]:
        """Groups whose day this lesson shapes: whole-group lessons and subgroup 1."""
        if a.subgroup_number and a.subgroup_number != 1:
            return []
        return list(a.group_ids)

    def _linear_cost(self, a, form, slot: Slot) -> int:
        ctx = self.ctx
        lt = ctx.lesson_times[slot.lesson_time_id]
        weekday = slot.date.weekday() if slot.date else slot.weekday
        cost = 0
        prefs = ctx.preferred.get(a.teacher_id)
        if prefs and (weekday, None) not in prefs and (weekday, lt.id) not in prefs:
            cost += self.w.get(Soft.TEACHER_PREFERENCE, 0)
        if form.code == "kunduzgi":
            cost += self.w.get(Soft.SHIFT, 0) * sum(
                1 for g in a.group_ids if ctx.groups[g].shift != lt.shift
            )
        if any(not b.is_hard and b.hits(weekday, form.id, lt) for b in ctx.blocked):
            cost += self.w.get(Soft.SOFT_BLOCKED, 0)
        return cost * self.factor(slot)

    def _symmetry(self) -> None:
        """Units of one assignment are interchangeable: place them in increasing time order."""
        groups: dict[str, list[int]] = defaultdict(list)
        for ui, u in enumerate(self.p.units):
            groups[u.group].append(ui)
        for members in groups.values():
            for u1, u2 in zip(members, members[1:], strict=False):
                p1, p2 = self.placed_vars[u1], self.placed_vars[u2]
                self.model.add(p1 >= p2)
                idx1 = self._index(u1)
                idx2 = self._index(u2)
                self.model.add(idx1 + 1 <= idx2).only_enforce_if(p2)

    def _index(self, ui: int):
        return sum(si * v for si, v in self.unit_y[ui])

    def _gaps(self, occ, occ_fixed) -> None:
        m = self.model
        w_student = self.w.get(Soft.STUDENT_GAPS, 0)
        w_teacher = self.w.get(Soft.TEACHER_GAPS, 0)
        for (entity, dk), by_number in occ.items():
            kind, ident = entity
            weight = w_student if kind == "g" else w_teacher
            if not weight:
                continue
            fixed = occ_fixed.get((entity, dk), set())
            numbers = set(by_number) | fixed
            if len(numbers) < 2:
                continue
            closed: set[int] = set()
            if kind == "g":
                weekday = dk[1] if dk[0] == "w" else dk[1].weekday()
                closed = self.closed.get((self.ctx.groups[ident].form_id, weekday), set())
            lo, hi = min(numbers), max(numbers)
            o = {}
            for n in range(lo, hi + 1):
                if n in fixed:
                    o[n] = 1
                elif by_number.get(n):
                    var = m.new_bool_var("")
                    m.add_max_equality(var, by_number[n])
                    o[n] = var
                else:
                    o[n] = 0
            pre, suf = {}, {}
            for n in range(lo, hi + 1):
                pre[n] = self._or([pre[n - 1], o[n]] if n > lo else [o[n]])
            for n in range(hi, lo - 1, -1):
                suf[n] = self._or([suf[n + 1], o[n]] if n < hi else [o[n]])
            for n in range(lo + 1, hi):
                if n in closed or n in fixed:
                    continue
                gap = m.new_bool_var("")
                m.add(gap >= pre[n - 1] + suf[n + 1] - o[n] - 1)
                self.soft.append(weight * self.key_factor(dk) * gap)

    def _or(self, items):
        consts = [i for i in items if isinstance(i, int)]
        if any(consts):
            return 1
        vars_ = [i for i in items if not isinstance(i, int)]
        if not vars_:
            return 0
        if len(vars_) == 1:
            return vars_[0]
        var = self.model.new_bool_var("")
        self.model.add_max_equality(var, vars_)
        return var

    def _crowding(self, crowd, crowd_fixed) -> None:
        weight = self.w.get(Soft.SUBJECT_CROWDING, 0)
        if not weight:
            return
        for key, terms in crowd.items():
            fixed = crowd_fixed.get(key, 0)
            if len(terms) + fixed <= 2:
                continue
            excess = self.model.new_int_var(0, len(terms) + fixed, "")
            self.model.add(excess >= sum(terms) + fixed - 2)
            self.soft.append(weight * self.key_factor(key[1]) * excess)

    def _buildings(self, in_building, fixed_buildings) -> None:
        """Keep each group in few buildings (building spread; also cuts walks between lessons).
        uses[g, b] = 1 if any lesson of group g is in building b; every extra building costs."""
        weight = self.w.get(Soft.BUILDING_SPREAD, 0) + self.w.get(Soft.BUILDING_MOVES, 0)
        if not weight:
            return
        uses: dict[tuple[int, int], object] = {}
        for (ui, building), zs in in_building.items():
            a = self.ctx.assignments[self.p.units[ui].assignment_id]
            for g in a.group_ids:
                if building in fixed_buildings.get(g, ()):
                    continue  # already paid for by a kept lesson
                if (g, building) not in uses:
                    uses[(g, building)] = self.model.new_bool_var("")
                    self.soft.append(2 * weight * uses[(g, building)])
                self.model.add(sum(zs) <= uses[(g, building)])

    # ------------------------------------------------------------------ hints / results
    def add_hints(self, hints: dict[str, tuple]) -> None:
        """hints: unit key -> (slot, room_id) from the previous timetable (warm start)."""
        for ui, u in enumerate(self.p.units):
            hint = hints.get(u.key)
            if not hint:
                continue
            slot, room = hint
            for si, s in enumerate(u.slots):
                if s == slot and (ui, si) in self.y:
                    self.model.add_hint(self.y[(ui, si)], 1)
                    if room is not None and (ui, si, room) in self.z:
                        self.model.add_hint(self.z[(ui, si, room)], 1)
                    break

    def snapshot(self, solver: cp_model.CpSolver) -> list[tuple]:
        return [(v, solver.value(v)) for v in (*self.y.values(), *self.z.values())]

    def extract(self, solver: cp_model.CpSolver) -> list[Placement]:
        out = []
        for (ui, si), y in self.y.items():
            if not solver.value(y):
                continue
            u = self.p.units[ui]
            slot = u.slots[si]
            room = next(
                (r for r in u.rooms if (ui, si, r) in self.z and solver.value(self.z[(ui, si, r)])),
                None,
            )
            out.append(to_placement(u.key, u.assignment_id, slot, room))
        return out
