# -*- coding: utf-8 -*-
"""يولّد المصغّرات من وصفها في publish.json مع توافقٍ آمن للحمولات القديمة."""
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


def value(item, names):
    for key in names:
        v = item.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def split_title(title):
    """اقسم عنواناً واحداً إلى سطرين متوازنين من غير تغيير كلماته."""
    words = title.split()
    if len(words) < 2:
        return title, " "
    best = min(
        range(1, len(words)),
        key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))),
    )
    return " ".join(words[:best]), " ".join(words[best:])


for name, t in zip("abcdef", thumbs):
    bg = os.path.join(PROJ, "img", t["bg"] + ".jpg")
    if not os.path.exists(bg):
        raise SystemExit("⛔ خلفيةُ المصغّرة غير موجودة: " + bg)
    l1 = value(t, ("l1", "line1", "title1", "text1", "headline", "top"))
    l2 = value(t, ("l2", "line2", "title2", "text2", "subheadline", "subtitle", "bottom"))
    if not l1 and not l2:
        title = value(t, ("title",))
        if title:
            l1, l2 = split_title(title)
    if not l1 or not l2:
        safe_keys = ",".join(sorted(str(k) for k in t))
        raise SystemExit("⛔ نص المصغّرة ناقص؛ الحقول الموجودة: " + safe_keys)
    out = os.path.join(PROJ, "thumb-%s.jpg" % name)
    cmd = [sys.executable, os.path.join(HERE, "mkthumb.py"), bg, out, l1, l2]
    if t.get("badge"):
        cmd.append(t["badge"])
    sp.run(cmd, check=True)
    print("✅ %s" % out, flush=True)
