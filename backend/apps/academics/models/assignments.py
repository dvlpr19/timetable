"""Teaching assignments (yuklama taqsimoti): the input of manual editing and the solver."""

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .calendar import TeachingPeriod
from .curriculum import CurriculumItem, LessonType, Subject
from .people import Group, Stream, SubGroup, Teacher
from .rooms import RoomType


class TeachingAssignment(models.Model):
    """Teacher X teaches lesson type Y of subject Z to exactly one group, stream or subgroup.

    Weekly forms: `weekly_lessons` every week plus `alternating_lessons` on odd or even weeks
    (for 1.5 lessons/week: 1 + 1). Session forms: `total_lessons` spread over session days.
    `total_lessons` is always the number the plan expects in the period.
    """

    period = models.ForeignKey(TeachingPeriod, on_delete=models.CASCADE, related_name="assignments")
    teacher = models.ForeignKey(Teacher, on_delete=models.PROTECT, related_name="assignments")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="assignments")
    lesson_type = models.ForeignKey(LessonType, on_delete=models.PROTECT, related_name="+")
    curriculum_item = models.ForeignKey(
        CurriculumItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments",
    )
    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, null=True, blank=True, related_name="assignments"
    )
    stream = models.ForeignKey(
        Stream, on_delete=models.CASCADE, null=True, blank=True, related_name="assignments"
    )
    subgroup = models.ForeignKey(
        SubGroup, on_delete=models.CASCADE, null=True, blank=True, related_name="assignments"
    )
    weekly_lessons = models.PositiveSmallIntegerField(_("lessons every week"), default=0)
    alternating_lessons = models.PositiveSmallIntegerField(_("lessons every other week"), default=0)
    total_lessons = models.PositiveSmallIntegerField(_("lessons in the period"))
    required_room_type = models.ForeignKey(
        RoomType, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = _("teaching assignment")
        verbose_name_plural = _("teaching assignments")
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(group__isnull=False, stream__isnull=True, subgroup__isnull=True)
                    | Q(group__isnull=True, stream__isnull=False, subgroup__isnull=True)
                    | Q(group__isnull=True, stream__isnull=True, subgroup__isnull=False)
                ),
                name="assignment_single_target",
            ),
            models.CheckConstraint(
                condition=Q(total_lessons__gte=1), name="assignment_total_positive"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.subject} · {self.lesson_type} · {self.target_name} · {self.teacher}"

    @property
    def target(self) -> Group | Stream | SubGroup:
        return self.group or self.stream or self.subgroup

    @property
    def target_name(self) -> str:
        if self.stream_id:
            return " + ".join(g.name for g in self.target_groups())
        return str(self.target)

    def target_groups(self) -> list[Group]:
        if self.group_id:
            return [self.group]
        if self.subgroup_id:
            return [self.subgroup.group]
        return list(self.stream.groups.all())

    @property
    def teaching_language(self) -> str:
        if self.stream_id:
            return self.stream.teaching_language
        return self.target_groups()[0].teaching_language

    @property
    def student_count(self) -> int:
        if self.subgroup_id:
            return self.subgroup.student_count
        return sum(g.student_count for g in self.target_groups())

    def slot_keys(self) -> list[int]:
        if self.subgroup_id:
            return self.subgroup.slot_keys()
        return sorted(k for g in self.target_groups() for k in g.slot_keys())
