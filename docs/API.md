# API izohlari

To'liq interaktiv hujjat: http://localhost:8010/api/docs/ (Swagger, `drf-spectacular`).
Bu yerda asosiy qoidalar va jadval bilan ishlash tartibi qisqacha yozilgan.

## Umumiy

- **Kirish:** `POST /api/auth/login/` (`username`, `password`) → `access`, `refresh` (JWT).
  So'rovlarga `Authorization: Bearer <access>` qo'shiladi. Token yangilash: `POST /api/auth/refresh/`.
- **Til:** javob matnlari (xatolar, ziddiyat sabablari, fan va xona turi nomlari) `Accept-Language: uz | ru | en`
  sarlavhasiga qarab chiqadi. Tarjima qilinadigan nomlar uchun `name` (so'rov tilida, bo'lmasa o'zbekcha),
  `name_uz` (majburiy), `name_ru`, `name_en` maydonlari bor.
- **Profil:** `GET /api/auth/me/` foydalanuvchi, rol, ilova tili va talaba yoki o'qituvchi profilini qaytaradi.
  `PATCH /api/auth/me/ {"language": "ru"}` ilova tilini o'zgartiradi.
- **Ro'yxatlar:** sahifalanadi (`?page=`, `?page_size=` ≤ 1000), `?search=`, maydon bo'yicha filtr
  va `?ordering=` bor.

## Rollar

| Rol | Ko'radi | O'zgartiradi |
|---|---|---|
| `admin` (dispetcher) | hammasini | hammasini; jadvalni faqat u tahrirlaydi va e'lon qiladi |
| `dekanat` | ma'lumotnomalar, qoralamalar, ziddiyatlar; faqat o'z fakultetining talabalari | o'z fakultetining guruhlari, kichik guruhlari, oqimlari, talabalari, o'quv rejasi va yuklamasi |
| `kafedra_mudiri` | ma'lumotnomalar, qoralamalar, ziddiyatlar | o'z kafedrasining o'qituvchilari, ularning qulay vaqtlari va yuklamasi |
| `oqituvchi` | ma'lumotnomalar, o'z yuklamasi, **faqat e'lon qilingan** jadval | faqat o'zining qulay vaqtlari |
| `talaba` | ma'lumotnomalar, **faqat e'lon qilingan** jadval | hech narsa |

Huquqlar serverda tekshiriladi. Ruxsat yo'q bo'lsa `403` qaytadi, qoralama talaba uchun mavjud bo'lmagandek `404` bo'ladi.

## Ma'lumotnomalar (CRUD)

`/api/faculties/`, `departments/`, `education-levels/`, `education-forms/` (qo'ng'iroq jadvali bilan),
`lesson-times/`, `blocked-periods/`, `programs/`, `program-forms/`, `academic-years/`, `semesters/`,
`teaching-periods/`, `calendar-days/`, `buildings/`, `room-types/`, `rooms/`, `lesson-types/`, `subjects/`,
`curriculum/`, `groups/`, `subgroups/`, `streams/`, `teachers/`, `teacher-availability/`, `students/`,
`assignments/` (yuklama taqsimoti).

- `PUT /api/teacher-availability/replace/ {"teacher": id, "rows": [{"weekday", "lesson_time", "level"}]}`:
  o'qituvchining "Qulay kunlarim" jadvalini bir martada almashtiradi.
- **Excel import:** `rooms`, `subjects`, `teachers`, `groups`, `students`.
  - `GET …/import-template/` foydalanuvchi tilidagi sarlavhali shablonni beradi.
  - `POST …/import/` (multipart `file`) bilan to'ldirilgan shablon yuklanadi. Mavjud yozuvlar tabiiy kalit bo'yicha
    yangilanadi: xona — bino va nomi, fan — kodi, guruh — nomi, talaba — HEMIS ID.
  - Bitta qatorda xato bo'lsa hech narsa saqlanmaydi, javobda `{"errors": [{"row", "column", "message"}]}` qaytadi.

## Dars jadvali

| So'rov | Kim | Nima qiladi |
|---|---|---|
| `GET /api/schedules/` | hamma (talaba/o'qituvchi faqat e'lon qilinganini) | Versiyalar |
| `POST /api/schedules/ {"semester", "name", "based_on"?}` | admin | Yangi qoralama (yoki mavjud versiyadan nusxa) |
| `POST /api/schedules/{id}/publish/` | admin | E'lon qilish. Qat'iy ziddiyat bo'lsa `409` va ro'yxati qaytadi |
| `GET /api/schedules/{id}/conflicts/` | xodimlar | Ziddiyatlar: `code`, `constraint` (1–11), `entries`, `message` |
| `GET /api/schedules/{id}/unplaced/?group=&teacher=&form=` | xodimlar | Joylashtirilmagan darslar (muharrir yon paneli) |
| `GET /api/schedules/{id}/options/?entry=` yoki `?assignment=` | admin | To'rning har bir katagi: `ok`, sabablar, bo'sh xonalar |
| `POST /api/schedules/{id}/check/` | admin | O'zgarishni saqlamasdan tekshirish va kimga xabar ketishini sanash |
| `GET /api/schedules/{id}/changes/` | xodimlar | O'zgarishlar tarixi |
| `POST /api/schedules/{id}/undo/` | admin | Oxirgi o'zgarishlar to'plamini bekor qilish |
| `GET /api/schedules/{id}/stats/` | xodimlar | Yumshoq cheklovlar bali va reja bajarilishi |
| `POST /api/entries/` | admin | Dars qo'yish. Haftalik: `weekday` + `week_parity`, sirtqi: `date`, masofaviy: `online_url` |
| `PATCH /api/entries/{id}/` | admin | Darsni ko'chirish yoki xonasini almashtirish (`comment` xabarga qo'shiladi) |
| `DELETE /api/entries/{id}/` | admin | Darsni olib tashlash |
| `POST /api/entries/{id}/cancel/ {"date", "comment", "restore"?}` | admin | Bitta sanadagi darsni bekor qilish yoki tiklash |
| `GET /api/timetable/?group= \| teacher= \| room= \| me=1` | hamma | Haftalik yoki sessiya jadvali (`schedule=` faqat xodimlar uchun) |
| `GET /api/timetable/occurrences/?me=1&date_from=&date_to=` | hamma | Aniq sanalar bo'yicha darslar (bekor qilinganlari bilan) |
| `GET /api/export/?type=xlsx \| pdf&group= \| teacher= \| room= \| me=1&lang=` | hamma | Excel yoki PDF |
| `GET /api/dashboard/?form=` | xodimlar | Bosh sahifa raqamlari va fakultetlar bo'yicha tayyorlik |

