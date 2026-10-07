# -*- coding: utf-8 -*-
"""تقرير الإصغاء للتحكيم (weekly-film ② و②ب): رايةٌ أو «لم يُفحص» لكلّ كتلةٍ في blocks.json.

⛔ درس الشوط 87 (الأرك 2026-10-05): كان التقرير يعدّ مفاتيح listen_results.json كما هي، فعدّ نتائج صوتٍ
قديمٍ (قبل تبديل الصوت إلى Algenib) مفحوصةً، وقال «لم يُفحص: 0» والإصغاءُ لم يسمع كتلةً واحدة.
⇒ لا تُحسب نتيجةٌ إلا لصوت الكتلة الحاليّ: بصمتها (نصّ + \\0 + الصوت، كـlisten_cache.js) تطابق input_sha256،
   والكتلةُ بلا ملفّ صوت أو بلا نتيجة أو بنتيجةٍ قديمة تُسمّى «لم يُفحص» بسببها.
الاستعمال: python tools/listen_report.py <proj>  ⇒ <proj>/listen_report.json
"""
import hashlib
import json
import os
import sys


def report(proj):
    blocks = json.load(open(os.path.join(proj, 'blocks.json'), encoding='utf-8'))
    try:
        res = json.load(open(os.path.join(proj, 'listen_results.json'), encoding='utf-8'))
    except (OSError, ValueError):
        res = {}
    flags, unchecked, why = {}, [], {}
    for b in blocks:
        k = b['id']
        f = os.path.join(proj, 'audio', k + '.wav')
        if not os.path.exists(f):
            unchecked.append(k); why[k] = 'لا ملفّ صوت'; continue
        digest = hashlib.sha256(b['text'].encode('utf-8') + b'\0' + open(f, 'rb').read()).hexdigest()
        v = res.get(k)
        if not isinstance(v, dict) or not isinstance(v.get('ok'), bool):
            unchecked.append(k); why[k] = (v or {}).get('why', 'بلا نتيجة') if isinstance(v, dict) else 'بلا نتيجة'
        elif v.get('input_sha256') != digest:
            unchecked.append(k); why[k] = 'نتيجةٌ قديمة لصوتٍ سابق'
        elif v['ok'] is False:
            flags[k] = v
    return {'flags': flags, 'unchecked': unchecked, 'why_unchecked': why}


if __name__ == '__main__':
    proj = sys.argv[1]
    r = report(proj)
    open(os.path.join(proj, 'listen_report.json'), 'w', encoding='utf-8').write(json.dumps(r, ensure_ascii=False, indent=1))
    tally = {}
    for w in r['why_unchecked'].values():
        tally[w] = tally.get(w, 0) + 1
    print('رايات:', len(r['flags']), '| لم يُفحص:', len(r['unchecked']), tally if tally else '')
