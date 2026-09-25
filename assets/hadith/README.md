# نصوصُ الحديث المحلّيّة — لا جلبَ من الشبكة

سببُ وجودها: كلُّ جلبٍ من sunnah.com أو dorar.net كان يوقف المالكَ بطلب إذن (2026-09-25).
فصارت الكتبُ السبعة هنا، ويُبحث فيها بـ`python3 tools/hadith_find.py "<كلمات>"`.

المصدر: fawazahmed0/hadith-api (الإصدار 1)، النسخ العربية `editions/ara-<كتاب>.min.json` عبر raw.githubusercontent.com.
البنية: `{"metadata":…, "hadiths":[{"hadithnumber", "arabicnumber", "text", "grades":[{"name","grade"}], "reference"}]}`.
الدرجاتُ موجودةٌ في السنن (من الألباني وشاكر وغيرهما) وغائبةٌ في الصحيحين لأنّهما صحيحان أصلاً.

⛔ لا يُنسب حديثٌ في سيناريو إلا بكتابه ورقمه من هذه الملفّات، ولا يُذكر بلا درجته إن لم يكن في الصحيحين.

| الملفّ | sha256 |
|---|---|
| ara-bukhari.json | f887d8724f75fb6e1d5d29342a173af5346ad9b933173c85e6e3cb570063ea33 |
| ara-muslim.json | 2cb296f3455ff8a3da9f6a0ca3de75da675788b2fb446ad316df297838e48217 |
| ara-abudawud.json | 30dd3792ea65abe7fd0be8d568809d4eac04e38cbbd588b9c6055218fe43675f |
| ara-tirmidhi.json | 22b7ffbbca9beb5d4f108cc0389a3cd16917876b3ceb32993c46e1554afd871b |
| ara-nasai.json | 18294d8da9ec9a735719f26709858ac30657c1122f6a39d179f128bfc59ecb80 |
| ara-ibnmajah.json | 495fcccdea5f2d157794d2b1bd1eaa0e0a5ff5aeb6be2d7817de8f25e3b3349c |
| ara-malik.json | 8bcc8001df35cfff1697f792d99d9fa5a865e7d89734ff8a77bd49d12f7465b7 |
