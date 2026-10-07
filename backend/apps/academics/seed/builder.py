"""Builds the deterministic demo dataset. Entry point: `build_demo(stdout)`."""

import math
import random
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from django.apps import apps
from django.contrib.auth.hashers import make_password
from django.db import connection, transaction
from django.utils import timezone
from django.utils.translation import override

from apps.accounts.models import Role, User
from apps.notifications.models import Notification, NotificationKind
from apps.notifications.rendering import render
from apps.scheduling.models import (
    ChangeAction,
    EntryOccurrence,
    OccurrenceStatus,
    Schedule,
    ScheduleChange,
    ScheduleEntry,
    ScheduleStatus,
)
from apps.scheduling.services.occurrences import CalendarIndex, sync_occurrences
from apps.scheduling.validators import describe, validate_schedule

from ..models import (
    HOURS_PER_CREDIT,
    HOURS_PER_LESSON,
    AcademicCalendarDay,
    AcademicYear,
    Academy,
    BlockedPeriod,
    Building,
    CurriculumItem,
    Department,
    EducationForm,
    EducationLevel,
    Faculty,
    Group,
    LessonTime,
    LessonType,
    Program,
    ProgramForm,
    Room,
    RoomType,
    Semester,
    Stream,
    Student,
    SubGroup,
    Subject,
    Teacher,
    TeacherAvailability,
    TeachingAssignment,
    TeachingPeriod,
)
from ..naming import group_name
from . import data as D

TYPE_LETTERS = {"L": "lecture", "P": "practice", "S": "seminar", "B": "lab"}
SEED_APPS = ("notifications", "solver", "scheduling", "academics", "accounts")


def names(triple) -> dict:
    uz, ru, en = triple
    return {"name_uz": uz, "name_ru": ru, "name_en": en}


def parse_plan(spec: str) -> dict[str, int]:
    """ "L1 S1" → {"lecture": 1, "seminar": 1}"""
    return {TYPE_LETTERS[part[0]]: int(part[1:]) for part in spec.split()}


