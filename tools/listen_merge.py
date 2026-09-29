# -*- coding: utf-8 -*-
"""يدمج نتائج إصغاءٍ سابقة في proj/listen_results.json فلا يُعاد فحصُ ما فُحص (أمر المالك 2026-09-29).

درس عين جالوت: شوطان أصغيا إلى الكتل الـ193 كلّها مرّتين، لأنّ الثاني بدأ قبل أن تُحفظ
نتائج الأول؛ ومقاطعُ الراوي n_ أُصغي إليها في شوط الافتتاحية ثم أُعيدت في شوط الفيلم.
⇒ قبل الإصغاء تُجلب أحدثُ النتائج (من <slug>-out و<slug>-intro-out) وتُدمج هنا.
الدمج آمن: listen.js لا يعيد استعمال نتيجةٍ إلا إن طابقت بصمتُها (النصّ + الصوت) البصمةَ الحالية،
فنتيجةُ صوتٍ تغيّر تُهمَل تلقائيّاً. ولا تغلب نتيجةٌ ناقصة (ok ليست منطقية) نتيجةً مكتملة.
الاستعمال: python tools/listen_merge.py <proj> <ملف1> [ملف2 …]
"""
import io
import json
import os
import sys


def load(path):
    try:
        with io.open(path, encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def done(v):
    return isinstance(v, dict) and isinstance(v.get('ok'), bool) and bool(v.get('input_sha256'))


def merge(cur, other):
    added = 0
    for k, v in other.items():
        if done(v) and not done(cur.get(k)):
            cur[k] = v
            added += 1
    return added


def main(proj, sources):
    out = os.path.join(proj, 'listen_results.json')
    cur = load(out)
    total = 0
    for s in sources:
        n = merge(cur, load(s))
        total += n
        print('دُمج من %s: %d نتيجة' % (s, n))
    tmp = out + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        json.dump(cur, f, ensure_ascii=False, indent=1)
    os.replace(tmp, out)
    print('نتائج الإصغاء المحفوظة الآن: %d (أُضيف %d)' % (sum(done(v) for v in cur.values()), total))


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit('الاستعمال: listen_merge.py <proj> <ملف…>')
    main(sys.argv[1], sys.argv[2:])
