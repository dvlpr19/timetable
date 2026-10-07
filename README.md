# Dars jadvali

O'zbekiston xalqaro islom akademiyasi dars jadvalini tuzish, tekshirish va e'lon qilishni
avtomatlashtiruvchi tizim (BMI loyihasi). To'rtta ta'lim shakli bitta tizimda: kunduzgi, kechki,
sirtqi (sessiya) va masofaviy. Ilova o'zbek, rus va ingliz tillarida ishlaydi.

## Imkoniyatlar

**Dispetcher (o'quv bo'limi), dekanat va kafedra uchun — admin panel**

- Bosh sahifa: guruhlar, o'qituvchilar, xonalar, joylashtirilgan va qolgan darslar, ziddiyatlar,
  fakultetlar bo'yicha tayyorlik foizi.
- Ma'lumotnomalar: fakultet, kafedra, yo'nalish, guruh, oqim, o'qituvchi, talaba, xona, fan,
  o'quv reja, yuklama, qo'ng'iroq jadvali, yopiq vaqtlar (juma namozi), akademik kalendar.
  Qidiruv, filtrlar, Excel'dan yuklash (shablon foydalanuvchi tilida, xato bo'lsa hech narsa saqlanmaydi).
- Jadval muharriri: haftalik va sessiya to'ri, sudrab ko'chirish va klaviatura bilan joy tanlash,
  har bir katakda "qo'yish mumkin / mumkin emas" va sababi, qadash, xonani almashtirish,
  o'zgarishlar tarixi va bekor qilish (undo), qoralama va e'lon qilish, Excel / PDF eksport.
  11 ta qat'iy qoida (o'qituvchi, guruh va xona to'qnashuvi, sig'im, xona turi, juma namozi,
  bayramlar, o'qituvchi band vaqti, kunlik chegara, o'qitish tili va h.k.) har bir o'zgarishda
  tekshiriladi, bazada `EXCLUDE` cheklovlari bilan ham himoyalangan.
- Avtomatik tuzish (Google OR-Tools CP-SAT): fakultet yoki shakl bo'yicha, "qayta tuzish" yoki
  "yetishmayotganini qo'yish", yumshoq cheklovlar og'irliklari, oldindan tekshirish, jonli progress,
  natija yangi qoralama bo'lib saqlanadi va joriy versiya bilan solishtiriladi.
