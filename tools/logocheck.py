# -*- coding: utf-8 -*-
"""⛔⛔ حارسُ الشعار — أمرُ المالك 2026-09-15: «لا يتكرّر ذلك تحت أيّ ظرف».

يفحص ثلاثةَ أشياء، ويسقط عند أوّل خللٍ **قبل** أن يُصرف وقتُ تصييرٍ أو حصّة:
① الشعارُ موجودٌ وسليمٌ ويُفتح بـPIL وأبعادُه معقولة.
② لا أداةَ تتخطّى الشعارَ صامتةً (‏`if LOGO:` ممنوعٌ في أدوات المخرَجات).
③ أداةُ تركيب الفيلم تُركّب الشعارَ فعلاً (وهي التي كانت لا تفعل).

الاستعمال: python tools/logocheck.py [<film.mp4>]
وإن مُرِّر فيلمٌ فُحص **إطارٌ منه فعلاً**: أيتغيّر ركنُ الشعار عمّا تحته؟
"""
import io, os, re, subprocess as sp, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import envpaths
from PIL import Image

bad = []

# ① الشعارُ نفسُه
path = envpaths.logo(required=False)
if not path:
    bad.append("⛔ لا شعارَ في assets/logo.png — ادفعْ ملفاً في ops/logo/ ليجلبه logo.yml")
else:
    try:
        Image.open(path).verify()
        im = Image.open(path)
        if min(im.size) < 128:
            bad.append("⛔ الشعارُ أصغرُ من أن يُرسم: %s" % (im.size,))
        else:
            print("✅ الشعار:", path, im.size)
    except Exception as e:
        bad.append("⛔ الشعارُ لا يُفتح: %s" % e)

# ② لا تخطٍّ صامت
for t in ("mont3d.py", "mkreel3d.py", "mkthumb.py"):
    src = io.open(os.path.join(HERE, t), encoding="utf-8").read()
    if re.search(r"^\s*if\s+LOGO\s*:", src, re.M):
        bad.append("⛔ %s يتخطّى الشعارَ صامتاً (if LOGO:) — الغيابُ سقوطٌ لا تخطٍّ" % t)

# ③ الفيلمُ يُركَّب عليه الشعار
src = io.open(os.path.join(HERE, "mont3d.py"), encoding="utf-8").read()
if "overlay=" not in src or "envpaths.logo(" not in src:
    bad.append("⛔ mont3d.py لا يُركّب الشعارَ على الفيلم — وهذا هو العطبُ المقيس")
else:
    print("✅ تركيبُ الشعار مطلوبٌ في أداة الفيلم")

# ④ فحصُ إطارٍ حقيقيٍّ إن مُرِّر فيلم
if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
    f = sys.argv[1]
    png = os.path.join(os.path.dirname(os.path.abspath(f)), "_logocheck.png")
    sp.run([envpaths.FF, "-v", "error", "-y", "-ss", "3", "-i", f,
            "-frames:v", "1", png], check=True)
    im = Image.open(png).convert("RGB")
    W, H = im.size
    corner = im.crop((W - 46 - 120, 46, W - 46, 46 + 120))
    # الركنُ الذي فيه شعارٌ ذهبيٌّ على داكنٍ يحمل تبايناً أعلى من جوارِه المسطّح
    ex = im.crop((W - 46 - 120 - 160, 46, W - 46 - 160, 46 + 120))
    var = lambda p: sum((c - sum(p.convert("L").getdata()) / (120 * 120)) ** 2
                        for c in p.convert("L").getdata()) / (120 * 120)
    v1, v2 = var(corner), var(ex)
    print("تباينُ ركن الشعار: %.0f | وجوارُه: %.0f" % (v1, v2))
    if v1 <= v2 * 1.15:
        bad.append("⛔ لا أثرَ للشعار في إطار الفيلم عند موضعه — الفيلمُ بلا شعار")
    else:
        print("✅ الشعارُ ظاهرٌ في إطارٍ من الفيلم")
    os.remove(png)

if bad:
    print("\n".join(bad)); sys.exit(1)
print("✅ حارسُ الشعار: لا ملاحظة")
