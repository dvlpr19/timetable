"""CRUD for reference data, people, curriculum and teaching load.

Access summary (also tested in tests/test_api_permissions.py):
- admin (dispatcher): everything.
- dekanat: reads all; writes groups, subgroups, streams, students, curriculum and teaching
  assignments of its own faculty; sees only its faculty's students.
- kafedra_mudiri: reads all reference data; writes teachers, their availability and teaching
  assignments of its own department.
- oqituvchi: reads reference data; writes only its own availability.
- talaba: reads reference data needed to browse published timetables.
"""

from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import Role
from apps.core.permissions import STAFF_ROLES, is_admin, role_of
from apps.core.viewsets import RoleModelViewSet

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
from . import serializers as s
from .imports import ExcelImportMixin

DEKANAT_WRITE = frozenset({Role.ADMIN, Role.DEKANAT})
KAFEDRA_WRITE = frozenset({Role.ADMIN, Role.KAFEDRA_MUDIRI})


def user_faculty(request) -> int | None:
    return request.user.faculty_id


def user_department(request) -> int | None:
    return request.user.department_id


# --------------------------------------------------------------------------- reference data


class FacultyViewSet(RoleModelViewSet):
    queryset = Faculty.objects.all()
    serializer_class = s.FacultySerializer
    search_fields = ("code", "name_uz", "name_ru", "name_en")


class DepartmentViewSet(RoleModelViewSet):
    queryset = Department.objects.select_related("faculty")
    serializer_class = s.DepartmentSerializer
    filterset_fields = ("faculty",)
    search_fields = ("code", "name_uz", "name_ru", "name_en")


class EducationLevelViewSet(RoleModelViewSet):
    queryset = EducationLevel.objects.order_by("code")
    serializer_class = s.EducationLevelSerializer


class EducationFormViewSet(RoleModelViewSet):
    queryset = EducationForm.objects.prefetch_related("lesson_times")
    serializer_class = s.EducationFormSerializer


class LessonTimeViewSet(RoleModelViewSet):
    """Bell schedules (qo'ng'iroq jadvali), editable by the dispatcher."""

    queryset = LessonTime.objects.select_related("form")
    serializer_class = s.LessonTimeSerializer
    filterset_fields = ("form", "shift")
    pagination_class = None


class BlockedPeriodViewSet(RoleModelViewSet):
    queryset = BlockedPeriod.objects.order_by("weekday", "start")
    serializer_class = s.BlockedPeriodSerializer
    filterset_fields = ("form", "weekday", "is_hard")


class ProgramViewSet(RoleModelViewSet):
    queryset = Program.objects.select_related("faculty", "level")
    serializer_class = s.ProgramSerializer
    filterset_fields = ("faculty", "level")
    search_fields = ("code", "name_uz", "name_ru", "name_en")


class ProgramFormViewSet(RoleModelViewSet):
    queryset = ProgramForm.objects.select_related("program", "form").order_by(
        "program", "form__order"
    )
    serializer_class = s.ProgramFormSerializer
    filterset_fields = ("program", "form", "program__faculty")


class AcademicYearViewSet(RoleModelViewSet):
    queryset = AcademicYear.objects.all()
    serializer_class = s.AcademicYearSerializer


class SemesterViewSet(RoleModelViewSet):
    queryset = Semester.objects.select_related("year")
    serializer_class = s.SemesterSerializer
    filterset_fields = ("year", "kind", "is_current")


class TeachingPeriodViewSet(RoleModelViewSet):
    queryset = TeachingPeriod.objects.select_related("semester", "form")
    serializer_class = s.TeachingPeriodSerializer
    filterset_fields = ("semester", "form")


class CalendarDayViewSet(RoleModelViewSet):
    queryset = AcademicCalendarDay.objects.all()
    serializer_class = s.CalendarDaySerializer
    filterset_fields = {"kind": ["exact"], "date": ["gte", "lte", "exact"]}


class BuildingViewSet(RoleModelViewSet):
    queryset = Building.objects.all()
    serializer_class = s.BuildingSerializer


