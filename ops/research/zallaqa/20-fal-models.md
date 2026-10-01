# z20 — نماذج fal للراوي المتكلّم، ولقطة التحوّل، ومشاهد المعارك

تاريخ البحث: 2026-09-28. المصدر الرئيس: صفحات `llms.txt` وصفحات `api` لكل نموذج على fal.ai (قُرئت عبر WebFetch؛ الاتصال المباشر بـ fal.ai بـ curl مرفوض من الوكيل). لم يُستدعَ fal فعلياً ولم يُثبَّت شيء.
الأسعار كما تعرضها fal اليوم وقد تتغيّر؛ ما وُسِم «محسوب» فهو حسابي من معادلة الرموز المنشورة (بافتراض 24 إطاراً/ث).

---

## 1) OmniHuman v1.5 على fal — `fal-ai/bytedance/omnihuman/v1.5`

المصدر: https://fal.ai/models/fal-ai/bytedance/omnihuman/v1.5/llms.txt و https://fal.ai/models/fal-ai/bytedance/omnihuman/v1.5/api

| الحقل | النوع | إلزامي | الافتراضي | ملاحظات |
|---|---|---|---|---|
| `image_url` | string | نعم | — | صورة الشخص |
| `audio_url` | string | نعم | — | الصوت الذي يقود الفيديو |
| `prompt` | string | لا | — | «The text prompt used to guide the video generation» |
| `mask_url` | string | لا | — | قناع: يُحرَّك الشخص في المنطقة البيضاء فقط |
| `turbo_mode` | boolean | لا | `false` | أسرع مع نقصٍ طفيف في الجودة |
| `resolution` | enum | لا | `"1080p"` | `"720p"` أو `"1080p"` |

- المخرجات: `video` (File)، و`duration` (float — المدّة المحتسبة للفوترة).
- **السعر: 0.16$ لكل ثانية** (لم تُذكر تفرقة سعرية بين 720p و1080p).
- **حدّ الصوت: أقلّ من 30 ثانية عند 1080p، وأقلّ من 60 ثانية عند 720p.**

### هل الـprompt يتحكّم فعلاً في الإيماءات والكاميرا؟
نعم، وهذه ميزة الإصدار 1.5 الأساسية. صفحة المشروع الرسمية تقول إنه «accepts text prompts and demonstrates exceptional prompt-following, enabling precise control over object generation, camera movements, and specific actions»، وتعرض أمثلةً لأفعالٍ متسلسلة، منها:
- «The character's face moves forward, they look at the camera, then reach out and poke the camera lens. After that, the camera moves backward, and the character crosses their arms and starts to talk.»
- «Man takes cigarette out, looks to camera, speaks.»
المصدر: https://omnihuman-lab.github.io/v1_5/

### دليل fal الرسمي لكتابة الـprompt
المصدر: https://fal.ai/learn/devs/omnihuman-1-5-prompt-guide
- الترتيب المقترح: **[حركة الكاميرا] + [الانفعال] + [حالة الكلام] + [الأفعال المحدّدة]**، لأن النموذج «processes your prompt left-to-right».
- الكاميرا بعباراتٍ صريحة: «A static medium shot holds on the subject»، «The camera slowly dollies in from a medium shot to a close-up». وتجنّب «the camera moves around».
- أفعال الكلام: «talks directly to the camera»، «speaks passionately while gesturing».
- التسلسل الزمني بكلمات الانتقال: «First… then… finally» أو «Initially… as the audio continues… by the end».
- تجنّب التعليمات المتناقضة.

