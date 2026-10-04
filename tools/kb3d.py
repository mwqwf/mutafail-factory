#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
kb3d.py — التحريك المجسَّم (parallax 2.5D) لصور الوثائقيات.
يحوّل الصورة الثابتة إلى لقطة متحرّكة بعمق حقيقي: القريب يتحرّك أسرع من البعيد.

الاستعمال:
    python kb3d.py depth  <projectDir>              # المرحلة ١: خرائط العمق لكل صور المشروع
    python kb3d.py clips  <projectDir> [مدة]        # المرحلة ٢: تصيير مقطع لكل صورة
    python kb3d.py one <img> <out.mp4> <مدة> <بذرة> # صورة واحدة

المخرَج: <projectDir>/anim/<اسم>.mp4  (1920×1080، 25 إطارًا/ث، بلا صوت)

⛔ ملاحظات مقيسة:
- خريطة العمق تُنعَّم بغاوس قبل الإزاحة، وإلا ظهرت تمزّقات عند حواف الأعماق.
- التصيير بـoverscan ثم قصّ، وإلا ظهر شريط أسود على الحواف.
- نموذج العمق يُحمَّل مرّة واحدة لكل عملية (تحميله ~60 ث، والصورة ~3.5 ث).
"""
import os, sys, glob, time, subprocess as sp
import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from envpaths import FF
from depthpath import depth_of  # noqa: E402 — خريطة العمق في images/ أو img/ (درس الأرك 2026-10-04)

W, H, FPS = 1920, 1080, 25
# ⭐ الإصدار الثاني (حكم المالك 2026-10-04 على عيّنة الأرك: «التحريك المجسّم… لازال بعيداً جداً عمّا أطمح إليه»):
#    أخذُ العيّنات ثنائيّ الخطّ (cv2.remap) بدل أقرب جار — كان يُرعش الحوافّ —، وإزاحةُ عمقٍ أكبر بمرّتين، وكاميرا تتقدّم
#    فيكبر القريب أسرع من البعيد، ودورانٌ خفيف في المدار، وعمقُ ميدانٍ خفيف حين يبرز في الصورة قريبٌ واضح.
OVER = 1.20          # تكبير احتياطي قبل القصّ (يمنع الحواف السوداء)
MAXPX = 78.0         # أقصى إزاحة للطبقة الأقرب، بالبكسل
DEPTH_BLUR = 13      # تنعيم خريطة العمق — يمنع التمزّق
PAR_ZOOM = 1.25      # القريب يكبر بقدر (1 + PAR_ZOOM × عمقه) من تقدّم الكاميرا
DOF = 0.42           # أقصى مزجٍ للخلفية المغبّشة (عمق الميدان) — يُطفأ في الصور المسطّحة
VERSION = 2          # يُكتب في اسم المقطع عند mont_hybrid فلا يُعاد استعمال مقاطع الإصدار الأوّل

# ثمانية مسارات كاميرا: (إزاحة أفقية، رأسية) بوحدة MAXPX، والتكبير، والدوران بالدرجات — تتناوب فلا تتشابه لقطتان متجاورتان
MOVES = [
    ("dolly_in",  lambda p: ( 0.12 * p - 0.06, -0.06 * p + 0.03, 1.00 + 0.15 * p, 0.0)),
    ("truck_r",   lambda p: ( 1.00 * p - 0.50,  0.08 * p - 0.04, 1.07, 0.0)),
    ("crane_up",  lambda p: ( 0.10 * p - 0.05,  0.95 * p - 0.47, 1.04 + 0.06 * p, 0.0)),
    ("orbit",     lambda p: ( 0.90 * p - 0.45, -0.10 * p + 0.05, 1.08, 1.8 * p - 0.9)),
    ("dolly_out", lambda p: (-0.12 * p + 0.06,  0.06 * p - 0.03, 1.16 - 0.14 * p, 0.0)),
    ("truck_l",   lambda p: (-1.00 * p + 0.50, -0.06 * p + 0.03, 1.07, 0.0)),
    ("push_tilt", lambda p: ( 0.16 * p - 0.08,  0.12 * p - 0.06, 1.00 + 0.13 * p, -1.5 * p + 0.3)),
    ("reveal",    lambda p: ( 0.06 * p - 0.03, -0.60 * p + 0.30, 1.19 - 0.16 * p, 0.0)),
]


def depth_maps(proj):
    """يولّد <name>_depth.png لكل صورة في <proj>/img لم تُعالَج بعد."""
    from transformers import pipeline
    imgs = sorted(glob.glob(os.path.join(proj, "img", "*.jpg")))
    todo = [f for f in imgs
            if not os.path.exists(f.rsplit('.', 1)[0] + "_depth.png")]
    print(f"صور: {len(imgs)} · تحتاج عمقًا: {len(todo)}", flush=True)
    if not todo:
        return
    t0 = time.time()
    pipe = pipeline("depth-estimation",
                    model="depth-anything/Depth-Anything-V2-Small-hf", device=-1)
    print(f"النموذج جاهز خلال {time.time()-t0:.0f} ث", flush=True)
    for i, f in enumerate(todo, 1):
        t = time.time()
        try:
            r = pipe(Image.open(f).convert("RGB"))
            r["depth"].save(f.rsplit('.', 1)[0] + "_depth.png")
            print(f"  [{i}/{len(todo)}] {os.path.basename(f)}  {time.time()-t:.1f} ث", flush=True)
        except Exception as e:
            print(f"  ⛔ {os.path.basename(f)}: {e}", flush=True)


def _cover(im, bw, bh, resample):
    """قصٌّ مركزيٌّ يملأ (bw، bh) بلا تشويه."""
    iw, ih = im.size
    sc = max(bw / iw, bh / ih)
    im = im.resize((max(bw, int(iw * sc + 0.5)), max(bh, int(ih * sc + 0.5))), resample)
    return im.crop(((im.width - bw) // 2, (im.height - bh) // 2,
                    (im.width - bw) // 2 + bw, (im.height - bh) // 2 + bh))


def render(src, out, dur=6.0, seed=0, size=None, energy=1.0):
    """يصيّر مقطعًا مجسَّمًا واحدًا. يحتاج <src>_depth.png بجانب الصورة أو في <proj>/img.
    size=(عرض,ارتفاع) للريلزات العمودية (1080,1920)؛ والافتراض أفقيّ 1920×1080.
    energy: شدّة الحركة (المعركة أقوى من التمهيد) — تضرب الإزاحة والتكبير."""
    import cv2                                  # opencv-python-headless (weekly-film يثبّته)
    W, H = size if size else (globals()["W"], globals()["H"])
    dpath = depth_of(src)
    bw, bh = int(W * OVER), int(H * OVER)
    a = np.asarray(_cover(Image.open(src).convert("RGB"), bw, bh, Image.LANCZOS), dtype=np.uint8)

    if os.path.exists(dpath):
        dm = _cover(Image.open(dpath).convert("L"), bw, bh, Image.BILINEAR)
        dm = dm.filter(ImageFilter.GaussianBlur(DEPTH_BLUR))
        d = np.asarray(dm, dtype=np.float32) / 255.0
    else:   # بلا عمق: تدرّج رأسيّ — كين-بيرنز محسَّن، لا مجسَّم
        d = np.linspace(0.15, 1.0, bh, dtype=np.float32)[:, None].repeat(bw, 1)
    d = d - d.mean()                       # المتوسّط ثابت، فالحركة حول مستوى الصورة
    sep = float(d.std())
    dof = DOF * min(1.0, max(0.0, (sep - 0.12) / 0.10))     # عمق ميدانٍ حين يبرز قريبٌ واضح فقط (لا أثر «المجسّم المصغّر»)
    blur = cv2.GaussianBlur(a, (0, 0), 3.2) if dof > 0.02 else None
    dfocus = float(np.percentile(d, 90))                    # البؤرة على القريب

    name, fn = MOVES[seed % len(MOVES)]
    e = max(0.4, float(energy))
    # الإزاحة ناعمةٌ (العمق مغبَّش) فتُحسب على شبكةٍ بربع الدقّة ثم تُكبَّر ثنائياً — أسرع بأضعاف، والصورة نفسها تُؤخذ بدقّتها الكاملة
    F = 4
    ws, hs = (W + F - 1) // F, (H + F - 1) // F
    gy, gx = np.mgrid[0:hs, 0:ws].astype(np.float32)
    ox, oy = (bw - W) / 2.0, (bh - H) / 2.0
    cx, cy = bw / 2.0, bh / 2.0
    qx = (gx + 0.5) * F - 0.5 + ox - cx              # موضع عيّنة الشبكة من مركز الصورة (محاذاة cv2.resize)
    qy = (gy + 0.5) * F - 0.5 + oy - cy
    N = max(2, int(round(FPS * dur)))

    p = sp.Popen([FF, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                  "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                  "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                  "-pix_fmt", "yuv420p", out], stdin=sp.PIPE)
    try:
        for i in range(N):
            t = i / (N - 1)
            t = 0.75 * t + 0.25 * t * t * (3 - 2 * t)   # حركةٌ متّصلة تكاد تكون خطّية: لا توقّف عند الانتقالات المتداخلة
            mx, my, zm, rot = fn(t)
            zm = 1.0 + (zm - 1.0) * e
            mx, my, rot = mx * e, my * e, rot * e
            th = np.deg2rad(rot)
            c, s_ = np.float32(np.cos(th)), np.float32(np.sin(th))
            rx, ry = c * qx + s_ * qy, -s_ * qx + c * qy          # دورانٌ عكسيّ حول المركز
            dd = np.zeros_like(qx)
            for _ in range(3):                                     # تكرارٌ ثابت النقطة: العمق في موضع المصدر الحقيقيّ
                z = zm * (1.0 + PAR_ZOOM * (zm - 1.0) * dd)
                sx = cx + rx / z - MAXPX * mx * dd
                sy = cy + ry / z - MAXPX * my * dd
                dd = cv2.remap(d, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            z = zm * (1.0 + PAR_ZOOM * (zm - 1.0) * dd)
            sx = cv2.resize(cx + rx / z - MAXPX * mx * dd, (W, H), interpolation=cv2.INTER_LINEAR)
            sy = cv2.resize(cy + ry / z - MAXPX * my * dd, (W, H), interpolation=cv2.INTER_LINEAR)
            fr = cv2.remap(a, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            if blur is not None:
                w = cv2.resize(np.clip((dfocus - dd) / 0.55, 0.0, 1.0) * dof, (W, H), interpolation=cv2.INTER_LINEAR)
                fb = cv2.remap(blur, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
                fr = cv2.blendLinear(fr, fb, (1.0 - w).astype(np.float32), w.astype(np.float32))
            p.stdin.write(fr.tobytes())
        p.stdin.close()
    except BrokenPipeError:
        pass
    p.wait()
    return name


def clips(proj, dur=6.0):
    outdir = os.path.join(proj, "anim")
    os.makedirs(outdir, exist_ok=True)
    imgs = sorted(f for f in glob.glob(os.path.join(proj, "img", "*.jpg"))
                  if not f.endswith("_depth.png"))
    done = 0
    for i, f in enumerate(imgs):
        out = os.path.join(outdir, os.path.splitext(os.path.basename(f))[0] + ".mp4")
        if os.path.exists(out) and os.path.getsize(out) > 20000:
            continue
        t = time.time()
        mv = render(f, out, dur, i)
        done += 1
        print(f"  [{i+1}/{len(imgs)}] {os.path.basename(out)} · {mv} · {time.time()-t:.1f} ث", flush=True)
    print(f"صُيِّر {done} مقطعًا في {outdir}", flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "depth":
        depth_maps(sys.argv[2])
    elif cmd == "clips":
        clips(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 6.0)
    elif cmd == "one":
        print(render(sys.argv[2], sys.argv[3],
                     float(sys.argv[4]) if len(sys.argv) > 4 else 6.0,
                     int(sys.argv[5]) if len(sys.argv) > 5 else 0))
    else:
        print(__doc__)
