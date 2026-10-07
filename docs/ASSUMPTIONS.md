# Taxminlar (o'quv bo'limidan tasdiqlash kerak)

Ishonchim komil bo'lmagan har bir qoida sozlanadigan qilib qo'yilgan. Tasdiqlangach, "Holat" ustuni yangilanadi.
Ustunlar: **Qayerda sozlanadi** — admin panel (Django admin, 5-bosqichdan boshlab dispetcher paneli) yoki kod/sozlama.

## Tuzilma va dasturlar

| # | Taxmin | Qayerda sozlanadi | Holat |
|---|---|---|---|
| 1 | Dastur shifrlari namuna: Islomshunoslik `60220300`, Dinshunoslik `60221600`, magistratura Islomshunoslik `70220301`. | Admin: Ta'lim yo'nalishlari | Almashtirish kerak |
| 2 | O'qish muddati: kunduzgi bakalavr 4 yil, kechki 4,5 yil, sirtqi va masofaviy 5 yil, magistratura 2 yil. | Admin: Yo'nalish va ta'lim shakli → `duration_years` | Taxmin |
| 3 | Rus fakultetining nomi namuna: "Rus tilida ta'lim fakulteti", kafedrasi "Islomshunoslik va ijtimoiy fanlar kafedrasi". | Admin: Fakultetlar, Kafedralar | Almashtirish kerak |
| 4 | Guruh nomi `{prefiks}-{kurs}{raqam:02d}`: `IS-301`, kechki `IS-K-201`, sirtqi `IS-S-101`, masofaviy `IS-M-101`, magistratura `IS-MG-101`, rus guruhlari `IS-R-201`, rus sirtqi `IS-RS-201`. Prefiks yo'nalish+shakl uchun alohida beriladi, umumiy qolip `GROUP_NAME_PATTERN` (masalan, `ИС-301` uchun prefiks `ИС`). | Admin: `group_prefix`; `.env`: `GROUP_NAME_PATTERN` | Taxmin |
| 5 | Guruhda ixtiyoriy `gender_composition` (aralash / o'g'il bolalar / qizlar) maydoni bor. Oqim ma'ruzalarida turli tarkibdagi guruhlar birga o'tiradi. | Admin: Guruhlar | Taxmin |
| 6 | Rus guruhlari uchun alohida o'quv reja bor (`teaching_language = ru`), masalan "Ingliz tili" o'rniga "O'zbek tili". Til ko'rsatilmagan reja umumiy reja hisoblanadi. | Admin: O'quv reja | Taxmin |
| 7 | 1-2-kurslarda (faqat kunduzgi) ingliz tili amaliy mashg'ulotlari va 1-kurs axborot texnologiyalari laboratoriyasi kichik guruhlarda o'tadi. Arab tili butun guruh bilan o'tadi (mobil dizayndagidek). | Yuklama taqsimoti (seed: `SPLIT`) | Taxmin |

## Vaqt va kalendar