### لماذا خرجت إيماءاتكم عامّة؟ (استنتاجٌ عمليّ)
النموذج يربط الحركة بإيقاع الصوت وانفعاله، لكنه **لا يفهم دلالة الكلام العربي كلمةً كلمة** ليختار الإيماءة المناسبة. والـprompt الواحد لمقطعٍ طويل فيه جملٌ كثيرة يذوب في حركةٍ عامّة. الحلّ:
1. **قصّ الصوت جملةً جملة (مقاطع من 3 إلى 8 ثوانٍ)**، وشغّل كل مقطعٍ على حدة بـprompt خاصٍّ بإيماءة واحدة أو اثنتين فقط، ثم ألصقها بمونتاجٍ مع قطعٍ على لقطةٍ أخرى أو انتقالٍ خفيف. والتكلفة لا تتغيّر لأن الفوترة بالثانية.
2. prompt إنجليزيّ قصير، يبدأ بتثبيت الكاميرا ثم يصف الفعل بالتسلسل. مثال لجملة الجرس:
   `A static medium shot. The man speaks to the camera with urgency. First he raises his right arm and points his index finger upward toward the bell above him, glancing up at it; then he looks back into the lens and keeps talking.`
   ومثال للسلام:
   `A static medium shot. The man smiles warmly, raises his right hand to shoulder height with the palm open toward the camera in a greeting, then lowers it and speaks calmly.`
3. صورة المصدر يجب أن تُظهر **اليدين كاملتين** ضمن الإطار (لقطة متوسّطة حتى الخصر فما دون)؛ فإن كانت اليدان خارج الإطار فلن يأتي بإشاراتٍ واضحة.
4. `resolution: "720p"` إن أردتم مقاطع أطول، و`turbo_mode: false` للجودة.

---

## 2) بدائل على fal للأفاتار المتكلّم (صورة + صوت)

