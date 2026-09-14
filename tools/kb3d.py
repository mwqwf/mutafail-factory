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

W, H, FPS = 1920, 1080, 25
OVER = 1.10          # تكبير احتياطي قبل القصّ (يمنع الحواف السوداء)
MAXPX = 34.0         # أقصى إزاحة للطبقة الأقرب، بالبكسل
DEPTH_BLUR = 9       # تنعيم خريطة العمق — يمنع التمزّق

# ستة أنماط حركة، تُوزَّع بالتناوب فلا تتشابه لقطتان متجاورتان
MOVES = [
    ("pan_r",  lambda p: ( 1.0*p - 0.5,  0.10*p - 0.05, 1.00 + 0.045*p)),
    ("pan_l",  lambda p: (-1.0*p + 0.5, -0.08*p + 0.04, 1.00 + 0.045*p)),
    ("push",   lambda p: ( 0.18*p - 0.09, 0.06*p - 0.03, 1.00 + 0.075*p)),
    ("pull",   lambda p: (-0.15*p + 0.07, 0.05*p - 0.02, 1.075 - 0.075*p)),
    ("rise",   lambda p: ( 0.12*p - 0.06, 0.85*p - 0.42, 1.00 + 0.050*p)),
    ("drift",  lambda p: ( 0.75*p - 0.37,-0.55*p + 0.27, 1.00 + 0.040*p)),
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


def render(src, out, dur=6.0, seed=0, size=None):
    """يصيّر مقطعًا مجسَّمًا واحدًا. يحتاج <src>_depth.png بجانب الصورة.
    size=(عرض,ارتفاع) للريلزات العمودية (1080,1920)؛ والافتراض أفقيّ 1920×1080."""
    W, H = size if size else (globals()["W"], globals()["H"])
    dpath = src.rsplit('.', 1)[0] + "_depth.png"
    bw, bh = int(W * OVER), int(H * OVER)
    im = Image.open(src).convert("RGB")
    iw, ih = im.size                       # قصّ مركزيّ يملأ الإطار بلا تشويه
    sc = max(bw / iw, bh / ih)
    im = im.resize((max(bw, int(iw * sc + 0.5)), max(bh, int(ih * sc + 0.5))), Image.LANCZOS)
    im = im.crop(((im.width - bw) // 2, (im.height - bh) // 2,
                  (im.width - bw) // 2 + bw, (im.height - bh) // 2 + bh))
    a = np.asarray(im, dtype=np.uint8)

    if os.path.exists(dpath):
        dm = Image.open(dpath).convert("L")
        dsc = max(bw / dm.width, bh / dm.height)
        dm = dm.resize((max(bw, int(dm.width * dsc + 0.5)), max(bh, int(dm.height * dsc + 0.5))), Image.LANCZOS)
        dm = dm.crop(((dm.width - bw) // 2, (dm.height - bh) // 2,
                      (dm.width - bw) // 2 + bw, (dm.height - bh) // 2 + bh))
        dm = dm.filter(ImageFilter.GaussianBlur(DEPTH_BLUR))
        d = np.asarray(dm, dtype=np.float32) / 255.0
    else:   # بلا عمق: تدرّج رأسيّ — كين-بيرنز محسَّن، لا مجسَّم
        d = np.linspace(0.15, 1.0, bh, dtype=np.float32)[:, None].repeat(bw, 1)
    d = d - d.mean()                       # المتوسّط ثابت، فالحركة حول مستوى الصورة

    name, fn = MOVES[seed % len(MOVES)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ox, oy = (bw - W) / 2.0, (bh - H) / 2.0
    N = max(2, int(round(FPS * dur)))

    p = sp.Popen([FF, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                  "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                  "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                  "-pix_fmt", "yuv420p", out], stdin=sp.PIPE)
    try:
        for i in range(N):
            t = i / (N - 1)
            t = t * t * (3 - 2 * t)                 # تنعيم البداية والنهاية
            mx, my, zm = fn(t)
            cx, cy = bw / 2.0, bh / 2.0
            sx = cx + (xx + ox - cx) / zm
            sy = cy + (yy + oy - cy) / zm
            dd = d[np.clip(sy, 0, bh - 1).astype(np.int32),
                   np.clip(sx, 0, bw - 1).astype(np.int32)]
            sx = np.clip(sx + MAXPX * mx * dd, 0, bw - 1).astype(np.int32)
            sy = np.clip(sy + MAXPX * my * dd, 0, bh - 1).astype(np.int32)
            p.stdin.write(a[sy, sx].tobytes())
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
