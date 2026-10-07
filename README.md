# Dars jadvali

O'zbekiston xalqaro islom akademiyasi dars jadvalini avtomatlashtiruvchi tizim (BMI loyihasi).

## Ishga tushirish

Kerak: Docker va Docker Compose.

```bash
cp .env.example .env     # parollar va maxfiy kalitni o'zgartiring
make up                  # postgres, redis, backend, worker, frontend
make seed                # namuna ma'lumotlar (2-bosqichdan boshlab)
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

2-bosqichdagi `make seed` dan keyin paydo bo'ladi (ro'yxat shu yerga yoziladi).

## Hujjatlar

`docs/PLAN.md` (bosqichlar), `docs/ASSUMPTIONS.md` (taxminlar).