| النموذج (endpoint) | المدخلات بأسمائها الدقيقة | السعر | الحدّ الأقصى | prompt للحركة؟ | إيماءات اليدين (السمعة/التوثيق) |
|---|---|---|---|---|---|
| **OmniHuman v1.5** `fal-ai/bytedance/omnihuman/v1.5` | `image_url`, `audio_url`, `prompt`, `mask_url`, `turbo_mode`, `resolution` | **0.16$/ث** | <30ث (1080p)، <60ث (720p) | **نعم، بقوّة** (كاميرا + أفعال متسلسلة) | الأفضل توثيقاً في الإيماءات الدلالية وحركة الجسم الكامل |
| **Kling AI Avatar v2 Pro** `fal-ai/kling-video/ai-avatar/v2/pro` | `image_url`, `audio_url`, `prompt` (الافتراضي `"."`) | **0.115$/ث** | حتى 5 دقائق حسب دليل Kling | نعم (وصف «الأداء»: الانفعال والأفعال) | جيّدة، وأقرب إلى «مقدّم برامج»؛ يُنصح بـprompt من 1 إلى 3 جمل |
| **Kling AI Avatar v2 Standard** `fal-ai/kling-video/ai-avatar/v2/standard` | `image_url`, `audio_url`, `prompt` | **0.0562$/ث** | كسابقه | نعم | أضعف من Pro |
| **Creatify Aurora** `fal-ai/creatify/aurora` | `image_url`, `audio_url`, `prompt`, `guidance_scale` (1، 0–5)، `audio_guidance_scale` (2، 0–5)، `resolution` (`480p`/`720p`) | 0.07$/ث (480p)، **0.14$/ث (720p)** بتقريب الثواني لأعلى | غير مذكور | نعم (نصّ فقط) | موجّه للإعلانات والاستوديو؛ الأمثلة الرسمية تُظهر ضبط الجسم («hands remain below frame»)، أي أن النصّ يؤثّر فيه |
| **VEED Fabric 1.0** `veed/fabric-1.0` | `image_url`, `audio_url`, `resolution` (`480p`/`720p`) | 0.08$/ث (480p)، 0.15$/ث (720p) | غير مذكور | **لا prompt** | لا تحكّم؛ حركة تلقائية |
| **InfiniteTalk** `fal-ai/infinitalk` | `image_url`, `audio_url`, `prompt` (إلزامي)، `num_frames` (145، 41–721)، `resolution` (`480p`)، `seed`، `acceleration` | 0.20$/ث (480p)، ويتضاعف عند 720p (0.40$) | 721 إطاراً (نحو 30ث) | نعم، لكنه ضعيف | تركيزه على الشفاه والوجه؛ الإيماءات محدودة |
| **MultiTalk** `fal-ai/ai-avatar` (ومعه `ai-avatar/multi` و`single-text`) | الحقول نفسها التي في InfiniteTalk | 0.20$/ث | 721 إطاراً | نعم، ضعيف | متوسّطة |
| **Wan 2.2 S2V 14B** `fal-ai/wan/v2.2-14b/speech-to-video` | `image_url`, `audio_url`, `prompt`, `negative_prompt`, `num_frames` (80، 40–120، بمضاعفات 4)، `frames_per_second` (16)، `resolution` (`480p`/`580p`/`720p`)، `num_inference_steps`، `guidance_scale` (3.5)، `shift`… | 0.10$ / 0.15$ / 0.20$ للثانية | **120 إطاراً ≈ 7.5ث فقط** | نعم | متوسّطة، ومدّته قصيرة |
| **Sync Lipsync v2/v3** `fal-ai/sync-lipsync/v3` | تحتاج **فيديو** + صوت (vid2vid) | — | — | لا | يعدّل الشفاه فقط، فلا يولّد إيماءات |
| **Mirage Avatar X** `mirage-api/avatar-x/reference-to-video` | `audio_url`, `image_reference_url`, `video_reference_url`, `avatar` | 0.30$/ث | 3–180ث | لا | خارج الميزانية |
| **HeyGen Avatar V** `fal-ai/heygen/avatar5/digital-twin` | أفاتارات جاهزة فقط | 0.10$/ث | — | لا (الـprompt نصٌّ للكلام) | لا يقبل صورتنا |
| **Seedance 2.0 / 2.5 reference-to-video** `bytedance/seedance-2.0/reference-to-video` | `prompt`, `image_urls`, `audio_urls` (≤15ث مجموعاً في 2.0، و≤30.2ث في 2.5)، `generate_audio`… | 0.30$/ث في 2.0 (720p)، و0.22$/ث في 2.5 (480p) أو 0.47$/ث (720p) | 15ث في 2.0، و30ث في 2.5 | نعم، قويّ جداً | فوق السقف، والصوت فيه **مرجعٌ** لا مسارٌ يُلتزم به حرفياً |

- Hedra Character-3: **لم أجده endpoint على fal** (قوائم fal للأفاتار لا تذكره؛ وهو متاح على منصّة Hedra نفسها).
- **ByteDance OmniHuman أحدث من 1.5: لا يوجد على fal.** المعروض هو `v1.5` و`omnihuman` (الإصدار 1)، ولم أجد إعلاناً عن OmniHuman 2.

### التوصية (إيماءات يدٍ مطابقة للكلام بسعر ≤ 0.20$/ث)
1. **يبقى OmniHuman v1.5 (0.16$/ث)**، لكن بطريقة تشغيلٍ مختلفة: مقطعٌ لكل جملة، وprompt بإيماءةٍ محدّدة، وصورةٌ تظهر فيها اليدان. هو الوحيد في هذه الفئة الذي يعرض توثيقُه الرسمي أفعالاً متسلسلة يتحكّم فيها النص («point… then… crosses arms»).
2. **بديلٌ للمقارنة A/B: Kling AI Avatar v2 Pro (0.115$/ث)** بالطريقة نفسها. أرخص، ويقبل مقاطع أطول، لكن توثيقه يصف تحكّماً عامّاً بـ«الأداء» لا إيماءةً بعينها.
3. يُستبعد Fabric (لا prompt)، ويُستبعد Sync (شفاه فقط)، ويُستبعد Wan S2V (7.5ث، وجودته متوسّطة).

