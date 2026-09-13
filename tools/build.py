# -*- coding: utf-8 -*-
"""يبني blocks.json و images.json و shots.json من script.md + images-extra.md"""
import io, json, os, sys

# ⭐ مجلّد المشروع من الوسيط، وإلا فموضع الملفّ (لئلّا ينكسر الاستعمال المحلّيّ).
P = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
VOICE = {"C": "Charon", "R": "Iapetus", "U": "Umbriel",
         "A": "Schedar", "S": "Algenib", "E": "Enceladus"}

blocks, imgs, order = [], [], []
for line in io.open(os.path.join(P, "script.md"), encoding="utf-8"):
    line = line.rstrip("\n").strip()
    if not line:
        continue
    if line.startswith("IMG:"):
        i, prompt = line[4:].split("|", 1)
        imgs.append({"id": i, "prompt": prompt})
        order.append(("img", i))
    else:
        bid, v, txt = line.split("|", 2)
        blocks.append({"id": bid, "voice": VOICE[v], "text": txt})
        order.append(("blk", bid))

_ex = os.path.join(P, "images-extra.md")
for line in (io.open(_ex, encoding="utf-8") if os.path.exists(_ex) else []):
    line = line.rstrip("\n").strip()
    if line.startswith("IMG:"):
        i, prompt = line[4:].split("|", 1)
        imgs.append({"id": i, "prompt": prompt})

# مجموعات: كل صورة تغطّي الكتل التي سبقتها
groups, cur = [], []
for kind, val in order:
    if kind == "blk":
        cur.append(val)
    else:
        groups.append((val, cur))
        cur = []
if cur:
    groups[-1] = (groups[-1][0], groups[-1][1] + cur)

# الصور الإضافية تُقسم أطول المجموعات
extra = [i["id"] for i in imgs if int(i["id"][1:]) >= 18]
shots = []
gi = 0
for img, bl in groups:
    if len(bl) >= 4 and extra:
        h = len(bl) // 2
        shots.append({"img": img, "from": bl[0], "to": bl[h - 1]})
        shots.append({"img": extra.pop(0), "from": bl[h], "to": bl[-1]})
    else:
        shots.append({"img": img, "from": bl[0], "to": bl[-1]})

# ما تبقّى من الصور الإضافية: قسّم مجموعات الثلاث
i = 0
while extra and i < len(shots):
    s = shots[i]
    a = [b["id"] for b in blocks]
    f, t = a.index(s["from"]), a.index(s["to"])
    if t - f >= 2:
        shots.insert(i + 1, {"img": extra.pop(0), "from": a[f + 1], "to": a[t]})
        s["to"] = a[f]
        i += 2
    else:
        i += 1

json.dump(blocks, io.open(os.path.join(P, "blocks.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump([i for i in imgs], io.open(os.path.join(P, "images.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(shots, io.open(os.path.join(P, "shots.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("blocks:", len(blocks), "| images:", len(imgs), "| shots:", len(shots),
      "| extra unused:", len(extra))
