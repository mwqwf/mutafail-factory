# -*- coding: utf-8 -*-
"""حارس «نطق التعليمات»: يمسك كل كتلةٍ نطق فيها النموذجُ توجيهَ الأداء الإنجليزي أو أيَّ كلامٍ إنجليزي
(درس الزلاقة 2026-09-28: قال الراوي «Say quickly…» بصوتٍ مسموع ثم حُرِّك على صوته).
الاستعمال: python style_leak.py <proj>
لكل كتلةٍ ممسوكة: يحذف style منها في blocks.json، ويحذف صوتها ليُعاد توليده بلا توجيه.
رمز الخروج 1 إن أُمسك شيء (ليعاد التوليد والإصغاء قبل أي تحريك)، و0 إن كان الصوت نظيفاً."""
import json, os, re, sys

P = lambda *a: os.path.join(os.path.abspath(sys.argv[1]), *a)
res = json.load(open(P('listen_results.json'), encoding='utf-8')) if os.path.exists(P('listen_results.json')) else {}
LATIN = re.compile(r'[A-Za-z]{3,}')
leak = []
for k, v in res.items():
    if not isinstance(v, dict) or v.get('ok') is not False: continue
    why, heard = str(v.get('why', '')), str(v.get('written', ''))
    if 'إنجليز' in why or 'انجليز' in why or 'توجيه' in why or 'تعليم' in why or LATIN.search(heard):
        leak.append(k)
if not leak:
    print('لا نطقَ لتعليماتٍ إنجليزية'); sys.exit(0)
blocks = json.load(open(P('blocks.json'), encoding='utf-8'))
for b in blocks:
    if b['id'] in leak: b.pop('style', None)
json.dump(blocks, open(P('blocks.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
shots = json.load(open(P('shots.json'), encoding='utf-8')) if os.path.exists(P('shots.json')) else []
for k in leak:
    for f in (P('audio', k + '.wav'),):
        if os.path.exists(f): os.remove(f)
    # مقطع الراوي المتزامن مع الصوت المعيب يُحذف أيضاً فيُعاد تحريكه على الصوت الجديد (لا شفاه على صوتٍ آخر)
    for s in shots:
        if s.get('lipsync') == k:
            for f in (P('clips', s['id'] + '_av.mp4'), P('clips', s['id'] + '.mp4')):
                if os.path.exists(f): os.remove(f)
    res.pop(k, None)
json.dump(res, open(P('listen_results.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('⛔ نطقٌ لتعليماتٍ إنجليزية في:', ' '.join(leak), '— أُزيل التوجيه وسيُعاد التوليد')
sys.exit(1)
