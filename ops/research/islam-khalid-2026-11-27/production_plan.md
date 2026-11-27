# خطة إنتاج «إسلام خالد بن الوليد» — 2026-11-27

> مبنيّة على `script.md` (58 كتلة، ~7:46) بأدوات المصنع الجديدة (أمر المالك 2026-11-27: جودة المؤثّرات والصور والتحريك، واختيار الأصوات لكلّ سيناريو). لا توليد ولا نشر هنا. ملفّات المشروع الآلية في `proj/` (blocks · casting · sfx_cues · style_bible · shotlist · shots). الأوقات **تقديرية** (0.5627 ث/كلمة) وتُعاد من الصوت الفعليّ عند المونتاج.

## البوّابات على هذه الخطة

```
python3 tools/casting.py check proj        → ✓
python3 tools/sfx_cues.py lint proj        → ✓ 28 إشارة
python3 tools/image_prompts.py prompts proj → ✓ 43 أمر
python3 tools/motion_plan.py lint proj     → ✓
تغطية الكتل باللقطات                        → ✓ 58/58
```

## ⚠️ تصحيحان على توجيهات السيناريو البصرية

- ف6: «قبّة/ساحة المسجد النبوي» ⇐ **لا قبّة** (مفارقة عصر: المسجد سنة 8هـ جدران لبِن وجذوع نخل وسقف جريد). اللقطتان S31 وS33 مكتوبتان هكذا، والبوّابة ترفض «dome».
- ف0/ف1: «صفوف مصلّين» تبقى من الخلف بلا إمام في الإطار، وصلاة النبي ﷺ (d_006) لا يُسمع فوقها مؤثّر.

## ١) الأصوات (casting)

التفصيل والأسباب في `proj/casting.md`. الملخّص:

| الدور | الصوت | الكتل |
|---|---|---|
| الراوي | Algenib · epic (والمدينة reverent) | كل كتل N |
| خالد بن الوليد | Algieba (بديل للعيّنة: Iapetus) | d_008 d_010 d_017 d_023 d_025 d_035 d_043 d_045 d_051 d_053 |
| عمرو بن العاص | Charon (بديل للعيّنة: Schedar) | d_034 d_037 d_048 |
| الوليد بن الوليد (أخو خالد) | Umbriel (بديل للعيّنة: Achird) | d_020 d_021 d_040 |
| النجاشي | Rasalgethi (بديل للعيّنة: Alnilam) | d_029 d_031 |
| فرسان قريش (جماعة) | Fenrir (بديل للعيّنة: Orus) | d_002 |

- كلام النبي ﷺ المنقول (d_006 وd_013 وd_015 وd_044 وd_046 وd_049 وd_055 وفي كتاب الوليد d_020–d_021) لا يُسند إلى صوت شخصية أبداً: يقرؤه الراوي أو صوت الوليد الذي ينقله في كتابه، بلا تمثيل.
- **قبل التوليد الكامل:** عيّنة لكلّ صوت وبديله في `tools/voice_lab.py` (جملة لكل شخصية، وجملتان للراوي: d_001 ملحمي وd_044 موقّر)، ثم الإصغاء، ثم `samples.status=approved`. `casting.py apply` يرفض قبل ذلك.

## ٢) ورقة المؤثّرات (cue sheet)

الجمل المفتاحية (لا مؤثّر فوقها إلا الصمت): d_006 d_013 d_015 d_020 d_021 d_035 d_041 d_043 d_044 d_046 d_049 d_055

مستويات dB نسبةً للكلام تحت الصوت (الفرش ≤ −22، النقاط ≤ −18)، وتعلو بين الجمل 8 dB بحدّ −8. لا موسيقى ولا طبول ولا حفيف على القطعات.

