# أرشيف فيلم الحكايات الأول — «أصحاب الأخدود» (صحيح مسلم ٣٠٠٥)

القناة: «المتفائل | حكايات إسلامية بمصادرها» (UC7owFa1Z0P8vv5tSzhRYfPw). وُضع الأرشيف بتاريخ 2026-11-27.

## على يوتيوب
| المادة | المعرّف | الموعد |
|---|---|---|
| الفيلم (11:30) | [-WCn4Flseg8](https://youtu.be/-WCn4Flseg8) | عرض أول 2026-11-27 الساعة 18:00 بتوقيت الجزائر |
| شورت | [H0SSKzqg1uo](https://youtube.com/shorts/H0SSKzqg1uo) | مجدول |
| شورت | [cCc2A_EYPNY](https://youtube.com/shorts/cCc2A_EYPNY) | مجدول |
| شورت | [hPUX2h757EQ](https://youtube.com/shorts/hPUX2h757EQ) | مجدول |

## المحتوى
- `script/`: السيناريو المشكول (script.md، وscript_v1.md مع خريطة البنية)، وكتل الصوت voice_ready.json/.txt، وcasting.md، وshotlist.md، وstyle_bible.md، وأوامر الصور image_prompts.json، وخطة المونتاج plan.json، وأزمنة الكتل block_starts.json.
- `publish/`: البيانات والوصف والوسوم والتعليق المثبت. وpublish.json مسوّدة محلية سابقة للرفع، والموعد الفعلي هو المذكور أعلاه.
- `audio_reports/`: سجلّ فحص الصوت voice_qa_status.md، ونتائج الإصغاء (gemini) والتفريغ (whisper).
- `narration/ukhdud_narration_final.mp3`: صوت الفيلم النهائي، أحادي بمعدّل 96 كيلوبت.
- `shorts/`: مواصفة الشورتات وخطتها وأوامر صورها وأوصافها، وأداتها في tools_local/mk_shorts.py.
- `thumbs/`: المصغّرتان A/B.
- `docs/`: فحص سياسات يوتيوب، وسجلّ المراجعة اللغوية، وقرارات Ask Studio (بلا أرقام)، ومرجع القناة.
- `sources/`: نص الحديث من الشاملة، والنسخة المشكولة من hadithdb.
- `tools_local/`: أدوات الفيلم المحلية: التحقّق من لفظ الحديث، والتوقيت، وبناء الصوت، والفحص، والإيقاع، والمونتاج بحركة Ken Burns، والمصغّرات، والشورتات.

## التقنية
- الصوت: gemini-3.1-flash-tts-preview بصوت Charon وحده، 84 كتلة. أُعيدت 6 كتل لأخطاء نطق (d_015، d_024، d_030، d_046، d_056، d_077). المسار وسير العمل hikayat-voice.yml على الفرع hikayat/film1-voice.
- المونتاج: 44 صورة ثابتة بحركة Ken Burns في 129 لقطة، بلا موسيقى ولا مؤثرات. الجهارة −14 LUFS، والدقّة 1920×1080.
- لا وسائط كبيرة هنا (لا mp4 ولا wav)، ولا أرقام Studio خاصة.
