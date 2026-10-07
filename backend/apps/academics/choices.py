"""Enumerations shared across apps. Labels are gettext-translated."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class TeachingLanguage(models.TextChoices):
    """Language a group is taught in (not the UI language)."""

    UZ = "uz", _("Uzbek")
    RU = "ru", _("Russian")
    EN = "en", _("English")
    AR = "ar", _("Arabic")


class ScheduleMode(models.TextChoices):
    WEEKLY = "weekly", _("Weekly recurring")
    SESSION = "session", _("Session (fixed dates)")


class SemesterKind(models.TextChoices):
    AUTUMN = "autumn", _("Autumn semester")
    SPRING = "spring", _("Spring semester")


class Weekday(models.IntegerChoices):
    MONDAY = 0, _("Monday")
    TUESDAY = 1, _("Tuesday")
    WEDNESDAY = 2, _("Wednesday")
    THURSDAY = 3, _("Thursday")
    FRIDAY = 4, _("Friday")
    SATURDAY = 5, _("Saturday")
    SUNDAY = 6, _("Sunday")


class WeekParity(models.TextChoices):
    EVERY = "every", _("Every week")
    ODD = "odd", _("Odd weeks")
    EVEN = "even", _("Even weeks")


class CalendarDayKind(models.TextChoices):
    HOLIDAY = "holiday", _("Public holiday")
    DAY_OFF = "day_off", _("Day off")
    WORKDAY = "workday", _("Transferred working day")


class GenderComposition(models.TextChoices):
    MIXED = "mixed", _("Mixed")
    MALE = "male", _("Male students")
    FEMALE = "female", _("Female students")


class Gender(models.TextChoices):
    MALE = "m", _("Male")
    FEMALE = "f", _("Female")


class Position(models.TextChoices):
    ASSISTANT = "assistant", _("Assistant")
    TEACHER = "teacher", _("Lecturer")
    SENIOR_TEACHER = "senior_teacher", _("Senior lecturer")
    ASSOCIATE_PROFESSOR = "associate_professor", _("Associate professor")
    PROFESSOR = "professor", _("Professor")


class AcademicDegree(models.TextChoices):
    NONE = "none", _("No degree")
    PHD = "phd", _("PhD")
    DSC = "dsc", _("DSc")


class EmploymentType(models.TextChoices):
    STAFF = "staff", _("Full-time")
    PART_TIME = "part_time", _("Part-time (second job)")
    HOURLY = "hourly", _("Hourly")


class ControlType(models.TextChoices):
    EXAM = "exam", _("Exam")
    CREDIT = "credit", _("Pass/fail test")


class AvailabilityLevel(models.TextChoices):
    PREFERRED = "preferred", _("Preferred")
    POSSIBLE = "possible", _("Possible")
    UNAVAILABLE = "unavailable", _("Unavailable")


class LessonTypeCode(models.TextChoices):
    LECTURE = "lecture", _("Lecture")
    PRACTICE = "practice", _("Practical class")
    SEMINAR = "seminar", _("Seminar")
    LAB = "lab", _("Laboratory")


# Group/subgroup occupancy is encoded as integer "slots" so that PostgreSQL can
# enforce the subgroup rule with an array-overlap exclusion constraint:
# a whole group occupies all of its subgroup slots, a subgroup only its own.
MAX_SUBGROUPS = 3
SLOTS_PER_GROUP = 10