class RoomTypeViewSet(RoleModelViewSet):
    queryset = RoomType.objects.all()
    serializer_class = s.RoomTypeSerializer


class RoomViewSet(ExcelImportMixin, RoleModelViewSet):
    queryset = Room.objects.select_related("building", "room_type")
    serializer_class = s.RoomSerializer
    filterset_fields = {
        "building": ["exact"],
        "room_type": ["exact"],
        "faculty": ["exact"],
        "is_active": ["exact"],
        "capacity": ["gte", "lte"],
    }
    search_fields = ("name",)
    ordering_fields = ("name", "capacity", "floor")
    import_resource = "rooms"


class LessonTypeViewSet(RoleModelViewSet):
    queryset = LessonType.objects.all()
    serializer_class = s.LessonTypeSerializer


class SubjectViewSet(ExcelImportMixin, RoleModelViewSet):
    queryset = Subject.objects.select_related("department")
    serializer_class = s.SubjectSerializer
    filterset_fields = ("department", "is_language")
    search_fields = ("code", "name_uz", "name_ru", "name_en")
    import_resource = "subjects"


# --------------------------------------------------------------------------- faculty scope


class FacultyScopedViewSet(RoleModelViewSet):
    """Admin everywhere; dekanat only inside its own faculty."""

    write_roles = DEKANAT_WRITE
    faculty_path: str = ""  # lookup from the model to its faculty id

    def faculty_id_of(self, obj) -> int | None:
        value = obj
        for part in self.faculty_path.split("__"):
            value = getattr(value, part)
        return value

    def in_scope(self, obj) -> bool:
        if is_admin(self.request.user):
            return True
        return role_of(self.request.user) == Role.DEKANAT and (
            self.faculty_id_of(obj) == user_faculty(self.request)
        )


class CurriculumItemViewSet(FacultyScopedViewSet):
    queryset = CurriculumItem.objects.select_related("subject", "program", "form")
    serializer_class = s.CurriculumItemSerializer
    read_roles = STAFF_ROLES
    faculty_path = "program__faculty_id"
    filterset_fields = ("program", "form", "teaching_language", "study_semester", "subject")


class GroupViewSet(ExcelImportMixin, FacultyScopedViewSet):
    queryset = Group.objects.select_related("program_form__program").prefetch_related("subgroups")
    serializer_class = s.GroupSerializer
    faculty_path = "program_form__program__faculty_id"
    filterset_fields = {
        "program_form": ["exact"],
        "program_form__form": ["exact"],
        "program_form__program__faculty": ["exact"],
        "course": ["exact"],
        "teaching_language": ["exact"],
    }
    search_fields = ("name",)
    import_resource = "groups"


class SubGroupViewSet(FacultyScopedViewSet):
    queryset = SubGroup.objects.select_related("group__program_form__program")
    serializer_class = s.SubGroupSerializer
    faculty_path = "group__program_form__program__faculty_id"
    filterset_fields = ("group",)


class StreamViewSet(FacultyScopedViewSet):
    queryset = Stream.objects.prefetch_related("groups")
    serializer_class = s.StreamSerializer
    faculty_path = "faculty_id"
    filterset_fields = ("semester", "faculty", "teaching_language")
    search_fields = ("name",)


class StudentViewSet(ExcelImportMixin, FacultyScopedViewSet):
    """Personal data: only the dispatcher and the student's own dean's office."""

    queryset = Student.objects.select_related("group__program_form__program", "subgroup")
    serializer_class = s.StudentSerializer
    read_roles = DEKANAT_WRITE
    faculty_path = "group__program_form__program__faculty_id"
    filterset_fields = ("group", "subgroup", "gender")
    search_fields = ("last_name", "first_name", "hemis_id")
    import_resource = "students"

    def scope_queryset(self, qs):
        if is_admin(self.request.user):
            return qs
        return qs.filter(group__program_form__program__faculty_id=user_faculty(self.request))


# --------------------------------------------------------------------------- department scope


