# -*- coding: utf-8 -*-
"""⛔⛔ حارسُ الشعار — أمرُ المالك 2026-09-15: «لا يتكرّر ذلك تحت أيّ ظرف».

يفحص ثلاثةَ أشياء، ويسقط عند أوّل خللٍ **قبل** أن يُصرف وقتُ تصييرٍ أو حصّة:
① الشعارُ موجودٌ وسليمٌ ويُفتح بـPIL وأبعادُه معقولة.
② لا أداةَ تتخطّى الشعارَ صامتةً (‏`if LOGO:` ممنوعٌ في أدوات المخرَجات).
③ أداةُ تركيب الفيلم تُركّب الشعارَ فعلاً (وهي التي كانت لا تفعل).
④ الشعار الظاهر هو شعار القناة الصحيحة (MUTAFAIL_CHANNEL / envpaths.logo)، لا شعار أختها.

الاستعمال: python tools/logocheck.py [<output.mp4> <baseline.mp4> [film|reel] [overlay_without_logo.png]]
وإن مُرِّر مخرجٌ فُحص **إطارٌ منه فعلاً** مقابل الإطار نفسه قبل تركيب الشعار.
لا يكفي ارتفاعُ التباين في الركن، لأن المشهد نفسه قد يرفعه ويعطي نجاحاً زائفاً.
"""
import io, os, re, subprocess as sp, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import envpaths
from PIL import Image, ImageDraw, ImageFilter


def layout_box(layout, W, H):
    if layout == "reel":
        size, x, y = 118, (W - 118) // 2, H - 158
    else:
        size, x, y = 120, W - 46 - 120, 46
    return x, y, size


def logo_score(frame, box, asset):
    """ارتباط منطقة الشعار في الإطار بالشارة المتوقَّعة (داخل الدائرة فقط)."""
    import numpy as np
    if len(box) == 3:
        x, y, size = box
    else:
        x, y, x2, y2 = box
        size = x2 - x
    crop = np.asarray(frame.crop((x, y, x + size, y + size)).convert("RGB"), float)
    im = Image.open(asset).convert("RGB").resize((size, size), Image.LANCZOS)
    m = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(m).ellipse([4, 4, size * 4 - 4, size * 4 - 4], fill=255)
    a = np.asarray(m.filter(ImageFilter.GaussianBlur(3)).resize((size, size), Image.LANCZOS), float) / 255.0
    exp = np.asarray(im, float)
    msk = a > 0.5
    if not msk.any():
        return 0.0
    c = crop[msk].ravel()
    e = exp[msk].ravel()
    c = c - c.mean()
    e = e - e.mean()
    n = float(np.linalg.norm(c) * np.linalg.norm(e))
    return float(c @ e / n) if n else 0.0


def sister_logos(expected):
    """شعارات قنوات أخرى في المستودع للمقارنة (لا يُعتدّ بالشعار المتوقع نفسه)."""
    repo = envpaths._REPO
    cands = {
        "history": os.path.join(repo, "assets", "logo.png"),
        "hikayat": os.path.join(repo, "ops", "branding", "2026-11-27-v2", "hikayat",
                                "hikayat_youtube_icon_800x800.png"),
    }
    # أي قناة لها channel.json
    ch_root = os.path.join(repo, "ops", "channels")
    if os.path.isdir(ch_root):
        import json
        for name in os.listdir(ch_root):
            cfg = os.path.join(ch_root, name, "channel.json")
            if os.path.isfile(cfg):
                try:
                    asset = json.load(open(cfg, encoding="utf-8")).get("logo", {}).get("asset")
                except Exception:
                    asset = None
                if asset:
                    cands[name] = asset if os.path.isabs(asset) else os.path.join(repo, asset)
    exp = os.path.realpath(expected) if expected and os.path.exists(expected) else None
    out = {}
    for name, p in cands.items():
        if os.path.exists(p) and (exp is None or os.path.realpath(p) != exp):
            out[name] = p
    return out