- O'qituvchilarning ko'chirish so'rovlari, hisobotlar: o'quv reja bajarilishi, o'qituvchilar yuklamasi,
  xonalar bandligi (ekranda, Excel va PDF'da).

**Talaba va o'qituvchi uchun — mobil ilova (PWA)**

- Bugun (hozirgi va keyingi dars, o'zgarishlar sariq kartada), Hafta (sirtqida sessiya kunlari),
  dars tafsiloti, boshqa guruh / o'qituvchi / xona jadvalini qidirish.
- O'qituvchi: "Qulay kunlarim", bo'sh xona topish, darsni ko'chirishni so'rash.
- Jadvalni PDF, Excel va kalendar (`.ics`) ko'rinishida yuklab olish.
- Xabarlar: dars ko'chirilsa yoki bekor qilinsa, o'sha darsdagi talabalar va o'qituvchiga
  o'z tilida xabar (ilova ichida va Web Push), dars oldidan eslatma, soat 20:00 da ertangi darslar.
- Telefonga o'rnatiladi, internet bo'lmaganda oxirgi yuklangan jadval ko'rinadi.

## Ishga tushirish

Kerak: Docker va Docker Compose.

```bash
cp .env.example .env     # parollar va maxfiy kalitni o'zgartiring
make up                  # postgres, redis, backend, worker, beat, frontend
make seed                # bazani tozalab, namuna ma'lumotlarni yuklaydi
```

| Manzil | Nima |
|---|---|
| http://localhost:5173 | Ilova: xodimlar admin panelga, talaba va o'qituvchi mobil ilovaga tushadi |
| http://localhost:8010/api/docs/ | API hujjati (Swagger) |
| http://localhost:8010/django-admin/ | Django admin |

Portlar `.env` faylida o'zgartiriladi (`FRONTEND_HOST_PORT`, `BACKEND_HOST_PORT`, `POSTGRES_HOST_PORT`).

### Servislar

| Servis | Vazifasi |
|---|---|
| `postgres` | PostgreSQL 16 (`btree_gist` bilan) |
| `redis` | Celery navbati |
| `backend` | Django + DRF API |
| `worker` | Celery: avtomatik tuzish, xabar yuborish |
| `beat` | Celery beat: har daqiqada dars oldidan eslatma, 20:00 da kechki xulosa |
| `frontend` | React (Vite) ilova |

### Sozlamalar (`.env`)

| O'zgaruvchi | Ma'nosi |
|---|---|
| `DEMO_NOW` | Demo "bugun" sanasi (namuna semestr ichida, masalan `2026-04-08`). Bo'sh bo'lsa haqiqiy sana |
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` | Web Push kalitlari: `docker compose exec backend python manage.py generate_vapid_keys`. Bo'sh bo'lsa push o'chiq, xabarlar ilova ichida baribir ko'rinadi |
| `VAPID_CLAIM_EMAIL` | Push xizmatlari uchun aloqa manzili |

## Buyruqlar

| Buyruq | Vazifasi |
|---|---|
| `make up` / `make down` | Ishga tushirish / to'xtatish |
| `make seed` | Namuna ma'lumotlarni qaytadan yuklash (bazadagi hamma narsa o'chadi) |
| `make test` | Linterlar + backend (pytest) + frontend (vitest) testlari |
| `make format` | Kodni avtomatik formatlash |
| `make migrate` | Migratsiyalar |
| `make makemessages` | Backend tarjima kataloglarini yangilash |
| `make logs` | Loglar |
| `docker compose exec backend python manage.py run_solver --faculty ISL --time-limit 90` | Avtomatik tuzishni buyruq qatoridan ishga tushirish (tajribalar uchun) |

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
33 o'qituvchi, 28 xona, 20 fan, 215 ta yuklama. Joriy davr: 2025–2026 o'quv yilining bahorgi semestri.
E'lon qilingan jadvalda faqat IS-301 guruhining haftasi bor (qo'lda joylashtirilgan va qadalgan).
Qolgan guruhlarni "Avtomatik tuzish" sahifasida bir necha daqiqada joylashtirish mumkin
(demo fakultet: 252 ta darsning hammasi, 0 ta qat'iy ziddiyat, ~2 daqiqa).
Hamma ism va ID'lar to'qima.

## Tuzilishi

```
backend/                 Django 5, DRF, Celery
  apps/accounts          foydalanuvchilar, rollar, til
  apps/academics         tuzilma, odamlar, xonalar, o'quv reja, yuklama, kalendar, Excel import
  apps/scheduling        jadval versiyalari, darslar, validator, tahrir, eksport, hisobotlar
  apps/solver            avtomatik tuzish (CP-SAT)
  apps/notifications     xabarlar, Web Push, eslatmalar
  locale/                uz / ru / en tarjimalari
frontend/                React 18, TypeScript, Vite, TanStack Query, Tailwind
  src/pages/admin        admin panel
  src/pages/app          talaba va o'qituvchi ilovasi
  src/locales            uz / ru / en tarjimalari
  public/sw.js           service worker (offline, push)
docs/                    reja, ER-diagramma, API izohlari, taxminlar
```

## Tillar

Frontend matnlari `frontend/src/locales/{uz,ru,en}/*.json`, backend matnlari
`backend/locale/{uz,ru,en}/LC_MESSAGES/django.po` fayllarida. Testlar har bir tilda kalitlar to'liq
mosligini tekshiradi; JSX ichida qattiq yozilgan matnni ESLint taqiqlaydi. Xabarlar va avtomatik tuzish
izohlari har bir foydalanuvchiga uning tilida yaratiladi.

## Hujjatlar

- `docs/PLAN.md` — bosqichlar rejasi
- `docs/ER.md` — ma'lumotlar modeli (ER-diagramma) va bazadagi ziddiyat cheklovlari
- `docs/API.md` — API izohlari (to'liq ro'yxat: `/api/docs/`)
- `docs/ASSUMPTIONS.md` — o'quv bo'limidan tasdiqlanishi kerak bo'lgan taxminlar
