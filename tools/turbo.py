# -*- coding: utf-8 -*-
"""عامل موازٍ يصيّر لقطات mont3d من الآخر إلى الأول، بنفس الاسم والمدّة والبذرة.
حين يصل mont3d التسلسليّ إليها يجدها جاهزة فيتخطّاها.
الاستعمال: python turbo.py <projectDir> <workerIndex> <workers>
"""
import json, io, os, sys, subprocess as sp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "Desktop", "claude-media"))
import kb3d
from envpaths import FP

PROJ, WI, WN = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
GAP = 0.30
WORK = os.path.join(PROJ, "work")
SEG = os.path.join(WORK, "seg")
os.makedirs(SEG, exist_ok=True)

blocks = [b for b in json.load(io.open(os.path.join(PROJ, "blocks.json"), encoding="utf-8"))
          if not b.get("reel_only")]
shots = json.load(io.open(os.path.join(PROJ, "shots.json"), encoding="utf-8"))
ids = [b["id"] for b in blocks]


def dur(f):
    o = sp.run([FP, "-v", "error", "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1", f], capture_output=True, text=True)
    try:
        return float(o.stdout.strip())
    except Exception:
        return 0.0


durs = {b: dur(os.path.join(PROJ, "audio", b + ".wav")) for b in ids}


def span(s):
    i0, i1 = ids.index(s["from"]), ids.index(s["to"])
    return sum(durs.get(ids[i], 0) + GAP for i in range(i0, i1 + 1)) / 1.05


# من الآخر إلى الأول، وكل عامل يأخذ حصّته بالتناوب
order = [n for n in range(len(shots) - 1, -1, -1) if n % WN == WI]
done = 0
for n in order:
    s = shots[n]
    img = os.path.join(PROJ, "img", s["img"] + ".jpg")
    if not os.path.exists(img):
        continue
    out = os.path.join(SEG, "s%03d.mp4" % n)
    sec = span(s)
    if os.path.exists(out) and os.path.getsize(out) > 20000 and abs(dur(out) - sec) < 0.05:
        continue
    tmp = out[:-4] + ".w%d.mp4" % WI
    kb3d.render(img, tmp, sec, n)
    try:
        os.replace(tmp, out)   # ذرّيّ: لا يرى mont3d ملفاً نصفَ مكتوب
    except Exception:
        pass
    done += 1
    print("  عامل%d [%d] %s · %.1f ث" % (WI, n + 1, s["img"], sec), flush=True)
print("عامل%d: صيَّر %d" % (WI, done), flush=True)