| # | ~الوقت | الكتلة | الحدث | المرساة | المدة | المستوى | السبب |
|---|---|---|---|---|---|---|---|
| c01 | 0:00 | d_001 | wind (bed) | +0.0 ث | 16.0 ث | -24 dB | كثيبٌ مكشوف في عسفان: الريح وحدها تحمل الافتتاح |
| c02 | 0:00 | d_001 | horse_snort (spot) | خيل | 1.6 ث | -20 dB | خيل المشركين على الكثيب: نخرة فرسٍ واحدة تعلن وجودهم |
| c03 | 0:10 | d_002 | silence (silence) | لو | 1.4 ث | — | صمتٌ عند «لو حملنا عليهم» (توجيه السيناريو) |
| c04 | 0:15 | d_003 | hooves (spot) | حمل | 2.2 ث | -22 dB | سؤال «فهل حمل خالد عليهم؟»: حوافر تقترب ثم تتوقّف (الجواب لا) |
| c05 | 0:22 | d_005 | wind (bed) | +0.0 ث | 4.5 ث | -26 dB | عسفان بين الظهر والعصر: فرشٌ خفيف قبل مشهد الصلاة |
| c06 | 0:39 | d_007 | wind (bed) | +0.0 ث | 3.0 ث | -24 dB | قطع إلى خالد من الخلف: ريح ثم صمت (توجيه السيناريو) |
| c07 | 0:41 | d_008 | silence (silence) | +0.0 ث | 1.2 ث | — | «الرجل ممنوع»: نصف ثانية صمت |
| c08 | 1:03 | d_011 | gallop (bed) | خيل | 5.0 ث | -23 dB | أُحُد: خيل قريش تدور حول التلّ |
| c09 | 1:05 | d_012 | battle (bed) | +0.4 ث | 3.0 ث | -25 dB | دخلت الخيل والتبست الصفوف: التحامٌ بعيد بلا دم |
| c10 | 1:25 | d_014 | hooves (spot) | يركض | 2.0 ث | -20 dB | خالد يركض نذيراً لقريش |
| c11 | 1:41 | d_016 | fire (bed) | +0.0 ث | 14.0 ث | -28 dB | بيتٌ مكّي ليلاً بضوء مصباح: لهبٌ خافت |
| c12 | 2:14 | d_019 | leather (spot) | فكتب | 1.2 ث | -22 dB | كتاب الوليد يُفتح بيد: رقٌّ وجلد |
| c13 | 2:51 | d_023 | footsteps (spot) | للخروج | 2.5 ث | -22 dB | «نشطت للخروج»: خطوات خالد تخرج من البيت |
| c14 | 3:15 | d_026 | camels (spot) | راحلتي | 2.5 ث | -21 dB | «هذه راحلتي بفخّ مناخة»: رغاء راحلة تُنهَض |
| c15 | 3:19 | d_026 | wind (bed) | الفجر | 7.0 ث | -26 dB | وادٍ في ظلمة ما قبل الفجر |
| c16 | 3:49 | d_028 | sea (bed) | الحبشة | 7.0 ث | -26 dB | الحبشة: ميناءٌ وسفينة من بعيد |
| c17 | 4:42 | d_033 | camels (spot) | الطريق | 2.5 ث | -22 dB | لقاء الركبين في الطريق |
| c18 | 4:42 | d_033 | wind (bed) | الطريق | 6.0 ث | -25 dB | مفترق الطريق في الفجر: ريح وحوافر بعيدة |
| c19 | 4:54 | d_035 | silence (silence) | فحتى | 1.2 ث | — | ذروة «فحتى متى؟»: صمتٌ كامل قبل الكلمة الأخيرة |
| c20 | 5:07 | d_039 | camels (spot) | المدينة | 2.5 ث | -22 dB | ثلاثة ركبان ينيخون على الحرّة عند المدينة |
| c21 | 5:08 | d_039 | wind (bed) | المدينة | 9.0 ث | -27 dB | المدينة عصراً: ريحٌ خفيفة (توجيه السيناريو) |
| c22 | 5:27 | d_042 | footsteps (spot) | +0.0 ث | 2.5 ث | -23 dB | خطوات على الرمل نحو المجلس قبل الشهادة |
| c23 | 7:08 | d_054 | battle (bed) | مؤتة | 6.0 ث | -26 dB | مؤتة: ساحة بعيدة بالغبار |
| c24 | 7:09 | d_054 | banner (bed) | الراية | 9.0 ث | -24 dB | الرايات تسقط واحدة بعد أخرى ثم تُرفع بيد خالد |
| c25 | 7:39 | d_056 | sword_clash (spot) | انقطعت | 1.6 ث | -20 dB | «انقطعت في يدي تسعة أسياف»: ضربةٌ واحدة لا تسع |
| c26 | 7:46 | d_056 | sword_draw (spot) | صفيحة | 1.6 ث | -21 dB | «صفيحة يمانية»: النصل الأخير |
| c27 | 7:47 | d_057 | wind (bed) | +0.0 ث | 9.0 ث | -26 dB | العودة إلى الكثيب الأول بالضوء الآخر (انعكاس الافتتاح) |
| c28 | 7:59 | d_058 | silence (silence) | سيوف | 2.5 ث | — | آخر ثانيتين صمت ثم شاشة النهاية |

