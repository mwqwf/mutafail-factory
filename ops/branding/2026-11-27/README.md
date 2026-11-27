# أصول هوية المتفائل — 27 نوفمبر 2026

هوية عائلة من قناتين بنظام الحلقة المشتركة (الخيار 2). التفاصيل في `RING_SPEC.md` و`SHARED_IDENTITY_STUDY.md`. حزمة نصوص استوديو المعارك في `studio_text.md`.

⛔ هذا المجلد لا يغيّر يوتيوب ستوديو ولا `assets/logo.png` ولا `assets/branding/` (أصول الإنتاج الجارية لأفلام اليوم). التطبيق على قناة المعارك `UCda-VgyvZwAH5_Pl1elVEnw` يتمّ لاحقاً بعد التحقق من المعرّف. ملفات الحكايات للمشاركة مع بوت تلك القناة فقط؛ لا يُمسّ `UC7owFa1Z0P8vv5tSzhRYfPw` من هذا العمل.

## قناة المعارك — `history/` — UCda-VgyvZwAH5_Pl1elVEnw

- `history_youtube_icon_800x800.png` — أيقونة يوتيوب
- `history_banner_2560x1440.jpg` — الغلاف (720 ك.ب، دون 6 ميغابايت)
- `history_banner_crop_zones_preview.jpg` — مناطق القصّ (تلفاز/سطح/لوحي/جوال)
- `history_banner_mobile_safe_crop.jpg` — قصّ الشريط الآمن 1546×423
- `history_watermark_150x150.png` — علامة الفيديو، شفافية خارج الحلقة
- `history_bot_avatar_512x512.png` — صورة البوت
- `history_mark_transparent_800.png` — العلامة بشفافية (لإعادة الاستخدام)
- `history_seal_wordmark_800.png` — ختم كبير بكلمة «المتفائل»
- `layers/` — خلفية الغلاف وطبقة النص منفصلتان لإعادة التحرير، مع `layout.json`

## قناة الحكايات — `hikayat/` — UC7owFa1Z0P8vv5tSzhRYfPw

الأسماء نفسها بالبادئة `hikayat_`. الحلقة مطابقة حرفياً، والحقل زمرّدي والرمز فانوس وكتاب.

## إعادة التصيير

```
python3 ops/branding/2026-11-27/compose.py
```

يفحص `tools/text_gate.py` ثم يصيّر. يسقط إن خرج محتوى الغلاف عن هامش 8 بكسل داخل الشريط الآمن.
