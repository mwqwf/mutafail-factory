# -*- coding: utf-8 -*-
"""يولّد فصول يوتيوب بتوقيتاتها من مدد ملفات الصوت.
الاستعمال: python chapters.py <projectDir> <sections.json>
sections.json = [{"id":"s001","title":"..."} , ...]  (id = أول كتلة في الفصل)
يكتب <proj>/الفصول.txt جاهزًا للنسخ.
"""
import json, os, sys, subprocess as sp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from envpaths import FP

PROJ = os.path.abspath(sys.argv[1])
SEC = json.load(open(sys.argv[2], encoding="utf-8"))
GAP = float(sys.argv[3]) if len(sys.argv) > 3 else 0.30
TEMPO = 1.05

blocks = [b for b in json.load(open(os.path.join(PROJ, "blocks.json"), encoding="utf-8"))
          if not b.get("reel_only")]

def dur(f):
    o = sp.run([FP, "-v", "error", "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1", f], capture_output=True, text=True)
    try:
        return float(o.stdout.strip())
    except Exception:
        # ⛔ الصمتُ هنا كان يُخرج فصولاً كلُّها 0:00 بلا أن يشكوَ أحد
        raise SystemExit("⛔ تعذّرت قراءة مدّة %s عبر %s: %s" % (f, FP, o.stderr.strip()))

starts, t = {}, 0.0
for b in blocks:
    starts[b["id"]] = t / TEMPO
    a = os.path.join(PROJ, "audio", b["id"] + ".wav")
    t += (dur(a) + GAP) if os.path.exists(a) else GAP

def fmt(s):
    s = int(s); return "%d:%02d:%02d" % (s // 3600, (s % 3600) // 60, s % 60) if s >= 3600 else "%d:%02d" % (s // 60, s % 60)

lines = []
for i, sec in enumerate(SEC):
    ts = 0.0 if i == 0 else starts.get(sec["id"], 0.0)
    lines.append("%s %s" % (fmt(ts), sec["title"]))

out = os.path.join(PROJ, "الفصول.txt")
open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines))
print("\n✅ " + out)
