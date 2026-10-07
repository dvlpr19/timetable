"""Groups, subgroups, streams, students, teachers and their availability."""

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from ..choices import (
    MAX_SUBGROUPS,
    SLOTS_PER_GROUP,
    AcademicDegree,
    AvailabilityLevel,
    EmploymentType,
    Gender,
    GenderComposition,
    Position,
    TeachingLanguage,
    Weekday,
)
from .calendar import LessonTime, Semester
from .curriculum import Subject
from .structure import Department, Faculty, ProgramForm


class Group(models.Model):
    program_form = models.ForeignKey(ProgramForm, on_delete=models.PROTECT, related_name="groups")
    name = models.CharField(_("name"), max_length=30, unique=True)
    course = models.PositiveSmallIntegerField(_("year of study"))
    number = models.PositiveSmallIntegerField(_("number within course"))
    teaching_language = models.CharField(
        _("teaching language"), max_length=2, choices=TeachingLanguage.choices
    )
    student_count = models.PositiveSmallIntegerField(_("students"))
    gender_composition = models.CharField(
        _("composition"), max_length=10, choices=GenderComposition.choices, blank=True, default=""
    )
    shift = models.PositiveSmallIntegerField(_("shift"), default=1)

    class Meta:
        verbose_name = _("group")
        verbose_name_plural = _("groups")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["program_form", "course", "number", "teaching_language"],
                name="group_unique_number",
            ),
            models.CheckConstraint(
                condition=Q(course__gte=1) & Q(course__lte=6), name="group_course_range"
            ),
            models.CheckConstraint(condition=Q(shift__in=[1, 2]), name="group_shift_valid"),
            models.CheckConstraint(
                condition=Q(teaching_language__in=TeachingLanguage.values),
                name="group_language_valid",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def form(self):
        return self.program_form.form

    @property
    def faculty_id(self) -> int:
        return self.program_form.program.faculty_id

    def study_semester(self, semester_kind: str) -> int:
        return (self.course - 1) * 2 + (2 if semester_kind == "spring" else 1)

    def slot_keys(self) -> list[int]:
        """The whole group occupies every subgroup slot."""
        return [self.pk * SLOTS_PER_GROUP + k for k in range(1, MAX_SUBGROUPS + 1)]


class SubGroup(models.Model):
    """Half of a group for language or lab lessons."""

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="subgroups")
    number = models.PositiveSmallIntegerField(_("number"))
    student_count = models.PositiveSmallIntegerField(_("students"))

    class Meta:
        verbose_name = _("subgroup")
        verbose_name_plural = _("subgroups")
        ordering = ["group__name", "number"]
        constraints = [
            models.UniqueConstraint(fields=["group", "number"], name="subgroup_unique_number"),
            models.CheckConstraint(
                condition=Q(number__gte=1) & Q(number__lte=MAX_SUBGROUPS),
                name="subgroup_number_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.group.name}/{self.number}"

    def slot_keys(self) -> list[int]:
        return [self.group_id * SLOTS_PER_GROUP + self.number]


class Stream(models.Model):
    """Oqim: several groups of the same teaching language attending one lecture."""

    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name="streams")
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name="streams")
    name = models.CharField(_("name"), max_length=100)
    teaching_language = models.CharField(
        _("teaching language"), max_length=2, choices=TeachingLanguage.choices
    )
    groups = models.ManyToManyField(Group, related_name="streams")

    class Meta:
        verbose_name = _("stream")
        verbose_name_plural = _("streams")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["semester", "name"], name="stream_unique_name"),
        ]

    def __str__(self) -> str:
        return self.name


class Teacher(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teacher",
    )
    last_name = models.CharField(_("last name"), max_length=100)
    first_name = models.CharField(_("first name"), max_length=100)
    middle_name = models.CharField(_("patronymic"), max_length=100, blank=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="teachers")
    position = models.CharField(_("position"), max_length=30, choices=Position.choices)
    degree = models.CharField(
        _("academic degree"), max_length=10, choices=AcademicDegree.choices, default="none"
    )
    employment = models.CharField(
        _("employment"), max_length=20, choices=EmploymentType.choices, default="staff"
    )
    annual_load_hours = models.PositiveSmallIntegerField(_("annual teaching load (hours)"))
    max_weekly_lessons = models.PositiveSmallIntegerField(_("max lessons per week"), default=18)
    subjects = models.ManyToManyField(Subject, related_name="teachers", blank=True)
    teaching_languages = ArrayField(
        models.CharField(max_length=2, choices=TeachingLanguage.choices),
        verbose_name=_("teaching languages"),
        default=list,
    )

    class Meta:
        verbose_name = _("teacher")
        verbose_name_plural = _("teachers")
        ordering = ["last_name", "first_name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(teaching_languages__contained_by=TeachingLanguage.values)
                & Q(teaching_languages__len__gte=1),
                name="teacher_languages_valid",
            ),
        ]

    def __str__(self) -> str:
        return self.short_name

    @property
    def short_name(self) -> str:
        """Yusupov S."""
        return f"{self.last_name} {self.first_name[:1]}."

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.last_name, self.first_name, self.middle_name) if p)

    def can_teach_in(self, language: str) -> bool:
        return language in self.teaching_languages


class TeacherAvailability(models.Model):
    """A teacher's preference for a weekday (whole day if lesson_time is empty) or a single lesson.

    Missing rows mean "possible".
    """

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="availability")
    weekday = models.PositiveSmallIntegerField(_("weekday"), choices=Weekday.choices)
    lesson_time = models.ForeignKey(
        LessonTime, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    level = models.CharField(_("availability"), max_length=12, choices=AvailabilityLevel.choices)

    class Meta:
        verbose_name = _("teacher availability")
        verbose_name_plural = _("teacher availability")
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "weekday", "lesson_time"],
                name="availability_unique",
                nulls_distinct=False,
            ),
            models.CheckConstraint(
                condition=Q(weekday__gte=0) & Q(weekday__lte=6), name="availability_weekday_range"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.teacher} · {self.get_weekday_display()} · {self.get_level_display()}"


class Student(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student",
    )
    last_name = models.CharField(_("last name"), max_length=100)
    first_name = models.CharField(_("first name"), max_length=100)
    middle_name = models.CharField(_("patronymic"), max_length=100, blank=True)
    hemis_id = models.CharField(_("HEMIS ID"), max_length=20, unique=True)
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="students")
    subgroup = models.ForeignKey(
        SubGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name="students"
    )
    gender = models.CharField(_("gender"), max_length=1, choices=Gender.choices)
    phone = models.CharField(_("phone"), max_length=20, blank=True)

    class Meta:
        verbose_name = _("student")
        verbose_name_plural = _("students")
        ordering = ["group__name", "last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.last_name} {self.first_name}"
