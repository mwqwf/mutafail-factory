# -*- coding: utf-8 -*-
"""يولّد المصغّرتين (أ/ب) من وصفهما في publish.json.

الاستعمال:  python mkthumbs.py <projectDir>

الصيغة المعيارية هي l1/l2. ويُقبل مؤقتاً عدد محدود من الأسماء القديمة
حتى لا يُهدر تصييرٌ كامل بسبب اختلاف اسم حقل في حمولة مختومة.
"""
import io
import json
import os
import subprocess as sp
import sys

PROJ = os.path.abspath(sys.argv[1])
HERE = os.path.dirname(os.path.abspath(__file__))
meta = json.load(io.open(os.path.join(PROJ, "publish.json"), encoding="utf-8"))
thumbs = meta.get("thumbs", [])
if not thumbs:
    raise SystemExit("⛔ لا مصغّرات في publish.json — ولا يُرفع فيلمٌ بلا مصغّرة")


def text_field(item, canonical, aliases):
    for key in (canonical, *aliases):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    safe_keys = ",".join(sorted(str(k) for k in item))
    raise SystemExit(
        "⛔ المصغّرة بلا %s؛ الحقول الموجودة: %s" % (canonical, safe_keys)
    )


for name, t in zip("abcdef", thumbs):
    bg = os.path.join(PROJ, "img", t["bg"] + ".jpg")
    if not os.path.exists(bg):
        raise SystemExit("⛔ خلفيةُ المصغّرة غير موجودة: " + bg)
    out = os.path.join(PROJ, "thumb-%s.jpg" % name)
    l1 = text_field(t, "l1", ("line1", "title1", "text1", "headline", "title", "top"))
    l2 = text_field(t, "l2", ("line2", "title2", "text2", "subheadline", "subtitle", "bottom"))
    cmd = [sys.executable, os.path.join(HERE, "mkthumb.py"), bg, out, l1, l2]
    if t.get("badge"):
        cmd.append(t["badge"])
    sp.run(cmd, check=True)
    print("✅ %s" % out, flush=True)
