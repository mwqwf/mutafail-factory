# Owner financial stop — 2026-09-18

No new charges are authorized. Before any push, PR, workflow dispatch, rerun, schedule, deployment, storage write or external API use, establish that the entire operation is free within available quotas. `ubuntu-latest`, a public repository, or an available budget alone is not sufficient proof. Do not re-enable Actions or use old branch snapshots to bypass the stop. Paid work requires NEW explicit owner approval of the necessity, estimated cost and hard cap. Never make private repositories public or disclose private code/secrets to obtain free compute. Prefer verified free cloud, then the session environment, then lightweight local work. Continue read-only analysis and small offline checks; do not repeat rejected candidates or tests without a material reason. Existing Quran accuracy gates and the 5% threshold remain mandatory. Use existing follow-up cycles only.

All default-branch workflow jobs have a reversible `if: ${{ false }}` stop. This does NOT cancel already running jobs or disable GitHub schedules at the API level. See `ops/FINANCIAL_STOP_2026-09-18.md` for rollback and outstanding cancellation.

> **أمر المالك الأحدث — 2026-09-17:** اقرأ ops/DAILY_PRODUCTION_CONTRACT.md أولاً. فيلم واحد فقط يومياً مع شورتين إلى الإيقاف؛ تطوير السلاسل الحالية؛ OpenAI للصور المولدة؛ أحدث Gemini TTS المجاني مع حرية إخراج الأصوات؛ ممنوع مس المنشور السابق. العقد يغلب البنود القديمة المتعارضة في العدد والأصوات وانتظار المالك ومسار الصور، ويحفظ المصادر والمحظورات. لا تعتبر الجدولة أو الحراس منفذة قبل دليل التحقق. الهدف مستمر لا ينتهي بعد 15 يوماً.

# تعليمات جلسات المصنع

- التواصل والتوثيق بالعربية. اقرأ `skill/SKILL.md` و`skill/PLAN.md` ثم مراجع المرحلة كاملة قبل تنفيذها.
- الحالة الفعلية في `ops/state/plan_state.json`؛ لا تستخدم `skill/PLAN_STATE.json` لتقرير الحلقة التالية.
- اقرأ `ops/CODEX_PRODUCTION_PLAN.md` لتعديلات 2026-09-16، و`ops/ENGINE.md` و`ops/CAPABILITIES.md` للتشغيل السحابي.
- أحدث توجيه للمالك: لا اعتماد على حاسوبه. لا تنفّذ تعليمات Windows القديمة بوصفها مسار التشغيل المطلوب.
- افحص وجود أداة الصور المدمجة فعلاً في الجلسة. إن وُجدت استخدمها للصور الإنتاجية، ولا تفترض حصة يومية أو وصولاً إليها من Actions. تبقى طريقة `imgdl3.py` الأصلية احتياطاً ولا تُحذف.
- ابدأ بتقييم التحسين الآمن في الجودة والسرعة قبل العمل؛ لا تُسقط أي بوابة لتسريع الإنتاج.
- لا صور نساء ولا آلات موسيقية ولا موسيقى. النصوص القرآنية والاقتباسات لا تُولد داخل الصور ولا تُنقل من الذاكرة.
- كل دعوى موثقة، والتفنيد قبل السيناريو. لا تساوِ بين نسخة نصية وصورة طبعة أصلية.
- لا نشر مع فحص سمعي ناقص. سجّل تحكيم الرايات المعلل على البصمة الحالية، ولا تصنّف نتيجة مجهولة كإيجابية كاذبة.
- المستودع عام: لا مفاتيح ولا OAuth ولا حمولة غير منشورة خاماً في git أو السجلات. افتح مخرجات Actions على أنها قابلة للوصول لمستخدمي GitHub، لا خزينة خاصة.
- لا تستهلك حصة توليد في الاختبارات؛ شغّل `python -m unittest discover -s tools -p 'test_*.py'` و`node tools/test_listen_cache.js` و`node --check tools/listen.js` بلا استدعاء خدمات.
- لا حذف لمنشور على يوتيوب. لا تكرر الرفع عند انتهاء مهلة؛ اقرأ أثر النشر أولاً واحفظ المعرّف فور نجاحه.
- لا تقل إن العمل سيستمر أسابيع لمجرد وجود cron؛ تحقّق أن الجدولة تطلق العمل فعلاً وتحفظ نقطة الاستئناف.
- احفظ تقرير التقدم والبراهين دون أسرار. لا تُعلن نجاحاً أوسع مما اختُبر.
