# -*- coding: utf-8 -*-
"""إعادة توزيع اللقطات: تُقسَّم كل لقطة تتجاوز MAXDUR باستعمال الصور الإضافية (b56+).
يحفظ shots.json الجديد، ويطبع أطول لقطة قبل وبعد."""
import json, io, os, subprocess

MAXDUR = 24.0
GAP = 0.3
P = os.path.dirname(os.path.abspath(__file__))
FP = os.path.join(os.path.expanduser("~"), "Desktop", "claude-media", "ffbin",
                  "ffmpeg-9.0.1-essentials_build", "bin", "ffprobe.exe")

B = [b for b in json.load(io.open(os.path.join(P, "blocks.json"), encoding="utf-8"))
     if not b.get("reel_only")]
ids = [b["id"] for b in B]
idx = {b: i for i, b in enumerate(ids)}

dur = {}
for b in ids:
    o = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", os.path.join(P, "audio", b + ".wav")],
                       capture_output=True, text=True)
    dur[b] = float(o.stdout.strip() or 0) + GAP

def span(a, z):
    return sum(dur[ids[i]] for i in range(a, z + 1))

shots = json.load(io.open(os.path.join(P, "shots.json"), encoding="utf-8"))
used = {s["img"] for s in shots}
pool = [i["id"] for i in json.load(io.open(os.path.join(P, "images.json"), encoding="utf-8"))
        if i["id"] not in used and os.path.exists(os.path.join(P, "img", i["id"] + ".jpg"))]
pool.sort(key=lambda x: int(x[1:]))

before = max(span(idx[s["from"]], idx[s["to"]]) for s in shots)

# قسّم مراراً: في كل جولة اقسم أطول لقطة تتجاوز الحدّ وتحتمل القسمة
work = [{"img": s["img"], "a": idx[s["from"]], "z": idx[s["to"]]} for s in shots]
while pool:
    cand = [w for w in work if w["z"] > w["a"] and span(w["a"], w["z"]) > MAXDUR]
    if not cand:
        break
    w = max(cand, key=lambda w: span(w["a"], w["z"]))
    half, acc, target = w["a"], 0.0, span(w["a"], w["z"]) / 2
    for i in range(w["a"], w["z"]):
        acc += dur[ids[i]]
        half = i
        if acc >= target:
            break
    new = {"img": pool.pop(0), "a": half + 1, "z": w["z"]}
    w["z"] = half
    work.insert(work.index(w) + 1, new)

work.sort(key=lambda w: w["a"])
out = [{"img": w["img"], "from": ids[w["a"]], "to": ids[w["z"]]} for w in work]
json.dump(out, io.open(os.path.join(P, "shots.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

after = max(span(w["a"], w["z"]) for w in work)
over = sum(1 for w in work if span(w["a"], w["z"]) > MAXDUR)
tot = sum(span(w["a"], w["z"]) for w in work)
print("لقطات: %d -> %d | أطول: %.1f -> %.1f ث | فوق %.0f ث: %d | صور فائضة: %d | المدة: %.1f د"
      % (len(shots), len(out), before, after, MAXDUR, over, len(pool), tot / 60))
