"""Academic year, semesters, teaching periods, calendar days, bell schedules and blocked times."""

from datetime import date, timedelta

from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

from ..choices import CalendarDayKind, SemesterKind, Weekday
from .structure import EducationForm


class AcademicYear(models.Model):
    name = models.CharField(_("name"), max_length=20, unique=True)  # "2025-2026"
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"))

    class Meta:
        verbose_name = _("academic year")
        verbose_name_plural = _("academic years")
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gt=F("start_date")), name="year_dates_order"
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Semester(models.Model):
    year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="semesters")
    kind = models.CharField(_("semester"), max_length=10, choices=SemesterKind.choices)
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"))
    is_current = models.BooleanField(_("current semester"), default=False)

    class Meta:
        verbose_name = _("semester")
        verbose_name_plural = _("semesters")
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(fields=["year", "kind"], name="semester_unique_kind"),
            models.UniqueConstraint(
                fields=["is_current"], condition=Q(is_current=True), name="semester_single_current"
            ),
            models.CheckConstraint(
                condition=Q(end_date__gt=F("start_date")), name="semester_dates_order"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.year} · {self.get_kind_display()}"


class TeachingPeriod(models.Model):
    """When a form studies within a semester.

    Weekly forms: the semester teaching weeks. Sirtqi: a session with fixed dates.
    """

    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name="periods")
    form = models.ForeignKey(EducationForm, on_delete=models.PROTECT, related_name="periods")
    name = models.CharField(_("name"), max_length=255)
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"))
    weeks_count = models.PositiveSmallIntegerField(
        _("teaching weeks"), null=True, blank=True, help_text=_("Only for weekly forms.")
    )

    class Meta:
        verbose_name = _("teaching period")
        verbose_name_plural = _("teaching periods")
        ordering = ["semester", "form__order", "start_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")), name="period_dates_order"
            ),
            models.CheckConstraint(
                condition=Q(weeks_count__isnull=True) | Q(weeks_count__gte=1),
                name="period_weeks_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.semester} · {self.name}"

    @property
    def first_monday(self) -> date:
        return self.start_date - timedelta(days=self.start_date.weekday())

    def week_number(self, day: date) -> int:
        """1-based teaching week of `day`; week 1 is the week containing start_date."""
        return (day - self.first_monday).days // 7 + 1

    def dates(self):
        day = self.start_date
        while day <= self.end_date:
            yield day
            day += timedelta(days=1)


class AcademicCalendarDay(models.Model):
    """Holidays and days off (no lessons) or transferred working days.

    A transferred working day follows the timetable of `works_as_weekday`.
    """

    date = models.DateField(_("date"), unique=True)
    kind = models.CharField(_("type"), max_length=10, choices=CalendarDayKind.choices)
    name = models.CharField(_("name"), max_length=255)
    works_as_weekday = models.PositiveSmallIntegerField(
        _("works as weekday"),
        choices=Weekday.choices,
        null=True,
        blank=True,
        help_text=_("For transferred working days: whose timetable is followed."),
    )
    is_assumption = models.BooleanField(
        _("date is an estimate"),
        default=False,
        help_text=_("E.g. Eid dates depend on the lunar calendar and must be confirmed."),
    )

    class Meta:
        verbose_name = _("calendar day")
        verbose_name_plural = _("academic calendar")
        ordering = ["date"]
        constraints = [
            models.CheckConstraint(
                condition=(Q(kind=CalendarDayKind.WORKDAY) & Q(works_as_weekday__isnull=False))
                | (~Q(kind=CalendarDayKind.WORKDAY) & Q(works_as_weekday__isnull=True)),
                name="calendar_workday_weekday",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.date} {self.name}"


class LessonTime(models.Model):
    """One row of a form's bell schedule: lesson N runs start–end (80 min, one "juftlik")."""

    form = models.ForeignKey(EducationForm, on_delete=models.CASCADE, related_name="lesson_times")
    number = models.PositiveSmallIntegerField(_("lesson number"))
    start = models.TimeField(_("start"))
    end = models.TimeField(_("end"))
    shift = models.PositiveSmallIntegerField(_("shift"), default=1)

    class Meta:
        verbose_name = _("lesson time")
        verbose_name_plural = _("bell schedule")
        ordering = ["form__order", "number"]
        constraints = [
            models.UniqueConstraint(fields=["form", "number"], name="lessontime_unique_number"),
            models.CheckConstraint(condition=Q(end__gt=F("start")), name="lessontime_order"),
            models.CheckConstraint(condition=Q(number__gte=1), name="lessontime_number_positive"),
            models.CheckConstraint(condition=Q(shift__in=[1, 2]), name="lessontime_shift_valid"),
        ]

    def __str__(self) -> str:
        return f"{self.form} · {self.number}: {self.start:%H:%M}–{self.end:%H:%M}"


class BlockedPeriod(models.Model):
    """Time that must stay free (Friday prayer) or should preferably stay free (asr break)."""

    name = models.CharField(_("name"), max_length=255)
    weekday = models.PositiveSmallIntegerField(
        _("weekday"),
        choices=Weekday.choices,
        null=True,
        blank=True,
        help_text=_("Empty means every day."),
    )
    start = models.TimeField(_("start"))
    end = models.TimeField(_("end"))
    form = models.ForeignKey(
        EducationForm,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="blocked_periods",
        help_text=_("Empty means all education forms."),
    )
    is_hard = models.BooleanField(
        _("strict"), default=True, help_text=_("Strict: never schedule. Otherwise only avoided.")
    )

    class Meta:
        verbose_name = _("blocked time")
        verbose_name_plural = _("blocked times")
        constraints = [
            models.CheckConstraint(condition=Q(end__gt=F("start")), name="blocked_order"),
        ]

    def __str__(self) -> str:
        return self.name

    def applies_to(self, weekday: int, form_id: int) -> bool:
        return (self.weekday is None or self.weekday == weekday) and (
            self.form_id is None or self.form_id == form_id
        )

    def overlaps(self, lesson_time: LessonTime) -> bool:
        return lesson_time.start < self.end and self.start < lesson_time.end
