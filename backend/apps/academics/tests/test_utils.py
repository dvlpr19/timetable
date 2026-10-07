import pytest

from apps.academics.naming import group_name
from apps.academics.utils import distribute_weekly


@pytest.mark.parametrize(
    ("hours", "weeks", "weekly", "alternating", "total"),
    [
        (30, 15, 1, 0, 15),  # 1 lesson a week
        (60, 15, 2, 0, 30),
        (45, 15, 1, 1, 23),  # 1.5 a week → every week + odd weeks
    ],
)
def test_distribute_weekly(hours, weeks, weekly, alternating, total):
    d = distribute_weekly(hours, weeks)
    assert (d.weekly, d.alternating, d.total) == (weekly, alternating, total)


def test_group_name_default_pattern():
    assert group_name("IS", 3, 1) == "IS-301"
    assert group_name("IS-K", 2, 1) == "IS-K-201"


def test_group_name_pattern_is_configurable(settings):
    settings.GROUP_NAME_PATTERN = "{prefix}{course}{number:02d}"
    assert group_name("ИС", 3, 1) == "ИС301"
