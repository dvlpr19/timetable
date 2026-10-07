# Taxminlar (o'quv bo'limidan tasdiqlash kerak)

Har bir taxmin konfiguratsiya qilinadigan qilib qo'yilgan. Tasdiqlangach, shu yerda belgilanadi.

| # | Taxmin | Qayerda sozlanadi | Holat |
|---|---|---|---|
| 1 | O'zbek lotin matnlarida tutuq belgisi sifatida oddiy apostrof (`'`) ishlatiladi (`O'zbekiston`, `Qur'on`), `ʻ` emas. | `frontend/src/locales/uz/*.json`, `backend/locale/uz` | Taxmin |
| 2 | Ilova tili birinchi kirishda brauzer tilidan aniqlanadi, aniqlanmasa o'zbekcha. Keyin profilda saqlanadi. | `frontend/src/i18n/index.ts` | Promptdan |

Keyingi bosqichlarda qo'shiladi: dastur shifrlari, qo'ng'iroq jadvallari, juma namozi oralig'i, asr tanaffusi, hayit sanalari, guruh nomlash qoidasi, o'qish muddatlari, `gender_composition`, kunlik dars limitlari.
