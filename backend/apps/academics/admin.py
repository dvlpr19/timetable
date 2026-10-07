from django.contrib import admin
from modeltranslation.admin import TabbedTranslationAdmin

from .models import (
    AcademicCalendarDay,
    AcademicYear,
    Academy,
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


@admin.register(Academy, EducationLevel, Building, RoomType)
class NamedAdmin(TabbedTranslationAdmin):
    list_display = ("name",)


@admin.register(Faculty)
class FacultyAdmin(TabbedTranslationAdmin):
    list_display = ("code", "name", "teaching_language")


@admin.register(Department)
class DepartmentAdmin(TabbedTranslationAdmin):
    list_display = ("code", "name", "faculty")
    list_filter = ("faculty",)


class LessonTimeInline(admin.TabularInline):
    model = LessonTime
    extra = 0


@admin.register(EducationForm)
class EducationFormAdmin(TabbedTranslationAdmin):
    list_display = ("name", "schedule_mode", "requires_room", "max_lessons_per_day")
    inlines = [LessonTimeInline]


@admin.register(Program)
class ProgramAdmin(TabbedTranslationAdmin):
    list_display = ("code", "name", "level", "faculty")
    list_filter = ("faculty", "level")


@admin.register(ProgramForm)
class ProgramFormAdmin(admin.ModelAdmin):
    list_display = ("program", "form", "duration_years", "group_prefix")
    list_filter = ("form",)


class TeachingPeriodInline(admin.TabularInline):
    model = TeachingPeriod
    extra = 0


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date")


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ("__str__", "start_date", "end_date", "is_current")
    inlines = [TeachingPeriodInline]


@admin.register(AcademicCalendarDay)
class CalendarDayAdmin(TabbedTranslationAdmin):
    list_display = ("date", "name", "kind", "is_assumption")
    list_filter = ("kind",)


@admin.register(BlockedPeriod)
class BlockedPeriodAdmin(TabbedTranslationAdmin):
    list_display = ("name", "weekday", "start", "end", "form", "is_hard")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "building", "floor", "room_type", "capacity", "is_active")
    list_filter = ("building", "room_type", "is_active")
    search_fields = ("name",)


@admin.register(LessonType)
class LessonTypeAdmin(TabbedTranslationAdmin):
    list_display = ("code", "name", "default_room_type")


@admin.register(Subject)
class SubjectAdmin(TabbedTranslationAdmin):
    list_display = ("code", "name", "department", "is_language")
    list_filter = ("department", "is_language")
    search_fields = ("code", "name_uz", "name_ru", "name_en")


@admin.register(CurriculumItem)
class CurriculumItemAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "program",
        "form",
        "teaching_language",
        "study_semester",
        "credits",
        "hours_lecture",
        "hours_practice",
        "hours_seminar",
        "hours_lab",
    )
    list_filter = ("program", "form", "teaching_language", "study_semester")


class SubGroupInline(admin.TabularInline):
    model = SubGroup
    extra = 0


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "program_form", "course", "teaching_language", "student_count", "shift")
    list_filter = ("program_form__form", "course", "teaching_language")
    search_fields = ("name",)
    inlines = [SubGroupInline]


@admin.register(Stream)
class StreamAdmin(admin.ModelAdmin):
    list_display = ("name", "semester", "teaching_language")
    filter_horizontal = ("groups",)


class AvailabilityInline(admin.TabularInline):
    model = TeacherAvailability
    extra = 0


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("full_name", "department", "position", "degree", "employment")
    list_filter = ("department", "position", "employment")
    search_fields = ("last_name", "first_name")
    filter_horizontal = ("subjects",)
    inlines = [AvailabilityInline]
    raw_id_fields = ("user",)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("__str__", "hemis_id", "group", "subgroup", "gender")
    list_filter = ("group__program_form__form", "group")
    search_fields = ("last_name", "first_name", "hemis_id")
    raw_id_fields = ("user",)


@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "lesson_type",
        "target_name",
        "teacher",
        "weekly_lessons",
        "total_lessons",
    )
    list_filter = ("period", "lesson_type", "teacher")
    search_fields = ("subject__name_uz", "group__name", "teacher__last_name")
    list_select_related = (
        "subject",
        "lesson_type",
        "teacher",
        "group",
        "subgroup__group",
        "stream",
    )