مصادر: https://fal.ai/models/fal-ai/kling-video/ai-avatar/v2/pro/llms.txt · https://fal.ai/models/fal-ai/kling-video/ai-avatar/v2/standard/llms.txt · https://fal.ai/learn/devs/kling-avatar-v2-prompt-guide · https://kling.ai/quickstart/kling-ai-avatar-2-user-guide · https://fal.ai/models/fal-ai/creatify/aurora/llms.txt · https://fal.ai/models/veed/fabric-1.0/llms.txt · https://fal.ai/models/fal-ai/infinitalk/llms.txt · https://fal.ai/models/fal-ai/ai-avatar/llms.txt · https://fal.ai/models/fal-ai/wan/v2.2-14b/speech-to-video/llms.txt · https://fal.ai/explore/best-avatar-models · https://fal.ai/models/mirage-api/avatar-x/reference-to-video/llms.txt · https://fal.ai/models/fal-ai/heygen/avatar5/digital-twin/llms.txt · https://fal.ai/models/bytedance/seedance-2.0/reference-to-video/llms.txt · https://fal.ai/models/bytedance/seedance-2.5/reference-to-video/llms.txt

---

## 3) صورة إلى فيديو بإطار بداية ونهاية (لقطة التحوّل)

### نماذج Kling — اسم الحقل يختلف من إصدار إلى آخر

| endpoint | حقل البداية | **حقل النهاية** | المدّة | السعر | `generate_audio` | `cfg_scale` / `negative_prompt` |
|---|---|---|---|---|---|---|
| `fal-ai/kling-video/v2.1/pro/image-to-video` | `image_url` | **`tail_image_url`** | `"5"`/`"10"` | 0.49$ (5ث) / 0.98$ (10ث) | لا | نعم / نعم |
| `fal-ai/kling-video/v2.5-turbo/pro/image-to-video` | `image_url` | **`tail_image_url`** | `"5"`/`"10"` | **0.35$ (5ث) / 0.70$ (10ث)** | لا | نعم (0.5) / نعم |
| `fal-ai/kling-video/v2.6/pro/image-to-video` | `start_image_url` | **`end_image_url`** | `"5"`/`"10"` | 0.35$ / 0.70$ بلا صوت، و0.70$ / 1.40$ بالصوت (0.07$/ث بلا صوت، 0.14$/ث بالصوت، 0.168$/ث مع التحكّم بالصوت) | نعم (الافتراضي `true`) | لا يوجد `cfg_scale` / نعم |
| `fal-ai/kling-video/v3/standard/image-to-video` | `start_image_url` | **`end_image_url`** | `"3"` إلى `"15"` | 0.084$/ث بلا صوت، و0.126$/ث بالصوت: **0.42$ (5ث) / 0.84$ (10ث) بلا صوت** | نعم (`true`) | نعم / نعم، ومعهما `elements` و`multi_prompt` و`shot_type` |
| `fal-ai/kling-video/v3/pro/image-to-video` | `start_image_url` | **`end_image_url`** | `"3"` إلى `"15"` | 0.112$/ث بلا صوت، و0.168$/ث بالصوت: **0.56$ (5ث) / 1.12$ (10ث) بلا صوت** | نعم (`true`) | نعم / نعم، ومعهما `elements` |
| `fal-ai/kling-video/o3/standard/image-to-video` (خليفة o1) | `image_url` | **`end_image_url`** | `"3"` إلى `"15"` | 0.084$/ث بلا صوت، و0.112$/ث بالصوت: 0.42$ (5ث) | نعم (الافتراضي `false`) | غير موجودين |

**تنبيه:** Kling v2.6 وv3 تجعل `generate_audio` مفعّلاً افتراضياً، فتتضاعف الكلفة تقريباً. يجب إرسال `generate_audio: false` صراحةً، وهذا يلزمنا أيضاً لأن **الموسيقى محرّمة** وقد يولّد النموذج موسيقى.

