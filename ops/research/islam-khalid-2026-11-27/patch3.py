# -*- coding: utf-8 -*-
"""patch3 (2026-11-27 ظهراً): أوقات حقيقية، ضبط مستويات المؤثّرات بالقياس، حركة احتياطية قوية للّقطات الحيّة وملاحظات الجودة."""
import io
s = io.open('build_plan.py', encoding='utf-8').read()
if 'LEVEL_FIX' in s:
    raise SystemExit('patched already')
s = s.replace("FAC = '/workspace/mutafail-factory/tools'", "FAC = os.environ.get('MF_TOOLS', '/workspace/mutafail-factory/tools')", 1)
s = s.replace("bt = sfx_cues.block_times(P, blocks)", "bt = {k: tuple(v) for k, v in json.load(open(os.path.join(P, 'real_timing.json')))['bt'].items()}  # أوقات حقيقية من الصوت المُصيَّر", 1)
s = s.replace("(58 كتلة، ~7:46)", "(58 كتلة، المدة الحقيقية 8:58 من الصوت المُصيَّر)", 1)
s = s.replace("the hand slowly unfolds the parchment, flame flickers gently; camera static",
              "the folded parchment stays closed in the hand, only the lamp flame flickers and dust drifts; camera static, no writing ever visible")
trim = """# ضبط بالأذن والقياس على المزج الحقيقي (2026-11-27): المؤثّرات الفعلية كانت أخفض من قيم الإشارات بـ2–8 dB؛ رُفعت ضمن السقوف
LEVEL_FIX = {'c04': -20, 'c05': -24, 'c06': -22, 'c08': -22, 'c12': -18, 'c13': -19, 'c14': -19, 'c22': -21, 'c25': -18, 'c26': -18}
for _c in CUES['cues']:
    if _c['id'] in LEVEL_FIX:
        _c['why'] += ' (رُفع من %s إلى %s dB بعد قياس المزج الفعلي)' % (_c.get('level'), LEVEL_FIX[_c['id']])
        _c['level'] = LEVEL_FIX[_c['id']]
"""
s = s.replace("json.dump(CUES, open(", trim + "json.dump(CUES, open(", 1)
fb = """# ── حركة احتياطية قوية للّقطات الحيّة (2026-11-27): GenerateVideo غير متاح للوكيل المنفّذ، فإن غاب المقطع الحيّ
#    صيّر mont_hybrid اللقطة kb3d بهذه الحركة (عمق وتزيّح قويّان، طاقة أعلى) بدل السكون؛ وحين يصل المقطع الحيّ يُستعمل هو.
#    ملاحظات المراجعة: S13 وS24 فيهما أشخاص صغار بعيدون مواجهون ⇒ حركة لا تكبّرهم؛ S17 كتابة زائفة ⇒ تُموَّه ولا يُقرَّب منها؛ لا تكبير لوجه.
LIVE_FALLBACK = {
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
for _s in SH:
    if _s['id'] in LIVE_FALLBACK:
        _s['move3d'], _s['energy'], _s['ease'] = LIVE_FALLBACK[_s['id']]
    _s.update(QA_FIX.get(_s['id'], {}))
"""
s = s.replace("json.dump(SH, open(os.path.join(P, 'shots.json')", fb + "json.dump(SH, open(os.path.join(P, 'shots.json')", 1)
io.open('build_plan.py', 'w', encoding='utf-8').write(s)
print('patched')
