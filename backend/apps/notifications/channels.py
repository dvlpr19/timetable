"""Delivery channels. In-app messages are the record; Web Push (and later Telegram) only
announce a message that already exists, so a failed push never loses information."""

from __future__ import annotations

import json
import logging

from django.conf import settings
from django.utils import timezone

from .models import Notification, PushSubscription

log = logging.getLogger(__name__)


class Channel:
    name = "base"

    def send(self, notifications: list[Notification]) -> int:
        raise NotImplementedError


class WebPushChannel(Channel):
    """Browser push via VAPID. Without keys in the environment it stays silent."""

    name = "webpush"

    @staticmethod
    def enabled() -> bool:
        return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)

    def send(self, notifications: list[Notification]) -> int:
        if not self.enabled() or not notifications:
            return 0
        from pywebpush import WebPushException, webpush

        by_user: dict[int, list[PushSubscription]] = {}
        for sub in PushSubscription.objects.filter(
            user__in={n.recipient_id for n in notifications}
        ):
            by_user.setdefault(sub.user_id, []).append(sub)
        sent = 0
        now = timezone.now()
        for n in notifications:
            payload = json.dumps(
                {"title": n.title, "body": n.body, "url": "/messages", "tag": f"n{n.pk}"},
                ensure_ascii=False,
            )
            for sub in by_user.get(n.recipient_id, []):
                try:
                    webpush(
                        subscription_info={
                            "endpoint": sub.endpoint,
                            "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                        },
                        data=payload,
                        vapid_private_key=settings.VAPID_PRIVATE_KEY,
                        vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIM_EMAIL}"},
                        ttl=6 * 3600,
                    )
                    sub.last_success_at = now
                    sub.save(update_fields=["last_success_at"])
                    sent += 1
                except WebPushException as e:
                    status = getattr(e.response, "status_code", None)
                    if status in (404, 410):  # the browser dropped the subscription
                        sub.delete()
                    else:
                        log.warning("push to %s failed: %s", sub.pk, e)
        Notification.objects.filter(pk__in=[n.pk for n in notifications]).update(pushed_at=now)
        return sent


CHANNELS: list[Channel] = [WebPushChannel()]