| # | Taxmin | Qayerda sozlanadi | Holat |
|---|---|---|---|
| 8 | Qo'ng'iroq jadvallari. Kunduzgi va sirtqi: 08:30–09:50, 10:00–11:20, 11:30–12:50, (tushlik va peshin namozi), 13:30–14:50, 15:00–16:20, 16:30–17:50. Kechki: 18:00–19:20, 19:30–20:50. Masofaviy: 18:30–19:50, 20:00–21:20. | Admin: Ta'lim shakllari → qo'ng'iroq jadvali | Taxmin |
| 9 | Smenalar: 1-smena 1–3-darslar, 2-smena 4–6-darslar. 1- va 3-kurslar 1-smenada, 2- va 4-kurslar hamda magistratura 2-smenada o'qiydi. | Admin: Guruh → `shift` | Taxmin |
| 10 | Juma namozi: juma 12:00–14:00, barcha shakllar uchun qat'iy (kunduzgida 3- va 4-darslar). | Admin: Band vaqtlar | Promptdan |
| 11 | Asr namozi tanaffusi: har kuni 15:00–16:20, yumshoq cheklov (iloji boricha dars qo'yilmaydi). | Admin: Band vaqtlar (`is_hard = false`) | Taxmin |
| 12 | O'qish kunlari: kunduzgi, sirtqi va masofaviy du–sh, kechki faqat du–ju. | Admin: Ta'lim shakli → `study_weekdays` | Taxmin |
| 13 | Kuniga ko'pi bilan: kunduzgi 4, kechki 2, sirtqi 4, masofaviy 2 dars. | Admin: Ta'lim shakli → `max_lessons_per_day` | Kechki va masofaviy taxmin |
| 14 | 2025–2026 bahorgi semestr: dars haftalari 23-fevral – 6-iyun 2026 (15 hafta, 6–11-aprel 7-hafta, dizayndagidek). Semestr 30-iyungacha. Kuzgi semestr: 1-sentabr 2025 – 24-yanvar 2026. | Admin: Semestrlar, O'qish davrlari | Taxmin |
| 15 | Sirtqi o'quv-sinov sessiyasi: 6–25-aprel 2026. | Admin: O'qish davrlari | Taxmin |
| 16 | Hafta raqami o'qish davri boshlangan haftadan sanaladi. 1-hafta toq hafta hisoblanadi. | Kod: `TeachingPeriod.week_number` | Taxmin |
| 17 | 2026 bayramlari: 8-mart, 21-mart (Navro'z), 9-may. Ramazon hayiti **20-mart** va Qurbon hayiti **27-may** taxminiy sanalar (oy taqvimiga bog'liq), `is_assumption` bilan belgilangan. Hukumat qarori bilan beriladigan qo'shimcha dam olish va ko'chirilgan ish kunlari kiritilmagan. | Admin: Akademik kalendar | Tasdiqlash kerak |
| 18 | Bayram kuniga to'g'ri kelgan dars avtomatik ravishda "ko'chirilishi kerak" holatiga tushadi. Ko'chirilgan ish kunida esa ko'rsatilgan hafta kunining jadvali bo'yicha o'qiladi. | Kod | Taxmin |

## Kredit va yuklama

| # | Taxmin | Qayerda sozlanadi | Holat |
|---|---|---|---|
| 19 | 1 kredit = 30 soat (auditoriya + mustaqil ta'lim). Bazada `CHECK` bilan tekshiriladi. | Kod: `HOURS_PER_CREDIT` | Promptdan |
| 20 | Seed'dagi kunduzgi reja kreditlari auditoriya soatidan hisoblangan (auditoriya soatlari kreditning taxminan yarmi). Sirtqi rejada kredit o'sha, auditoriya soatlari esa kam. | Admin: O'quv reja | Namuna |
| 21 | O'qituvchining semestrdagi yuklamasi yillik yuklamaning yarmidan oshmaydi. Haftalik darslar chegarasi har bir o'qituvchida sozlanadi (odatda 16–18 ta). | Admin: O'qituvchi → `annual_load_hours`, `max_weekly_lessons` | Taxmin |
| 22 | O'qituvchi lavozimlari: assistent, o'qituvchi, katta o'qituvchi, dotsent, professor. Ish turi: shtatdagi, o'rindosh, soatbay. | Kod: `choices.py` | Promptdan |

## Ilova

| # | Taxmin | Qayerda sozlanadi | Holat |
|---|---|---|---|
| 23 | O'zbek lotin matnlarida tutuq belgisi sifatida oddiy apostrof (`'`) ishlatiladi (`O'zbekiston`, `Qur'on`), `ʻ` emas. | Tarjima fayllari | Taxmin |
| 24 | Ilova tili birinchi kirishda brauzer tilidan aniqlanadi, aniqlanmasa o'zbekcha. Keyin profilda saqlanadi. Rus guruhi talabalari uchun boshlang'ich til ruscha. | `frontend/src/i18n`, `User.language` | Promptdan |
| 25 | Demo "bugun" sanasi 2026-yil 8-aprel (chorshanba). Haqiqiy sana 2025–2026 o'quv yilidan keyin bo'lgani uchun busiz "Bugun" ekrani bo'sh qolardi. Faqat sana qotiriladi, kun vaqti haqiqiy ("hozir" va "keyingi" dars shunga qarab belgilanadi). Bo'sh qoldirilsa haqiqiy sana ishlatiladi. | `.env`: `DEMO_NOW` | Bajarildi |
| 26 | Hamma ism, familiya, HEMIS ID va telefonlar to'qima. HEMIS ID formati namuna: `36` + shifrning oxirgi 4 raqami + tartib raqami. | Seed | To'qima |

## Cheklovlar (validator)

| # | Taxmin | Qayerda sozlanadi | Holat |
|---|---|---|---|
| 27 | Yumshoq cheklovlarning boshlang'ich og'irliklari: talaba oynasi 10, bir kunda bir fandan 2 tadan ortiq dars 8, binolar orasida ko'chish 6, smenadan chiqish 6, o'qituvchining qulay vaqti 5, ma'ruzaning seminardan oldin bo'lishi 4, o'qituvchi oynasi 3, haftada bir nechta bino 2, asr tanaffusi 1. Haftalik darslar bir toq va bir juft hafta bo'yicha o'rtacha hisoblanadi. | `DEFAULT_WEIGHTS`, keyin "Avtomatik tuzish" ekranidagi slayderlar | Taxmin |
| 28 | Kunlik dars limiti har bir talaba nuqtai nazaridan sanaladi: butun guruh darsi va o'z kichik guruhining darsi. Masalan, 3 ta umumiy dars va har bir kichik guruhga 1 tadan dars bo'lsa, talabada 4 ta dars, 5 ta emas. | Kod | Taxmin |
| 29 | Toq va juft haftada o'tiladigan darslar (masalan, haftasiga 1,5 dars) eng yaqin butun songa yaxlitlanadi. Rejadagi va jadvaldagi soatlar orasidagi farq "reja bajarilishi" hisobotida ko'rsatiladi. | `distribute_weekly` | Taxmin |

## Avtomatik tuzish (CP-SAT)

| # | Taxmin | Qayerda sozlanadi | Holat |
|---|---|---|---|
| 30 | Har bir dars o'ziga sig'adigan (va kerakli turdagi) eng kichik 8 ta xonadan birini oladi. Katta xonalar katta darslar uchun bo'sh qoladi, model ham kichik bo'ladi. | Kod: `ROOMS_PER_UNIT` | Taxmin |
| 31 | Haftalik shakllar (kunduzgi, kechki, masofaviy) bir xil hafta raqamlashidan foydalanadi (1-hafta toq). Ikki haftalik dars bir vaqtga to'g'ri kelsa, ularning davrlari kesishmasa ham ziddiyat deb hisoblanadi (ehtiyotkor yondashuv). Sirtqi sana darslari esa haftalik darslar bilan aniq sana bo'yicha solishtiriladi. | Kod: `apps/solver/cpsat.py` | Taxmin |
| 32 | Dastur avval iloji boricha ko'p darsni joylashtiradi (1-bosqich, vaqtning 40 %), keyin shu sonni saqlagan holda yumshoq cheklovlarni yaxshilaydi (2-bosqich). Vaqt chegarasi butun ishga tushirishni (yuklash va saqlash bilan) o'z ichiga oladi. | Kod: `PHASE1_SHARE`, "Avtomatik tuzish" ekrani | Taxmin |
| 33 | Qidiruv paytida optimallashtiriladi: talaba va o'qituvchi oynalari, o'qituvchining qulay vaqti, bir kunda bir fandan ko'p dars, smena, asr tanaffusi, guruh foydalanadigan binolar soni (binolar orasida yurishni ham kamaytiradi). "Avval ma'ruza, keyin seminar" tartibi va aniq yurishlar soni faqat natijada baholanadi. | Kod | Taxmin |
| 34 | Avtomatik qo'yilgan masofaviy darslarga vaqtinchalik `https://link-kerak.invalid/…` havolasi yoziladi (bazada xona yoki havola majburiy). Bu manzil hech qachon ochilmaydi, validator uni "havola yo'q" deb hisoblaydi, shuning uchun haqiqiy havolalar kiritilmaguncha jadval e'lon qilinmaydi. | `LINK_PLACEHOLDER` | Taxmin |
| 35 | Avtomatik tuzish natijasi har doim yangi qoralama bo'ladi; e'lon qilingan jadval o'zgarmaydi. Qadalgan darslar va tanlangan doiradan (fakultet, shakl) tashqaridagi darslar joyida qoladi. | "Avtomatik tuzish" ekrani | Promptdan |

## Talaba va o'qituvchi ilovasi (PWA)

| # | Taxmin | Qayerda sozlanadi | Holat |
|---|---|---|---|
| 36 | Offline rejimda oxirgi yuklangan jadval (har bir ochilgan hafta) brauzerda saqlanadi va "oxirgi yangilanish" vaqti bilan ko'rsatiladi. Chiqishda saqlangan nusxa o'chiriladi (umumiy telefonda boshqa odam ko'rmasligi uchun). Ilova qobig'i service worker orqali offline ochiladi. | Kod: `lib/offline.ts`, `public/sw.js` | Taxmin |
| 37 | Ko'chirish so'rovi faqat xabar: dispetcher "Rozi" desa ham dars avtomatik ko'chmaydi, uni muharrirda o'zi ko'chiradi (ziddiyatlar shu yerda tekshiriladi). | Kod | Taxmin |
| 38 | Bo'sh xona qidiruvi faqat e'lon qilingan jadvalga qaraydi (qoralamalar hisobga olinmaydi) va talabalarga ko'rinmaydi. | Kod | Taxmin |
| 39 | "Qulay kunlarim" har bir ta'lim shaklining qo'ng'iroq jadvali bo'yicha alohida belgilanadi; "butun kun" holati barcha shakllarga tegishli. | O'qituvchi ilovasi | Taxmin |

## Bildirishnomalar

| # | Taxmin | Qayerda sozlanadi | Holat |
|---|---|---|---|
| 40 | Faqat e'lon qilingan jadvaldagi o'zgarishlar xabar qilinadi (qoralama hech kimga ko'rinmaydi). Xabar shu darsning talabalariga (kichik guruh darsida faqat shu kichik guruhga) va o'qituvchisiga boradi; o'qituvchi almashsa, eskisiga ham. | Kod | Taxmin |
| 41 | "Dars bekor qilindi" va "dars vaqti o'zgardi" xabarlarini o'chirib bo'lmaydi; boshqalarini har kim profilida o'chira oladi. Eslatma va kechki xulosa sukut bo'yicha o'chiq. | Profil → Bildirishnomalar | Taxmin |
| 42 | Xabar o'zgarishdan bir necha soniya ichida yaratiladi. Ilova yangi xabarlarni har 25 soniyada so'raydi, shuning uchun Web Push bo'lmasa ham o'zgarish 30 soniya ichida ko'rinadi. | Kod: `POLL_MS` | Taxmin |
| 43 | E'lon qilinishidan oldin bekor qilingan (undo) tahrir va uning bekor qilinishi xabarsiz qoladi. Xuddi shu o'zgarish bir kishiga ikki marta kelmaydi (`dedup_key`). | Kod | Taxmin |
| 44 | Web Push uchun VAPID kalitlari `.env`da (`python manage.py generate_vapid_keys`). Kalitsiz push o'chiq, xabarlar ilova ichida ko'rinadi. iPhone'da push faqat bosh ekranga qo'shilgan ilovada ishlaydi (iOS 16.4+). Chiqishda shu qurilmaning push obunasi o'chiriladi. | `.env` | Taxmin |
| 45 | Dars oldidan eslatma har daqiqada tekshiriladi (5, 10, 15, 30 yoki 60 daqiqa oldin), kechki xulosa soat 20:00 da faqat ertaga darsi borlarga yuboriladi. Demo sana (`DEMO_NOW`) bilan ham shu soatlar ishlaydi. | `CELERY_BEAT_SCHEDULE` | Taxmin |

## Hisobotlar

| # | Taxmin | Qayerda sozlanadi | Holat |
|---|---|---|---|
| 46 | Bitta dars (para, 80 daqiqa) = 2 akademik soat. O'qituvchining semestr me'yori yillik yuklamaning yarmi. | Kod: `HOURS_PER_LESSON` | Taxmin |
| 47 | Xona bandligida haftalik vaqtlar: auditoriyada o'qiladigan haftalik shakllarning (kunduzgi, kechki) o'qish kunlari × paralari, yopiq vaqtlarsiz. Toq/juft hafta darsi yarim hisoblanadi; sessiya darslari alohida ustunda. | Kod | Taxmin |
| 48 | Imzo joyida "Tasdiqlayman: o'quv ishlari bo'yicha prorektor" yoziladi. | Tarjima fayllari | Taxmin |
