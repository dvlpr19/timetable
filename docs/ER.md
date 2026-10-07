# Ma'lumotlar modeli (ER-diagramma)

Tizim to'rtta Django ilovasidan iborat: `academics` (tuzilma, odamlar, o'quv reja, yuklama),
`scheduling` (jadval versiyalari va darslar), `solver` (avtomatik tuzish) va `notifications` (xabarlar).
`name` maydonlari uch tilda saqlanadi: `name_uz` (majburiy), `name_ru`, `name_en`.

## 1. Tuzilma va o'quv reja

```mermaid
erDiagram
    Academy ||--o{ Faculty : ""
    Faculty ||--o{ Department : "kafedralar"
    Faculty ||--o{ Program : "yo'nalishlar"
    EducationLevel ||--o{ Program : ""
    Program ||--o{ ProgramForm : "shakllar bo'yicha"
    EducationForm ||--o{ ProgramForm : ""
    EducationForm ||--o{ LessonTime : "qo'ng'iroq jadvali"
    EducationForm |o--o{ BlockedPeriod : "juma namozi va h.k."
    ProgramForm ||--o{ Group : ""
    Group ||--o{ SubGroup : "kichik guruhlar"
    Group ||--o{ Student : ""
    SubGroup |o--o{ Student : ""
    Stream }o--o{ Group : "oqim"
    Program ||--o{ CurriculumItem : "o'quv reja"
    EducationForm ||--o{ CurriculumItem : ""
    Subject ||--o{ CurriculumItem : ""
    Department |o--o{ Subject : ""
    Department ||--o{ Teacher : ""
    Teacher }o--o{ Subject : "o'ta oladigan fanlar"
    Teacher ||--o{ TeacherAvailability : "qulay vaqtlar"
    RoomType ||--o{ Room : ""
    Building ||--o{ Room : ""

    Faculty {
        string code UK
        string name
        string teaching_language "asosiy ta'lim tili"
    }
    EducationForm {
        string code UK "kunduzgi/kechki/sirtqi/masofaviy"
        string schedule_mode "weekly | session"
        bool requires_room "masofaviyda false"
        int max_lessons_per_day
        int_list study_weekdays
    }
    ProgramForm {
        decimal duration_years
        string group_prefix "IS, IS-K, IS-S ..."
    }
    LessonTime {
        int number "1-dars ..."
        time start
        time end
        int shift "1 | 2"
    }
    BlockedPeriod {
        int weekday "bo'sh = har kuni"
        time start
        time end
        bool is_hard "qat'iy / yumshoq"
    }
    Group {
        string name UK "IS-301"
        int course
        string teaching_language "uz/ru/en/ar"
        int student_count
        string gender_composition "ixtiyoriy"
        int shift
    }
    Stream {
        string name
        string teaching_language "guruhlarniki bilan bir xil"
    }
    CurriculumItem {
        string teaching_language "bo'sh = umumiy reja"
        int study_semester
        int credits "1 kredit = 30 soat (CHECK)"
        int hours_lecture
        int hours_practice
        int hours_seminar
        int hours_lab
        int hours_independent
        string control_type "imtihon / sinov"
    }
    Teacher {
        string position
        string degree
        string employment "shtat / o'rindosh / soatbay"
        int annual_load_hours
        int max_weekly_lessons
        string_list teaching_languages
    }
    TeacherAvailability {
        int weekday
        string level "qulay / mumkin / mumkin emas"
    }
    Room {
        string name "A-115"
        int floor
        int capacity
        int computer_count
    }
```

## 2. Kalendar, yuklama va jadval

