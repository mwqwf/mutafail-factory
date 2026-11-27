# مقترح البنية الموحّدة لمصنع المتفائل (موجز، 2026-11-27)

> مقترح فقط. لا نقل للملفات قبل نشر فيلم التاريخ اليوم، وكل تغيير في النواة أو في ملفات التاريخ بطلب دمج يراجعه بوت التاريخ. عمل الحكايات في فرع مستقلّ (`hikayat/…`).

## البنية
```
mutafail-factory/
  ops/core/          ← المشترك: NEW_FILM_PIPELINE.md (عامّ يقرأ القناة من المحفّز)، PRODUCTION_QUALITY، SOURCES، القوالب، البوّابات
  ops/channels/history/  ← CHANNEL.json (UCda…)، REFERENCE.md (شروط المعارك: خالد في العنوان، < 11 د)، DIAGNOSIS_*، series/sayf-allah-*، pinned_comment
  ops/channels/hikayat/  ← CHANNEL.json (UC7ow…)، REFERENCE.md (hikayat_reference.md)، DIAGNOSIS_*، episodes.json
  tools/             ← كما هي؛ تقرأ `--channel history|hikayat` من CHANNEL.json (المعرّف، ألفاظ البحث، رمز OAuth، قائمة السلسلة)
```
- `CHANNEL.json` لكل قناة: `channel_id`, `wrong_channel_ids`, `search_terms` (لـ`meta_gate`)، `max_minutes`، `oauth_secret` (`YT_OAUTH_JSON` / `YT_OAUTH_HIKAYAT_JSON`)، `series_catalog`، `pinned_comment_mode`.
- كل أداة تكتب اليوم `UCda…` حرفياً (`channel_branding.mjs`، `publish_repaired_promo.py`) تقرأ المعرّف من `CHANNEL.json` بدل الثابت.
- المهارة: نواة `mutafail-factory` واحدة تحيل إلى `ops/channels/<القناة>/REFERENCE.md`؛ لا مهارة مستقلّة لكل بوت.

## سلوك المحفّز (لأي بوت، بلا اعتماد على بوت بعينه)
- «ابدأ فلماً جديداً في **المتفائل للتاريخ**» ⇒ `channel=history`؛ «… في **المتفائل للحكايات**» ⇒ `channel=hikayat`؛ «ابدأ فلماً جديداً» بلا قناة ⇒ التاريخ (السلوك الحالي) مع سطر تنبيه.
- البوت يقرأ: نواة المهارة ← `docs/NOW.md` ← `ops/channels/<c>/CHANNEL.json` و`REFERENCE.md` ← ثم يجري الخطوات ١–٨ من `ops/core/NEW_FILM_PIPELINE.md` بقيم القناة (المعرّف، الشروط، القوالب، السلسلة).
- الحالة لكل قناة في `docs/NOW.md` بقسمين، وسطر في `BOARD.md` ▸ مصنع المتفائل بوسم القناة.
