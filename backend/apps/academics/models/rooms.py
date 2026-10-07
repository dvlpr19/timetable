"""Buildings, room types and rooms."""

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .structure import Faculty


class Building(models.Model):
    code = models.CharField(_("code"), max_length=10, unique=True)  # "A"
    name = models.CharField(_("name"), max_length=100)
    address = models.CharField(_("address"), max_length=255, blank=True)

    class Meta:
        verbose_name = _("building")
        verbose_name_plural = _("buildings")
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name


class RoomType(models.Model):
    code = models.CharField(_("code"), max_length=30, unique=True)
    name = models.CharField(_("name"), max_length=100)

    class Meta:
        verbose_name = _("room type")
        verbose_name_plural = _("room types")
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name


class Room(models.Model):
    building = models.ForeignKey(Building, on_delete=models.PROTECT, related_name="rooms")
    name = models.CharField(_("room"), max_length=50)  # "A-115", "Ma'ruza zali 1"
    floor = models.SmallIntegerField(_("floor"), default=1)
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT, related_name="rooms")
    capacity = models.PositiveSmallIntegerField(_("seats"))
    has_projector = models.BooleanField(_("projector"), default=False)
    computer_count = models.PositiveSmallIntegerField(_("computers"), default=0)
    has_board = models.BooleanField(_("board"), default=True)
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rooms",
        help_text=_("Optional: room reserved for a faculty."),
    )
    is_active = models.BooleanField(_("in use"), default=True)

    class Meta:
        verbose_name = _("room")
        verbose_name_plural = _("rooms")
        ordering = ["building__code", "name"]
        constraints = [
            models.UniqueConstraint(fields=["building", "name"], name="room_unique_name"),
            models.CheckConstraint(condition=Q(capacity__gte=1), name="room_capacity_positive"),
        ]

    def __str__(self) -> str:
        return self.name
