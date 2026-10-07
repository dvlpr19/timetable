"""Messages of the signed-in user, their settings and browser push subscriptions."""

from django.conf import settings
from django.urls import path
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView

from .channels import WebPushChannel
from .models import (
    MANDATORY_KINDS,
    Notification,
    NotificationKind,
    NotificationPreference,
    PushSubscription,
)
from .rendering import states

# kinds a person can choose to (not) receive; reminders and the digest have own switches
OPTIONAL_KINDS = [
    NotificationKind.ROOM_CHANGED,
    NotificationKind.TEACHER_CHANGED,
    NotificationKind.LESSON_ADDED,
    NotificationKind.LINK_CHANGED,
    NotificationKind.SCHEDULE_PUBLISHED,
    NotificationKind.REQUEST_ANSWERED,
]


class NotificationSerializer(serializers.ModelSerializer):
    was = serializers.SerializerMethodField()
    now = serializers.SerializerMethodField()
    lesson_date = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id",
            "kind",
            "title",
            "body",
            "comment",
            "entry",
            "lesson_date",
            "was",
            "now",
            "is_read",
            "created_at",
        )

    def _states(self, n):
        if not hasattr(n, "_states"):
            n._states = states(n.kind, n.params, n.language)
        return n._states

    def get_was(self, n) -> str | None:
        s = self._states(n)
        return s[0] if s else None

    def get_now(self, n) -> str | None:
        s = self._states(n)
        return s[1] if s else None

    def get_lesson_date(self, n) -> str | None:
        when = n.params.get("new_when") or n.params.get("when") or {}
        return when.get("date") if isinstance(when, dict) else None


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user)
        if self.request.query_params.get("unread"):
            qs = qs.filter(is_read=False)
        return qs

    @action(detail=False, url_path="unread-count")
    def unread_count(self, request):
        """Polled every 25 seconds by the apps (the bell)."""
        qs = Notification.objects.filter(recipient=request.user, is_read=False)
        latest = qs.order_by("-created_at").values_list("id", flat=True).first()
        return Response({"count": qs.count(), "latest": latest})

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        updated = Notification.objects.filter(recipient=request.user, pk=pk, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({"updated": updated})

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        updated = Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({"updated": updated})


class PreferenceSerializer(serializers.ModelSerializer):
    optional_kinds = serializers.SerializerMethodField()
    mandatory_kinds = serializers.SerializerMethodField()

    class Meta:
        model = NotificationPreference
        fields = (
            "disabled_kinds",
            "reminder_enabled",
            "reminder_minutes",
            "daily_digest_enabled",
            "optional_kinds",
            "mandatory_kinds",
        )

    def get_optional_kinds(self, _obj) -> list[str]:
        return list(OPTIONAL_KINDS)

    def get_mandatory_kinds(self, _obj) -> list[str]:
        return sorted(MANDATORY_KINDS)

    def validate_disabled_kinds(self, value):
        bad = [k for k in value if k not in OPTIONAL_KINDS]
        if bad:
            raise ValidationError(
                _("These messages cannot be switched off: %(kinds)s") % {"kinds": ", ".join(bad)}
            )
        return sorted(set(value))

    def validate_reminder_minutes(self, value):
        if value not in (5, 10, 15, 30, 60):
            raise ValidationError(_("Choose 5, 10, 15, 30 or 60 minutes."))
        return value


class PreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def _pref(self, request):
        return NotificationPreference.objects.get_or_create(user=request.user)[0]

    def get(self, request):
        return Response(PreferenceSerializer(self._pref(request)).data)

    def patch(self, request):
        serializer = PreferenceSerializer(self._pref(request), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PushView(APIView):
    """GET: is push available and the public key; POST subscribe / DELETE unsubscribe."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "enabled": WebPushChannel.enabled(),
                "public_key": settings.VAPID_PUBLIC_KEY,
                "subscriptions": PushSubscription.objects.filter(user=request.user).count(),
            }
        )

    def post(self, request):
        endpoint = request.data.get("endpoint")
        keys = request.data.get("keys") or {}
        if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
            raise ValidationError(_("Incomplete push subscription."))
        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user": request.user,
                "p256dh": keys["p256dh"],
                "auth": keys["auth"],
                "user_agent": request.headers.get("User-Agent", "")[:255],
            },
        )
        return Response({"ok": True}, status=201)

    def delete(self, request):
        endpoint = request.data.get("endpoint")
        PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
        return Response(status=204)


router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("notifications/preferences/", PreferenceView.as_view(), name="notification-preferences"),
    path("notifications/push/", PushView.as_view(), name="notification-push"),
    *router.urls,
]