28 إشارة في ~480 ث: 11 نقطة، 13 فرش، 4 صمت (كان في أجنادين مؤثّرٌ لكلّ لقطة 146/146 وحفيفٌ على كل قطع).

## ٣) قائمة اللقطات وأوامر GenerateImage النهائية

دليل الأسلوب: `proj/style_bible.json` (اللوحة: مغرة دافئة وظلال بنّية وزرقة الغسق، والذهب محجوز للحظات الهداية؛ والموتيف: الكثيب نفسه والفارس نفسه في الافتتاح والختام).
كل صورة 16:9 بأعلى دقّة، ثم `python3 tools/image_prompts.py gate proj <صور>` ومراجعة يدوية في `proj/image_review.json` (اليدان، السلاح، الوجوه، النساء، الصلبان، الكتابة، العصر، التشوّه). المرفوض يُعاد حتى 3 مرّات ثم تُغيَّر اللقطة.

### S01 · 0:00 · d_001 — حيّ (GenerateVideo)

```
A lone veiled rider seen from behind on a high dune ridge at Usfan, his horse restless, and far below him long rows of worshippers seen from behind standing in prayer on open sand. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. over-the-shoulder from behind the figure. 24mm anamorphic lens, f/5.6, deep focus. hard low-angle desert sun, long shadows, warm key and cool sky fill. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S02 · 0:07 · d_002 — حيّ (GenerateVideo)

```
A line of Quraysh horsemen seen from behind on the ridge, lances upright, cloaks snapping in the wind, the prayer rows small in the valley. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. low camera angle looking up, heroic scale. 24mm anamorphic lens, f/5.6, deep focus. hard low-angle desert sun, long shadows, warm key and cool sky fill. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S03 · 0:14 · d_003 — حيّ (GenerateVideo)

```
Silhouette of the veiled rider from behind, sword still sheathed at his side, sun behind him. medium shot, subject on a third line, layered foreground, midground and background for depth. low camera angle looking up, heroic scale. 35mm lens, f/2.8, shallow depth of field. golden-hour backlight, rim light on silhouettes, dust glowing in the air. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S04 · 0:19 · d_004 — حيّ (GenerateVideo)

```
The dune ridge at Usfan in hard afternoon light, a single set of hoofprints leading away along the crest. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. high aerial view. 24mm anamorphic lens, f/5.6, deep focus. golden-hour backlight, rim light on silhouettes, dust glowing in the air. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S05 · 0:22 · d_005 — حيّ (GenerateVideo)

```
Open plain of Usfan between noon and afternoon, heat haze, distant black goat-hair tents and tethered camels. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. eye-level camera. 24mm anamorphic lens, f/5.6, deep focus. hard low-angle desert sun, long shadows, warm key and cool sky fill. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S06 · 0:27 · d_006 — حيّ (GenerateVideo)

```
Two rows of worshippers seen from behind: one row bowing in prayer, the second row standing guard behind them with sheathed swords, no leader visible in frame. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. high angle looking down, sense of vulnerability. 24mm anamorphic lens, f/5.6, deep focus. hard low-angle desert sun, long shadows, warm key and cool sky fill. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S07 · 0:39 · d_007 d_008 — حيّ (GenerateVideo)

