"""A tiny in-memory academy for validator tests (no database).

Forms: 1 kunduzgi (weekly), 2 sirtqi (session 6–25 April 2026), 3 masofaviy (weekly, online).
Teaching weeks: 23 Feb – 6 Jun 2026; 6–11 April is week 7 (odd), 13–18 April week 8 (even).
"""

from datetime import date, time
from itertools import count

from apps.scheduling.services.occurrences import CalendarIndex
from apps.scheduling.validators import (
    AssignmentInfo,
    BlockedInfo,
    FormInfo,
    GroupInfo,
    LessonTimeInfo,
    Names,
    PeriodInfo,
    Placement,
    RoomInfo,
    ValidationContext,
)

DAY, SESSION, ONLINE = 1, 2, 3
WEEKS = (date(2026, 2, 23), date(2026, 6, 6))
DAYTIME = [
    (time(8, 30), time(9, 50), 1),
    (time(10, 0), time(11, 20), 1),
    (time(11, 30), time(12, 50), 1),
    (time(13, 30), time(14, 50), 2),
    (time(15, 0), time(16, 20), 2),
    (time(16, 30), time(17, 50), 2),
]
# lesson time id = form * 10 + number
LT = {(DAY, n): DAY * 10 + n for n in range(1, 7)}
LT.update({(SESSION, n): SESSION * 10 + n for n in range(1, 7)})
LT.update({(ONLINE, 1): 31, (ONLINE, 2): 32})

AUD, HALL, COMPUTER = 1, 2, 3
ROOM = {"A-101": 1, "Ma'ruza zali": 2, "Kompyuter": 3, "Yopiq": 4, "B-201": 5}
IS301, IS302, IS_S201, RU201, IS_M101 = 1, 2, 3, 4, 5
YUSUPOV, KARIMOV, AHMEDOV, BUSY = 100, 101, 102, 103

NAVRUZ = date(2026, 3, 21)
SESSION_DAY_OFF = date(2026, 4, 18)


