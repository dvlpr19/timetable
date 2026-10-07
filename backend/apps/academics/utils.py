"""Pure helpers for curriculum arithmetic (no database access)."""

import math
from dataclasses import dataclass

from .models.curriculum import HOURS_PER_LESSON


@dataclass(frozen=True)
class WeeklyDistribution:
    weekly: int  # lessons every week
    alternating: int  # extra lessons on odd (or even) weeks only
    total: int  # lessons the plan requires in the period


def lessons_from_hours(hours: int) -> int:
    return math.ceil(hours / HOURS_PER_LESSON)


def distribute_weekly(hours: int, weeks: int) -> WeeklyDistribution:
    """Split plan hours into weekly + every-other-week lessons.

    30 h / 15 weeks → 1 per week. 45 h / 15 weeks = 1.5 per week → 1 every week + 1 on odd weeks.
    """
    total = lessons_from_hours(hours)
    weekly = total // weeks
    remainder = total - weekly * weeks
    alternating = math.ceil(remainder / math.ceil(weeks / 2)) if remainder else 0
    return WeeklyDistribution(weekly=weekly, alternating=alternating, total=total)