```
The veiled rider seen from behind on the ridge, shoulders lowered, hand loosening on the reins. medium shot, subject on a third line, layered foreground, midground and background for depth. over-the-shoulder from behind the figure. 35mm lens, f/2.8, shallow depth of field. hard low-angle desert sun, long shadows, warm key and cool sky fill. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S08 · 0:43 · d_009 d_010 — kb3d

```
A lone rider seen from behind riding away from a dusty field at dusk, a column of riders far ahead of him. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. eye-level camera. 24mm anamorphic lens, f/5.6, deep focus. golden-hour backlight, rim light on silhouettes, dust glowing in the air. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S09 · 1:00 · d_011 — حيّ (GenerateVideo)

```
Quraysh cavalry seen from a distance circling behind a rocky hill at Uhud, dust trailing, no faces visible. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. high angle looking down, sense of vulnerability. 24mm anamorphic lens, f/5.6, deep focus. hard low-angle desert sun, long shadows, warm key and cool sky fill. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S10 · 1:04 · d_012 — kb3d

```
Distant clash below a low hill, ranks of men in silhouette merging in a cloud of dust, archers' hill empty in the foreground. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. high angle looking down, sense of vulnerability. 24mm anamorphic lens, f/5.6, deep focus. hard low-angle desert sun, long shadows, warm key and cool sky fill. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S11 · 1:08 · d_013 — kb3d

```
Simple top-down relief map of the road to Hudaybiyya, plain sand texture, one arrow of fine dust curving to the right, no writing. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. high aerial view. 24mm anamorphic lens, f/5.6, deep focus. hard low-angle desert sun, long shadows, warm key and cool sky fill. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S12 · 1:21 · d_014 — حيّ (GenerateVideo)

```
A rider seen from behind galloping along a valley floor toward distant hills, a wall of dust rising on the horizon behind him. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. low camera angle looking up, heroic scale. 24mm anamorphic lens, f/5.6, deep focus. hard low-angle desert sun, long shadows, warm key and cool sky fill. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S13 · 1:28 · d_015 — kb3d

```
Empty open plain at Hudaybiyya at dusk, an acacia tree alone, a tethered camel resting. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. eye-level camera. 24mm anamorphic lens, f/5.6, deep focus. golden-hour backlight, rim light on silhouettes, dust glowing in the air. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S14 · 1:41 · d_016 d_017 — kb3d

```
A man seen from behind standing at the doorway of a Meccan mudbrick house at night, clay oil lamp on a niche, long shadow on the ground. medium shot, subject on a third line, layered foreground, midground and background for depth. over-the-shoulder from behind the figure. 35mm lens, f/2.8, shallow depth of field. moonlit cool fill with a single warm firelight or oil-lamp key, deep blacks. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S15 · 1:44 · d_017 — kb3d

```
Three dark roads branching from a single point in a moonlit desert, one toward the sea, one north, one back toward a sleeping town. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. high aerial view. 24mm anamorphic lens, f/5.6, deep focus. moonlit cool fill with a single warm firelight or oil-lamp key, deep blacks. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S16 · 2:02 · d_018 — kb3d

```
Distant view of Mecca's valley of mudbrick houses at dawn, a long column of pilgrims in white entering from the far side, one house's doorway closed and dark in the foreground. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. high angle looking down, sense of vulnerability. 24mm anamorphic lens, f/5.6, deep focus. blue pre-dawn light, faint warm horizon line, stars fading. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S17 · 2:11 · d_019 d_020 — حيّ (GenerateVideo)

```
Close shot of a man's hand holding a folded parchment by an oil lamp, the writing not legible, warm flame light. insert detail shot, tactile texture, shallow focus. eye-level camera. 100mm macro lens, f/4. single shaft of daylight through a doorway, volumetric dust, dark falloff. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S18 · 2:16 · d_020 d_021 — kb3d

```
A row of horsemen seen from behind on a ridge with one gap in the line where a rider is missing, an empty space. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. eye-level camera. 24mm anamorphic lens, f/5.6, deep focus. golden-hour backlight, rim light on silhouettes, dust glowing in the air. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S19 · 2:46 · d_022 d_023 — kb3d

