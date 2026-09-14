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
        b = {"id": bid, "voice": VOICE[v], "text": txt}
        # ⛔⛔ الفخُّ المقيس (SKILL §٨): كتلتا مفتتحِ الريلز ونداءِ ختامه تُولَّدان مع
        #    بقيّة الكتل، فتُلحقهما أداةُ المونتاج **بآخر الفيلم** — فيسمع مشاهدُ
        #    الوثائقيّ في ختامه نداءً موجَّهاً لمشاهدي الريلز. والعلامةُ: مُعرّفٌ يبدأ بـ`r_`.
        if bid.startswith("r_"):
            b["reel_only"] = True
        blocks.append(b)
        # ⛔ وكتلُ الريلز خارج تسلسل الفيلم البصريّ كذلك: لو دخلت `order` لأسندت
        #    إليها لقطةٌ من الفيلم، ثمّ سقط `mont3d` بـValueError لأنّه يستبعدها.
        if not b.get("reel_only"):
            order.append(("blk", bid))

_ex = os.path.join(P, "images-extra.md")
for line in (io.open(_ex, encoding="utf-8") if os.path.exists(_ex) else []):
    line = line.rstrip("\n").strip()
    if line.startswith("IMG:"):
        i, prompt = line[4:].split("|", 1)
        imgs.append({"id": i, "prompt": prompt})

# مجموعات: كل صورة تغطّي الكتل التي سبقتها
# ⛔ وصورةٌ لم يسبقها كتلة (كأن يبدأ السيناريو بسطر IMG) كانت تُسقط الأداة بـIndexError
#    في وظيفة `prepare` بعد اجتياز البوّابتين — فتُحتجز حتى الكتل التي تليها.
groups, cur = [], []
for kind, val in order:
    if kind == "blk":
        cur.append(val)
    else:
        if not cur:
            raise SystemExit(
                "⛔ سطرُ الصورة «%s» لا كتلةَ قبله. والقاعدة: **الصورة تُكتب بعد الكتل "
                "التي تغطّيها**، فلا يبدأ السيناريو بسطر IMG ولا تتجاور صورتان." % val)
        groups.append((val, cur))
        cur = []
if not groups:
    raise SystemExit("⛔ لا صورةَ في script.md — ولا يُركَّب فيلمٌ بلا لقطات")
if cur:
    groups[-1] = (groups[-1][0], groups[-1][1] + cur)

# الصور الإضافية تُقسم أطول المجموعات
# ⛔ كان التمييزُ بـ`int(id[1:]) >= 18` — وهو حدسٌ يصدق على فيلمٍ صورُه دون سبعَ عشرة
#    وحدَه. فمتى تجاوزتها صورُ السيناريو صارت الصورةُ الواحدة **لقطتين**: لقطةً بحقّها
#    وأخرى بالقسمة ⇒ فيديو أطولُ من الصوت. والصحيحُ ما أُريد أصلاً: الإضافيُّ هو ما
#    جاء من `images-extra.md` لا ما تجاوز رقمُه ثمانيةَ عشرَ.
_in_script = {v for k, v in order if k == "img"}
extra = [i["id"] for i in imgs if i["id"] not in _in_script]
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
