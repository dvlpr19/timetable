from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.academics.models import EducationForm, Faculty, Semester
from apps.scheduling.models import Schedule


class SolverStatus(models.TextChoices):
    QUEUED = "queued", _("Queued")
    RUNNING = "running", _("Running")
    SUCCEEDED = "succeeded", _("Finished")
    INFEASIBLE = "infeasible", _("No solution")
    FAILED = "failed", _("Error")
    CANCELLED = "cancelled", _("Cancelled")


class SolverRun(models.Model):
    """One automatic timetabling run; its statistics feed the thesis experiments."""

    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name="solver_runs")
    faculty = models.ForeignKey(
        Faculty, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    form = models.ForeignKey(
        EducationForm, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    algorithm = models.CharField(_("algorithm"), max_length=30, default="cpsat")
    base_schedule = models.ForeignKey(
        Schedule, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    result_schedule = models.ForeignKey(
        Schedule, on_delete=models.SET_NULL, null=True, blank=True, related_name="solver_runs"
    )
    params = models.JSONField(_("parameters"), default=dict)  # weights, time limit, seed
    status = models.CharField(
        max_length=12, choices=SolverStatus.choices, default=SolverStatus.QUEUED
    )
    progress = models.JSONField(default=dict)  # live: elapsed, best objective, placed
    celery_task_id = models.CharField(max_length=64, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    # results
    objective = models.FloatField(null=True, blank=True)
    best_bound = models.FloatField(null=True, blank=True)
    lessons_total = models.PositiveIntegerField(default=0)
    lessons_placed = models.PositiveIntegerField(default=0)
    hard_violations = models.PositiveIntegerField(default=0)
    soft_violations = models.JSONField(default=dict)  # {constraint_code: count}
    diagnostics = models.JSONField(default=list)  # human-readable reasons when infeasible
    model_stats = models.JSONField(default=dict)  # variables, constraints, presolve info

    class Meta:
        verbose_name = _("automatic scheduling run")
        verbose_name_plural = _("automatic scheduling runs")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"#{self.pk} {self.get_status_display()}"