```
The man seen from behind stepping out of the doorway into the moonlit street, lamp left burning behind him. medium shot, subject on a third line, layered foreground, midground and background for depth. over-the-shoulder from behind the figure. 35mm lens, f/2.8, shallow depth of field. moonlit cool fill with a single warm firelight or oil-lamp key, deep blacks. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S20 · 2:57 · d_024 d_025 — kb3d

```
Two men seen from behind sitting at the edge of a dark courtyard at night, one gesturing toward a small rock hollow. medium shot, subject on a third line, layered foreground, midground and background for depth. over-the-shoulder from behind the figure. 35mm lens, f/2.8, shallow depth of field. moonlit cool fill with a single warm firelight or oil-lamp key, deep blacks. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S21 · 3:04 · d_025 — kb3d

```
A fox curled inside a narrow rock burrow, water running into the mouth of the burrow. close shot on hands, objects or a silhouette, clean negative space on one side of the frame. low camera angle looking up, heroic scale. 85mm lens, f/2, creamy background separation. moonlit cool fill with a single warm firelight or oil-lamp key, deep blacks. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S22 · 3:12 · d_026 — حيّ (GenerateVideo)

```
Two camels kneeling saddled in a dark valley before dawn, two cloaked men seen from behind approaching them, stars above. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. eye-level camera. 24mm anamorphic lens, f/5.6, deep focus. blue pre-dawn light, faint warm horizon line, stars fading. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S23 · 3:25 · d_027 — kb3d

```
The two riders seen from behind on camels in a wide valley at first light, path stretching to the horizon. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. high angle looking down, sense of vulnerability. 24mm anamorphic lens, f/5.6, deep focus. blue pre-dawn light, faint warm horizon line, stars fading. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S24 · 3:43 · d_028 — kb3d

```
An ancient Red Sea harbour in Abyssinia with a wooden ship far off, palms and mudbrick warehouses, seen from a hill. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. high angle looking down, sense of vulnerability. 24mm anamorphic lens, f/5.6, deep focus. hard low-angle desert sun, long shadows, warm key and cool sky fill. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S25 · 3:43 · d_028 d_029 — kb3d

```
A king seen from behind on a carved wooden throne in a dim hall, one raised hand, a visitor kneeling far away in shadow, no religious symbols. medium shot, subject on a third line, layered foreground, midground and background for depth. over-the-shoulder from behind the figure. 35mm lens, f/2.8, shallow depth of field. single shaft of daylight through a doorway, volumetric dust, dark falloff. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S26 · 4:19 · d_030 d_031 d_032 — kb3d

```
A man seen from behind leaving a palace gate at dusk toward the harbour, his shadow long ahead of him. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. eye-level camera. 24mm anamorphic lens, f/5.6, deep focus. golden-hour backlight, rim light on silhouettes, dust glowing in the air. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S27 · 4:41 · d_033 d_034 — حيّ (GenerateVideo)

```
Three riders seen from behind meeting at a desert crossroads at dawn, camels and a horse, soft mist. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. high angle looking down, sense of vulnerability. 24mm anamorphic lens, f/5.6, deep focus. blue pre-dawn light, faint warm horizon line, stars fading. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S28 · 4:49 · d_035 — حيّ (GenerateVideo)

```
The veiled rider seen from behind lifting his head toward a horizon that bursts with gold light, the path ahead lit. medium shot, subject on a third line, layered foreground, midground and background for depth. low camera angle looking up, heroic scale. 35mm lens, f/2.8, shallow depth of field. golden-hour backlight, rim light on silhouettes, dust glowing in the air. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S29 · 4:56 · d_036 d_037 — kb3d

```
Two riders seen from behind side by side on the lit road, their shadows merging. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. over-the-shoulder from behind the figure. 24mm anamorphic lens, f/5.6, deep focus. golden-hour backlight, rim light on silhouettes, dust glowing in the air. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S30 · 5:02 · d_038 — kb3d

```
The empty dawn road with the three riders small in the distance. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. high aerial view. 24mm anamorphic lens, f/5.6, deep focus. golden-hour backlight, rim light on silhouettes, dust glowing in the air. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S31 · 5:06 · d_039 — حيّ (GenerateVideo)

