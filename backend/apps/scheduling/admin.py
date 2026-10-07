from django.contrib import admin

from .models import RescheduleRequest, Schedule, ScheduleChange, ScheduleEntry


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("name", "semester", "status", "created_at", "published_at")
    list_filter = ("status", "semester")


@admin.register(ScheduleEntry)
class ScheduleEntryAdmin(admin.ModelAdmin):
    list_display = ("__str__", "schedule", "room", "is_locked")
    list_filter = ("schedule", "weekday", "is_locked")
    raw_id_fields = ("assignment",)


@admin.register(ScheduleChange)
class ScheduleChangeAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "entry", "user", "comment", "notified", "undone")
    list_filter = ("action", "notified")
    raw_id_fields = ("entry",)


@admin.register(RescheduleRequest)
class RescheduleRequestAdmin(admin.ModelAdmin):
    list_display = ("teacher", "entry", "status", "created_at")
    list_filter = ("status",)
    raw_id_fields = ("entry",)