def wipe() -> None:
    tables = [
        model._meta.db_table
        for label in SEED_APPS
        for model in apps.get_app_config(label).get_models(include_auto_created=True)
    ]
    with connection.cursor() as cursor:
        cursor.execute(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE")


class DemoBuilder:
    def __init__(self, stdout):
        self.out = stdout
        self.rng = random.Random(42)
        self.forms: dict[str, EducationForm] = {}
        self.lesson_times: dict[tuple[str, int], LessonTime] = {}
        self.room_types: dict[str, RoomType] = {}
        self.rooms: dict[str, Room] = {}
        self.lesson_types: dict[str, LessonType] = {}
        self.subjects: dict[str, Subject] = {}
        self.departments: dict[str, Department] = {}
        self.faculties: dict[str, Faculty] = {}
        self.programs: dict[str, Program] = {}
        self.program_forms: dict[tuple[str, str], ProgramForm] = {}
        self.groups: dict[str, Group] = {}
        self.teachers: dict[str, Teacher] = {}
        self.periods: dict[str, TeachingPeriod] = {}
        self.streams: dict[str, Stream] = {}
        self.stream_of: dict[str, tuple[Stream, list | None]] = {}
        self.assignments: dict[tuple, TeachingAssignment] = {}
        # teacher load bookkeeping: weekly lessons and semester hours
        self.weekly_load: dict[int, int] = defaultdict(int)
        self.semester_hours: dict[int, int] = defaultdict(int)
        self.teaches: dict[tuple[int, str], set[int]] = defaultdict(set)

    def log(self, msg: str) -> None:
        self.out.write(msg)

    # ------------------------------------------------------------------ structure
    def build_structure(self) -> None:
        self.academy = Academy.objects.create(**names(D.ACADEMY), short_name="O'XIA")
        for code, (triple, lang) in D.FACULTIES.items():
            self.faculties[code] = Faculty.objects.create(
                academy=self.academy, code=code, teaching_language=lang, **names(triple)
            )
        for code, (fac, triple) in D.DEPARTMENTS.items():
            self.departments[code] = Department.objects.create(
                faculty=self.faculties[fac], code=code, **names(triple)
            )
        levels = {
            code: EducationLevel.objects.create(code=code, **names(t))
            for code, t in D.LEVELS.items()
        }
        for order, (code, (triple, mode, room, per_day, days)) in enumerate(D.FORMS.items()):
            self.forms[code] = EducationForm.objects.create(
                code=code,
                schedule_mode=mode,
                requires_room=room,
                max_lessons_per_day=per_day,
                study_weekdays=days,
                order=order,
                **names(triple),
            )
        for form_code, rows in D.LESSON_TIMES.items():
            for number, start, end, shift in rows:
                self.lesson_times[(form_code, number)] = LessonTime.objects.create(
                    form=self.forms[form_code], number=number, start=start, end=end, shift=shift
                )
        for triple, weekday, start, end, hard in D.BLOCKED:
            BlockedPeriod.objects.create(
                weekday=weekday, start=start, end=end, is_hard=hard, **names(triple)
            )
        for code, (fac, level, prog_code, triple) in D.PROGRAMS.items():
            self.programs[code] = Program.objects.create(
                faculty=self.faculties[fac], level=levels[level], code=prog_code, **names(triple)
            )
        for prog, form, years, prefix in D.PROGRAM_FORMS:
            self.program_forms[(prog, form)] = ProgramForm.objects.create(
                program=self.programs[prog],
                form=self.forms[form],
                duration_years=Decimal(years),
                group_prefix=prefix,
            )

    def build_rooms(self) -> None:
        for code, triple in D.ROOM_TYPES.items():
            self.room_types[code] = RoomType.objects.create(code=code, **names(triple))
        buildings = {
            code: Building.objects.create(code=code, **names(t)) for code, t in D.BUILDINGS.items()
        }
        for bld, name, floor, rtype, cap, projector, computers in D.ROOMS:
            self.rooms[name] = Room.objects.create(
                building=buildings[bld],
                name=name,
                floor=floor,
                room_type=self.room_types[rtype],
                capacity=cap,
                has_projector=projector,
                computer_count=computers,
            )
        for order, (code, (triple, room_type)) in enumerate(D.LESSON_TYPES.items()):
            self.lesson_types[code] = LessonType.objects.create(
                code=code,
                order=order,
                default_room_type=self.room_types.get(room_type),
                **names(triple),
            )
        for code, (triple, dept, is_lang, room_type) in D.SUBJECTS.items():
            self.subjects[code] = Subject.objects.create(
                code=code,
                department=self.departments[dept],
                is_language=is_lang,
                practice_room_type=self.room_types.get(room_type),
                **names(triple),
            )

    # ------------------------------------------------------------------ calendar
    def build_calendar(self) -> None:
        name, start, end = D.ACADEMIC_YEAR
        year = AcademicYear.objects.create(name=name, start_date=start, end_date=end)
        Semester.objects.create(
            year=year, kind="autumn", start_date=D.AUTUMN[0], end_date=D.AUTUMN[1]
        )
        self.semester = Semester.objects.create(
            year=year, kind="spring", start_date=D.SPRING[0], end_date=D.SPRING[1], is_current=True
        )
        # Monday of week 1 + N weeks, ending on Saturday
        teaching_end = D.SPRING[0] + timedelta(days=D.SPRING_WEEKS * 7 - 2)
        for code in ("kunduzgi", "kechki", "masofaviy"):
            self.periods[code] = TeachingPeriod.objects.create(
                semester=self.semester,
                form=self.forms[code],
                name=f"{self.forms[code].name_uz}: {D.SPRING_WEEKS} hafta",
                start_date=D.SPRING[0],
                end_date=teaching_end,
                weeks_count=D.SPRING_WEEKS,
            )
        session_name, s_start, s_end = D.SESSION
        self.periods["sirtqi"] = TeachingPeriod.objects.create(
            semester=self.semester,
            form=self.forms["sirtqi"],
            name=session_name,
            start_date=s_start,
            end_date=s_end,
        )
        for day, kind, triple, weekday, assumption in D.CALENDAR:
            AcademicCalendarDay.objects.create(
                date=day,
                kind=kind,
                works_as_weekday=weekday,
                is_assumption=assumption,
                **names(triple),
            )

    # ------------------------------------------------------------------ curriculum
    def build_curriculum(self) -> None:
        self.curriculum: dict[tuple, list[CurriculumItem]] = defaultdict(list)
        for (prog, form, lang), semesters in D.WEEKLY_PLANS.items():
            weeks = self.periods[form].weeks_count
            for sem, subjects in semesters.items():
                for subj, spec in subjects.items():
                    hours = {lt: n * HOURS_PER_LESSON * weeks for lt, n in parse_plan(spec).items()}
                    classroom = sum(hours.values())
                    credits = max(2, math.ceil(classroom * 2 / HOURS_PER_CREDIT))
                    self._curriculum_item(prog, form, lang, sem, subj, hours, credits)
        for (prog, form, lang), semesters in D.SESSION_PLANS.items():
            for sem, subjects in semesters.items():
                for subj, (spec, credits) in subjects.items():
                    self._curriculum_item(prog, form, lang, sem, subj, parse_plan(spec), credits)

    def _curriculum_item(self, prog, form, lang, sem, subj, hours, credits) -> None:
        classroom = sum(hours.values())
        item = CurriculumItem.objects.create(
            program=self.programs[prog],
            form=self.forms[form],
            teaching_language=lang,
            study_semester=sem,
            subject=self.subjects[subj],
            credits=credits,
            hours_lecture=hours.get("lecture", 0),
            hours_practice=hours.get("practice", 0),
            hours_seminar=hours.get("seminar", 0),
            hours_lab=hours.get("lab", 0),
            hours_independent=credits * HOURS_PER_CREDIT - classroom,
            control_type="exam" if credits >= 4 else "credit",
        )
        self.curriculum[(prog, form, lang, sem)].append(item)

    def plan_for(self, group: Group) -> list[CurriculumItem]:
        """Language-specific plan if it exists, otherwise the general one."""
        pf = group.program_form
        prog = next(k for k, p in self.programs.items() if p.pk == pf.program_id)
        form = pf.form.code
        sem = group.study_semester("spring")
        return self.curriculum.get(
            (prog, form, group.teaching_language, sem)
        ) or self.curriculum.get((prog, form, "", sem), [])

    # ------------------------------------------------------------------ groups & people
    def build_groups(self) -> None:
        for prog, form, course, number, lang, count, comp, shift in D.GROUPS:
            pf = self.program_forms[(prog, form)]
            name = group_name(pf.group_prefix, course, number)
            self.groups[name] = Group.objects.create(
                program_form=pf,
                name=name,
                course=course,
                number=number,
                teaching_language=lang,
                student_count=count,
                gender_composition=comp,
                shift=shift,
            )
        for name, group_names, subjects in D.STREAMS:
            groups = [self.groups[g] for g in group_names]
            stream = Stream.objects.create(
                semester=self.semester,
                faculty=self.faculties["RUS" if groups[0].teaching_language == "ru" else "ISL"],
                name=name,
                teaching_language=groups[0].teaching_language,
            )
            stream.groups.set(groups)
            self.streams[name] = stream
            for g in group_names:
                self.stream_of[g] = (stream, subjects)

    def build_teachers(self) -> None:
        for row in D.TEACHERS:
            last, first, middle, dept, pos, degree, emp, hours, per_week, subjects, langs = row
            teacher = Teacher.objects.create(
                last_name=last,
                first_name=first,
                middle_name=middle,
                department=self.departments[dept],
                position=pos,
                degree=degree,
                employment=emp,
                annual_load_hours=hours,
                max_weekly_lessons=per_week,
                teaching_languages=langs,
            )
            teacher.subjects.set([self.subjects[s] for s in subjects])
            teacher.subject_codes = set(subjects)
            self.teachers[last] = teacher
        for last, weekday, number, level in D.AVAILABILITY:
            TeacherAvailability.objects.create(
                teacher=self.teachers[last],
                weekday=weekday,
                lesson_time=self.lesson_times[("kunduzgi", number)] if number else None,
                level=level,
            )

    def build_students(self) -> None:
        seq = 0
        students = []
        for group in self.groups.values():
            subgroups = [
                SubGroup.objects.create(group=group, number=n, student_count=c)
                for n, c in ((1, (group.student_count + 1) // 2), (2, group.student_count // 2))
            ]
            for i in range(group.student_count):
                seq += 1
                if group.name == "IS-301" and i == 0:
                    first, last, gender, middle = "Aziza", "Karimova", "f", "Akmal qizi"
                else:
                    first, last, gender, middle = self._random_person(group)
                students.append(
                    Student(
                        last_name=last,
                        first_name=first,
                        middle_name=middle,
                        hemis_id=f"36{group.program_form.program.code[-4:]}{seq:05d}",
                        group=group,
                        subgroup=subgroups[0 if i < subgroups[0].student_count else 1],
                        gender=gender,
                    )
                )
        Student.objects.bulk_create(students)

    def _random_person(self, group: Group) -> tuple[str, str, str, str]:
        comp = group.gender_composition
        gender = {"male": "m", "female": "f"}.get(comp) or self.rng.choice("mf")
        if group.teaching_language == "ru":
            first = self.rng.choice(D.RU_MALE_FIRST if gender == "m" else D.RU_FEMALE_FIRST)
            last = self.rng.choice(D.RU_SURNAMES)
            if gender == "f" and last[-1] in "вн":
                last += "а"
            return first, last, gender, ""
        first = self.rng.choice(D.MALE_FIRST if gender == "m" else D.FEMALE_FIRST)
        last = self.rng.choice(D.SURNAMES) + ("a" if gender == "f" else "")
        middle = self.rng.choice(D.UZ_MALE_PATRONYMIC if gender == "m" else D.UZ_FEMALE_PATRONYMIC)
        return first, last, gender, middle

    # ------------------------------------------------------------------ assignments
    def build_assignments(self) -> None:
        """Turn each group's plan into teaching assignments and pick teachers."""
        # Scarce combinations first: Russian-medium groups need the few Russian-speaking teachers.
        ordered = sorted(self.groups.values(), key=lambda g: g.teaching_language != "ru")
        for group in ordered:
            form = group.program_form.form
            period = self.periods[form.code]
            sem = group.study_semester("spring")
            for item in self.plan_for(group):
                for lt_code in ("lecture", "seminar", "practice", "lab"):
                    hours = item.hours_for(lt_code)
                    if not hours:
                        continue
                    target = self._target(group, item.subject.code, lt_code, sem, form.code)
                    for target_kind, target_obj in target:
                        key = (target_kind, target_obj.pk, item.subject.code, lt_code)
                        if key in self.assignments:
                            continue  # stream lecture already created via the partner group
                        self._assign(
                            key, period, item, lt_code, hours, target_kind, target_obj, group
                        )

    def _target(self, group, subj, lt_code, sem, form_code):
        if lt_code == "lecture" and group.name in self.stream_of:
            stream, subjects = self.stream_of[group.name]
            if subjects is None or subj in subjects:
                return [("stream", stream)]
        if form_code == "kunduzgi" and sem in D.SPLIT.get((subj, lt_code), ()):
            return [("subgroup", sg) for sg in group.subgroups.order_by("number")]
        return [("group", group)]

    def _assign(self, key, period, item, lt_code, hours, target_kind, target_obj, group) -> None:
        total = hours // HOURS_PER_LESSON
        weekly = total // period.weeks_count if period.weeks_count else 0
        teacher = self._pick_teacher(group, item.subject.code, lt_code, weekly, hours, key)
        lesson_type = self.lesson_types[lt_code]
        room_type = lesson_type.default_room_type
        if lt_code in ("practice", "lab") and item.subject.practice_room_type_id:
            room_type = item.subject.practice_room_type
        self.assignments[key] = TeachingAssignment.objects.create(
            period=period,
            teacher=teacher,
            subject=item.subject,
            lesson_type=lesson_type,
            curriculum_item=item,
            **{target_kind: target_obj},
            weekly_lessons=weekly,
            alternating_lessons=0,
            total_lessons=total,
            required_room_type=room_type,
        )
        self.weekly_load[teacher.pk] += weekly
        self.semester_hours[teacher.pk] += hours
        self.teaches[(teacher.pk, item.subject.code)].add(group.pk)

    def _pick_teacher(self, group, subj, lt_code, weekly, hours, key) -> Teacher:
        fixed = D.FIXED_TEACHERS.get((group.name, subj, lt_code))
        if key[0] == "stream":
            stream = self.streams_by_pk[key[1]]
            fixed = fixed or next(
                (
                    D.FIXED_TEACHERS[(g.name, subj, lt_code)]
                    for g in stream.groups.all()
                    if (g.name, subj, lt_code) in D.FIXED_TEACHERS
                ),
                None,
            )
        if fixed:
            return self.teachers[fixed]

        def fits(t: Teacher) -> bool:
            return (
                subj in t.subject_codes
                and t.can_teach_in(group.teaching_language)
                and self.weekly_load[t.pk] + weekly <= t.max_weekly_lessons
                and self.semester_hours[t.pk] + hours <= t.annual_load_hours // 2
            )

        candidates = [t for t in self.teachers.values() if fits(t)]
        if not candidates:
            raise RuntimeError(f"No teacher available for {group.name} {subj} {lt_code}")
        # Prefer the teacher who already teaches this subject to the group, then teachers of
        # the group's own faculty, then the least loaded one, so the load is spread evenly.
        faculty_id = group.program_form.program.faculty_id

        def key(t: Teacher):
            return (
                group.pk not in self.teaches[(t.pk, subj)],
                t.department.faculty_id != faculty_id,
                self.weekly_load[t.pk] / t.max_weekly_lessons,
                t.last_name,
            )

        return min(candidates, key=key)

    # ------------------------------------------------------------------ users
    def build_users(self) -> None:
        unusable = make_password(None)
        users = []
        teacher_users = {}
        for teacher in self.teachers.values():
            username = f"t{teacher.pk:03d}"
            teacher_users[teacher.pk] = User(
                username=username,
                first_name=teacher.first_name,
                last_name=teacher.last_name,
                role=Role.OQITUVCHI,
                password=unusable,
            )
        users.extend(teacher_users.values())
        students = list(Student.objects.select_related("group"))
        student_users = {
            s.pk: User(
                username=s.hemis_id,
                first_name=s.first_name,
                last_name=s.last_name,
                role=Role.TALABA,
                language="ru" if s.group.teaching_language == "ru" else "uz",
                language_auto=s.group.teaching_language != "ru",
                password=unusable,
            )
            for s in students
        }
        users.extend(student_users.values())
        User.objects.bulk_create(users)
        for teacher in self.teachers.values():
            teacher.user = teacher_users[teacher.pk]
        Teacher.objects.bulk_update(self.teachers.values(), ["user"])
        for s in students:
            s.user = student_users[s.pk]
        Student.objects.bulk_update(students, ["user"], batch_size=500)

        # Demo accounts (README).
        pw = {k: make_password(v) for k, v in D.DEMO_PASSWORDS.items()}
        User.objects.create(
            username="admin",
            first_name="Dispetcher",
            role=Role.ADMIN,
            is_staff=True,
            is_superuser=True,
            password=pw["admin"],
        )
        User.objects.create(
            username="dekanat",
            first_name="Dekanat",
            last_name="Islomshunoslik",
            role=Role.DEKANAT,
            faculty=self.faculties["ISL"],
            password=pw["dekanat"],
        )
        head = self.teachers["Ibragimov"]
        User.objects.filter(pk=head.user_id).update(
            username="kafedra",
            role=Role.KAFEDRA_MUDIRI,
            faculty=self.faculties["ISL"],
            department=head.department,
            password=pw["kafedra"],
        )
        User.objects.filter(pk=self.teachers["Yusupov"].user_id).update(
            username="oqituvchi", password=pw["oqituvchi"]
        )
        aziza = Student.objects.get(group__name="IS-301", first_name="Aziza", last_name="Karimova")
        User.objects.filter(pk=aziza.user_id).update(username="talaba", password=pw["talaba"])
        ru_student = Student.objects.filter(group__name="IS-R-201").order_by("pk").first()
        User.objects.filter(pk=ru_student.user_id).update(
            username="talaba_ru", password=pw["talaba_ru"], language="ru", language_auto=False
        )

    # ------------------------------------------------------------------ IS-301 timetable
    def build_schedule(self) -> None:
        self.schedule = Schedule.objects.create(
            semester=self.semester,
            name="2025-2026 bahorgi semestr",
            status=ScheduleStatus.PUBLISHED,
            published_at=timezone.make_aware(datetime(2026, 2, 20, 9, 0)),
        )
        stream = self.stream_of["IS-301"][0]
        self.entries: dict[tuple[int, int], ScheduleEntry] = {}
        rows = [
            (wd, n, subj, lt, room, t, target, "IS-301")
            for wd, n, subj, lt, room, t, target in D.IS301_WEEK
        ]
        rows += [
            (wd, n, subj, lt, room, t, "group", g) for wd, n, g, subj, lt, room, t in D.EXTRA_PINNED
        ]
        for wd, number, subj, lt, room, _teacher, target, group_name_ in rows:
            group = self.groups[group_name_]
            key = (
                ("stream", stream.pk, subj, lt)
                if target == "stream"
                else ("group", group.pk, subj, lt)
            )
            entry = ScheduleEntry.objects.create(
                schedule=self.schedule,
                assignment=self.assignments[key],
                lesson_time=self.lesson_times[("kunduzgi", number)],
                weekday=wd,
                week_parity="every",
                room=self.rooms[room],
                is_locked=True,
            )
            if group_name_ == "IS-301":
                self.entries[(wd, number)] = entry
        entries = ScheduleEntry.objects.select_related(
            "lesson_time",
            "assignment__period",
            "assignment__stream",
            "assignment__group",
            "assignment__subgroup__group",
        )
        self.occurrences = sync_occurrences(entries, CalendarIndex.load())

    # ------------------------------------------------------------------ changes & notifications
    def build_notifications(self) -> None:
        semester_names = {
            lang: f"2025-2026, {self._t(lang, 'Spring semester').lower()}"
            for lang in ("uz", "ru", "en")
        }
        is301 = self.groups["IS-301"]
        students = list(User.objects.filter(student__group=is301))
        aqida = self.entries[(3, 3)]
        tafsir_sem = self.entries[(0, 2)]

        def subject_names(entry):
            s = entry.assignment.subject
            return {"uz": s.name_uz, "ru": s.name_ru, "en": s.name_en}

        def teacher_user(entry):
            return User.objects.get(teacher=entry.assignment.teacher)

        published_at = self.schedule.published_at
        all_teachers = list(
            User.objects.filter(teacher__assignments__entries__schedule=self.schedule).distinct()
        )
        self._notify(
            students + all_teachers,
            NotificationKind.SCHEDULE_PUBLISHED,
            {"semester": semester_names},
            key=f"published:{self.schedule.pk}",
            created=published_at,
            read=True,
        )

        # 1) Tafsir seminar moved A-201 → A-204 (earlier, already read)
        c1 = self._change(
            tafsir_sem,
            {"room": "A-201"},
            {"room": "A-204"},
            created=timezone.make_aware(datetime(2026, 4, 1, 16, 5)),
        )
        self._notify(
            students + [teacher_user(tafsir_sem)],
            NotificationKind.ROOM_CHANGED,
            {
                "when": {"weekday": 0},
                "number": 2,
                "subject": subject_names(tafsir_sem),
                "old_room": "A-201",
                "new_room": "A-204",
            },
            key=f"change:{c1.pk}",
            created=c1.created_at,
            read=True,
            entry=tafsir_sem,
            change=c1,
        )
        # 2) Aqida lecture moved Ma'ruza zali 2 → A-115 (the design's yellow notice; unread)
        c2 = self._change(
            aqida,
            {"room": "Ma'ruza zali 2"},
            {"room": "A-115"},
            created=timezone.make_aware(datetime(2026, 4, 7, 18, 40)),
        )
        self._notify(
            students + [teacher_user(aqida)],
            NotificationKind.ROOM_CHANGED,
            {
                "when": {"weekday": 3},
                "number": 3,
                "subject": subject_names(aqida),
                "old_room": "Ma'ruza zali 2",
                "new_room": "A-115",
            },
            key=f"change:{c2.pk}",
            created=c2.created_at,
            read=False,
            entry=aqida,
            change=c2,
        )
        # 3) One Tafsir seminar cancelled: teacher ill (students unread, teacher read)
        cancel_day = datetime(2026, 4, 13).date()
        EntryOccurrence.objects.filter(entry=tafsir_sem, date=cancel_day).update(
            status=OccurrenceStatus.CANCELLED
        )
        c3 = self._change(
            tafsir_sem,
            {"status": "scheduled"},
            {"status": "cancelled"},
            created=timezone.make_aware(datetime(2026, 4, 8, 8, 12)),
            action=ChangeAction.CANCEL,
            occurrence_date=cancel_day,
            comment="O'qituvchi kasal",
        )
        params = {
            "when": {"date": cancel_day.isoformat()},
            "number": 2,
            "subject": subject_names(tafsir_sem),
        }
        self._notify(
            students,
            NotificationKind.CANCELLED,
            params,
            key=f"change:{c3.pk}",
            created=c3.created_at,
            read=False,
            entry=tafsir_sem,
            change=c3,
            comment=c3.comment,
        )
        self._notify(
            [teacher_user(tafsir_sem)],
            NotificationKind.CANCELLED,
            params,
            key=f"change:{c3.pk}",
            created=c3.created_at,
            read=True,
            entry=tafsir_sem,
            change=c3,
            comment=c3.comment,
        )

    @staticmethod
    def _t(lang: str, msgid: str) -> str:
        from django.utils.translation import gettext

        with override(lang):
            return gettext(msgid)

    def _change(
        self,
        entry,
        before,
        after,
        created,
        action=ChangeAction.UPDATE,
        occurrence_date=None,
        comment="",
    ):
        change = ScheduleChange.objects.create(
            schedule=self.schedule,
            entry=entry,
            batch=uuid.UUID(int=self.rng.getrandbits(128)),
            action=action,
            before=before,
            after=after,
            occurrence_date=occurrence_date,
            comment=comment,
            notified=True,
        )
        ScheduleChange.objects.filter(pk=change.pk).update(created_at=created)
        change.created_at = created
        return change

    def _notify(self, users, kind, params, key, created, read, entry=None, change=None, comment=""):
        rows = []
        for user in users:
            title, body = render(kind, params, user.language)
            rows.append(
                Notification(
                    recipient=user,
                    kind=kind,
                    params=params,
                    language=user.language,
                    title=title,
                    body=body,
                    comment=comment,
                    entry=entry,
                    change=change,
                    dedup_key=key,
                    is_read=read,
                    read_at=created if read else None,
                )
            )
        created_rows = Notification.objects.bulk_create(rows)
        Notification.objects.filter(pk__in=[n.pk for n in created_rows]).update(created_at=created)

    # ------------------------------------------------------------------ run
    def run(self) -> dict:
        self.build_structure()
        self.build_rooms()
        self.build_calendar()
        self.build_curriculum()
        self.build_groups()
        self.streams_by_pk = {s.pk: s for s in self.streams.values()}
        self.build_teachers()
        self.build_students()
        self.build_assignments()
        self.build_users()
        self.build_schedule()
        self.build_notifications()
        self.check_schedule()
        return self.summary()

    def check_schedule(self) -> None:
        """Section 7: the seeded timetable must have zero hard conflicts."""
        report, ctx, placements = validate_schedule(self.schedule)
        if report.conflicts:
            reasons = "\n".join(describe(v, ctx, placements) for v in report.conflicts)
            raise RuntimeError(f"Seeded timetable has conflicts:\n{reasons}")
        self.hard_conflicts = len(report.conflicts)
        self.not_placed = sum(
            v.params["required"] - v.params["placed"]
            for v in report.violations
            if v.is_completeness
        )

    def summary(self) -> dict:
        return {
            "faculties": Faculty.objects.count(),
            "departments": Department.objects.count(),
            "programs": Program.objects.count(),
            "groups": Group.objects.count(),
            "streams": Stream.objects.count(),
            "students": Student.objects.count(),
            "teachers": Teacher.objects.count(),
            "rooms": Room.objects.count(),
            "subjects": Subject.objects.count(),
            "curriculum items": CurriculumItem.objects.count(),
            "teaching assignments": TeachingAssignment.objects.count(),
            "weekly lessons to place": sum(
                a.weekly_lessons
                for a in TeachingAssignment.objects.filter(period__weeks_count__isnull=False)
            ),
            "session lessons to place": sum(
                a.total_lessons
                for a in TeachingAssignment.objects.filter(period__weeks_count__isnull=True)
            ),
            "timetable entries (pinned)": ScheduleEntry.objects.count(),
            "hard conflicts (validator)": self.hard_conflicts,
            "lessons not yet placed": self.not_placed,
            "lesson occurrences": EntryOccurrence.objects.count(),
            "calendar days": AcademicCalendarDay.objects.count(),
            "users": User.objects.count(),
            "notifications": Notification.objects.count(),
        }


@transaction.atomic
def build_demo(stdout) -> dict:
    wipe()
    return DemoBuilder(stdout).run()