```
Three riders seen from behind kneeling their camels on black lava ground outside a palm-filled Medina at golden afternoon, a simple mosque of mudbrick walls and palm-trunk pillars in the distance. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. eye-level camera. 24mm anamorphic lens, f/5.6, deep focus. golden-hour backlight, rim light on silhouettes, dust glowing in the air. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S32 · 5:15 · d_040 — kb3d

```
Two men seen from behind walking quickly along a Medina lane between mudbrick walls and palm trunks. medium shot, subject on a third line, layered foreground, midground and background for depth. over-the-shoulder from behind the figure. 35mm lens, f/2.8, shallow depth of field. golden-hour backlight, rim light on silhouettes, dust glowing in the air. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S33 · 5:24 · d_041 d_042 — حيّ (GenerateVideo)

```
A shaft of golden light on a plain palm-leaf mat in a simple courtyard of palm-trunk pillars; a man seen from behind lowering himself respectfully at its edge. medium shot, subject on a third line, layered foreground, midground and background for depth. over-the-shoulder from behind the figure. 35mm lens, f/2.8, shallow depth of field. single shaft of daylight through a doorway, volumetric dust, dark falloff. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S34 · 5:30 · d_043 — kb3d

```
Close shot of a man's right hand extended forward in pledge, seen from behind his shoulder, warm light. close shot on hands, objects or a silhouette, clean negative space on one side of the frame. over-the-shoulder from behind the figure. 85mm lens, f/2, creamy background separation. single shaft of daylight through a doorway, volumetric dust, dark falloff. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S35 · 5:41 · d_044 d_045 d_046 — kb3d

```
The empty palm-leaf mat in the light shaft, a cloaked man seen from behind kneeling before it with bowed head. medium shot, subject on a third line, layered foreground, midground and background for depth. high angle looking down, sense of vulnerability. 35mm lens, f/2.8, shallow depth of field. single shaft of daylight through a doorway, volumetric dust, dark falloff. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S36 · 6:17 · d_047 d_048 d_049 — kb3d

```
Two more men seen from behind waiting their turn in the courtyard shade, palm-trunk pillars, soft dust in the air. medium shot, subject on a third line, layered foreground, midground and background for depth. eye-level camera. 35mm lens, f/2.8, shallow depth of field. single shaft of daylight through a doorway, volumetric dust, dark falloff. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S37 · 6:44 · d_050 d_051 — kb3d

```
The man seen from behind standing among a group of companions also seen from behind in a palm grove, at ease. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. eye-level camera. 24mm anamorphic lens, f/5.6, deep focus. golden-hour backlight, rim light on silhouettes, dust glowing in the air. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S38 · 6:56 · d_052 d_053 — kb3d

```
Callback: the prayer rows of Usfan seen from the ridge again, quieter light, the rider's place on the ridge empty. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. high angle looking down, sense of vulnerability. 24mm anamorphic lens, f/5.6, deep focus. golden-hour backlight, rim light on silhouettes, dust glowing in the air. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S39 · 7:05 · d_054 — حيّ (GenerateVideo)

```
A distant battlefield at Mu'tah in dust, a banner falling, then another banner falling further away, no bodies. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. high angle looking down, sense of vulnerability. 24mm anamorphic lens, f/5.6, deep focus. hard low-angle desert sun, long shadows, warm key and cool sky fill. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S40 · 7:05 · d_054 — حيّ (GenerateVideo)

```
A hand seen from behind raising a banner high above the dust, light breaking through. medium shot, subject on a third line, layered foreground, midground and background for depth. low camera angle looking up, heroic scale. 35mm lens, f/2.8, shallow depth of field. golden-hour backlight, rim light on silhouettes, dust glowing in the air. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S41 · 7:22 · d_055 — kb3d