### بدائل
| endpoint | الحقول | السعر | ملاحظات |
|---|---|---|---|
| Veo 3.1 Fast `fal-ai/veo3.1/fast/first-last-frame-to-video` | `prompt`, `first_frame_url`, `last_frame_url`, `duration` (`4s`/`6s`/`8s`)، `resolution`، `generate_audio` (`true`)، `negative_prompt`، `seed` | 0.10$/ث بلا صوت: **0.80$ لـ8ث** | جودة عالية، ومرشّحٌ ثانٍ |
| Veo 3.1 `fal-ai/veo3.1/first-last-frame-to-video` | الحقول نفسها | 0.20$/ث بلا صوت، و0.40$/ث بالصوت | غالٍ |
| Wan 2.1 FLF2V `fal-ai/wan-flf2v` | `prompt`, `start_image_url`, `end_image_url`, `num_frames` (81–100)، `guide_scale`، `negative_prompt`، `resolution` | 0.20$ (480p) / 0.40$ (720p) للمقطع | أضعف في الحفاظ على الوجه |
| Wan 2.2 A14B `fal-ai/wan/v2.2-a14b/image-to-video` | `image_url`, `end_image_url`, `prompt`, `negative_prompt`, `guidance_scale`, `guidance_scale_2`, `num_frames` (17–161) | 0.08$/ث (720p) | الأرخص، وجودته متوسّطة |
| Seedance 1.0 Pro `fal-ai/bytedance/seedance/v1/pro/image-to-video` | `image_url`, `end_image_url`, `camera_fixed`, `duration` (2–12)، `resolution`، `seed` | نحو 0.62$ (1080p، 5ث)؛ نحو 0.27$ (720p، 5ث — محسوب) | لا `negative_prompt` |
| Seedance 1.5 Pro `fal-ai/bytedance/seedance/v1.5/pro/image-to-video` | `image_url`, `end_image_url`, `camera_fixed`, `generate_audio` (`true`)، `duration` (4–12)، `resolution` (`720p`) | 0.26$ (720p، 5ث بالصوت)؛ **نحو 0.13$ بلا صوت** (محسوب: 1.2$ لكل مليون رمز) | خيار رخيص جيّد |
| Seedance 1.0 Lite | — | — | **مُهمَل**، يُحوَّل إلى Pro Fast الذي **يتجاهل `end_image_url`** |
| PixVerse v5 Transition `fal-ai/pixverse/v5/transition` | `prompt`, `first_image_url`, `end_image_url`, `duration` (`5`/`8`)، `resolution`، `negative_prompt` | 0.20$ (720p، 5ث) | مخصّص للانتقالات، وأسلوبه أقرب إلى «المورف» |

### التوصية للقطة التحوّل
- **الأول: Kling v3 Pro** `fal-ai/kling-video/v3/pro/image-to-video` بـ`start_image_url` و`end_image_url`، مع `duration: "5"` أو `"8"`، و`generate_audio: false`، و`cfg_scale` بين 0.6 و0.7، و`negative_prompt`. الكلفة **0.56$ لـ5ث**. ويمكن إضافة `elements` (صورة وجه الراوي، ويُشار إليها في الـprompt بـ`@Element1`) لتثبيت الهويّة. تحفّظ: لم أتحقّق من البنية الداخلية لحقل `elements` ولا من توافقه مع `end_image_url`، فالتوثيق يقول فقط «image set (frontal + reference images) or a video».
- **الاقتصادي: Kling v2.5 Turbo Pro** بـ`image_url` و`tail_image_url` و`cfg_scale` و`negative_prompt`، بكلفة 0.35$ لـ5ث (أو v3 Standard بكلفة 0.42$).
- **للمقارنة: Veo 3.1 Fast FLF** بكلفة 0.80$ لـ8ث بلا صوت.
- شروط نجاح التحوّل بلا تشوّهٍ للوجه:
  1. يكون الإطاران **بالتأطير نفسه والوضعية نفسها وزاوية الوجه نفسها والإضاءة نفسها**، ولا يتغيّر بينهما إلا الملابس والأرض. وبما أن Claude ممنوع من توليد الصور (العقد الأسبوعي)، فالإطاران يأتيان من المالك أو من أداته.
  2. الكاميرا ثابتة، ويُطلب في الـprompt «gradually, visibly, from the shoulders downward, the modern jacket fabric transforms into…»، مع وصف تحوّل الأرض من الأسفل صراحةً.
  3. `negative_prompt`: `face change, identity change, morphing face, different person, distorted face, extra fingers, blur, low quality`.
  4. اللثام **مُنزَلٌ تحت الذقن** في إطار النهاية، ليبقى الوجه مكشوفاً ولا يخترعه النموذج من جديد.

