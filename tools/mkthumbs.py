# -*- coding: utf-8 -*-
"""يولّد المصغّرتين (أ/ب) من وصفهما في publish.json.

الاستعمال:  python mkthumbs.py <projectDir>

publish.json:
  "thumbs": [{"bg":"g07","l1":"…","l2":"…","badge":"…"}, {...}]
المخرَج:  <proj>/thumb-a.jpg و<proj>/thumb-b.jpg  (والناشرُ يرفع «أ»، و«ب» للاختبار)
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

for name, t in zip("abcdef", thumbs):
    bg = os.path.join(PROJ, "img", t["bg"] + ".jpg")
    if not os.path.exists(bg):
        raise SystemExit("⛔ خلفيةُ المصغّرة غير موجودة: " + bg)
    out = os.path.join(PROJ, "thumb-%s.jpg" % name)
    cmd = [sys.executable, os.path.join(HERE, "mkthumb.py"), bg, out, t["l1"], t["l2"]]
    if t.get("badge"):
        cmd.append(t["badge"])
    sp.run(cmd, check=True)
    print("✅ %s" % out, flush=True)