def check_identity(frame, layout, expected, others=None):
    """يسقط إن لم يطابق الشعار الظاهر شعار القناة، أو طابق شعار قناة أخرى أوضح."""
    W, H = frame.size
    box = layout_box(layout, W, H)
    others = others if others is not None else sister_logos(expected)
    if not expected or not os.path.exists(expected):
        return ["⛔ لا شعار متوقَّع للقناة لفحص المطابقة"]
    s_ok = logo_score(frame, box, expected)
    wrong = []
    for name, p in others.items():
        s_o = logo_score(frame, box, p)
        if s_o >= 0.55 and s_o > s_ok + 0.05:
            wrong.append((name, s_o))
    if wrong:
        wrong.sort(key=lambda x: -x[1])
        return ["⛔ شعار خاطئ في المخرج: الظاهر أقرب لشعار %s (%.2f) لا لشعار القناة (%.2f)"
                % (wrong[0][0], wrong[0][1], s_ok)]
    if s_ok < 0.55:
        return ["⛔ الشعار الظاهر لا يطابق شعار القناة (ارتباط %.2f < 0.55)" % s_ok]
    return []


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
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
    if len(argv) > 0 and not os.path.isfile(argv[0]):
        bad.append("⛔ ملف الفيديو المطلوب فحصه غير موجود؛ لا نجاح بلا مخرج فعلي")
    if len(argv) > 0 and os.path.exists(argv[0]):
        f = argv[0]
        baseline = argv[1] if len(argv) > 1 else ""
        layout = argv[2] if len(argv) > 2 else "film"
        if not baseline or not os.path.exists(baseline):
            bad.append("⛔ لا خطَّ أساسٍ بصرياً قبل الشعار؛ لا يمكن إثبات ظهوره فعلياً")
        if layout not in ("film", "reel"):
            bad.append("⛔ تخطيطُ فحص الشعار غير معروف: %s" % layout)
        if layout == "reel" and (len(argv) < 4 or not os.path.exists(argv[3])):
            bad.append("⛔ لا طبقةَ ريلٍ مرجعيةً بلا شعار؛ لا يمكن عزل ظهور الشعار")

    frame_im = None
    layout = argv[2] if len(argv) > 2 else "film"
    if len(argv) > 1 and os.path.exists(argv[0]) and os.path.exists(argv[1]):
        f, baseline = argv[0], argv[1]
        layout = argv[2] if len(argv) > 2 else "film"
        root = os.path.dirname(os.path.abspath(f))
        png = os.path.join(root, "_logocheck-output.png")
        base_png = os.path.join(root, "_logocheck-baseline.png")
        for video, frame in ((f, png), (baseline, base_png)):
            sp.run([envpaths.FF, "-v", "error", "-y", "-ss", "3", "-i", video,
                    "-frames:v", "1", frame], check=True)
        im = Image.open(png).convert("RGB")
        base = Image.open(base_png).convert("RGB")
        if layout == "reel" and len(argv) > 3 and os.path.exists(argv[3]):
            overlay = Image.open(argv[3]).convert("RGBA")
            if overlay.size != base.size:
                bad.append("⛔ أبعادُ طبقة الريل المرجعية مختلفة: %s != %s" %
                           (overlay.size, base.size))
            else:
                base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
        if im.size != base.size:
            bad.append("⛔ أبعادُ المخرج وخطِّ الأساس مختلفة: %s != %s" % (im.size, base.size))
        else:
            W, H = im.size
            x, y, size = layout_box(layout, W, H)

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
            frame_im = im
        if os.path.exists(png):
            os.remove(png)
        if os.path.exists(base_png):
            os.remove(base_png)

    # مطابقة شعار القناة (حتى إن وُجد خطّ الأساس)
    if frame_im is not None and path:
        for e in check_identity(frame_im, layout, path):
            bad.append(e)
        if not any("خاطئ" in e or "لا يطابق" in e for e in bad):
            if frame_im is not None:
                print("✅ الشعار الظاهر هو شعار القناة الصحيحة")

    if bad:
        print("\n".join(bad)); return 1
    print("✅ حارسُ الشعار: لا ملاحظة")
    return 0


if __name__ == "__main__":
    sys.exit(main())
