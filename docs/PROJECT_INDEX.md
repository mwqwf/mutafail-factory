# فهرس المشروع الآليّ — `mutafail-factory`

> ⛔ مولَّد آلياً بـ`tools/agents/gen_project_index.py` (سير عمل `project-index` عند الدفع إلى الفرع الرئيسيّ). لا تعدّله يدوياً.
> الحالة والخطة والعمل المفتوح في `docs/PROJECT_STATE.md` (يحدّثها الوكلاء في كل تغيير).

## البنية (عدد الملفات المتتبَّعة)
| المجلد | الملفات |
|---|---|
| `.agents/` | 53 |
| `.github/` | 46 |
| `assets/` | 34 |
| `docs/` | 5 |
| `ops/` | 599 |
| `payload/` | 9 |
| `skill/` | 19 |
| `tools/` | 167 |

## سير العمل (43)
| الملف | الاسم | المحفّزات | الجدول (cron UTC) | المشغّل |
|---|---|---|---|---|
| `admin.yml` | مصنع المتفائل — تعديلاتُ ما بعد النشر | push, workflow_dispatch | — | ubuntu |
| `artifact-roundtrip.yml` | تحقق تشفير المخرجات السحابية | workflow_dispatch | — | ubuntu |
| `audit.yml` | مصنع المتفائل — تشريحُ الشوط بعد النشر | workflow_run | — | ubuntu |
| `cancel-run.yml` | مصنع المتفائل — إلغاء شوط خاطئ | issues | — | ubuntu |
| `cancel-stuck.yml` | إيقاف شوطٍ عالق | push | — | ubuntu |
| `channel-branding.yml` | المتفائل — تطبيق الهوية المعتمدة | workflow_dispatch | — | ubuntu |
| `channel-stats.yml` | إحصاءات القناة — أضعف الريلزات بالأرقام | push, schedule, workflow_dispatch | 17 7 * * * | ubuntu |
| `daily-production.yml` | مصنع المتفائل — مشغّل الإنتاج اليومي | workflow_dispatch | — | ubuntu |
| `export-amal4-prompts.yml` | Export amal-4 image prompts securely | push | — | ubuntu |
| `film.yml` | مصنع المتفائل — إنتاج حلقة | push, workflow_dispatch | — | ubuntu |
| `finalize-amal4.yml` | Finalize and dispatch amal-4 | push, workflow_dispatch | — | ubuntu |
| `finish.yml` | مصنع المتفائل — إتمامُ نشرٍ ناقص | push, workflow_dispatch | — | ubuntu |
| `inspect-amal4-layout.yml` | Inspect amal-4 encrypted checkpoint layout | push, workflow_dispatch | — | ubuntu |
| `inspect-listen-probe.yml` | مصنع المتفائل — تصنيف نتيجة مسبار الفحص | push, workflow_dispatch | — | ubuntu |
| `listen-model-probe.yml` | مصنع المتفائل — مسبار نموذج الفحص | push, workflow_dispatch | — | ubuntu |
| `logo.yml` | مصنع المتفائل — جلبُ شعار القناة | push, workflow_dispatch | — | ubuntu |
| `models-probe.yml` | فحص حصص النماذج | push, workflow_dispatch | — | ubuntu |
| `mushafak-gemini-sync.yml` | mushafak-gemini-sync | push, schedule, workflow_dispatch | 41 4 * * * | ubuntu |
| `owner-dispatch.yml` | مصنع المتفائل — صوت مبكر موثّق | issues | — | ubuntu |
| `policy-check.yml` | 🛡️ بوّابة المخالفات (إصدار) | workflow_dispatch | — | ubuntu |
| `policy-watch.yml` | 📜 مراقبة سياسات يوتيوب | schedule, workflow_dispatch | 23 6 1,15 * * | ubuntu |
| `prepublish-gates.yml` | بوّابات ما قبل النشر — فحصٌ بلا نشر | push | — | ubuntu |
| `project-index.yml` | project-index | push, workflow_dispatch | — | ubuntu |
| `publish-amal2-exception.yml` | مصنع المتفائل — نشر استثنائي amal-2 | push, workflow_dispatch | — | ubuntu |
| `publish-amal3-exception.yml` | مصنع المتفائل — نشر استثنائي amal-3 | push, workflow_dispatch, workflow_run | — | ubuntu |
| `publish-amal4-free.yml` | مصنع المتفائل — نشر amal-4 المجاني مرة واحدة | push | — | ubuntu |
| `publish-repaired-promo.yml` | نشر ريلز السلسلة المصحح بعد المراجعة | workflow_dispatch | — | ubuntu |
| `pulse.yml` | مصنع المتفائل — نبضةُ اليقظة | workflow_dispatch | — | ubuntu |
| `quality-tests.yml` | اختبارات حراس الجودة والاستئناف | push, pull_request | — | ubuntu |
| `quota-probe.yml` | فحص حصّة الصوت — بلا توليدٍ يُذكر | push, workflow_dispatch | — | ubuntu |
| `resume-listen.yml` | مصنع المتفائل — استئناف الفحص والنشر | push, workflow_dispatch | — | ubuntu |
| `retry.yml` | مصنع المتفائل — حارسُ الإعادة | workflow_run | — | ubuntu |
| `sealed-publish.yml` | مصنع المتفائل — نشرُ حمولةٍ مختومةٍ من إصدار | push, workflow_dispatch | — | ubuntu |
| `selftest.yml` | فحصُ المحرّك — بلا رصيدٍ ولا حصّة | push | — | ubuntu |
| `series-promo-repair.yml` | فحص وإصلاح نهاية ريلز السلسلة | workflow_dispatch | — | ubuntu |
| `set-privacy.yml` | مصنع المتفائل — تغيير خصوصية فيديو منشور (بلا حذف) | push | — | ubuntu |
| `set-thumbs.yml` | مصنع المتفائل — استبدالُ مصغّراتِ أفلامٍ منشورة | push | — | ubuntu |
| `thumbnails-batch.yml` | رفع دفعة مصغرات القناة | workflow_dispatch | — | ubuntu |
| `voice-lab.yml` | مختبر الأصوات — اختيار أقوى صوتٍ وأجوده آلياً | push | — | ubuntu |
| `voice-sample.yml` | عيّنة الصوت — مقارنة بالأذن قبل توليد صوت الفيلم | push | — | ubuntu |
| `weekly-film.yml` | مصنع المتفائل — الفيلم الأسبوعي (سحابيّ كلّه) | push, workflow_dispatch | — | ubuntu |
| `x.yml` | اكس — الربط والنشر والمراقبة والتنظيف | push, schedule, workflow_dispatch | 41 6 * * * | ubuntu |
| `yt-oauth.yml` | تجديد تفويض يوتيوب من الهاتف | push | — | ubuntu |

## المهارات (13) — `.agents/skills/` (و`.claude/skills/` روابط لها)
`arabic-digest-and-x` (مركزية) · `arabic-rtl-and-islamic-typography` (مركزية) · `automation-first` (مركزية) · `mutafail-factory` (مركزية) · `mutafail-storycraft` (مركزية) · `mwqwf-workflow` (مركزية) · `project-registry` (مركزية) · `receiving-code-review` (مركزية) · `systematic-debugging` (مركزية) · `test-driven-development` (مركزية) · `verification-before-completion` (مركزية) · `verify-and-review` (مركزية) · `writing-plans` (مركزية)

## وثائق `docs/`
[`OWNER_AUDIT_2026-10-02.md`](OWNER_AUDIT_2026-10-02.md) · [`PROJECT_STATE.md`](PROJECT_STATE.md)