class TeacherViewSet(ExcelImportMixin, RoleModelViewSet):
    queryset = Teacher.objects.select_related("department").prefetch_related("subjects")
    write_roles = KAFEDRA_WRITE
    filterset_fields = ("department", "department__faculty", "position", "employment")
    search_fields = ("last_name", "first_name", "middle_name")
    import_resource = "teachers"

    def get_serializer_class(self):
        if role_of(self.request.user) in STAFF_ROLES:
            return s.TeacherSerializer
        return s.TeacherPublicSerializer

    def in_scope(self, obj) -> bool:
        if is_admin(self.request.user):
            return True
        return role_of(self.request.user) == Role.KAFEDRA_MUDIRI and (
            obj.department_id == user_department(self.request)
        )


class TeacherAvailabilityViewSet(RoleModelViewSet):
    """Teachers manage their own "qulay kunlarim"; heads of department their staff's."""

    queryset = TeacherAvailability.objects.select_related("teacher", "lesson_time")
    serializer_class = s.TeacherAvailabilitySerializer
    read_roles = STAFF_ROLES | {Role.OQITUVCHI}
    write_roles = KAFEDRA_WRITE | {Role.OQITUVCHI}
    filterset_fields = ("teacher", "weekday", "level")
    pagination_class = None

    def scope_queryset(self, qs):
        if role_of(self.request.user) == Role.OQITUVCHI:
            return qs.filter(teacher__user=self.request.user)
        return qs

    def in_scope(self, obj) -> bool:
        user = self.request.user
        match role_of(user):
            case Role.ADMIN:
                return True
            case Role.KAFEDRA_MUDIRI:
                return obj.teacher.department_id == user.department_id
            case Role.OQITUVCHI:
                return obj.teacher.user_id == user.id
        return False

    @action(detail=False, methods=["put"], url_path="replace")
    def replace(self, request):
        """Replace all availability rows of one teacher (the "Qulay kunlarim" grid)."""
        teacher_id = request.data.get("teacher")
        rows = request.data.get("rows", [])
        teacher = Teacher.objects.filter(pk=teacher_id).first()
        probe = TeacherAvailability(teacher=teacher) if teacher else None
        if probe is None or not self.in_scope(probe):
            return Response(status=403)
        serializer = s.TeacherAvailabilitySerializer(
            data=[{**row, "teacher": teacher.pk} for row in rows], many=True
        )
        serializer.is_valid(raise_exception=True)
        TeacherAvailability.objects.filter(teacher=teacher).delete()
        serializer.save()
        return Response(serializer.data)


class TeachingAssignmentViewSet(RoleModelViewSet):
    """Yuklama taqsimoti. Dekanat edits its faculty's groups, kafedra its own teachers."""

    queryset = (
        TeachingAssignment.objects.select_related(
            "teacher", "subject", "lesson_type", "group", "subgroup__group", "stream"
        )
        .prefetch_related("stream__groups")
        .order_by("period", "subject__code", "pk")
    )
    serializer_class = s.TeachingAssignmentSerializer
    read_roles = STAFF_ROLES | {Role.OQITUVCHI}
    write_roles = STAFF_ROLES
    filterset_fields = (
        "period",
        "period__semester",
        "period__form",
        "teacher",
        "subject",
        "lesson_type",
        "group",
        "stream",
        "subgroup",
    )
    search_fields = ("subject__name_uz", "teacher__last_name", "group__name")

    def scope_queryset(self, qs):
        if role_of(self.request.user) == Role.OQITUVCHI:
            return qs.filter(teacher__user=self.request.user)
        return qs

    def in_scope(self, obj) -> bool:
        user = self.request.user
        match role_of(user):
            case Role.ADMIN:
                return True
            case Role.KAFEDRA_MUDIRI:
                return obj.teacher.department_id == user.department_id
            case Role.DEKANAT:
                return all(
                    g.program_form.program.faculty_id == user.faculty_id
                    for g in obj.target_groups()
                )
        return False
