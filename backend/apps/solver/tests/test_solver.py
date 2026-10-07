"""Automatic timetabling: pre-filtering, the CP-SAT result checked by the validator, the run
service and the API."""

from unittest import mock

import pytest
from django.db.models import Q
from rest_framework.test import APIClient

from apps.academics.models import EducationForm, Faculty, Teacher
from apps.accounts.models import User
from apps.scheduling.models import Schedule, ScheduleEntry
from apps.scheduling.validators import (
    LINK_PLACEHOLDER,
    Code,
    load_context,
    placements_from_entries,
    validate,
)
from apps.solver import service
from apps.solver.base import SolveParams
from apps.solver.cpsat import CpSatSolver
from apps.solver.models import SolverRun, SolverStatus
from apps.solver.problem import build_problem

pytestmark = pytest.mark.django_db


def client_for(username: str) -> APIClient:
    client = APIClient()
    client.force_authenticate(User.objects.get(username=username))
    return client


@pytest.fixture
def published(demo):
    return Schedule.objects.get(status="published")


@pytest.fixture
def ctx(demo, published):
    return load_context(published.semester)


def kechki(ctx):
    return next(f.id for f in ctx.forms.values() if f.code == "kechki")


# --- pre-filtering -------------------------------------------------------------------------


def test_candidates_never_include_closed_or_impossible_times(ctx):
    problem = build_problem(ctx, [], mode="rebuild")
    assert problem.units
    for u in problem.units:
        a = ctx.assignments[u.assignment_id]
        form = ctx.form_of(a)
        for slot in u.slots:
            lt = ctx.lesson_times[slot.lesson_time_id]
            weekday = slot.date.weekday() if slot.date else slot.weekday
            assert lt.form_id == form.id
            assert weekday in form.study_weekdays
            assert not any(b.is_hard and b.hits(weekday, form.id, lt) for b in ctx.blocked)
            assert slot.date not in ctx.calendar.days_off
        for room_id in u.rooms:
            assert ctx.rooms[room_id].capacity >= a.student_count


def test_lesson_the_teacher_cannot_teach_is_explained_not_attempted(ctx):
    a = next(a for a in ctx.assignments.values() if ctx.form_of(a).code == "kechki")
    ctx.teacher_languages[a.teacher_id] = frozenset({"ar"})
    problem = build_problem(ctx, [], form_id=kechki(ctx))
    assert a.id in problem.skipped
    assert not [u for u in problem.units if u.assignment_id == a.id]
    message = next(d for d in problem.diagnostics if d.assignment_id == a.id)
    assert message.code == "teacher_language"
    assert set(message.message) == {"uz", "ru", "en"}


def test_fill_mode_keeps_existing_lessons_and_places_only_the_rest(ctx, published):
    base = placements_from_entries(published.entries.all())
    problem = build_problem(ctx, base, mode="fill")
    assert len(problem.fixed) == len(base) and not problem.removed
    rebuild = build_problem(ctx, base, mode="rebuild")
    # pinned lessons stay in both modes (all IS-301 seed lessons are pinned)
    assert {p.key for p in rebuild.fixed} == {p.key for p in base if p.is_locked}


# --- the model ------------------------------------------------------------------------------


def test_cpsat_result_passes_the_validator(ctx, published):
    base = placements_from_entries(published.entries.all())
    problem = build_problem(ctx, base, form_id=kechki(ctx))
    result = CpSatSolver().solve(problem, SolveParams(time_limit=20, workers=4))
    assert result.status in ("optimal", "feasible")
    assert len(result.placements) == len(problem.units)  # the evening form fits completely
    report = validate(problem.fixed + result.placements, ctx)
    assert [v for v in report.conflicts if v.code != Code.LINK_MISSING] == []
    # every kept lesson is untouched
    assert {p.key for p in problem.fixed} <= {p.key for p in base}


def test_overloaded_teacher_gets_a_partial_timetable_with_reasons(ctx):
    form_id = kechki(ctx)
    evening = [a for a in ctx.assignments.values() if ctx.periods[a.period_id].form_id == form_id]
    teacher_id = evening[0].teacher_id
    # one evening slot only: Monday, first evening lesson
    first = min(
        (lt for lt in ctx.lesson_times.values() if lt.form_id == form_id), key=lambda lt: lt.number
    )
    ctx.unavailable[teacher_id] = {(wd, None) for wd in range(1, 7)} | {
        (0, lt.id) for lt in ctx.lesson_times.values() if lt.form_id == form_id and lt != first
    }
    for a in evening:
        ctx.assignments[a.id] = a.__class__(**{**a.__dict__, "teacher_id": teacher_id})
    problem = build_problem(ctx, [], form_id=form_id)
    assert any(d.code == "teacher_overloaded" for d in problem.diagnostics)
    result = CpSatSolver().solve(problem, SolveParams(time_limit=10, workers=4))
    assert len(result.placements) == 1
    reasons = service._explain_unplaced(problem, result.placements)
    assert reasons and all(d.code == "unplaced" for d in reasons)
    assert "teacher busy: 1" in reasons[0].message["en"]


# --- service --------------------------------------------------------------------------------


def make_run(published, **params) -> SolverRun:
    return SolverRun.objects.create(
        semester=published.semester,
        base_schedule=published,
        form=EducationForm.objects.get(code="kechki"),
        params={"mode": "rebuild", "time_limit": 25, "workers": 4, **params},
    )


