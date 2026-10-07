from django.contrib import admin

from .models import Notification, NotificationPreference, PushSubscription


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "recipient", "kind", "title", "is_read")
    list_filter = ("kind", "is_read")
    search_fields = ("recipient__username", "title")
    raw_id_fields = ("recipient", "entry", "change")


admin.site.register(PushSubscription)
admin.site.register(NotificationPreference)
