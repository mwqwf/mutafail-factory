# -*- coding: utf-8 -*-
"""حمولةٌ صوريّةٌ لفحص المحرّك — **محليّةٌ بالكامل، بلا شبكةٍ ولا رصيدٍ ولا حصّة**.

الاستعمال:  python selftest_fixture.py <dir>

تكتب: script.md · sections.json · reels.json · publish.json · meta.json
      و img/*.jpg (تدرّجاتٌ مرسومةٌ بـPIL) و audio/*.wav (صمتٌ بمدَدٍ مختلفة).
⇒ فيمرّ عليها خطُّ الإنتاج كلُّه كما يمرّ على فيلمٍ حقيقيّ، ولا يُستهلك شيء.
"""
import io
import json
import os
import subprocess as sp
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from envpaths import FF

D = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/tmp/proj")
os.makedirs(os.path.join(D, "img"), exist_ok=True)
os.makedirs(os.path.join(D, "audio"), exist_ok=True)

TAIL = "No text, no letters, no captions, no watermark."
NBLK, NIMG = 8, 3

# ── script.md: كتلٌ وأوصافُ صورٍ تجتاز البوّابتين ──
lines = []
for i in range(1, NBLK + 1):
    lines.append("d_%03d|%s|هَذِهِ كُتْلَةُ فَحْصٍ لِلْمُحَرِّكِ لَا تَدْخُلُ فِيلْماً قَطّْ." %
                 (i, "CRUASE"[i % 6]))
    # ⭐ الصورةُ تُكتب **بعد** الكتل التي تغطّيها — لا قبلها
    if i % 3 == 0 or i == NBLK:
        g = min(NIMG, (i + 2) // 3)
        lines.append("IMG:g%02d|Cinematic documentary photograph: a vast empty basalt "
                     "coastline under grey cloud, cold dawn light, desolate mood, "
                     "photorealistic 16:9. %s" % (g, TAIL))
io.open(os.path.join(D, "script.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")

json.dump([{"id": "d_001", "title": "المقدّمة"}, {"id": "d_005", "title": "الفصل الثاني"}],
          io.open(os.path.join(D, "sections.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

json.dump([{"id": "r1", "title": "ريلز فحص المحرّك",
            "blocks": ["d_001", "d_002", "d_003"],
            "imgs": ["g01", "g02", "g03"]}],
          io.open(os.path.join(D, "reels.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

json.dump({"slug": "selftest",
           "thumbs": [{"bg": "g01", "l1": "فحصُ المحرّك", "l2": "بلا رصيد", "badge": "تجربة"},
                      {"bg": "g02", "l1": "فحصُ المحرّك", "l2": "نسخةُ ب"}]},
          io.open(os.path.join(D, "publish.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

json.dump({"slug": "selftest", "title": "فحص المحرّك"},
          io.open(os.path.join(D, "meta.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ── صورٌ مرسومةٌ محليًّا: تدرّجٌ + ضوضاءُ عمقٍ حتى لا تكون مسطّحةً تماماً ──
rng = np.random.default_rng(7)
for g in range(1, NIMG + 1):
    h, w = 1080, 1920
    y = np.linspace(0, 1, h)[:, None]
    x = np.linspace(0, 1, w)[None, :]
    base = (0.25 + 0.55 * y) * (0.6 + 0.4 * np.sin(6.283 * (x + 0.17 * g)) ** 2)
    a = np.stack([base * 190, base * 205, base * 225], -1)
    a += rng.normal(0, 5, a.shape)
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(
        os.path.join(D, "img", "g%02d.jpg" % g), quality=94, subsampling=0)

# ── أصواتٌ صامتةٌ بمدَدٍ مختلفة (فتختبر حسابَ المدد لا مدّةً واحدة) ──
for i in range(1, NBLK + 1):
    sec = 1.6 + 0.35 * (i % 4)
    sp.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
            "-t", "%.2f" % sec, os.path.join(D, "audio", "d_%03d.wav" % i)], check=True)

print("✅ حمولةُ فحصٍ في %s · %d كتلة · %d صور" % (D, NBLK, NIMG))