مصادر: https://fal.ai/models/fal-ai/kling-video/v2.1/pro/image-to-video/llms.txt · https://fal.ai/models/fal-ai/kling-video/v2.5-turbo/pro/image-to-video/llms.txt · https://fal.ai/models/fal-ai/kling-video/v2.6/pro/image-to-video/llms.txt · https://fal.ai/models/fal-ai/kling-video/v3/pro/image-to-video/llms.txt · https://fal.ai/models/fal-ai/kling-video/v3/standard/image-to-video/llms.txt · https://fal.ai/models/fal-ai/kling-video/v3/pro/image-to-video/api · https://fal.ai/models/fal-ai/kling-video/o3/standard/image-to-video/llms.txt · https://fal.ai/models/fal-ai/veo3.1/fast/first-last-frame-to-video/llms.txt · https://fal.ai/models/fal-ai/veo3.1/first-last-frame-to-video/llms.txt · https://fal.ai/models/fal-ai/wan-flf2v/llms.txt · https://fal.ai/models/fal-ai/wan/v2.2-a14b/image-to-video/llms.txt · https://fal.ai/models/fal-ai/bytedance/seedance/v1/pro/image-to-video/llms.txt · https://fal.ai/models/fal-ai/bytedance/seedance/v1.5/pro/image-to-video/llms.txt · https://fal.ai/models/fal-ai/bytedance/seedance/v1/lite/image-to-video/llms.txt · https://fal.ai/models/fal-ai/pixverse/v5/transition/llms.txt

---

## 4) صورة إلى فيديو رخيص لمشاهد المعارك (خيل، جمال، جيوش)

| endpoint | كلفة 5ث | حقول التحكّم |
|---|---|---|
| Kling v2.6 Pro `fal-ai/kling-video/v2.6/pro/image-to-video` | 0.35$ بلا صوت | `negative_prompt`، ولا يوجد `cfg_scale` |
| Kling v2.5 Turbo Pro `fal-ai/kling-video/v2.5-turbo/pro/image-to-video` | **0.35$** | `negative_prompt` و`cfg_scale` (0–1) |
| Kling v3 Standard `fal-ai/kling-video/v3/standard/image-to-video` | 0.42$ بلا صوت | `negative_prompt` و`cfg_scale` و`elements` |
| Seedance 1.0 Pro Fast `fal-ai/bytedance/seedance/v1/pro/fast/image-to-video` | 0.243$ (1080p)؛ **نحو 0.11$ (720p، محسوب: 1$ لكل مليون رمز)** | `camera_fixed` و`seed`، ولا `negative_prompt` |
| Seedance 1.0 Pro | 0.62$ (1080p)؛ نحو 0.27$ (720p، محسوب) | كسابقه |
| Seedance 1.5 Pro | نحو 0.13$ (720p بلا صوت، محسوب) | كسابقه، ومعه `generate_audio` |
| Seedance 1.0 Lite | — | مُهمَل، ويُعاد توجيهه إلى Pro Fast |
| Wan 2.2 A14B | 0.40$ (720p، 5ث) | `negative_prompt` و`guidance_scale` |

