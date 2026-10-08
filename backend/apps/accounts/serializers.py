from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class LoginSerializer(TokenObtainPairSerializer):
    default_error_messages = {
        "no_active_account": _("Incorrect login or password."),
    }


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
        return {
            "id": student.pk,
            "group": {"id": group.pk, "name": group.name, "course": group.course},
            "subgroup": student.subgroup.number if student.subgroup_id else None,
            "program": group.program_form.program.name,
            "form": group.program_form.form.code,
        }

    def get_teacher(self, user) -> dict | None:
        teacher = getattr(user, "teacher", None)
        if teacher is None:
            return None
        return {
            "id": teacher.pk,
            "short_name": teacher.short_name,
            "department": teacher.department.name,
            "position": teacher.get_position_display(),
        }

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "full_name",
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
