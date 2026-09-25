# -*- coding: utf-8 -*-
"""⛔⛔ حارسُ الشعار — أمرُ المالك 2026-09-15: «لا يتكرّر ذلك تحت أيّ ظرف».

يفحص ثلاثةَ أشياء، ويسقط عند أوّل خللٍ **قبل** أن يُصرف وقتُ تصييرٍ أو حصّة:
① الشعارُ موجودٌ وسليمٌ ويُفتح بـPIL وأبعادُه معقولة.
② لا أداةَ تتخطّى الشعارَ صامتةً (‏`if LOGO:` ممنوعٌ في أدوات المخرَجات).
③ أداةُ تركيب الفيلم تُركّب الشعارَ فعلاً (وهي التي كانت لا تفعل).

الاستعمال: python tools/logocheck.py [<output.mp4> <baseline.mp4> [film|reel] [overlay_without_logo.png]]
وإن مُرِّر مخرجٌ فُحص **إطارٌ منه فعلاً** مقابل الإطار نفسه قبل تركيب الشعار.
لا يكفي ارتفاعُ التباين في الركن، لأن المشهد نفسه قد يرفعه ويعطي نجاحاً زائفاً.
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

# ④ فحصُ إطارٍ حقيقيٍّ إن مُرِّر مخرج
if len(sys.argv) > 1 and not os.path.isfile(sys.argv[1]):
    bad.append("⛔ ملف الفيديو المطلوب فحصه غير موجود؛ لا نجاح بلا مخرج فعلي")
if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
    f = sys.argv[1]
    baseline = sys.argv[2] if len(sys.argv) > 2 else ""
    layout = sys.argv[3] if len(sys.argv) > 3 else "film"
    if not baseline or not os.path.exists(baseline):
        bad.append("⛔ لا خطَّ أساسٍ بصرياً قبل الشعار؛ لا يمكن إثبات ظهوره فعلياً")
    if layout not in ("film", "reel"):
        bad.append("⛔ تخطيطُ فحص الشعار غير معروف: %s" % layout)
    if layout == "reel" and (len(sys.argv) < 5 or not os.path.exists(sys.argv[4])):
        bad.append("⛔ لا طبقةَ ريلٍ مرجعيةً بلا شعار؛ لا يمكن عزل ظهور الشعار")

if len(sys.argv) > 2 and os.path.exists(sys.argv[1]) and os.path.exists(sys.argv[2]):
    f, baseline = sys.argv[1], sys.argv[2]
    layout = sys.argv[3] if len(sys.argv) > 3 else "film"
    root = os.path.dirname(os.path.abspath(f))
    png = os.path.join(root, "_logocheck-output.png")
    base_png = os.path.join(root, "_logocheck-baseline.png")
    for video, frame in ((f, png), (baseline, base_png)):
        sp.run([envpaths.FF, "-v", "error", "-y", "-ss", "3", "-i", video,
                "-frames:v", "1", frame], check=True)
    im = Image.open(png).convert("RGB")
    base = Image.open(base_png).convert("RGB")
    if layout == "reel" and len(sys.argv) > 4 and os.path.exists(sys.argv[4]):
        overlay = Image.open(sys.argv[4]).convert("RGBA")
        if overlay.size != base.size:
            bad.append("⛔ أبعادُ طبقة الريل المرجعية مختلفة: %s != %s" %
                       (overlay.size, base.size))
        else:
            base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    if im.size != base.size:
        bad.append("⛔ أبعادُ المخرج وخطِّ الأساس مختلفة: %s != %s" % (im.size, base.size))
    W, H = im.size
    if layout == "reel":
        size, x, y = 118, (W - 118) // 2, H - 158
    else:
        size, x, y = 120, W - 46 - 120, 46

    def mad(a, b, box):
        aa, bb = a.crop(box), b.crop(box)
        pa, pb = list(aa.getdata()), list(bb.getdata())
        return sum(sum(abs(x - y) for x, y in zip(u, v)) / 3.0
                   for u, v in zip(pa, pb)) / len(pa)

    box = (x, y, x + size, y + size)
    # منطقتان ضابطتان بعيدتان عن الشعار تقيسان فرق إعادة الترميز الطبيعي.
    controls = [
        (max(0, x - size - 40), y, max(0, x - 40), y + size),
        (max(0, x - 2 * size - 80), y, max(0, x - size - 80), y + size),
    ]
    logo_delta = mad(im, base, box)
    control_delta = max(mad(im, base, b) for b in controls)
    print("فرقُ موضع الشعار: %.2f | فرقُ إعادة الترميز: %.2f" %
          (logo_delta, control_delta))
    if logo_delta < max(4.0, control_delta * 1.8):
        bad.append("⛔ لم يتغيّر موضعُ الشعار عن خطِّ الأساس بما يثبت ظهوره")
    else:
        print("✅ الشعارُ ظاهرٌ فعلياً في المخرج مقارنةً بخطِّ الأساس")
    os.remove(png); os.remove(base_png)

if bad:
    print("\n".join(bad)); sys.exit(1)
print("✅ حارسُ الشعار: لا ملاحظة")