**التوصية:**
- **Kling v2.5 Turbo Pro** للّقطات المهمّة: أرخص Kling جيّد، ويقبل `cfg_scale` و`negative_prompt` معاً (وهما أهمّ أداتين ضدّ تشوّه الخيل)، وحركته الديناميكية قويّة.
- **Seedance 1.0 Pro Fast أو 1.5 Pro بدقّة 720p** للّقطات الواسعة الكثيرة (نحو 0.11$ إلى 0.13$ لكل 5ث).
- Kling v2.6 Pro بالسعر نفسه لكنه بلا `cfg_scale`، وصوته مفعّلٌ افتراضياً، فلا ميزة له هنا.

**تجنّب تحوّل وجوه الخيل والجمال إلى وجوه بشر:**
1. `negative_prompt` (في Kling وWan):
   `human face on horse, human face on camel, anthropomorphic animal, humanoid animal face, merged rider and horse, extra legs, extra heads, deformed animals, morphing, blur, distort, low quality`.
2. `cfg_scale` بين 0.6 و0.75 في Kling v2.5/v3 (الافتراضي 0.5)، فرفعه يزيد الالتزام بالنص والـnegative. ولا يُرفع إلى 1، لأن الحركة تتصلّب وتظهر آثارٌ مصطنعة.
3. في الـprompt الموجب، سمِّ التشريح صراحةً وافصل الراكب عن الدابّة: «realistic horses with natural equine heads and long muzzles; riders in turbans sit on the horses».
4. استعمل لقطات واسعة أو متوسّطة، وتجنّب اللقطة القريبة لرأس الحصان مع وجه فارسٍ قريبٍ منه، فهذا الموضع الذي يختلط فيه الوجهان.
5. اجعل صورة البداية نظيفة التشريح (الخيل من الجانب أو بزاوية ثلاثة أرباع)، ولا تطلب «camera orbit» سريعاً حول الخيل.
6. قلّل الحركة المطلوبة في المقطع الواحد إلى فعلٍ واحد (عَدْو، أو التحام، أو اندفاع)، والتزم بـ5 ثوانٍ، وثبّت `seed` لإعادة المحاولة. ومع Seedance استعمل `camera_fixed: true` حين لا تحتاج حركة كاميرا.
7. الإطار الأخير في Kling (`tail_image_url` أو `end_image_url`) يثبّت التشريح في نهاية المقطع أيضاً.

مصادر إضافية: https://fal.ai/models/fal-ai/bytedance/seedance/v1/pro/fast/image-to-video/llms.txt · https://www.ambienceai.com/tutorials/kling-prompting-guide · https://magiclight.ai/academy/kling-ai-negative-prompts/

---

## خلاصة الحقول للنماذج الموصى بها

```jsonc
// الراوي — OmniHuman v1.5 (استدعاء لكل جملة)
{"image_url": "...", "audio_url": "<مقطع جملة واحدة>", "prompt": "A static medium shot. ... First ... then ...", "resolution": "720p", "turbo_mode": false}

// الراوي — بديل A/B: Kling AI Avatar v2 Pro
{"image_url": "...", "audio_url": "...", "prompt": "..."}

// التحوّل — Kling v3 Pro
{"prompt": "...", "start_image_url": "...", "end_image_url": "...", "duration": "5", "generate_audio": false, "negative_prompt": "...", "cfg_scale": 0.65}

// التحوّل الاقتصادي / المعارك — Kling v2.5 Turbo Pro
{"prompt": "...", "image_url": "...", "tail_image_url": "<اختياري>", "duration": "5", "negative_prompt": "...", "cfg_scale": 0.65}

// المعارك الواسعة الرخيصة — Seedance 1.5 Pro
{"prompt": "...", "image_url": "...", "resolution": "720p", "duration": "5", "camera_fixed": false, "generate_audio": false, "seed": 123}
```
