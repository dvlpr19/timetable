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
        )
        read_only_fields = ("id", "username", "first_name", "last_name", "role", "language_auto")