def test_run_saves_a_verified_draft_and_leaves_the_published_version_alone(published):
    before = list(published.entries.values_list("pk", flat=True))
    run = service.execute(make_run(published).pk)
    assert run.status == SolverStatus.SUCCEEDED, run.diagnostics
    assert run.hard_violations == 0
    assert run.lessons_placed == run.lessons_total > 0
    draft = run.result_schedule
    assert draft.status == "draft" and draft.based_on == published
    assert list(published.entries.values_list("pk", flat=True)) == before
    # pinned lessons were copied, new lessons have dated occurrences
    assert (
        draft.entries.filter(is_locked=True).count()
        == published.entries.filter(is_locked=True).count()
    )
    new = draft.entries.filter(is_locked=False)
    assert new.count() == run.lessons_placed
    assert all(e.occurrences.exists() for e in new)

    compare = service.compare(run)
    assert compare["result"]["hard_conflicts"] == 0
    assert compare["base"]["id"] == published.pk
    assert compare["added"] == run.lessons_placed


def test_distance_lessons_get_a_placeholder_link_that_blocks_publishing(published):
    run = SolverRun.objects.create(
        semester=published.semester,
        base_schedule=published,
        form=EducationForm.objects.get(code="masofaviy"),
        params={"time_limit": 20, "workers": 4},
    )
    run = service.execute(run.pk)
    assert run.status == SolverStatus.SUCCEEDED
    online = ScheduleEntry.objects.filter(schedule=run.result_schedule, room__isnull=True)
    assert online.exists()
    assert all(e.online_url.startswith(LINK_PLACEHOLDER) for e in online)
    assert any(d["code"] == "links_needed" for d in run.diagnostics)
    resp = client_for("admin").post(f"/api/schedules/{run.result_schedule_id}/publish/")
    assert resp.status_code == 409


def test_cancelled_run_stops_without_a_result(published):
    run = make_run(published)
    run.status = SolverStatus.CANCELLED
    run.save()
    assert service.execute(run.pk).result_schedule is None


# --- API ------------------------------------------------------------------------------------


def test_only_the_dispatcher_starts_runs_and_staff_can_watch(published):
    body = {"form": EducationForm.objects.get(code="kechki").pk, "time_limit": 30}
    assert client_for("dekanat").post("/api/solver-runs/", body, format="json").status_code == 403
    assert client_for("talaba").get("/api/solver-runs/").status_code == 403
    with mock.patch("apps.solver.api.views.run_solver.delay") as delay:
        delay.return_value.id = "task-1"
        with mock.patch("django.db.transaction.on_commit", lambda fn: fn()):
            resp = client_for("admin").post("/api/solver-runs/", body, format="json")
    assert resp.status_code == 201, resp.data
    run = SolverRun.objects.get(pk=resp.data["id"])
    delay.assert_called_once_with(run.pk)
    assert run.base_schedule == published and run.params["time_limit"] == 30
    assert run.celery_task_id == "task-1"
    assert client_for("dekanat").get(f"/api/solver-runs/{run.pk}/").status_code == 200

    cancel = client_for("admin").post(f"/api/solver-runs/{run.pk}/cancel/")
    assert cancel.status_code == 200 and cancel.data["status"] == "cancelled"
    assert client_for("admin").post(f"/api/solver-runs/{run.pk}/cancel/").status_code == 400


def test_bad_settings_are_rejected(demo):
    c = client_for("admin")
    assert c.post("/api/solver-runs/", {"time_limit": 5}, format="json").status_code == 400
    resp = c.post("/api/solver-runs/", {"weights": {"nonsense": 1}}, format="json")
    assert resp.status_code == 400 and "weights" in resp.data


def test_precheck_reports_problems_in_the_request_language(demo):
    teacher = Teacher.objects.filter(assignments__period__form__code="kechki").first()
    teacher.teaching_languages = ["ar"]
    teacher.save()
    resp = client_for("admin").post(
        "/api/solver-runs/precheck/",
        {"form": EducationForm.objects.get(code="kechki").pk},
        format="json",
        HTTP_ACCEPT_LANGUAGE="ru",
    )
    assert resp.status_code == 200
    assert resp.data["lessons"] > resp.data["units"]
    errors = [d for d in resp.data["diagnostics"] if d["code"] == "teacher_language"]
    assert errors
    assert "не преподаёт на языке группы" in errors[0]["message"]


def test_result_and_runs_export_as_csv(published):
    run = service.execute(make_run(published).pk)
    c = client_for("admin")
    entries = c.get(f"/api/solver-runs/{run.pk}/entries/")
    assert entries.status_code == 200 and entries["Content-Type"].startswith("text/csv")
    lines = entries.content.decode("utf-8-sig").strip().splitlines()
    assert len(lines) == 1 + run.result_schedule.entries.count()
    runs = c.get("/api/solver-runs/export/")
    assert runs.status_code == 200 and f"\n{run.pk}," in runs.content.decode("utf-8-sig")
    assert c.get(f"/api/solver-runs/{run.pk}/compare/").data["result"]["hard_conflicts"] == 0


def test_faculty_scope_only_places_that_facultys_lessons(published):
    rus = Faculty.objects.get(code="RUS")
    run = SolverRun.objects.create(
        semester=published.semester,
        base_schedule=published,
        faculty=rus,
        form=EducationForm.objects.get(code="kunduzgi"),
        params={"time_limit": 40, "workers": 4},
    )
    run = service.execute(run.pk)
    assert run.status == SolverStatus.SUCCEEDED and run.hard_violations == 0
    new = run.result_schedule.entries.filter(is_locked=False)
    assert new.exists()
    of_rus = (
        Q(assignment__group__program_form__program__faculty=rus)
        | Q(assignment__stream__groups__program_form__program__faculty=rus)
        | Q(assignment__subgroup__group__program_form__program__faculty=rus)
    )
    assert new.count() == new.filter(of_rus).distinct().count()
