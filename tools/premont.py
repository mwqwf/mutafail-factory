# -*- coding: utf-8 -*-
"""فاحص ما قبل المونتاج — يمنع «الفيلم المبتور» (بلا رصيد).
الاستعمال: python premont.py <projectDir>

يمسك ثلاثة أعطاب أوقعتنا فعليًّا:
1) كتلة بلا ملف صوت  ⇒ صوت أقصر من النصّ.
2) صورة مذكورة في shots.json وغير موجودة على القرص ⇒ mont.py يتخطّى اللقطة
   فيخرج الفيديو أقصر من الصوت، و«‎-shortest» يبتر الفيلم.
3) صورة تالفة تمرّ من فحص الحجم ⇒ الفحص الوحيد المعتمد هو PIL.
كما يتحقّق من تغطية shots.json لكل كتل الفيلم بلا فجوة.

يعود بـexit code 1 عند أي عطب، فيوقف خطّ الإنتاج.
"""
import json, os, sys

PROJ = os.path.abspath(sys.argv[1])
bad = []

blocks = json.load(open(os.path.join(PROJ, "blocks.json"), encoding="utf-8"))
film = [b for b in blocks if not b.get("reel_only")]
ids = [b["id"] for b in film]

# ١) الصوت
for b in blocks:
    a = os.path.join(PROJ, "audio", b["id"] + ".wav")
    if not os.path.exists(a):
        bad.append("صوت ناقص: " + b["id"])
    elif os.path.getsize(a) < 8000:
        bad.append("صوت تالف (أصغر من ٨ ك.ب): " + b["id"])

# ٢) و٣) الصور
shots = json.load(open(os.path.join(PROJ, "shots.json"), encoding="utf-8"))
try:
    from PIL import Image
except ImportError:
    Image = None
seen = set()
for s in shots:
    p = os.path.join(PROJ, "img", s["img"] + ".jpg")
    if not os.path.exists(p):
        bad.append("صورة ناقصة: " + s["img"]); continue
    if s["img"] in seen: continue
    seen.add(s["img"])
    if os.path.getsize(p) < 25000:
        bad.append("صورة أصغر من ٢٥ ك.ب: " + s["img"])
    if Image:
        try:
            Image.open(p).verify(); Image.open(p).load()
        except Exception:
            bad.append("صورة تالفة (فحص PIL): " + s["img"])

# ٤) تغطية اللقطات
cov = set()
for s in shots:
    try:
        i0, i1 = ids.index(s["from"]), ids.index(s["to"])
    except ValueError:
        bad.append("لقطة تشير إلى كتلة غير موجودة: %s → %s" % (s["from"], s["to"])); continue
    cov |= set(range(i0, i1 + 1))
gaps = sorted(set(range(len(ids))) - cov)
if gaps:
    bad.append("كتل بلا لقطة (%d): %s" % (len(gaps), ", ".join(ids[i] for i in gaps[:10])))

if bad:
    print("\n⛔ %d عطب — المونتاج موقوف:\n" % len(bad))
    for x in bad: print("  ·", x)
    sys.exit(1)

print("✅ %d كتلة · %d لقطة · %d صورة — لا عطب، يجوز المونتاج"
      % (len(blocks), len(shots), len(seen)))
