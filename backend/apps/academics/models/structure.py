"""Academy → faculty → department, education levels/forms and programs."""

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from ..choices import ScheduleMode, TeachingLanguage


class Academy(models.Model):
    name = models.CharField(_("name"), max_length=255)
    short_name = models.CharField(_("short name"), max_length=50, blank=True)

    class Meta:
        verbose_name = _("academy")
        verbose_name_plural = _("academies")

    def __str__(self) -> str:
        return self.name


class Faculty(models.Model):
    academy = models.ForeignKey(Academy, on_delete=models.PROTECT, related_name="faculties")
    code = models.CharField(_("code"), max_length=20, unique=True)
    name = models.CharField(_("name"), max_length=255)
    teaching_language = models.CharField(
        _("main teaching language"),
        max_length=2,
        choices=TeachingLanguage.choices,
        default=TeachingLanguage.UZ,
    )

    class Meta:
        verbose_name = _("faculty")
        verbose_name_plural = _("faculties")
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name


class Department(models.Model):
    """Kafedra. Teachers belong to departments."""

    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name="departments")
    code = models.CharField(_("code"), max_length=20, unique=True)
    name = models.CharField(_("name"), max_length=255)

    class Meta:
        verbose_name = _("department")
        verbose_name_plural = _("departments")
        ordering = ["faculty__code", "code"]

    def __str__(self) -> str:
        return self.name


class EducationLevel(models.Model):
    code = models.CharField(_("code"), max_length=20, unique=True)  # bachelor, master
    name = models.CharField(_("name"), max_length=100)

    class Meta:
        verbose_name = _("education level")
        verbose_name_plural = _("education levels")

    def __str__(self) -> str:
        return self.name


class EducationForm(models.Model):
    """Kunduzgi / kechki / sirtqi / masofaviy. Each has its own bell schedule and rules."""

    code = models.CharField(_("code"), max_length=20, unique=True)
    name = models.CharField(_("name"), max_length=100)
    schedule_mode = models.CharField(
        _("schedule type"), max_length=10, choices=ScheduleMode.choices
    )
    requires_room = models.BooleanField(
        _("needs a physical room"),
        default=True,
        help_text=_("Distance learning uses a virtual room link instead."),
    )
    max_lessons_per_day = models.PositiveSmallIntegerField(
        _("max lessons per day for a group"), default=4
    )
    # integer[] (not smallint[]): intarray's operators make smallint[] <@ ambiguous
    study_weekdays = ArrayField(
        models.IntegerField(),
        verbose_name=_("study days"),
        default=list,
        help_text=_("0 = Monday … 6 = Sunday."),
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = _("education form")
        verbose_name_plural = _("education forms")
        ordering = ["order"]
        constraints = [
            models.CheckConstraint(
                condition=Q(schedule_mode__in=ScheduleMode.values), name="form_mode_valid"
            ),
            models.CheckConstraint(
                condition=Q(max_lessons_per_day__gte=1), name="form_max_lessons_positive"
            ),
            models.CheckConstraint(
                condition=Q(study_weekdays__contained_by=[0, 1, 2, 3, 4, 5, 6])
                & Q(study_weekdays__len__gte=1),
                name="form_study_weekdays_valid",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def is_session(self) -> bool:
        return self.schedule_mode == ScheduleMode.SESSION


class Program(models.Model):
    """Ta'lim yo'nalishi (degree program), e.g. 60220300 Islomshunoslik."""

    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name="programs")
    level = models.ForeignKey(EducationLevel, on_delete=models.PROTECT, related_name="programs")
    code = models.CharField(_("program code"), max_length=20)
    name = models.CharField(_("name"), max_length=255)

    class Meta:
        verbose_name = _("program")
        verbose_name_plural = _("programs")
        ordering = ["faculty__code", "level__code", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["faculty", "level", "code"], name="program_unique_code"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} {self.name}"


class ProgramForm(models.Model):
    """A program offered in a given education form, with its own duration and group naming."""

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="forms")
    form = models.ForeignKey(EducationForm, on_delete=models.PROTECT, related_name="programs")
    duration_years = models.DecimalField(
        _("study duration (years)"), max_digits=3, decimal_places=1
    )
    group_prefix = models.CharField(
        _("group name prefix"),
        max_length=20,
        help_text=_("Used to build group names, e.g. IS → IS-301."),
    )

    class Meta:
        verbose_name = _("program form")
        verbose_name_plural = _("program forms")
        constraints = [
            models.UniqueConstraint(fields=["program", "form"], name="programform_unique"),
            models.CheckConstraint(
                condition=Q(duration_years__gt=0), name="programform_duration_positive"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.program} · {self.form}"