```
Medina at dusk from a distance, palm groves and mudbrick houses, a quiet gathering of men seen from behind. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. high angle looking down, sense of vulnerability. 24mm anamorphic lens, f/5.6, deep focus. golden-hour backlight, rim light on silhouettes, dust glowing in the air. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S42 · 7:36 · d_056 — حيّ (GenerateVideo)

```
Nine broken straight swords lying on sand in a row, and one intact Yemeni blade at the end catching the light. insert detail shot, tactile texture, shallow focus. high angle looking down, sense of vulnerability. 100mm macro lens, f/4. golden-hour backlight, rim light on silhouettes, dust glowing in the air. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

### S43 · 7:47 · d_057 d_058 — حيّ (GenerateVideo)

```
Mirror of the opening: the same dune ridge and the same veiled rider seen from behind, now in warm dawn light facing the open horizon. wide establishing shot, rule-of-thirds horizon, strong leading lines into depth, foreground element for parallax. over-the-shoulder from behind the figure. 24mm anamorphic lens, f/5.6, deep focus. blue pre-dawn light, faint warm horizon line, stars fading. period details: 7th-century Hijaz and Levant: sun-dried mudbrick, palm-trunk pillars and palm-frond roofs, black goat-hair tents, Arabian horses and camels with simple leather saddles and no stirrups, straight double-edged swords in leather scabbards, round leather or wooden shields, mail shirts, plain wool and linen robes, turbans and face-veils (litham), clay oil lamps, rolled parchment. cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail. all human figures seen from behind, in silhouette, at distance, or with faces hidden by shadow or litham; adult men only. no women, no visible faces, no prophets, no crosses, no religious inscriptions or Quranic text, no blood or gore, no domes, no minarets, no stirrups, no curved scimitars, no gunpowder, no modern objects, no fantasy armour. No text, no letters, no captions, no watermark.
```

## ٤) خطة التحريك

الحركة من الشعور (`tools/motion_plan.py`) لا من رقم اللقطة. الحيّ لكلّ لقطة مهمّة (أول 30 ث، الصلاة، الذروة، لحظة الإسلام، مؤتة، الختام). بعد التصيير: `motion_plan.py clip kb3d|live|action` (رعشة/تجمّد) — المرفوض يُعاد بحركة كاميرا ثابتة.

