from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import (
    AcademicCalendarDay,
    AcademicYear,
    BlockedPeriod,
    Building,
    CurriculumItem,
    Department,
    EducationForm,
    EducationLevel,
    Faculty,
    Group,
    LessonTime,
    LessonType,
    Program,
    ProgramForm,
    Room,
    RoomType,
    Semester,
    Stream,
    Student,
    SubGroup,
    Subject,
    Teacher,
    TeacherAvailability,
    TeachingAssignment,
    TeachingPeriod,
)

TRANSLATED = ("name", "name_uz", "name_ru", "name_en")


class TranslatedModelSerializer(serializers.ModelSerializer):
    """`name` is the value in the request language (falls back to Uzbek); the three
    language columns are writable and only `name_uz` is required."""

    name = serializers.CharField(read_only=True)

    def get_extra_kwargs(self):
        extra = super().get_extra_kwargs()
        extra.setdefault("name_uz", {})["required"] = True
        for lang in ("ru", "en"):
            extra.setdefault(f"name_{lang}", {}).update(required=False, allow_blank=True)
        return extra


class FacultySerializer(TranslatedModelSerializer):
    class Meta:
        model = Faculty
        fields = ("id", "academy", "code", *TRANSLATED, "teaching_language")


class DepartmentSerializer(TranslatedModelSerializer):
    class Meta:
        model = Department
        fields = ("id", "faculty", "code", *TRANSLATED)


class EducationLevelSerializer(TranslatedModelSerializer):
    class Meta:
        model = EducationLevel
        fields = ("id", "code", *TRANSLATED)


class LessonTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonTime
        fields = ("id", "form", "number", "start", "end", "shift")


class EducationFormSerializer(TranslatedModelSerializer):
    lesson_times = LessonTimeSerializer(many=True, read_only=True)

    class Meta:
        model = EducationForm
        fields = (
            "id",
            "code",
            *TRANSLATED,
            "schedule_mode",
            "requires_room",
            "max_lessons_per_day",
            "study_weekdays",
            "order",
            "lesson_times",
        )


class BlockedPeriodSerializer(TranslatedModelSerializer):
    class Meta:
        model = BlockedPeriod
        fields = ("id", *TRANSLATED, "weekday", "start", "end", "form", "is_hard")


class ProgramSerializer(TranslatedModelSerializer):
    class Meta:
        model = Program
        fields = ("id", "faculty", "level", "code", *TRANSLATED)


class ProgramFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgramForm
        fields = ("id", "program", "form", "duration_years", "group_prefix")


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ("id", "name", "start_date", "end_date")


class SemesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Semester
        fields = ("id", "year", "kind", "start_date", "end_date", "is_current")


class TeachingPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeachingPeriod
        fields = ("id", "semester", "form", "name", "start_date", "end_date", "weeks_count")


class CalendarDaySerializer(TranslatedModelSerializer):
    class Meta:
        model = AcademicCalendarDay
        fields = ("id", "date", "kind", *TRANSLATED, "works_as_weekday", "is_assumption")


class BuildingSerializer(TranslatedModelSerializer):
    class Meta:
        model = Building
        fields = ("id", "code", *TRANSLATED, "address")


class RoomTypeSerializer(TranslatedModelSerializer):
    class Meta:
        model = RoomType
        fields = ("id", "code", *TRANSLATED)


class RoomSerializer(serializers.ModelSerializer):
    building_name = serializers.CharField(source="building.name", read_only=True)
    room_type_name = serializers.CharField(source="room_type.name", read_only=True)

    class Meta:
        model = Room
        fields = (
            "id",
            "building",
            "building_name",
            "name",
            "floor",
            "room_type",
            "room_type_name",
            "capacity",
            "has_projector",
            "computer_count",
            "has_board",
            "faculty",
            "is_active",
        )


class LessonTypeSerializer(TranslatedModelSerializer):
    class Meta:
        model = LessonType
        fields = ("id", "code", *TRANSLATED, "default_room_type", "order")


class SubjectSerializer(TranslatedModelSerializer):
    class Meta:
        model = Subject
        fields = ("id", "code", *TRANSLATED, "department", "is_language", "practice_room_type")


class CurriculumItemSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    hours_independent = serializers.IntegerField(read_only=True)

    class Meta:
        model = CurriculumItem
        fields = (
            "id",
            "program",
            "form",
            "teaching_language",
            "study_semester",
            "subject",
            "subject_name",
            "credits",
            "hours_lecture",
            "hours_practice",
            "hours_seminar",
            "hours_lab",
            "hours_independent",
            "control_type",
        )

    def validate(self, attrs):
        """Independent study fills up the credit: 1 credit = 30 hours."""
        fields = ("credits", "hours_lecture", "hours_practice", "hours_seminar", "hours_lab")
        merged = {f: attrs.get(f, getattr(self.instance, f, 0)) or 0 for f in fields}
        independent = merged["credits"] * 30 - sum(merged[f] for f in fields[1:])
        if independent < 0:
            raise serializers.ValidationError(
                {"credits": _("Classroom hours exceed the credits (1 credit = 30 hours).")}
            )
        attrs["hours_independent"] = independent
        return attrs


class SubGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubGroup
        fields = ("id", "group", "number", "student_count")


class GroupSerializer(serializers.ModelSerializer):
    subgroups = SubGroupSerializer(many=True, read_only=True)
    form = serializers.IntegerField(source="program_form.form_id", read_only=True)
    faculty = serializers.IntegerField(source="program_form.program.faculty_id", read_only=True)

    class Meta:
        model = Group
        fields = (
            "id",
            "program_form",
            "form",
            "faculty",
            "name",
            "course",
            "number",
            "teaching_language",
            "student_count",
            "gender_composition",
            "shift",
            "subgroups",
        )


class StreamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stream
        fields = ("id", "semester", "faculty", "name", "teaching_language", "groups")

    def validate(self, attrs):
        groups = attrs.get("groups") or (self.instance.groups.all() if self.instance else [])
        language = attrs.get("teaching_language") or getattr(
            self.instance, "teaching_language", None
        )
        if any(g.teaching_language != language for g in groups):
            raise serializers.ValidationError(
                {"groups": _("Only groups with the same teaching language can form a stream.")}
            )
        return attrs


class TeacherPublicSerializer(serializers.ModelSerializer):
    """What students and teachers may see about a colleague."""

    short_name = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    position_display = serializers.CharField(source="get_position_display", read_only=True)

    class Meta:
        model = Teacher
        fields = (
            "id",
            "short_name",
            "full_name",
            "department",
            "department_name",
            "position",
            "position_display",
        )


class TeacherSerializer(TeacherPublicSerializer):
    class Meta:
        model = Teacher
        fields = (
            *TeacherPublicSerializer.Meta.fields,
            "user",
            "last_name",
            "first_name",
            "middle_name",
            "degree",
            "employment",
            "annual_load_hours",
            "max_weekly_lessons",
            "subjects",
            "teaching_languages",
        )


class TeacherAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherAvailability
        fields = ("id", "teacher", "weekday", "lesson_time", "level")
        # Empty lesson_time means "the whole day"; uniqueness is enforced by the database
        # (nulls not distinct), DRF's generated validator would make lesson_time required.
        validators = []
        extra_kwargs = {"lesson_time": {"required": False, "default": None}}


class StudentSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)

    class Meta:
        model = Student
        fields = (
            "id",
            "user",
            "last_name",
            "first_name",
            "middle_name",
            "hemis_id",
            "group",
            "group_name",
            "subgroup",
            "gender",
            "phone",
        )

    def validate(self, attrs):
        group = attrs.get("group") or getattr(self.instance, "group", None)
        subgroup = attrs.get("subgroup", getattr(self.instance, "subgroup", None))
        if subgroup and subgroup.group_id != group.id:
            raise serializers.ValidationError(
                {"subgroup": _("The subgroup belongs to another group.")}
            )
        return attrs


class TeachingAssignmentSerializer(serializers.ModelSerializer):
    target_name = serializers.CharField(read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    lesson_type_code = serializers.CharField(source="lesson_type.code", read_only=True)
    teacher_name = serializers.CharField(source="teacher.short_name", read_only=True)
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = TeachingAssignment
        fields = (
            "id",
            "period",
            "teacher",
            "teacher_name",
            "subject",
            "subject_name",
            "lesson_type",
            "lesson_type_code",
            "curriculum_item",
            "group",
            "stream",
            "subgroup",
            "target_name",
            "student_count",
            "weekly_lessons",
            "alternating_lessons",
            "total_lessons",
            "required_room_type",
        )

    def validate(self, attrs):
        def current(name):
            return attrs.get(name, getattr(self.instance, name, None))

        targets = [current(n) for n in ("group", "stream", "subgroup")]
        if sum(t is not None for t in targets) != 1:
            raise serializers.ValidationError(
                _("Choose exactly one of: group, stream or subgroup.")
            )
        teacher, target = current("teacher"), next(t for t in targets if t is not None)
        language = getattr(target, "teaching_language", None) or target.group.teaching_language
        if not teacher.can_teach_in(language):
            raise serializers.ValidationError(
                {"teacher": _("This teacher does not teach in the group's language.")}
            )
        return attrs
