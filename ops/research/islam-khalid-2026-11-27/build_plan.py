# -*- coding: utf-8 -*-
"""يبني خطة إنتاج «إسلام خالد» (2026-11-27): الأصوات، وورقة المؤثّرات، وقائمة اللقطات وأوامر الصور، وخطة التحريك —
ويشغّل بوّابات المصنع الجديدة عليها. لا توليد ولا نشر."""
import json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
FAC = os.environ.get('MF_TOOLS', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), 'tools'))
sys.path.insert(0, FAC)
import sfx_cues, image_prompts as ip, motion_plan as mp, casting, live_share  # noqa: E402

P = os.path.join(HERE, 'proj')
L = [l.rstrip('\n') for l in open(os.path.join(HERE, 'script.md'), encoding='utf-8') if re.match(r'd_\d+\|', l)]
blocks = [dict(zip(('id', 'role', 'text'), l.split('|', 2))) for l in L]
MEDINA = {'d_039', 'd_040', 'd_041', 'd_042', 'd_043', 'd_044', 'd_045', 'd_046', 'd_047', 'd_048', 'd_049', 'd_050', 'd_051'}
for b in blocks:
    if b['id'] in MEDINA and b['role'] == 'N':
        b['pos'] = 'medina'
json.dump(blocks, open(os.path.join(P, 'blocks.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
bt = {k: tuple(v) for k, v in json.load(open(os.path.join(P, 'real_timing.json')))['bt'].items()}  # أوقات حقيقية من الصوت المُصيَّر

# ── ١) الأصوات ──────────────────────────────────────────────────────────────────────────────────
CAST = {
 'title': 'إسلام خالد بن الوليد', 'series': 'sayf-allah',
 'narrator': {'voice': 'Algenib', 'style': 'epic', 'pos_styles': {'medina': 'reverent'},
              'reason': 'راوي السلسلة (فائز مختبر الأصوات في مؤتة واليمامة): أجشّ وقور يحمل الملحمة؛ القصة تأمّلية أكثر من المعارك، '
                        'فيُطلب في التوجيه إيقاعٌ أبطأ قليلاً في ف3 وف6، وأسلوب «reverent» بلا انفعال في مشاهد المدينة'},
 'characters': {
  'khalid': {'name': 'خالد بن الوليد', 'voice': 'Algieba', 'style': 'quote',
             'reason': 'صوت خالد في السلسلة (فائز دور الاقتباس في مختبر مؤتة على قوله «انقطعت في يدي تسعة أسياف»): ناعم ثابت بلا تمثيل؛ '
                       'حواره الداخلي (ف1، ف3) أخفض وأبطأ، وإعلانه «فحتى متى؟» أحزم'},
  'amr': {'name': 'عمرو بن العاص', 'voice': 'Charon', 'style': 'quote',
          'reason': 'أسنّ من خالد وداهية العرب: صوت أعمق وأكثر رزانة، يختلف عن خالد بالطبقة حتى يميّزه السامع في حوار الطريق (d_034–d_037)'},
  'walid': {'name': 'الوليد بن الوليد (أخو خالد)', 'voice': 'Umbriel', 'style': 'quote',
            'reason': 'الأخ الأصغر يكتب بمودّة وإلحاح: صوت أخفّ وأدفأ من خالد، وكتابه يُقرأ قراءةً لا تمثيلاً'},
  'najashi': {'name': 'النجاشي', 'voice': 'Rasalgethi', 'style': 'quote',
              'reason': 'ملكٌ وقور غاضبٌ ثم ناصح: صوتٌ فصيح مهيب (أجاد الإلقاء في مختبر مؤتة)، مختلف عن عمرو الذي يحاوره'},
  'quraysh': {'name': 'فرسان قريش (جماعة)', 'voice': 'Fenrir', 'style': 'quote',
              'reason': 'صيحة جماعةٍ مستعجلة «لقد أصبنا غرّة!»: صوتٌ منفعل حادّ يقابل سكينة المصلّين، ولا يُستعمل لغيرهم'}},
 'blocks': {'d_002': 'quraysh', 'd_008': 'khalid', 'd_010': 'khalid', 'd_017': 'khalid', 'd_020': 'walid', 'd_021': 'walid',
            'd_023': 'khalid', 'd_025': 'khalid', 'd_029': 'najashi', 'd_031': 'najashi', 'd_034': 'amr', 'd_035': 'khalid',
            'd_037': 'amr', 'd_040': 'walid', 'd_043': 'khalid', 'd_045': 'khalid', 'd_048': 'amr', 'd_051': 'khalid',
            'd_053': 'khalid'},
 'alternates': {'khalid': ['Algieba', 'Iapetus'], 'amr': ['Charon', 'Schedar'], 'walid': ['Umbriel', 'Achird'],
                'najashi': ['Rasalgethi', 'Alnilam'], 'quraysh': ['Fenrir', 'Orus']},
 'samples': {'status': 'approved', 'notes': 'أمر المالك 2026-11-27: لا عيّنات ولا إجازة مالك؛ الوكيل اختار الأصوات الأساسية بنفسه (الراوي Algenib، خالد Algieba، عمرو Charon، الوليد Umbriel، النجاشي Rasalgethi، قريش Fenrir) والأسباب أعلاه.'}}
json.dump(CAST, open(os.path.join(P, 'casting.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ── ٢) ورقة المؤثّرات ────────────────────────────────────────────────────────────────────────────
K = ['d_006', 'd_021', 'd_035', 'd_041', 'd_043', 'd_055']   # الصلاة بإمامة النبي ﷺ، الذروة، لحظة الإسلام، الشهادة (والآلية تضيف كلام النبي ﷺ)
C = lambda i, b, e, why, **k: dict(id='c%02d' % i, block=b, event=e, why=why, **k)
CUES = {'key_blocks': K, 'cues': [
 C(1, 'd_001', 'wind', 'كثيبٌ مكشوف في عسفان: الريح وحدها تحمل الافتتاح', at=0, dur=16, level=-24),
 C(2, 'd_001', 'horse_snort', 'خيل المشركين على الكثيب: نخرة فرسٍ واحدة تعلن وجودهم', anchor='خيل'),
 C(3, 'd_002', 'silence', 'صمتٌ عند «لو حملنا عليهم» (توجيه السيناريو)', anchor='لو', dur=1.4),
 C(4, 'd_003', 'hooves', 'سؤال «فهل حمل خالد عليهم؟»: حوافر تقترب ثم تتوقّف (الجواب لا)', anchor='حمل', dur=2.2, level=-22),
 C(5, 'd_005', 'wind', 'عسفان بين الظهر والعصر: فرشٌ خفيف قبل مشهد الصلاة', at=0, dur=4.5, level=-26),
 C(6, 'd_007', 'wind', 'قطع إلى خالد من الخلف: ريح ثم صمت (توجيه السيناريو)', at=0, dur=3, level=-24),
 C(7, 'd_008', 'silence', '«الرجل ممنوع»: نصف ثانية صمت', at=0, dur=1.2),
 C(8, 'd_011', 'gallop', 'أُحُد: خيل قريش تدور حول التلّ', anchor='خيل', dur=5, level=-23),
 C(9, 'd_012', 'battle', 'دخلت الخيل والتبست الصفوف: التحامٌ بعيد بلا دم', at=0.4, dur=3.0, level=-25),
 C(10, 'd_014', 'hooves', 'خالد يركض نذيراً لقريش', anchor='يركض', offset=-1.2, dur=2.0),
 C(11, 'd_016', 'fire', 'بيتٌ مكّي ليلاً بضوء مصباح: لهبٌ خافت', at=0, dur=14, level=-28),
 C(12, 'd_019', 'leather', 'كتاب الوليد يُفتح بيد: رقٌّ وجلد', anchor='فكتب', offset=-1.0, dur=1.2, level=-22),
 C(13, 'd_023', 'footsteps', '«نشطت للخروج»: خطوات خالد تخرج من البيت', anchor='للخروج', dur=2.5, level=-22),
 C(14, 'd_026', 'camels', '«هذه راحلتي بفخّ مناخة»: رغاء راحلة تُنهَض', anchor='راحلتي', dur=2.5),
 C(15, 'd_026', 'wind', 'وادٍ في ظلمة ما قبل الفجر', anchor='الفجر', dur=7, level=-26),
 C(16, 'd_028', 'sea', 'الحبشة: ميناءٌ وسفينة من بعيد', anchor='الحبشة', dur=7, level=-26),
 C(17, 'd_033', 'camels', 'لقاء الركبين في الطريق', anchor='الطريق', dur=2.5, level=-22),
 C(18, 'd_033', 'wind', 'مفترق الطريق في الفجر: ريح وحوافر بعيدة', anchor='الطريق', offset=0.5, dur=6, level=-25),
 C(19, 'd_035', 'silence', 'ذروة «فحتى متى؟»: صمتٌ كامل قبل الكلمة الأخيرة', anchor='فحتى', offset=-0.5, dur=1.2),
 C(20, 'd_039', 'camels', 'ثلاثة ركبان ينيخون على الحرّة عند المدينة', anchor='المدينة', dur=2.5, level=-22),
 C(21, 'd_039', 'wind', 'المدينة عصراً: ريحٌ خفيفة (توجيه السيناريو)', anchor='المدينة', offset=1.0, dur=9, level=-27),
 C(22, 'd_042', 'footsteps', 'خطوات على الرمل نحو المجلس قبل الشهادة', at=0, dur=2.5, level=-23),
 C(23, 'd_054', 'battle', 'مؤتة: ساحة بعيدة بالغبار', anchor='مؤتة', dur=6, level=-26),
 C(24, 'd_054', 'banner', 'الرايات تسقط واحدة بعد أخرى ثم تُرفع بيد خالد', anchor='الراية', dur=9, level=-24),
 C(25, 'd_056', 'sword_clash', '«انقطعت في يدي تسعة أسياف»: ضربةٌ واحدة لا تسع', anchor='انقطعت', level=-20),
 C(26, 'd_056', 'sword_draw', '«صفيحة يمانية»: النصل الأخير', anchor='صفيحة', level=-21),
 C(27, 'd_057', 'wind', 'العودة إلى الكثيب الأول بالضوء الآخر (انعكاس الافتتاح)', at=0, dur=9, level=-26),
 C(28, 'd_058', 'silence', 'آخر ثانيتين صمت ثم شاشة النهاية', anchor='سيوف', dur=2.5),
]}
# ضبط بالأذن والقياس على المزج الحقيقي (2026-11-27): المؤثّرات الفعلية كانت أخفض من قيم الإشارات بـ2–8 dB؛ رُفعت ضمن السقوف
LEVEL_FIX = {'c04': -20, 'c05': -24, 'c06': -22, 'c08': -22, 'c12': -18, 'c13': -19, 'c14': -19, 'c22': -21, 'c25': -18, 'c26': -18}
for _c in CUES['cues']:
    if _c['id'] in LEVEL_FIX:
        _c['why'] += ' (رُفع من %s إلى %s dB بعد قياس المزج الفعلي)' % (_c.get('level'), LEVEL_FIX[_c['id']])
        _c['level'] = LEVEL_FIX[_c['id']]
json.dump(CUES, open(os.path.join(P, 'sfx_cues.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ── ٣) دليل الأسلوب وقائمة اللقطات ────────────────────────────────────────────────────────────────
BIBLE = {'look': 'cinematic historical documentary still, photoreal, palette of warm ochre sand, umber shadows and dusk blue, '
                 'with gold light reserved for moments of guidance, soft 35mm film grain, gentle halation, high dynamic range, crisp micro-detail',
         'motif': 'the same lone dune ridge and the same veiled rider seen from behind opens and closes the film'}
json.dump(BIBLE, open(os.path.join(P, 'style_bible.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
S = lambda i, blocks, subj, size, angle, light, emo, kind='kb3d', **k: dict(id='S%02d' % i, blocks=blocks, subject=subj, size=size,
                                                                          angle=angle, light=light, emotion=emo, kind=kind, **k)
SH = [
 S(1, ['d_001'], 'A lone veiled rider seen from behind on a high dune ridge at Usfan, his horse restless, and far below him long rows of worshippers seen from behind standing in prayer on open sand', 'wide', 'over', 'day', 'tension', 'live', hook=True, video_prompt='slow push past the rider\'s shoulder toward the distant rows, horse tail flicks, dust drifts; camera steady, no shake'),
 S(2, ['d_002'], 'A line of Quraysh horsemen seen from behind on the ridge, lances upright, cloaks snapping in the wind, the prayer rows small in the valley', 'wide', 'low', 'day', 'tension', 'live', hook=True, video_prompt='cloaks and horse manes move in the wind, riders shift in saddles, camera locked off then a very slow push'),
 S(3, ['d_003'], 'Silhouette of the veiled rider from behind, sword still sheathed at his side, sun behind him', 'medium', 'low', 'golden', 'revelation', 'live', hook=True, video_prompt='slow dolly in on the sheathed sword hilt, rim light flares softly'),
 S(4, ['d_004'], 'The dune ridge at Usfan in hard afternoon light, a single set of hoofprints leading away along the crest', 'wide', 'aerial', 'golden', 'awe', 'live', video_prompt='slow aerial crane forward along the hoofprints'),
 S(5, ['d_005'], 'Open plain of Usfan between noon and afternoon, heat haze, distant black goat-hair tents and tethered camels', 'wide', 'eye', 'day', 'reflection', 'live', video_prompt='heat haze shimmers, a camel turns its head; slow lateral truck'),
 S(6, ['d_006'], 'Two rows of worshippers seen from behind: one row bowing in prayer, the second row standing guard behind them with sheathed swords, no leader visible in frame', 'wide', 'high', 'day', 'awe', 'live', key=True, video_prompt='near-static, only robes stirring in the wind; extremely slow crane up'),
 S(7, ['d_007', 'd_008'], 'The veiled rider seen from behind on the ridge, shoulders lowered, hand loosening on the reins', 'medium', 'over', 'day', 'reflection', 'live', key=True, video_prompt='static frame, only wind in the cloak; a slow breath of the horse'),
 S(8, ['d_009', 'd_010'], 'A lone rider seen from behind riding away from a dusty field at dusk, a column of riders far ahead of him', 'wide', 'eye', 'golden', 'reflection'),
 S(9, ['d_011'], 'Quraysh cavalry seen from a distance circling behind a rocky hill at Uhud, dust trailing, no faces visible', 'wide', 'high', 'day', 'action', 'live', video_prompt='riders sweep around the hill left to right, camera trucks with them smoothly'),
 S(10, ['d_012'], 'Distant clash below a low hill, ranks of men in silhouette merging in a cloud of dust, archers\' hill empty in the foreground', 'wide', 'high', 'day', 'action'),
 S(11, ['d_013'], 'Simple top-down relief map of the road to Hudaybiyya, plain sand texture, one arrow of fine dust curving to the right, no writing', 'wide', 'aerial', 'day', 'map'),  # بلا map=True: battlemap يحتاج مواصفة خريطة؛ الصورة نفسها خريطة رملية ⇒ kb3d بطيء
 S(12, ['d_014'], 'A rider seen from behind galloping along a valley floor toward distant hills, a wall of dust rising on the horizon behind him', 'wide', 'low', 'day', 'action', 'live', video_prompt='gallop away from camera, dust kicks up, camera tracks low and steady'),
 S(13, ['d_015'], 'Empty open plain at Hudaybiyya at dusk, an acacia tree alone, a tethered camel resting', 'wide', 'eye', 'golden', 'reflection'),
 S(14, ['d_016', 'd_017'], 'A man seen from behind standing at the doorway of a Meccan mudbrick house at night, clay oil lamp on a niche, long shadow on the ground', 'medium', 'over', 'night', 'tension'),
 S(15, ['d_017'], 'Three dark roads branching from a single point in a moonlit desert, one toward the sea, one north, one back toward a sleeping town', 'wide', 'aerial', 'night', 'reflection'),
 S(16, ['d_018'], 'Distant view of Mecca\'s valley of mudbrick houses at dawn, a long column of pilgrims in white entering from the far side, one house\'s doorway closed and dark in the foreground', 'wide', 'high', 'dawn', 'grief'),
 S(17, ['d_019', 'd_020'], 'Close shot of a man\'s hand holding a folded parchment by an oil lamp, the writing not legible, warm flame light', 'detail', 'eye', 'interior', 'revelation', 'live', video_prompt='the folded parchment stays closed in the hand, only the lamp flame flickers and dust drifts; camera static, no writing ever visible'),
 S(18, ['d_020', 'd_021'], 'A row of horsemen seen from behind on a ridge with one gap in the line where a rider is missing, an empty space', 'wide', 'eye', 'golden', 'grief'),
 S(19, ['d_022', 'd_023'], 'The man seen from behind stepping out of the doorway into the moonlit street, lamp left burning behind him', 'medium', 'over', 'night', 'journey'),
 S(20, ['d_024', 'd_025'], 'Two men seen from behind sitting at the edge of a dark courtyard at night, one gesturing toward a small rock hollow', 'medium', 'over', 'night', 'tension'),
 S(21, ['d_025'], 'A fox curled inside a narrow rock burrow, water running into the mouth of the burrow', 'close', 'low', 'night', 'tension'),
 S(22, ['d_026'], 'Two camels kneeling saddled in a dark valley before dawn, two cloaked men seen from behind approaching them, stars above', 'wide', 'eye', 'dawn', 'journey', 'live', video_prompt='a camel rises slowly, men walk toward it, stars fade; camera static'),
 S(23, ['d_027'], 'The two riders seen from behind on camels in a wide valley at first light, path stretching to the horizon', 'wide', 'high', 'dawn', 'journey'),
 S(24, ['d_028'], 'An ancient Red Sea harbour in Abyssinia with a wooden ship far off, palms and mudbrick warehouses, seen from a hill', 'wide', 'high', 'day', 'journey'),
 S(25, ['d_028', 'd_029'], 'A king seen from behind on a carved wooden throne in a dim hall, one raised hand, a visitor kneeling far away in shadow, no religious symbols', 'medium', 'over', 'interior', 'tension'),
 S(26, ['d_030', 'd_031', 'd_032'], 'A man seen from behind leaving a palace gate at dusk toward the harbour, his shadow long ahead of him', 'wide', 'eye', 'golden', 'revelation'),
 S(27, ['d_033', 'd_034'], 'Three riders seen from behind meeting at a desert crossroads at dawn, camels and a horse, soft mist', 'wide', 'high', 'dawn', 'journey', 'live', video_prompt='two riders converge from left and right toward a third, slow lateral move'),
 S(28, ['d_035'], 'The veiled rider seen from behind lifting his head toward a horizon that bursts with gold light, the path ahead lit', 'medium', 'low', 'golden', 'revelation', 'live', climax=True, video_prompt='slow push toward the horizon as the light grows, cloak lifts in the breeze; camera smooth'),
 S(29, ['d_036', 'd_037'], 'Two riders seen from behind side by side on the lit road, their shadows merging', 'wide', 'over', 'golden', 'journey'),
 S(30, ['d_038'], 'The empty dawn road with the three riders small in the distance', 'wide', 'aerial', 'golden', 'awe'),
 S(31, ['d_039'], 'Three riders seen from behind kneeling their camels on black lava ground outside a palm-filled Medina at golden afternoon, a simple mosque of mudbrick walls and palm-trunk pillars in the distance', 'wide', 'eye', 'golden', 'awe', 'live', key=True, video_prompt='camels kneel slowly, palms sway, warm light; camera crane down gently'),
 S(32, ['d_040'], 'Two men seen from behind walking quickly along a Medina lane between mudbrick walls and palm trunks', 'medium', 'over', 'golden', 'journey'),
 S(33, ['d_041', 'd_042'], 'A shaft of golden light on a plain palm-leaf mat in a simple courtyard of palm-trunk pillars; a man seen from behind lowering himself respectfully at its edge', 'medium', 'over', 'interior', 'revelation', 'live', key=True, video_prompt='dust motes drift in the light shaft, the man bows his head slowly; camera static'),
 S(34, ['d_043'], 'Close shot of a man\'s right hand extended forward in pledge, seen from behind his shoulder, warm light', 'close', 'over', 'interior', 'revelation'),
 S(35, ['d_044', 'd_045', 'd_046'], 'The empty palm-leaf mat in the light shaft, a cloaked man seen from behind kneeling before it with bowed head', 'medium', 'high', 'interior', 'reflection'),
 S(36, ['d_047', 'd_048', 'd_049'], 'Two more men seen from behind waiting their turn in the courtyard shade, palm-trunk pillars, soft dust in the air', 'medium', 'eye', 'interior', 'reflection'),
 S(37, ['d_050', 'd_051'], 'The man seen from behind standing among a group of companions also seen from behind in a palm grove, at ease', 'wide', 'eye', 'golden', 'awe'),
 S(38, ['d_052', 'd_053'], 'Callback: the prayer rows of Usfan seen from the ridge again, quieter light, the rider\'s place on the ridge empty', 'wide', 'high', 'golden', 'reflection'),
 S(39, ['d_054'], 'A distant battlefield at Mu\'tah in dust, a banner falling, then another banner falling further away, no bodies', 'wide', 'high', 'day', 'grief', 'live', key=True, video_prompt='banners fall one after another in the dust far away; camera slow push'),
 S(40, ['d_054'], 'A hand seen from behind raising a banner high above the dust, light breaking through', 'medium', 'low', 'golden', 'awe', 'live', key=True, video_prompt='the banner rises and unfurls in the wind; slow crane up'),
 S(41, ['d_055'], 'Medina at dusk from a distance, palm groves and mudbrick houses, a quiet gathering of men seen from behind', 'wide', 'high', 'golden', 'grief'),
 S(42, ['d_056'], 'Nine broken straight swords lying on sand in a row, and one intact Yemeni blade at the end catching the light', 'detail', 'high', 'golden', 'aftermath', 'live', video_prompt='very slow lateral move along the broken blades, dust settling'),
 S(43, ['d_057', 'd_058'], 'Mirror of the opening: the same dune ridge and the same veiled rider seen from behind, now in warm dawn light facing the open horizon', 'wide', 'over', 'dawn', 'awe', 'live', climax=True, video_prompt='slow push past the rider toward the horizon, light rises; ends still'),
]
json.dump(SH, open(os.path.join(P, 'shotlist.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
mp.apply(SH)
starts = [bt[s['blocks'][0]][0] for s in SH]
# ── حركة احتياطية للّقطات الحيّة — كانت تُطبَّق صامتةً (ثغرة «إسلام خالد»: خُطّط 28٪ وظهر نحو 5٪).
#    لا تُطبَّق الآن إلا مع ALLOW_LIVE_FALLBACK=1 أو إعفاء في live_waivers.json، ومع تحذير واضح. kb3d لا يُحسب حيّاً.
#    ملاحظات المراجعة: S13 وS24 فيهما أشخاص صغار بعيدون مواجهون ⇒ حركة لا تكبّرهم؛ S17 كتابة زائفة ⇒ تُموَّه ولا يُقرَّب منها؛ لا تكبير لوجه.
LIVE_KB3D_RESERVE = {
 'S01': ('dolly_in', 1.25, 'in'),    'S02': ('truck_r', 1.2, 'soft'),    'S03': ('crane_up', 1.1, 'out'),
 'S04': ('reveal', 1.2, 'out'),      'S05': ('dolly_out', 0.8, 'inout'), 'S06': ('crane_up', 1.15, 'out'),
 'S07': ('dolly_out', 0.8, 'inout'), 'S09': ('truck_l', 1.4, 'soft'),    'S12': ('push_tilt', 1.4, 'soft'),
 'S17': ('dolly_in', 0.5, 'inout'),  'S22': ('truck_l', 1.0, 'soft'),    'S27': ('truck_l', 1.0, 'soft'),
 'S28': ('crane_up', 1.2, 'out'),    'S31': ('reveal', 1.2, 'out'),      'S33': ('crane_up', 1.0, 'out'),
 'S39': ('crane_up', 1.0, 'inout'),  'S40': ('reveal', 1.3, 'out'),      'S42': ('crane_up', 0.8, 'inout'),
 'S43': ('dolly_out', 0.9, 'out'),
}
QA_FIX = {'S13': {'move3d': 'dolly_out', 'energy': 0.5, 'qa': 'أشخاص صغار بعيدون: لا تقريب'},
          'S24': {'energy': 0.5, 'qa': 'أشخاص صغار بعيدون: لا تقريب'},
          'S17': {'qa': 'كتابة زائفة: الصورة مموّهة في منطقة الرقّ (images_src/ الأصل)'}}
# motion_plan.py clip على المقاطع المصيَّرة: تجمّد في اللقطات الطويلة (S14 6.2 ث، S18 10 ث، S26 2.1، S36 1.9) ⇒ طاقة أعلى
ENERGY_FIX = {'S14': 1.15, 'S18': 1.3, 'S26': 1.15, 'S36': 1.1}
for _s in SH:
    if _s['id'] in ENERGY_FIX:
        _s['energy'] = ENERGY_FIX[_s['id']]; _s['ease'] = 'soft'   # inout يقف عند الطرفين في اللقطة الطويلة
    _s.update(QA_FIX.get(_s['id'], {}))
_applied, _fw = live_share.apply_kb3d_reserve(SH, LIVE_KB3D_RESERVE, waivers=live_share.load_waivers(P))
for _w in _fw:
    print(_w, flush=True)

# ── إيقاع اللقطات (thrill_gate: المتوسّط 10.4 ث > 6): كل لقطةٍ متعدّدة الكتل طولها ≥ 12 ث تُقسَم لقطةً لكل كتلة
#    على الصورة نفسها (حقل file) بحركةٍ مختلفة — بلا صور جديدة ولا صوت جديد. الأجزاء kb3d بلا key (الأصل يحمل الأهمية).
SPLIT_MIN = 12.0
_out = []
for _i, _s in enumerate(SH):
    _len = bt[_s['blocks'][-1]][1] - bt[_s['blocks'][0]][0]
    if len(_s['blocks']) < 2 or _len < SPLIT_MIN:
        _out.append(_s); continue
    _moves = mp.EMOTIONS[_s['emotion']][0]
    _nxt = SH[_i + 1].get('move3d') if _i + 1 < len(SH) else None
    _first = dict(_s, blocks=[_s['blocks'][0]]); _out.append(_first)
    _prev = _first.get('move3d') if _first.get('kind') != 'live' else None
    for _k, _b in enumerate(_s['blocks'][1:], 1):
        _last = _k == len(_s['blocks']) - 1
        _m = next((m for m in _moves if m != _prev and not (_last and m == _nxt)), _moves[0])
        _sub = {k: v for k, v in _s.items() if k not in ('key', 'hook', 'climax', 'video_prompt', 'qa')}
        _sub.update(id='%s%s' % (_s['id'], 'bcdefg'[_k - 1]), blocks=[_b], file=_s['id'] + '.jpg', kind='kb3d',
                    move3d=_m, ease='soft', energy=max(0.8, _s.get('energy', 0.8)), tr='fade')
        _out.append(_sub); _prev = _m
SH[:] = _out
starts = [bt[s['blocks'][0]][0] for s in SH]
json.dump(SH, open(os.path.join(P, 'shots.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ── البوّابات ────────────────────────────────────────────────────────────────────────────────────
bb = ip.bible(P)
prom = [(s, ip.compose(s, bb)) for s in SH]
gates = {
 'casting': casting.check(CAST, blocks, casting.load(casting.SERIES) if os.path.exists(casting.SERIES) else {}),
 'sfx': sfx_cues.lint(CUES, blocks, bt),
 'images': ['%s: %s' % (s['id'], e) for s, p in prom for e in ip.lint(p)],
 'motion': mp.lint(SH, starts),
}
covered = {b for s in SH for b in s['blocks']}
gates['coverage'] = ['%s بلا لقطة' % b['id'] for b in blocks if b['id'] not in covered]
json.dump(gates, open(os.path.join(P, 'gates.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k, v in gates.items():
    print(k, 'OK' if not v else v)
json.dump({'bt': bt, 'prompts': {s['id']: p for s, p in prom}}, open(os.path.join(P, '_plan_data.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# ── ٤) production_plan.md ───────────────────────────────────────────────────────────────────────
subprocess.run([sys.executable, os.path.join(FAC, 'casting.py'), 'md', P], check=True, capture_output=True)
fmt = lambda t: '%d:%02d' % (int(t) // 60, int(t) % 60)
by = {b['id']: b for b in blocks}
keys = sorted(sfx_cues.key_blocks(CUES, blocks))
o = ['# خطة إنتاج «إسلام خالد بن الوليد» — 2026-11-27', '',
     '> مبنيّة على `script.md` (58 كتلة، المدة الحقيقية 8:58 من الصوت المُصيَّر) بأدوات المصنع الجديدة (أمر المالك 2026-11-27: جودة المؤثّرات والصور والتحريك، واختيار الأصوات لكلّ سيناريو). '
     'لا توليد ولا نشر هنا. ملفّات المشروع الآلية في `proj/` (blocks · casting · sfx_cues · style_bible · shotlist · shots). '
     'الأوقات **تقديرية** (0.5627 ث/كلمة) وتُعاد من الصوت الفعليّ عند المونتاج.', '',
     '## البوّابات على هذه الخطة', '', '```',
     'python3 tools/casting.py check proj        → ' + ('✓' if not gates['casting'] else '⛔'),
     'python3 tools/sfx_cues.py lint proj        → ' + ('✓ %d إشارة' % len(CUES['cues']) if not gates['sfx'] else '⛔'),
     'python3 tools/image_prompts.py prompts proj → ' + ('✓ %d أمر' % len(SH) if not gates['images'] else '⛔'),
     'python3 tools/motion_plan.py lint proj     → ' + ('✓' if not gates['motion'] else '⛔'),
     'تغطية الكتل باللقطات                        → ' + ('✓ 58/58' if not gates['coverage'] else '⛔'), '```', '',
     '## ⚠️ تصحيحان على توجيهات السيناريو البصرية', '',
     '- ف6: «قبّة/ساحة المسجد النبوي» ⇐ **لا قبّة** (مفارقة عصر: المسجد سنة 8هـ جدران لبِن وجذوع نخل وسقف جريد). اللقطتان S31 وS33 مكتوبتان هكذا، والبوّابة ترفض «dome».',
     '- ف0/ف1: «صفوف مصلّين» تبقى من الخلف بلا إمام في الإطار، وصلاة النبي ﷺ (d_006) لا يُسمع فوقها مؤثّر.', '',
     '## ١) الأصوات (casting)', '', 'التفصيل والأسباب في `proj/casting.md`. الملخّص:', '',
     '| الدور | الصوت | الكتل |', '|---|---|---|',
     '| الراوي | %s · %s (والمدينة reverent) | كل كتل N |' % (CAST['narrator']['voice'], CAST['narrator']['style'])]
for k, c in CAST['characters'].items():
    o.append('| %s | %s (بديل للعيّنة: %s) | %s |' % (c['name'], c['voice'], CAST['alternates'][k][1],
                                                     ' '.join(sorted(i for i, w in CAST['blocks'].items() if w == k))))
o += ['', '- كلام النبي ﷺ المنقول (d_006 وd_013 وd_015 وd_044 وd_046 وd_049 وd_055 وفي كتاب الوليد d_020–d_021) لا يُسند إلى صوت شخصية أبداً: يقرؤه الراوي أو صوت الوليد الذي ينقله في كتابه، بلا تمثيل.',
      '- **لا عيّنات ولا إجازة مالك (أمر 2026-11-27 لاحقاً):** اختار الوكيل الأصوات الأساسية بنفسه، والتوليد الكامل مباشرةً؛ البوّابة تشترط casting.md بأسبابه فقط.',
      'الجمل المفتاحية (لا مؤثّر فوقها إلا الصمت): ' + ' '.join(keys), '',
      'مستويات dB نسبةً للكلام تحت الصوت (الفرش ≤ −22، النقاط ≤ −18)، وتعلو بين الجمل 8 dB بحدّ −8. لا موسيقى ولا طبول ولا حفيف على القطعات.', '',
      '| # | ~الوقت | الكتلة | الحدث | المرساة | المدة | المستوى | السبب |', '|---|---|---|---|---|---|---|---|']
for c in CUES['cues']:
    st, en = sfx_cues.cue_window(c, bt, by)
    kind = sfx_cues.EVENTS[c['event']][1]
    lv = c.get('level', sfx_cues.EVENTS[c['event']][2])
    o.append('| %s | %s | %s | %s (%s) | %s | %.1f ث | %s | %s |' % (c['id'], fmt(st), c['block'], c['event'], kind,
             c.get('anchor') or ('+%.1f ث' % c['at'] if c.get('at') is not None else '—'), en - st,
             '—' if lv is None else '%+d dB' % lv, c['why']))
dens = len([c for c in CUES['cues'] if sfx_cues.EVENTS[c['event']][1] == 'spot'])
o += ['', '%d إشارة في ~%.0f ث: %d نقطة، %d فرش، %d صمت (كان في أجنادين مؤثّرٌ لكلّ لقطة 146/146 وحفيفٌ على كل قطع).' % (
      len(CUES['cues']), max(e for a, e in bt.values()), dens,
      len([c for c in CUES['cues'] if sfx_cues.EVENTS[c['event']][1] == 'bed']),
      len([c for c in CUES['cues'] if c['event'] == 'silence'])), '',
      '## ٣) قائمة اللقطات وأوامر GenerateImage النهائية', '',
      'دليل الأسلوب: `proj/style_bible.json` (اللوحة: مغرة دافئة وظلال بنّية وزرقة الغسق، والذهب محجوز للحظات الهداية؛ والموتيف: الكثيب نفسه والفارس نفسه في الافتتاح والختام).',
      'كل صورة 16:9 بأعلى دقّة، ثم `python3 tools/image_prompts.py gate proj <صور>` ومراجعة يدوية في `proj/image_review.json` (اليدان، السلاح، الوجوه، النساء، الصلبان، الكتابة، العصر، التشوّه). المرفوض يُعاد حتى 3 مرّات ثم تُغيَّر اللقطة.', '']
for s, p in prom:
    st = bt[s['blocks'][0]][0]
    o += ['### %s · %s · %s — %s' % (s['id'], fmt(st), ' '.join(s['blocks']), {'live': 'حيّ (GenerateVideo)', 'kb3d': 'kb3d'}[s['kind']]),
          '', '```', p, '```', '']
o += ['## ٤) خطة التحريك', '',
      'الحركة من الشعور (`tools/motion_plan.py`) لا من رقم اللقطة. الحيّ لكلّ لقطة مهمّة (أول 30 ث، الصلاة، الذروة، لحظة الإسلام، مؤتة، الختام). '
      'بعد التصيير: `motion_plan.py clip kb3d|live|action` (رعشة/تجمّد) — المرفوض يُعاد بحركة كاميرا ثابتة.', '',
      '| اللقطة | ~الوقت | الشعور | النوع | الحركة | التسارع | الشدّة | الانتقال إليها | وصف الحركة الحيّة |', '|---|---|---|---|---|---|---|---|---|']
for s in SH:
    o.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (s['id'], fmt(bt[s['blocks'][0]][0]), s['emotion'], s['kind'],
             s.get('move3d', '—'), s.get('ease', '—'), s.get('energy', '—'), s.get('tr', '—'), s.get('video_prompt', '—')))
nlive = sum(1 for s in SH if s['kind'] == 'live')
o += ['', '%d لقطة: %d حيّة و%d kb3d (منها خريطة واحدة). متوسّط اللقطة ~%.1f ث؛ تُقسَّم اللقطات الأطول من 8 ث عند المونتاج بلقطة ثانية من الأمر نفسه بحجم آخر.' % (
      len(SH), nlive, len(SH) - nlive, max(e for a, e in bt.values()) / len(SH)), '',
      '## ٥) أوامر المرحلة التالية (بالترتيب)', '', '```',
      'python3 tools/casting.py md proj && (voice_lab بعيّنات الأصوات) && python3 tools/casting.py apply proj',
      'python3 tools/text_gate.py … && python3 tools/pre_generate.py …   # قبل أي توليد',
      '# GenerateImage بالأوامر أعلاه ⇐ python3 tools/image_prompts.py gate proj images/*.jpg',
      '# GenerateVideo للحيّ ⇐ python3 tools/motion_plan.py clip live clips/*.mp4',
      'python3 tools/motion_plan.py lint proj && python3 tools/sfx_cues.py lint proj',
      'python3 tools/mont_hybrid.py proj 0.30   # يصيّر المؤثّرات من الورقة ويشغّل بوّابة المزج ويتوقّف عند أي خلل',
      '```']
open(os.path.join(HERE, 'production_plan.md'), 'w', encoding='utf-8').write('\n'.join(o) + '\n')
print('✓ production_plan.md')
