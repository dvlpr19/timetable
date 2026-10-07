"""Group naming rule (configurable via settings.GROUP_NAME_PATTERN)."""

from django.conf import settings


def group_name(prefix: str, course: int, number: int) -> str:
    """IS + 3 + 1 → IS-301 (default pattern "{prefix}-{course}{number:02d}")."""
    return settings.GROUP_NAME_PATTERN.format(prefix=prefix, course=course, number=number)