```mermaid
erDiagram
    AcademicYear ||--o{ Semester : ""
    Semester ||--o{ TeachingPeriod : ""
    EducationForm ||--o{ TeachingPeriod : ""
    TeachingPeriod ||--o{ TeachingAssignment : ""
    Teacher ||--o{ TeachingAssignment : ""
    Subject ||--o{ TeachingAssignment : ""
    LessonType ||--o{ TeachingAssignment : ""
    CurriculumItem |o--o{ TeachingAssignment : "reja bajarilishi"
    Group |o--o{ TeachingAssignment : "yoki"
    Stream |o--o{ TeachingAssignment : "yoki"
    SubGroup |o--o{ TeachingAssignment : "yoki (aynan bittasi, CHECK)"
    Semester ||--o{ Schedule : "versiyalar"
    Schedule ||--o{ ScheduleEntry : ""
    TeachingAssignment ||--o{ ScheduleEntry : ""
    LessonTime ||--o{ ScheduleEntry : ""
    Room |o--o{ ScheduleEntry : "masofaviyda yo'q"
    ScheduleEntry ||--o{ EntryOccurrence : "aniq sanalar"
    Schedule ||--o{ ScheduleChange : "tarix"
    ScheduleEntry |o--o{ ScheduleChange : ""
    ScheduleEntry ||--o{ RescheduleRequest : "o'qituvchi so'rovi"
    AcademicCalendarDay }o..o{ EntryOccurrence : "bayram → ko'chirilishi kerak"

    TeachingPeriod {
        date start_date
        date end_date
        int weeks_count "faqat haftalik shakllar"
    }
    AcademicCalendarDay {
        date date UK
        string kind "bayram / dam olish / ko'chirilgan ish kuni"
        int works_as_weekday
        bool is_assumption "hayit sanalari"
    }
    TeachingAssignment {
        int weekly_lessons
        int alternating_lessons "toq/juft haftada"
        int total_lessons
    }
    Schedule {
        string status "draft / published / archived"
        datetime published_at
    }
    ScheduleEntry {
        int weekday "haftalik shakllar"
        string week_parity "every / odd / even"
        date date "sirtqi sessiya"
        string online_url "masofaviy"
        bool is_locked "solver qimirlatmaydi"
    }
    EntryOccurrence {
        date date
        tstzrange during
        int_list slot_keys "guruh*10 + kichik guruh"
        string status "scheduled / cancelled / reschedule"
    }
    ScheduleChange {
        uuid batch "bekor qilish uchun"
        string action
        json before
        json after
        date occurrence_date
        string comment
    }
```

**Ziddiyatlardan baza darajasida himoya.** Har bir `ScheduleEntry` aniq sanali darslarga
(`EntryOccurrence`) yoyiladi, shuning uchun haftalik va sessiya darslari bitta vaqt o'qida solishtiriladi.
`EntryOccurrence` jadvalida uchta `EXCLUDE USING gist` cheklovi bor (faqat `status = 'scheduled'` uchun):

| Cheklov | Ifoda |
|---|---|
| O'qituvchi | `schedule_id WITH =, teacher_id WITH =, during WITH &&` |
| Xona | `schedule_id WITH =, room_id WITH =, during WITH &&` (xona bo'lsa) |
| Guruh | `schedule_id WITH =, slot_keys WITH &&, during WITH &&` |

`slot_keys`: butun guruh o'zining barcha kichik guruh "o'rinlarini" egallaydi, kichik guruh esa faqat
o'zinikini. Natijada bir guruhning ikki kichik guruhi bir vaqtda o'qiy oladi, lekin butun guruh darsi
ular bilan to'qnashadi. Toq va juft hafta darslarining sanalari kesishmaydi, shu sababli ular ziddiyat emas.

## 3. Avtomatik tuzish va xabarlar

```mermaid
erDiagram
    Semester ||--o{ SolverRun : ""
    Schedule |o--o{ SolverRun : "natija qoralamasi"
    User ||--o{ Notification : ""
    ScheduleEntry |o--o{ Notification : ""
    ScheduleChange |o--o{ Notification : ""
    User ||--o{ PushSubscription : ""
    User ||--o| NotificationPreference : ""
    User |o--o| Teacher : ""
    User |o--o| Student : ""

    User {
        string role "admin/dekanat/kafedra_mudiri/oqituvchi/talaba"
        string language "ilova tili: uz/ru/en"
        fk faculty "dekanat doirasi"
        fk department "kafedra doirasi"
    }
    SolverRun {
        string algorithm "cpsat (keyin: genetic)"
        json params "og'irliklar, vaqt limiti"
        string status
        float objective
        int lessons_placed
        int hard_violations
        json soft_violations
        json diagnostics "yechim yo'q bo'lsa sabablar"
    }
    Notification {
        string kind
        json params "tilga bog'liq bo'lmagan faktlar"
        string language
        string title
        string body
        string dedup_key "recipient bilan UNIQUE"
        bool is_read
    }
```
