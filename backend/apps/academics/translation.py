"""django-modeltranslation: name_uz (required), name_ru, name_en with fallback to Uzbek."""

from modeltranslation.translator import TranslationOptions, register

from .models import (
    AcademicCalendarDay,
    Academy,
    BlockedPeriod,
    Building,
    Department,
    EducationForm,
    EducationLevel,
    Faculty,
    LessonType,
    Program,
    RoomType,
    Subject,
)


class NameTranslation(TranslationOptions):
    fields = ("name",)
    required_languages = ("uz",)


for model in (
    Academy,
    Faculty,
    Department,
    EducationLevel,
    EducationForm,
    Program,
    Building,
    RoomType,
    LessonType,
    Subject,
    AcademicCalendarDay,
    BlockedPeriod,
):
    register(model)(type(f"{model.__name__}Translation", (NameTranslation,), {}))
