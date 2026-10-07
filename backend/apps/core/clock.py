"""The app's "now". DEMO_NOW pins the date (e.g. 2026-04-08) so the demo semester has a
"today"; the time of day stays real unless DEMO_NOW also gives one (2026-04-08T10:15)."""

from datetime import date, datetime, time

from django.conf import settings
from django.utils import timezone


def now() -> datetime:
    real = timezone.localtime()
    raw = getattr(settings, "DEMO_NOW", "")
    if not raw:
        return real
    if "T" in raw:
        demo = datetime.fromisoformat(raw)
        return demo if timezone.is_aware(demo) else timezone.make_aware(demo)
    day = date.fromisoformat(raw)
    return timezone.make_aware(datetime.combine(day, time(real.hour, real.minute, real.second)))


def today() -> date:
    return now().date()


def is_demo() -> bool:
    return bool(getattr(settings, "DEMO_NOW", ""))
