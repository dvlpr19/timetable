import re

from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.academics.choices import TeachingLanguage

from .models import User


class LoginSerializer(TokenObtainPairSerializer):
    default_error_messages = {
        "no_active_account": _("Incorrect login or password."),
    }


PHONE_RE = re.compile(r"^\+?[0-9 ()-]{7,20}$")


class MeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    faculty_name = serializers.CharField(source="faculty.name", read_only=True, default=None)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    student = serializers.SerializerMethodField()
    teacher = serializers.SerializerMethodField()

    def get_student(self, user) -> dict | None:
        student = getattr(user, "student", None)
        if student is None:
            return None
        group = student.group
        program = group.program_form.program
        return {
            "id": student.pk,
            "hemis_id": student.hemis_id,
            "middle_name": student.middle_name,
            "group": {"id": group.pk, "name": group.name, "course": group.course},
            "subgroup": student.subgroup.number if student.subgroup_id else None,
            "program": program.name,
            "faculty": program.faculty.name,
            "form": group.program_form.form.code,
            "form_name": group.program_form.form.name,
            "teaching_language": group.get_teaching_language_display(),
            "shift": group.shift,
        }

    def get_teacher(self, user) -> dict | None:
        teacher = getattr(user, "teacher", None)
        if teacher is None:
            return None
        labels = dict(TeachingLanguage.choices)
        return {
            "id": teacher.pk,
            "short_name": teacher.short_name,
            "middle_name": teacher.middle_name,
            "department": teacher.department.name,
            "faculty": teacher.department.faculty.name,
            "position": teacher.get_position_display(),
            "degree": teacher.get_degree_display() if teacher.degree != "none" else None,
            "employment": teacher.get_employment_display(),
            "max_weekly_lessons": teacher.max_weekly_lessons,
            "annual_load_hours": teacher.annual_load_hours,
            "teaching_languages": [labels.get(c, c) for c in teacher.teaching_languages],
            "subjects": [s.name for s in teacher.subjects.all()],
        }

    def validate_phone(self, value):
        value = value.strip()
        if value and not PHONE_RE.match(value):
            raise serializers.ValidationError(_("Enter a valid phone number."))
        return value

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone",
            "date_joined",
            "last_login",
            "role",
            "language",
            "language_auto",
            "faculty",
            "faculty_name",
            "department",
            "department_name",
            "student",
            "teacher",
        )
        read_only_fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "role",
            "language_auto",
            "faculty",
            "department",
            "date_joined",
            "last_login",
        )


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError(_("Current password is incorrect."))
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value
