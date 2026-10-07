from .assignments import TeachingAssignment
from .calendar import (
    AcademicCalendarDay,
    AcademicYear,
    BlockedPeriod,
    LessonTime,
    Semester,
    TeachingPeriod,
)
from .curriculum import HOURS_PER_CREDIT, HOURS_PER_LESSON, CurriculumItem, LessonType, Subject
from .people import Group, Stream, Student, SubGroup, Teacher, TeacherAvailability
from .rooms import Building, Room, RoomType
from .structure import (
    Academy,
    Department,
    EducationForm,
    EducationLevel,
    Faculty,
    Program,
    ProgramForm,
)

__all__ = [
    "HOURS_PER_CREDIT",
    "HOURS_PER_LESSON",
    "AcademicCalendarDay",
    "AcademicYear",
    "Academy",
    "BlockedPeriod",
    "Building",
    "CurriculumItem",
    "Department",
    "EducationForm",
    "EducationLevel",
    "Faculty",
    "Group",
    "LessonTime",
    "LessonType",
    "Program",
    "ProgramForm",
    "Room",
    "RoomType",
    "Semester",
    "Stream",
    "Student",
    "SubGroup",
    "Subject",
    "Teacher",
    "TeacherAvailability",
    "TeachingAssignment",
    "TeachingPeriod",
]