| اللقطة | ~الوقت | الشعور | النوع | الحركة | التسارع | الشدّة | الانتقال إليها | وصف الحركة الحيّة |
|---|---|---|---|---|---|---|---|---|
| S01 | 0:00 | tension | live | — | — | — | fade | slow push past the rider's shoulder toward the distant rows, horse tail flicks, dust drifts; camera steady, no shake |
| S02 | 0:07 | tension | live | — | — | — | fade | cloaks and horse manes move in the wind, riders shift in saddles, camera locked off then a very slow push |
| S03 | 0:14 | revelation | live | — | — | — | fadewhite | slow dolly in on the sheathed sword hilt, rim light flares softly |
| S04 | 0:19 | awe | live | — | — | — | fade | slow aerial crane forward along the hoofprints |
| S05 | 0:22 | reflection | live | — | — | — | fade | heat haze shimmers, a camel turns its head; slow lateral truck |
| S06 | 0:27 | awe | live | — | — | — | fade | near-static, only robes stirring in the wind; extremely slow crane up |
| S07 | 0:39 | reflection | live | — | — | — | fade | static frame, only wind in the cloak; a slow breath of the horse |
| S08 | 0:43 | reflection | kb3d | dolly_in | inout | 0.55 | fade | — |
| S09 | 1:00 | action | live | — | — | — | whip | riders sweep around the hill left to right, camera trucks with them smoothly |
| S10 | 1:04 | action | kb3d | truck_r | soft | 1.25 | whip | — |
| S11 | 1:08 | map | kb3d | dolly_in | inout | 0.4 | fade | — |
| S12 | 1:21 | action | live | — | — | — | whip | gallop away from camera, dust kicks up, camera tracks low and steady |
| S13 | 1:28 | reflection | kb3d | dolly_in | inout | 0.55 | fade | — |
| S14 | 1:41 | tension | kb3d | push_tilt | in | 0.9 | fade | — |
| S15 | 1:44 | reflection | kb3d | dolly_in | inout | 0.55 | fade | — |
| S16 | 2:02 | grief | kb3d | dolly_out | inout | 0.5 | fade | — |
| S17 | 2:11 | revelation | live | — | — | — | fadewhite | the hand slowly unfolds the parchment, flame flickers gently; camera static |
| S18 | 2:16 | grief | kb3d | dolly_out | inout | 0.5 | fade | — |
| S19 | 2:46 | journey | kb3d | truck_r | soft | 0.8 | fade | — |
| S20 | 2:57 | tension | kb3d | dolly_in | in | 0.9 | fade | — |
| S21 | 3:04 | tension | kb3d | push_tilt | in | 0.9 | fade | — |
| S22 | 3:12 | journey | live | — | — | — | fade | a camel rises slowly, men walk toward it, stars fade; camera static |
| S23 | 3:25 | journey | kb3d | truck_r | soft | 0.8 | fade | — |
| S24 | 3:43 | journey | kb3d | truck_l | soft | 0.8 | fade | — |
| S25 | 3:43 | tension | kb3d | dolly_in | in | 0.9 | fade | — |
| S26 | 4:19 | revelation | kb3d | reveal | out | 0.75 | fadewhite | — |
| S27 | 4:41 | journey | live | — | — | — | fade | two riders converge from left and right toward a third, slow lateral move |
| S28 | 4:49 | revelation | live | — | — | — | fadewhite | slow push toward the horizon as the light grows, cloak lifts in the breeze; camera smooth |
| S29 | 4:56 | journey | kb3d | truck_r | soft | 0.8 | fade | — |
| S30 | 5:02 | awe | kb3d | crane_up | out | 0.8 | fade | — |
| S31 | 5:06 | awe | live | — | — | — | fade | camels kneel slowly, palms sway, warm light; camera crane down gently |
| S32 | 5:15 | journey | kb3d | truck_r | soft | 0.8 | fade | — |
| S33 | 5:24 | revelation | live | — | — | — | fadewhite | dust motes drift in the light shaft, the man bows his head slowly; camera static |
| S34 | 5:30 | revelation | kb3d | dolly_in | out | 0.75 | fadewhite | — |
| S35 | 5:41 | reflection | kb3d | dolly_out | inout | 0.55 | fade | — |
| S36 | 6:17 | reflection | kb3d | dolly_in | inout | 0.55 | fade | — |
| S37 | 6:44 | awe | kb3d | crane_up | out | 0.8 | fade | — |
| S38 | 6:56 | reflection | kb3d | dolly_in | inout | 0.55 | fade | — |
| S39 | 7:05 | grief | live | — | — | — | fade | banners fall one after another in the dust far away; camera slow push |
| S40 | 7:05 | awe | live | — | — | — | fade | the banner rises and unfurls in the wind; slow crane up |
| S41 | 7:22 | grief | kb3d | dolly_out | inout | 0.5 | fade | — |
| S42 | 7:36 | aftermath | live | — | — | — | fade | very slow lateral move along the broken blades, dust settling |
| S43 | 7:47 | awe | live | — | — | — | fade | slow push past the rider toward the horizon, light rises; ends still |

43 لقطة: 19 حيّة و24 kb3d (منها خريطة واحدة). متوسّط اللقطة ~11.2 ث؛ تُقسَّم اللقطات الأطول من 8 ث عند المونتاج بلقطة ثانية من الأمر نفسه بحجم آخر.

## ٥) أوامر المرحلة التالية (بالترتيب)

```
python3 tools/casting.py md proj && (voice_lab بعيّنات الأصوات) && python3 tools/casting.py apply proj
python3 tools/text_gate.py … && python3 tools/pre_generate.py …   # قبل أي توليد
# GenerateImage بالأوامر أعلاه ⇐ python3 tools/image_prompts.py gate proj images/*.jpg
# GenerateVideo للحيّ ⇐ python3 tools/motion_plan.py clip live clips/*.mp4
python3 tools/motion_plan.py lint proj && python3 tools/sfx_cues.py lint proj
python3 tools/mont_hybrid.py proj 0.30   # يصيّر المؤثّرات من الورقة ويشغّل بوّابة المزج ويتوقّف عند أي خلل
```
