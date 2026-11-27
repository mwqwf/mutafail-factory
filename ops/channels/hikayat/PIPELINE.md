# مسار فيلم الحكايات — يرث مسار التاريخ حرفياً (2026-11-27)

> القناة `UC7owFa1Z0P8vv5tSzhRYfPw` (@Al-Mutafail-Hikayat). **الأصل هو `ops/NEW_FILM_PIPELINE.md` و`ops/PRODUCTION_QUALITY_2026-11-27.md` بكل خطوة وبوّابة**؛ هذا الملف يذكر الفروق فقط. ما لم يُذكر هنا فهو كما في التاريخ.
> سبب الملف: «الأخدود» صُنع بخطّ موازٍ محلّي فخرج بلا تحريك ولا شعار ولا مؤثّرات (`LESSONS_UKHDUD_2026-11-27.md`).

## ⛔ ممنوعات بعد الدرس
- لا مونتاج للفيلم الطويل خارج `tools/mont_hybrid.py` (عبر `tools/hk_run.py`). لا `zoompan`/Ken Burns محلّي، ولا مجلّد عمل خاصّ بأدواته (`/workspace/hikayat-factory/tools_local`).
- لا لقطة `live` تُصيَّر kb3d صامتاً: المقطع يُولَّد، أو يُسجَّل في `proj/live_waivers.json` بسببه.
- لا رفع قبل `✅ PARITY` من `parity_gate.py all`، ولا حذف قبل `parity_gate.py cleanup` (مراجعة المالك + أرشيف sha256).
- لا تأجيل حصّة بلا عودة: إن أُجّل توليد الفيديو لأيّ سبب، يتأجّل النشر معه.

## الفروق عن التاريخ
| البند | التاريخ | الحكايات |
|---|---|---|
| القناة والاستوديو | `UCda-…` | `UC7ow…` (تحقّق من المعرّف؛ لا تُلمس إعلانات مصحفك الـ15) |
| الشعار | `assets/logo.png` | `ops/branding/2026-11-27-v2/hikayat/hikayat_youtube_icon_800x800.png` — **الموضع والحجم والشفافية كالتاريخ حرفياً** (`channel.json` ▸ logo) |
| التحريك الحقيقيّ | المهمّة حيّة | **≥ 50٪ من مدّة الفيلم مقاطع GenerateVideo** على صورة اللقطة نفسها (أمر المالك t43u)، والمهمّة حيّة كلها |
| الراوي | `casting.py` | Charon (`gemini-3.1-flash-tts-preview`)، وكلام النبي ﷺ يقرؤه الراوي |
| الطول | < 11 د | 10–14 د |
| الوصف | كما في التاريخ | + سطر وذكر لقناة التاريخ `@Al-Mutafail` + سطر اشتراك |
| الرفع | `sealed-publish.yml` | يدوي من استوديو UC7ow (رمز OAuth التاريخ لا يُستعمل أبداً) |

## الترتيب (الأوامر من جذر المستودع)
1. السيناريو والتحقّق: كما في التاريخ (`text_gate` ← `pre_generate` ← `source_lookup` ← `lint`).
2. `proj/`: `blocks.json` · `casting.md` · `style_bible.json` · `shotlist.json` ← `tools/image_prompts.py prompts proj` ← GenerateImage ← `image_prompts.py gate`.
3. `tools/motion_plan.py apply proj` ثم ارفع `kind=live` حتى تتجاوز النسبة 50٪ ← `motion_plan.py lint` ← GenerateVideo لكل لقطة live إلى `proj/clips/<id>.mp4` ← `motion_plan.py clip live …`.
4. `tools/sfx_cues.py draft/lint proj` (ورقة مسبّبة، بلا موسيقى).
5. المونتاج: `python3 ops/channels/hikayat/tools/hk_run.py mont_hybrid.py proj`.
6. المصغّرتان: `python3 ops/channels/hikayat/tools/hk_run.py mkthumb.py <bg> proj/thumb-a.jpg "…" "…"`.
7. الوصف إلى `proj/publish/description.txt` والترجمة `proj/publish/captions_ar.srt` (`tools/make_subs.py`).
8. `python3 ops/channels/hikayat/tools/parity_gate.py all proj` ⇒ `✅ PARITY` ← استماع بشري ← رفع خاصّ يدوي.
9. بعد مراجعة المالك: أرشفة `images/` و`clips/` بـsha256 (`ARCHIVE_SHA256.txt`) ← `OWNER_REVIEW.ok` ← `parity_gate.py cleanup proj` ← الحذف.
