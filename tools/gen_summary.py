#!/usr/bin/env python3
"""ملخّص مولّد الصوت بلا مفاتيح: النتاج وردود 429 وأيّ حدٍّ ضُرب، لكلّ ملفّ حالة (وادي المخازن 2026-10-11:
غاب 31 صوتاً ولم يُعرف السبب لأنّ سجلّ الشوط لا يُقرأ من الجلسة السحابية).
    python3 tools/gen_summary.py <مجلد_المشروع> <ملفّ_الخرج>"""
import glob, json, os, sys

proj, out = sys.argv[1], sys.argv[2]
r = {}
for f in sorted(glob.glob(os.path.join(proj, 'gen_state*.json'))):
    s = json.load(open(f, encoding='utf-8'))
    r[os.path.basename(f)] = {'done': len(s.get('done') or {}), 'calls': s.get('calls'), 'out': s.get('out'),
                              'q429': s.get('q429'), 'dayRetry': s.get('dayRetry'), 'quotaDay': s.get('quotaDay'),
                              'keys_by_index': s.get('keys')}   # أرقام المفاتيح ونتاجها، لا قيمها
json.dump(r, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