def make_ctx(assignments: list[AssignmentInfo]) -> ValidationContext:
    forms = {
        DAY: FormInfo(DAY, "kunduzgi", "weekly", True, 4, frozenset(range(6)), {"uz": "Kunduzgi"}),
        SESSION: FormInfo(
            SESSION, "sirtqi", "session", True, 4, frozenset(range(6)), {"uz": "Sirtqi"}
        ),
        ONLINE: FormInfo(
            ONLINE, "masofaviy", "weekly", False, 2, frozenset(range(6)), {"uz": "Masofaviy"}
        ),
    }
    periods = {
        DAY: PeriodInfo(DAY, DAY, *WEEKS, 15),
        SESSION: PeriodInfo(SESSION, SESSION, date(2026, 4, 6), date(2026, 4, 25)),
        ONLINE: PeriodInfo(ONLINE, ONLINE, *WEEKS, 15),
    }
    lesson_times = {}
    for form in (DAY, SESSION):
        for n, (start, end, shift) in enumerate(DAYTIME, 1):
            lesson_times[LT[(form, n)]] = LessonTimeInfo(LT[(form, n)], form, n, start, end, shift)
    lesson_times[31] = LessonTimeInfo(31, ONLINE, 1, time(18, 30), time(19, 50))
    lesson_times[32] = LessonTimeInfo(32, ONLINE, 2, time(20, 0), time(21, 20))
    rooms = {
        1: RoomInfo(1, "A-101", 1, AUD, 30),
        2: RoomInfo(2, "Ma'ruza zali", 1, HALL, 100),
        3: RoomInfo(3, "Kompyuter", 1, COMPUTER, 15),
        4: RoomInfo(4, "Yopiq", 1, AUD, 30, is_active=False),
        5: RoomInfo(5, "B-201", 2, AUD, 30),
    }
    groups = {
        IS301: GroupInfo(IS301, "IS-301", DAY, "uz", 1, 27),
        IS302: GroupInfo(IS302, "IS-302", DAY, "uz", 1, 27),
        IS_S201: GroupInfo(IS_S201, "IS-S-201", SESSION, "uz", 1, 28),
        RU201: GroupInfo(RU201, "IS-R-201", DAY, "ru", 1, 20),
        IS_M101: GroupInfo(IS_M101, "IS-M-101", ONLINE, "uz", 1, 22),
    }
    return ValidationContext(
        forms=forms,
        periods=periods,
        lesson_times=lesson_times,
        rooms=rooms,
        groups=groups,
        assignments={a.id: a for a in assignments},
        blocked=[
            BlockedInfo(
                4,
                time(12, 0),
                time(14, 0),
                None,
                True,
                {"uz": "Juma namozi", "ru": "Пятничная молитва", "en": "Friday prayer"},
            ),
            BlockedInfo(None, time(15, 0), time(16, 20), None, False, {"uz": "Asr"}),
        ],
        calendar=CalendarIndex(days_off={NAVRUZ, SESSION_DAY_OFF}),
        holiday_names={NAVRUZ: {"uz": "Navro'z", "ru": "Навруз", "en": "Navruz"}},
        teacher_languages={
            YUSUPOV: frozenset({"uz", "ar"}),
            KARIMOV: frozenset({"uz"}),
            AHMEDOV: frozenset({"ru"}),
            BUSY: frozenset({"uz"}),
        },
        unavailable={BUSY: {(0, None), (1, LT[(DAY, 1)])}},
        preferred={KARIMOV: {(0, None), (1, None)}},
        names=Names(
            teachers={
                YUSUPOV: "Yusupov S.",
                KARIMOV: "Karimov B.",
                AHMEDOV: "Ахмедов Т.",
                BUSY: "Band B.",
            },
            subjects={
                1: {"uz": "Tafsir", "ru": "Тафсир", "en": "Tafsir"},
                2: {"uz": "Fiqh", "ru": "Фикх", "en": "Fiqh"},
                3: {"uz": "Arab tili", "ru": "Арабский язык", "en": "Arabic Language"},
            },
            lesson_types={
                "lecture": {"uz": "Ma'ruza", "ru": "Лекция", "en": "Lecture"},
                "seminar": {"uz": "Seminar", "ru": "Семинар", "en": "Seminar"},
                "practice": {
                    "uz": "Amaliy mashg'ulot",
                    "ru": "Практическое занятие",
                    "en": "Practical class",
                },
                "lab": {"uz": "Laboratoriya", "ru": "Лабораторная работа", "en": "Laboratory"},
            },
            room_types={
                AUD: {"uz": "Auditoriya", "ru": "Аудитория", "en": "Classroom"},
                COMPUTER: {
                    "uz": "Kompyuter xona",
                    "ru": "Компьютерный класс",
                    "en": "Computer lab",
                },
            },
            streams={7: "IS-301 + IS-302", 8: "IS-301 + IS-R-201"},
            languages={"ru": {"uz": "Ruscha", "ru": "Русский", "en": "Russian"}},
        ),
    )


_ids = count(1)


def asg(
    teacher=YUSUPOV,
    groups=(IS301,),
    *,
    period=DAY,
    lesson_type="lecture",
    subject=1,
    subgroup=None,
    stream=None,
    language="uz",
    students=None,
    room_type=None,
    weekly=1,
    alternating=0,
    total=15,
) -> AssignmentInfo:
    sizes = {IS301: 27, IS302: 27, IS_S201: 28, RU201: 20, IS_M101: 22}
    if students is None:
        students = 14 if subgroup else sum(sizes[g] for g in groups)
    return AssignmentInfo(
        id=next(_ids),
        period_id=period,
        teacher_id=teacher,
        subject_id=subject,
        lesson_type_code=lesson_type,
        group_ids=tuple(groups),
        student_count=students,
        language=language,
        subgroup_number=subgroup,
        stream_id=stream,
        required_room_type_id=room_type,
        weekly_lessons=weekly,
        alternating_lessons=alternating,
        total_lessons=total,
    )


def weekly(a, weekday, number, room="A-101", parity="every", key=None, form=DAY, url=""):
    return Placement(
        key=key or f"{a.id}:{weekday}:{number}:{parity}",
        assignment_id=a.id,
        lesson_time_id=LT[(form, number)],
        weekday=weekday,
        week_parity=parity,
        room_id=ROOM[room] if room else None,
        online_url=url,
    )


def dated(a, day, number, room="A-101", key=None, form=SESSION):
    return Placement(
        key=key or f"{a.id}:{day}:{number}",
        assignment_id=a.id,
        lesson_time_id=LT[(form, number)],
        date=day,
        room_id=ROOM[room] if room else None,
    )
