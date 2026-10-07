from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    ADMIN = "admin", _("Dispatcher (academic office)")
    DEKANAT = "dekanat", _("Dean's office")
    KAFEDRA_MUDIRI = "kafedra_mudiri", _("Head of department")
    OQITUVCHI = "oqituvchi", _("Teacher")
    TALABA = "talaba", _("Student")


class UILanguage(models.TextChoices):
    UZ = "uz", "O'zbekcha"
    RU = "ru", "Русский"
    EN = "en", "English"


class User(AbstractUser):
    """Application user. UI language is a personal preference, unrelated to teaching language."""

    role = models.CharField(_("role"), max_length=20, choices=Role.choices, default=Role.TALABA)
    language = models.CharField(
        _("interface language"), max_length=2, choices=UILanguage.choices, default=UILanguage.UZ
    )
    # True until the user explicitly picks a language; lets the client apply browser detection.
    language_auto = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=Role.values), name="user_role_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(language__in=UILanguage.values), name="user_language_valid"
            ),
        ]

    @property
    def full_name(self) -> str:
        return f"{self.last_name} {self.first_name}".strip() or self.username
