"""Lesson types, subjects and curriculum (o'quv reja)."""

from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

from ..choices import ControlType, LessonTypeCode, TeachingLanguage
from .rooms import RoomType
from .structure import Department, EducationForm, Program

HOURS_PER_CREDIT = 30
HOURS_PER_LESSON = 2  # one lesson ("juftlik") = 2 academic hours


class LessonType(models.Model):
    code = models.CharField(_("code"), max_length=20, unique=True, choices=LessonTypeCode.choices)
    name = models.CharField(_("name"), max_length=100)
    default_room_type = models.ForeignKey(
        RoomType,
        verbose_name=_("default room type"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text=_("Room type this kind of lesson needs by default (e.g. lab → computer room)."),
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = _("lesson type")
        verbose_name_plural = _("lesson types")
        ordering = ["order"]

    def __str__(self) -> str:
        return self.name


class Subject(models.Model):
    code = models.CharField(_("code"), max_length=20, unique=True)
    name = models.CharField(_("name"), max_length=255)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="subjects",
        null=True,
        blank=True,
        verbose_name=_("department"),
    )
    is_language = models.BooleanField(
        _("language subject"), default=False, help_text=_("Practice is usually split in subgroups.")
    )
    practice_room_type = models.ForeignKey(
        RoomType,
        verbose_name=_("room type for practice"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text=_("Room type required for practical/lab lessons of this subject, if any."),
    )

    class Meta:
        verbose_name = _("subject")
        verbose_name_plural = _("subjects")
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name


class CurriculumItem(models.Model):
    """One subject in the plan of program + form + (teaching language) + study semester.

    `teaching_language` empty = the general plan, used when no language-specific plan exists.
    """

    program = models.ForeignKey(
        Program, verbose_name=_("program"), on_delete=models.CASCADE, related_name="curriculum"
    )
    form = models.ForeignKey(
        EducationForm,
        verbose_name=_("education form"),
        on_delete=models.PROTECT,
        related_name="curriculum",
    )
    teaching_language = models.CharField(
        _("teaching language"),
        max_length=2,
        choices=TeachingLanguage.choices,
        blank=True,
        default="",
    )
    study_semester = models.PositiveSmallIntegerField(_("study semester"))
    subject = models.ForeignKey(
        Subject, verbose_name=_("subject"), on_delete=models.PROTECT, related_name="curriculum"
    )
    credits = models.PositiveSmallIntegerField(_("credits"))
    hours_lecture = models.PositiveSmallIntegerField(_("lecture hours"), default=0)
    hours_practice = models.PositiveSmallIntegerField(_("practice hours"), default=0)
    hours_seminar = models.PositiveSmallIntegerField(_("seminar hours"), default=0)
    hours_lab = models.PositiveSmallIntegerField(_("laboratory hours"), default=0)
    hours_independent = models.PositiveSmallIntegerField(_("independent study hours"), default=0)
    control_type = models.CharField(_("assessment"), max_length=10, choices=ControlType.choices)

    class Meta:
        verbose_name = _("curriculum item")
        verbose_name_plural = _("curriculum")
        ordering = ["program", "form", "teaching_language", "study_semester", "subject__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["program", "form", "teaching_language", "study_semester", "subject"],
                name="curriculum_unique_subject",
            ),
            models.CheckConstraint(
                condition=Q(study_semester__gte=1) & Q(study_semester__lte=12),
                name="curriculum_semester_range",
            ),
            models.CheckConstraint(condition=Q(credits__gte=1), name="curriculum_credits_positive"),
            # 1 credit = 30 hours of classroom + independent study.
            models.CheckConstraint(
                condition=Q(
                    hours_independent=F("credits") * HOURS_PER_CREDIT
                    - F("hours_lecture")
                    - F("hours_practice")
                    - F("hours_seminar")
                    - F("hours_lab")
                ),
                name="curriculum_credit_hours",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.subject} · {self.study_semester}"

    @property
    def classroom_hours(self) -> int:
        return self.hours_lecture + self.hours_practice + self.hours_seminar + self.hours_lab

    def hours_for(self, lesson_type_code: str) -> int:
        return getattr(self, f"hours_{lesson_type_code}")
