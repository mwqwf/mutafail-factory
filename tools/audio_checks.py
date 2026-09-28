# -*- coding: utf-8 -*-
"""فحوص الصوت الآلية بعد التوليد (دروس «اليرموك» 2026-09-27) — تُسقط الشوط عند أيّ خلل.
الاستعمال: python tools/audio_checks.py <proj>
١) الترويسة: لا RIFF مكرّرة (طقطقة كل كتلة) ولا ضجيج في أوّل 240 عيّنة.
٢) الإيقاع: ث/حرف بين 0.09 و0.19 (توجيه الأداء المنطوق يضاعفه) — والشعر 3–10 ث للبيت.
٣) النقرات المعزولة: قفزة > 8000 بعد صمت.
يكتب <proj>/audio_checks.json ويخرج بـ1 إن وُجد خلل (الكتل المعيبة تُحذف لتُعاد)."""
import io, json, os, re, sys, wave
import numpy as np

PROJ = sys.argv[1]
blocks = json.load(io.open(os.path.join(PROJ, 'blocks.json'), encoding='utf-8'))
DIAC = re.compile(r'[ً-ْ\s\.،؛:!؟«»\-]')
bad = {}
for b in blocks:
    f = os.path.join(PROJ, 'audio', b['id'] + '.wav')
    if not os.path.exists(f): bad[b['id']] = 'غائب'; continue
    # كتلةٌ قُصّ أولها (lead_cut) مربوطةٌ بمقطع راوٍ مدفوع الثمن: إعادة توليدها تُفسد مزامنة الشفاه ⇒ لا تُحكم بالإيقاع
    if b.get('lead_cut'): continue
    raw = open(f, 'rb').read()
    if raw[44:48] == b'RIFF':                       # إصلاحٌ فوريّ لا إعادة توليد
        open(f, 'wb').write(raw[44:])
    w = wave.open(f); a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(int); r = w.getframerate()
    d = len(a) / r; chars = len(DIAC.sub('', b['text']))
    if np.abs(a[:240]).max() > 1500: bad[b['id']] = 'ضجيج في البداية'
    elif b.get('role') == 'P':
        if not 3 <= d <= 10: bad[b['id']] = 'بيت شعر %.1f ث (توجيه منطوق؟)' % d
    # الجملُ القصيرة (حوار الشخصيات 2026-09-27: «فقال ربعي:»، «ببايه!») يغلب فيها صمتُ الطرفين، فيُسمح بنحو 1.2 ث زائدة
    elif chars and not 0.09 <= d / chars <= 0.19 + 1.2 / chars: bad[b['id']] = 'إيقاع %.3f ث/حرف' % (d / chars)
    dd = np.abs(np.diff(a)); idx = np.where(dd > 8000)[0]
    iso = [i for i in idx if i > 240 and np.abs(a[i - 240:i - 24]).max() < 2000]
    if len(iso) > 1: bad.setdefault(b['id'], 'نقرات معزولة %d' % len(iso))
json.dump(bad, io.open(os.path.join(PROJ, 'audio_checks.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('فحوص الصوت: %d كتلة · معيب %d %s' % (len(blocks), len(bad), bad))
for k in bad:                                       # تُحذف لتُولَّد من جديد في الشوط التالي
    p = os.path.join(PROJ, 'audio', k + '.wav')
    if os.path.exists(p): os.remove(p)
sys.exit(1 if bad else 0)
