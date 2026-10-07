# Dars Jadvali — 1-versiya rejasi

**Holat:** 9 bosqichning hammasi bajarilgan (har biri alohida commit: `git log`).

Loyiha ildizi: `lesschedule/` (promptdagi `dars-jadvali/` shu papka). Har bir bosqich oxirida:
`make test` yashil, `docker compose up` ishlaydi, `git commit`, so'ng 5–10 qatorlik hisobot.

## Umumiy arxitektura

- **Servislar (docker-compose):** `postgres:16` (+`btree_gist`), `redis:7`, `backend` (Django 5 + DRF + gunicorn/runserver), `worker` (Celery: solver va bildirishnomalar), `beat` (eslatmalar, ertangi xulosa), `frontend` (Vite dev server; prod uchun nginx statik).
- **Backend ilovalari:** `accounts` (User, rollar, til tanlovi), `academics` (tuzilma, odamlar, xonalar, o'quv reja, yuklama, kalendar), `scheduling` (Schedule, ScheduleEntry, validators.py, o'zgarishlar tarixi, eksport), `solver` (BaseSolver → CpSatSolver, SolverRun), `notifications` (Notification, kanallar: InAppChannel, WebPushChannel; keyin TelegramChannel).
- **Vaqtni yagona ko'rinishga keltirish (ziddiyat yadrosi):** har bir `ScheduleEntry` saqlanayotganda hisoblanadigan `occupancy` qatorlari yaratiladi — aniq sana + `tstzrange` (dars boshlanishi–tugashi). Haftalik dars davr haftalari bo'yicha (juft/toq hafta, bayramlarni hisobga olib) sanalarga yoyiladi, sirtqi dars esa o'z sanasida. Shu tufayli:
  - kunduzgi seshanba 2-dars va sirtqi 15-aprel 10:00 darsi bitta jadvalda solishtiriladi;
  - toq va juft hafta darslari sanalari kesishmaydi → ziddiyat emas;
  - `EXCLUDE USING gist (teacher_id WITH =, during WITH &&)` va xona/guruh uchun xuddi shunday cheklovlar bazada ishlaydi (faqat e'lon qilingan/faol versiya qatorlari uchun, qoralamalar o'zaro to'qnashmasligi uchun `schedule_id` ham kalitda).
  - Guruh/kichik guruh qoidasi: occupancy'da `group_id` + `subgroup_no` (0 = butun guruh); EXCLUDE "bir xil guruh va (butun guruh yoki bir xil kichik guruh)" mantiqini massiv/sun'iy kalit orqali beradi — aniq texnika 3-bosqichda testlar bilan tasdiqlanadi.
- **Validator** (`scheduling/validators.py`): 11 ta qat'iy cheklov, sof Python, bazaga bog'liq bo'lmagan ma'lumot tuzilmalari ustida ishlaydi → qo'lda tahrir, Excel import, solver natijasi va seed uchun bitta kod.
- **i18n:** frontend `react-i18next` (`locales/{uz,ru,en}/*.json`), backend `gettext` + `django-modeltranslation` (`name_uz/ru/en`, fallback → uz), `Accept-Language` middleware, foydalanuvchi profilida `language`. Kalitlar mosligini tekshiruvchi test (vitest + pytest).
- **Dizayn:** Tailwind tokenlari (6.1-bo'lim) nom bilan, Manrope, `lucide-react`, qorong'i rejim (`prefers-color-scheme`). Figma MCP ulangan — har ekranni bir marta o'qiymiz.

## Bosqichlar

### 1. Loyiha skeleti
- Git repo, `.gitignore`, `.env.example`, `docker-compose.yml`, `Makefile` (`up`, `down`, `seed`, `test`, `lint`, `migrate`).
- Django loyihasi (`config/` settings: base/dev/test), DRF, simplejwt, drf-spectacular (`/api/docs/`), Celery + Redis, health endpoint.
- React + TS + Vite, Router, TanStack Query, Tailwind (tokenlar), i18next, til almashtirgich `UZ · RU · EN`, kirish sahifasi qobig'i.
- ruff, eslint, prettier, pytest, vitest; tarjima kalitlari mosligi testi.
- **Tekshirish:** `make up` → `localhost:5173` ochiladi, til almashadi; `/api/docs/` ishlaydi; `make test` yashil.

### 2. Ma'lumotlar modeli + seed
- 4-bo'limdagi barcha modellar (+ `EntryOccupancy`), migratsiyalar, `btree_gist`, CHECK/UNIQUE/EXCLUDE.
- Django admin, `docs/ER.md` (Mermaid), `docs/ASSUMPTIONS.md`.
- `manage.py seed_demo` (`random.seed(42)`): 2 fakultet, ~25 guruh, ~450 talaba, ~30 o'qituvchi, ~28 xona, o'quv reja, yuklama, kalendar, demo foydalanuvchilar, IS-301 qo'lda jadvali (e'lon qilingan), namuna xabarlar.
- **Tekshirish:** `make seed` xatosiz, sonlar chop etiladi.

### 3. Validator + testlar
- 11 qat'iy cheklov + yumshoq cheklov ballari; haftalik soni hisoblash (1,5 → "har hafta 1 + toq haftada 1").
- Har cheklov uchun "buziladi/buzilmaydi" testlari, shakllararo, juft/toq, sirtqi sana × kunduzgi hafta kuni testlari, EXCLUDE cheklovlari testlari.
- Seed oxirida validator → 0 ziddiyat.

### 4. REST API
- CRUD + qidiruv/filtr + Excel import, jadval (guruh/o'qituvchi/xona bo'yicha), ziddiyatlar, "bu katakka qo'ysa bo'ladimi" endpoint (drag paytida yashil/qizil), e'lon qilish, o'zgarishlar tarixi/undo, `.ics`, eksport (Excel/PDF, til tanlovi).
- Rol huquqlari backendda (admin, dekanat, kafedra_mudiri, oqituvchi, talaba) + ruxsat testlari.

### 5. Admin panel
- Kirish (HEMIS tugmasi o'chirilgan), bosh sahifa (statistika, ziddiyatlar, tayyorlik %), ma'lumot bo'limlari, qo'ng'iroq jadvallari, kalendar.
- Jadval muharriri: haftalik / sessiya to'ri, @dnd-kit, yon panel, yashil/qizil kataklar, tooltip sabablari, juma qulfi, pin, tarix, undo, xabar qilinadiganlar soni bilan tasdiqlash oynasi.

### 6. Avtomatik tuzish (CP-SAT)
- Oldindan filtrlash, `x[birlik, vaqt, xona]` (masofaviyda xonasiz), qat'iy + og'irlikli yumshoq cheklovlar, qulflangan darslar, oldindan tekshiruvlar va assumption'lar bilan tushunarli sabablar.
- Celery vazifa, progress (callback → SolverRun), qoralama versiya, joriy bilan solishtirish, CSV eksport.
- **Tekshirish:** demo fakultet uchun ≤2 daqiqada 0 qat'iy ziddiyat.

### 7. Mobil sahifalar + PWA
- Talaba: Bugun, Hafta (sirtqida sessiya kunlari), Dars tafsiloti, qidiruv, offline kesh ("oxirgi yangilanish").
- O'qituvchi: Bugun, Mening haftam (hamma shakllar), Qulay kunlarim (3 holat), ko'chirish so'rovi, bo'sh xona topish, PDF/.ics.

### 8. Bildirishnomalar
- Notification + PushSubscription + NotificationPreference, kanallar, Celery, dublikatsiz yuborish (idempotent kalit), har qabul qiluvchi tilida shablon.
- Qo'ng'iroqcha, Xabarlar, "Bugun"dagi sariq karta, eski/yangi holat, 30 soniyalik so'rov, Web Push (VAPID), iOS ko'rsatmasi, dars oldidan eslatma, 20:00 xulosa.
- **Tekshirish:** IS-301 xonasi o'zgarsa `talaba`da ≤30 s xabar, boshqa guruhda yo'q.

### 9. Eksport, hisobotlar, hujjatlar
- Excel/PDF (akademiya nomi, semestr, imzo joyi), reja bajarilishi, o'qituvchi yuklamasi, xona bandligi.
- README (o'zbekcha), `docs/` yakuni (ER, API izohlari, ASSUMPTIONS).

## Ochiq savollar / eslatmalar
- Lokal Node 18.19 — frontend Docker ichida Node 20 bilan ishlaydi, lokalda ham ishlatish uchun Node 20+ tavsiya etiladi.
- Taxminlar (shifrlar, qo'ng'iroq vaqtlari, hayit sanasi, guruh nomlash, o'qish muddati, gender tarkibi, asr tanaffusi) `ASSUMPTIONS.md`ga yoziladi va sozlanadigan qilinadi.