**Tahrir qoidasi.** Har bir `POST` yoki `PATCH` saqlanishdan oldin validatordan o'tadi (11 ta qat'iy cheklov, `docs/ER.md`).
Ziddiyat bo'lsa `409` qaytadi, `violations[].message` so'rov tilida bo'ladi. `"dry_run": true` bo'lsa hech narsa saqlanmaydi.
Javobdagi `notify_students` va `notify_teachers` o'zgarish kimga xabar qilinishini bildiradi
(faqat e'lon qilingan jadval uchun, qoralamada 0). Har bir o'zgarish `ScheduleChange`ga yoziladi.
Bazadagi `EXCLUDE` cheklovlari validator ko'ra olmagan holatni ham ushlaydi, masalan bir vaqtdagi ikki tahrirni.

## Avtomatik tuzish (CP-SAT)

| So'rov | Kim | Nima qiladi |
|---|---|---|
| `POST /api/solver-runs/precheck/` | admin | Boshlashdan oldin tekshirish: nechta dars qo'yiladi, nimasi qo'yib bo'lmaydi va nega (hech narsa saqlanmaydi) |
| `POST /api/solver-runs/ {"faculty"?, "form"?, "base_schedule"?, "mode": "rebuild" \| "fill", "time_limit": 10–600, "seed"?, "weights"?}` | admin | Ishga tushirish (Celery navbatiga qo'yiladi) |
| `GET /api/solver-runs/` va `/{id}/` | xodimlar | Holat, jonli `progress` (bosqich, joylashtirilgan darslar, vaqt), natija raqamlari va izohlar (so'rov tilida) |
| `POST /api/solver-runs/{id}/cancel/` | admin | To'xtatish (1 soniya ichida to'xtaydi, natija saqlanmaydi) |
| `GET /api/solver-runs/{id}/compare/` | xodimlar | Natijani boshlang'ich versiya bilan solishtirish: darslar, joylashtirilmaganlar, ziddiyatlar, yumshoq ko'rsatkichlar, nechta dars ko'chdi |
| `GET /api/solver-runs/{id}/entries/` | xodimlar | Natija jadvali CSV ko'rinishida |
| `GET /api/solver-runs/export/` | xodimlar | Barcha ishga tushirishlar raqamlari CSV (sozlamalar va algoritmlarni solishtirish uchun) |

- `mode = rebuild`: tanlangan doiradagi darslar qaytadan qo'yiladi, qadalganlari qoladi. `fill`: mavjud darslar qoladi, faqat yetishmayotganlari qo'yiladi.
- Natija har doim yangi qoralama (`result_schedule`). Undagi har bir dars validatordan qayta o'tkaziladi, `hard_violations` shu tekshiruv natijasi.
- Buyruq qatoridan: `python manage.py run_solver --faculty ISL --time-limit 90`.

## Talaba va o'qituvchi ilovasi

| So'rov | Kim | Nima qiladi |
|---|---|---|
| `GET /api/meta/` | hamma | `today`, `now` (demo sana `DEMO_NOW` bilan), `demo_date` |
| `GET /api/timetable/occurrences/?me=1&date_from=&date_to=` | hamma | "Bugun" va "Hafta" ekranlari: aniq sanalar, bekor qilingan va bayramga tushgan darslar bilan |
| `GET /api/export/ics/?me=1 \| group= \| teacher= \| room=` | hamma | Butun davr `.ics` fayli (har bir sana alohida voqea, bekor qilinganlari `STATUS:CANCELLED`) |
| `GET /api/free-rooms/?date=&lesson_time=&capacity=` | o'qituvchi, xodimlar | Shu vaqtda e'lon qilingan jadvalda band bo'lmagan xonalar |
| `GET/PUT /api/teacher-availability/…` | o'qituvchi (o'ziniki) | "Qulay kunlarim" (yuqorida) |
| `GET /api/reschedule-requests/` | o'qituvchi (o'ziniki), xodimlar | Ko'chirish so'rovlari |
| `POST /api/reschedule-requests/ {"entry", "reason", "occurrence_date"?, "desired_weekday"?, "desired_lesson_time"?, "desired_note"?}` | o'qituvchi | O'z darsini ko'chirishni so'rash (faqat e'lon qilingan jadval) |
| `DELETE /api/reschedule-requests/{id}/` | o'qituvchi | Javob kutayotgan so'rovni qaytarib olish |
| `POST /api/reschedule-requests/{id}/review/ {"status": "approved" \| "rejected", "comment"?}` | admin | Javob berish (darsni muharrirda o'zi ko'chiradi) |

## Bildirishnomalar

| So'rov | Kim | Nima qiladi |
|---|---|---|
| `GET /api/notifications/?unread=1` | har kim (o'ziniki) | Xabarlar, eng yangisi birinchi. `was` / `now` — eski va yangi holat (masalan, xona) |
| `GET /api/notifications/unread-count/` | har kim | Qo'ng'iroqcha uchun o'qilmaganlar soni (ilova har 25 soniyada so'raydi) |
| `POST /api/notifications/{id}/read/`, `POST /api/notifications/read-all/` | har kim | O'qildi deb belgilash |
| `GET/PATCH /api/notifications/preferences/` | har kim | Qaysi xabarlar kelsin, eslatma (daqiqa), kechki xulosa |
| `GET /api/notifications/push/` | har kim | Push yoqilganmi va ochiq VAPID kaliti |
| `POST /api/notifications/push/ {"endpoint", "keys": {"p256dh", "auth"}}`, `DELETE … {"endpoint"}` | har kim | Shu qurilmani push uchun ro'yxatdan o'tkazish / o'chirish |

E'lon qilingan jadvaldagi har bir tahrir (`POST/PATCH/DELETE /api/entries/`, bitta sanani bekor qilish, undo) tranzaksiya saqlangach Celery vazifasiga beriladi.
U xabarni kerakli odamlarga ularning tilida yaratadi va Web Push yuboradi. Yangi jadval e'lon qilinsa va ko'chirish so'roviga javob berilsa ham xabar ketadi.
Celery beat har daqiqada eslatmalarni, soat 20:00 da ertangi xulosani yuboradi (`docker compose` ichidagi `beat` servisi).

## Hisobotlar

| So'rov | Kim | Nima qiladi |
|---|---|---|
| `GET /api/reports/plan/?schedule=&faculty=&type=json \| xlsx \| pdf&lang=` | xodimlar | O'quv reja bajarilishi: har bir yuklama bo'yicha rejadagi va haqiqiy sanalardagi darslar, yo'qotilganlari (bayram, bekor), farq |
| `GET /api/reports/teachers/?…` | xodimlar | O'qituvchilar yuklamasi: haftalik darslar va chegara, semestrdagi darslar va soatlar, me'yordan foiz |
| `GET /api/reports/rooms/?…` | xodimlar | Xonalar bandligi: haftalik vaqtlarning necha foizi band, o'rtacha to'lish, sessiya darslari |

`schedule` bo'lmasa e'lon qilingan jadval olinadi. Excel va PDF'da akademiya nomi, semestr, imzo joyi va izohlar bor.
Jadvalning o'zi uchun `GET /api/export/` (yuqorida) ishlatiladi.
