# Dars jadvali

O'zbekiston xalqaro islom akademiyasi dars jadvalini avtomatlashtiruvchi tizim (BMI loyihasi).

## Ishga tushirish

Kerak: Docker va Docker Compose.

```bash
cp .env.example .env     # parollar va maxfiy kalitni o'zgartiring
make up                  # postgres, redis, backend, worker, frontend
make seed                # bazani tozalab, namuna ma'lumotlarni yuklaydi (~10 soniya)
```

| Manzil | Nima |
|---|---|
| http://localhost:5173 | Ilova (admin panel, talaba va o'qituvchi sahifalari) |
| http://localhost:8010/api/docs/ | API hujjati (Swagger) |
| http://localhost:8010/admin/ | Django admin |

Portlar `.env` faylida o'zgartiriladi (`FRONTEND_HOST_PORT`, `BACKEND_HOST_PORT`, `POSTGRES_HOST_PORT`).

## Buyruqlar

| Buyruq | Vazifasi |
|---|---|
| `make up` / `make down` | Ishga tushirish / to'xtatish |
| `make test` | Linterlar + backend (pytest) + frontend (vitest) testlari |
| `make format` | Kodni avtomatik formatlash |
| `make migrate` | Migratsiyalar |
| `make makemessages` | Backend tarjima kataloglarini yangilash |
| `make logs` | Loglar |

## Tillar

Ilova uz / ru / en tillarida ishlaydi. Frontend matnlari `frontend/src/locales/{uz,ru,en}/*.json`,
backend matnlari `backend/locale/{uz,ru,en}/LC_MESSAGES/django.po` fayllarida. Testlar har bir tilda
kalitlar to'liq mosligini tekshiradi; JSX ichida qattiq yozilgan matnni ESLint taqiqlaydi.

## Demo foydalanuvchilar

`make seed` dan keyin:

| Login | Parol | Kim |
|---|---|---|
| `admin` | `admin123` | Dispetcher (o'quv bo'limi), Django admin'ga ham kiradi |
| `dekanat` | `dekanat123` | Islomshunoslik fakulteti dekanati |
| `kafedra` | `kafedra123` | Qur'onshunoslik va hadisshunoslik kafedrasi mudiri (Ibragimov Sh.) |
| `oqituvchi` | `oqituvchi123` | Yusupov Sardor, dotsent |
| `talaba` | `talaba123` | Karimova Aziza, IS-301 |
| `talaba_ru` | `talaba123` | IS-R-201 guruhi talabasi (rus guruhi), ilova tili rus |

## Namuna ma'lumotlar

Ikki fakultet: Islomshunoslik (o'zbek tilida) va Rus tilida ta'lim fakulteti. Jami 26 guruh, ~600 talaba,
33 o'qituvchi, 28 xona, 20 fan. To'rtala ta'lim shakli bor: kunduzgi, kechki, sirtqi sessiya va masofaviy.
Joriy davr: 2025–2026 o'quv yilining bahorgi semestri. IS-301 guruhining haftalik jadvali mobil dizayndagidek
qo'lda joylashtirilgan va e'lon qilingan. Qolgan guruhlar uchun yuklama tayyor, ularning jadvali avtomatik
tuzish orqali to'ldiriladi. Hamma ism va ID'lar to'qima.

## Hujjatlar

`docs/PLAN.md` (bosqichlar), `docs/ER.md` (ER-diagramma), `docs/API.md` (API izohlari), `docs/ASSUMPTIONS.md` (taxminlar).
