#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild سيف الله trailers v4: series open card, subscribe end card,
cuts on silence with 30–80 ms audio fades, cinematic dip-to-black
transitions, complete spoken lines, no music.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/workspace/mutafail-factory/tools")
from sfx_synth import whoosh, thud, write as write_wav, SR as SFX_SR  # noqa: E402

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path("/workspace/series_trailer")
CLIPS = ROOT / "clips"
CARDS = ROOT / "cards"
SEG = ROOT / "seg"
TEXT = ROOT / "text"
SFX = ROOT / "sfx"
FACTORY_SFX = Path("/workspace/mutafail-factory/assets/sfx")
FPS = 25
NASKH = TEXT / "NotoNaskhArabic-SemiBold.ttf"
KUFI = TEXT / "NotoKufiArabic-ExtraBold.ttf"

# --- timeline (target ~76–78 s) ---
OPEN_DUR = 2.70
CARD_DUR = 1.00
END_DUR = 6.60
AUDIO_FADE = 0.06          # 60 ms fades at cuts, in the silence pad
VIDEO_FADE_IN = 0.20
VIDEO_FADE_OUT = 0.24
OVERLAY_FADE = 0.22

# Hunt: end in the silence before «فقاتل» (film 253.74 / clip 5.548)
HUNT_SRC = ROOT / "src/vid/hunt_prey_full.mp4"
HUNT_SS, HUNT_DUR = 248.192, 5.45  # ends 253.642, silence 4.97–5.61

# Kinana: start in silence before the sentence (clip 0.50 onset),
# end after «على رأس السور» (clip ~13.50), cut at 13.70
KIN_SRC = CLIPS / "04_kinana_climb.mp4"
KIN_SS, KIN_DUR = 0.40, 13.30  # 0.40–13.70

# Jarajah: start in silence (409.62) before «ومال» onset 409.70;
# end in the pause after «لحظة» and before «فما» at ~422.922
JAR_SRC = ROOT / "src/vid/jarajah_shield_full.mp4"
JAR_SS, JAR_DUR = 409.62, 12.97  # ends 422.590
JAR_SHIFT = 409.892 - JAR_SS  # +0.272 vs v3, for caption retiming

# Mafaza: A starts 70 ms before «هلكتم» onset (38.85);
# B starts 43.94 (word onset) with fadeblack hiding residual xfade ghost;
# B ends 47.28 after «لا يراها أحد منهم»
MAF_SRC = ROOT / "src/vid/mafaza_hook_full.mp4"
MAF_A_SS, MAF_A_DUR = 38.76, 4.54   # 38.76–43.30
MAF_B_SS, MAF_B_DUR = 43.94, 3.34   # 43.94–47.28
MAF_XFADE = 0.28
MAF_DUR = MAF_A_DUR + MAF_B_DUR - MAF_XFADE  # 7.60
MAF_B_AT = MAF_A_DUR - MAF_XFADE             # 4.26
MAF_A_SHIFT = 38.85 - MAF_A_SS               # +0.09 vs v3 overlay times

# Iraq: keep start (silence then speech at +0.45);
# cut at 8.45 in the silence after «بل اعبروا إلينا» (ended ~8.17),
# before the next phrase rises at ~8.55
IRQ_SRC = ROOT / "src/vid/iraq_open.mp4"
IRQ_SS, IRQ_DUR = 17.26, 8.45

MAF_BOX = (620, 400, 720, 320)
IRQ_BOX = (480, 350, 1040, 420)  # wider, typography «بل» starts ~rel 6.68

CLIPS_SPEC = [
    dict(
        id="00_ajnadayn",
        src=CLIPS / "01_ajnadayn_open.mp4",
        ss=0.00, dur=6.50,
        caps=[
            (0.00, 3.24, "لُفُّوا رَأْسِي بِثَوْبٍ!\\Nلَا أُحِبُّ أَنْ أَرَاهُ…"),
            (3.24, 6.50, "مَا رَأَيْتُ فِي الدُّنْيَا يَوْمًا أَشَدَّ مِنْ هَذَا!"),
        ],
        overlays=[], blur_box=None,
        blur_h_16=300, blur_h_9=500,
        bar_16=300, bar_9=500,
        grad_feather=50, grad_alpha=190,
        blur_luma=16, blur_chroma=12,
        l3=(0.25, 2.20, "أَجْنَادِين"),
    ),
    dict(
        id="01_salasil",
        src=CLIPS / "02_salasil_call.mp4",
        ss=0.00, dur=8.00,
        caps=[
            (0.00, 3.90, "بَيْنَ الصَّفَّيْنِ، رَجُلٌ يُنَادِي:"),
            (3.90, 8.00, "رَجُلٌ وَرَجُلٌ… أَيْنَ خَالِدٌ؟"),
        ],
        overlays=[], blur_box=None,
        l3=(0.25, 2.20, "ذَاتُ السَّلَاسِلِ"),
    ),
    dict(
        id="02_hunt",
        src=HUNT_SRC, ss=HUNT_SS, dur=HUNT_DUR,
        caps=[
            (0.11, 2.19, "فَاسْتَأْسَرَ أُكَيْدِرُ"),
            (3.01, HUNT_DUR, "وَامْتَنَعَ أَخُوهُ حَسَّانُ"),
        ],
        overlays=[], blur_box=None,
        l3=(0.25, 2.20, "أُكَيْدِر"),
    ),
    dict(
        id="03_kinana",
        src=KIN_SRC, ss=KIN_SS, dur=KIN_DUR,
        caps=[
            (0.00, 6.20, "فَلَمَّا ثَبَتَ مِنْهَا حَبْلَانِ\\Nتَسَلَّقَ فِيهِمَا الْقَعْقَاعُ وَمَذْعُورٌ"),
            (6.20, KIN_DUR, "ثُمَّ ثَبَتَتِ الْحِبَالُ كُلُّهَا\\Nحَتَّي اسْتَوَى خَالِدٌ وَأَصْحَابُهُ عَلَى رَأْسِ السُّورِ"),
        ],
        overlays=[], blur_box=None,
        l3=(0.25, 2.20, "فَتْحُ دِمَشْقَ"),
    ),
    dict(
        id="04_mafaza",
        src="MAFAZA_COMBINED",
        ss=0.00, dur=MAF_DUR,
        caps=[
            (0.00, MAF_B_AT, "قَالُوا: مَا نَرَاهَا.\\Nهَلَكْتُمْ وَاللَّهِ إِذَنْ، وَهَلَكْتُ مَعَكُمْ."),
            (MAF_B_AT, MAF_DUR, "جَيْشٌ كَامِلٌ مُعَلَّقٌ بِشَجَرَةٍ\\Nلَا يَرَاهَا أَحَدٌ مِنْهُمْ."),
        ],
        overlays=[
            (0.14, 2.14, "هَلَكْتُمْ", ""),
            (2.14, MAF_B_AT, "هَلَكْتُمْ وَاللَّهِ", "— دَلِيلُ الْجَيْشِ"),
        ],
        blur_box=MAF_BOX,
        blur_times=(0.10, MAF_B_AT),
        l3=(0.25, 2.20, "خَمْسُ لَيَالٍ بِلَا مَاءٍ"),
    ),
    dict(
        id="05_jarajah",
        src=JAR_SRC, ss=JAR_SS, dur=JAR_DUR,
        caps=[
            (0.00, 3.98 + JAR_SHIFT, "وَمَالَ بِفَرَسِهِ إِلَى جَانِبِ خَالِدٍ"),
            (3.98 + JAR_SHIFT, 5.66 + JAR_SHIFT, "عَلِّمْنِي الْإِسْلَامَ"),
            (6.26 + JAR_SHIFT, JAR_DUR, "أَمِيرٌ مِنْ أُمَرَاءِ الرُّومِ\\Nعَبَرَ مَا بَيْنَ الصَّفَّيْنِ فِي لَحْظَةٍ"),
        ],
        overlays=[], blur_box=None,
        l3=(0.25, 2.20, "الْيَرْمُوك"),
    ),
    dict(
        id="06_iraq",
        src=IRQ_SRC, ss=IRQ_SS, dur=IRQ_DUR,
        caps=[
            (0.00, 6.16, "إِمَّا أَنْ تَعْبُرُوا إِلَيْنَا،\\Nوَإِمَّا أَنْ نَعْبُرَ إِلَيْكُمْ."),
            (6.16, IRQ_DUR, "بَلِ اعْبُرُوا إِلَيْنَا."),
        ],
        overlays=[
            (6.50, IRQ_DUR, "بَلِ اعْبُرُوا إِلَيْنَا", "— خَالِدُ بْنُ الْوَلِيدِ"),
        ],
        blur_box=IRQ_BOX,
        blur_times=(6.48, IRQ_DUR),
        l3=(0.25, 2.20, "عُبُورُ الْعِرَاقِ"),
    ),
]
CARD_IDS = ["c1_ayn", "c2_hunt", "c3_wall", "c4_halaktum", "c5_islam", "c6_cross"]

def run(cmd, quiet=True, **kw):
    preview = []
    for c in cmd[:14]:
        s = str(c)
        preview.append(s[:90] + "…" if s.startswith("-filter") and len(s) > 90 else s)
    print("+", " ".join(preview), "...", flush=True)
    kw.setdefault("check", False)
    if quiet:
        kw.setdefault("stdout", subprocess.DEVNULL)
        kw.setdefault("stderr", subprocess.PIPE)
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        err = r.stderr.decode("utf-8", "replace") if r.stderr else ""
        print("FAILED", r.returncode, " ".join(preview)[:200])
        print(err[-2500:])
        raise SystemExit(f"cmd failed: {r.returncode}")
    return r


def probe_dur(path: Path) -> float:
    r = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path),
    ], text=True)
    return float(r.strip())


def kufi(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(KUFI), size, layout_engine=ImageFont.Layout.RAQM)


def naskh(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(NASKH), size, layout_engine=ImageFont.Layout.RAQM)


def make_gradient(path: Path, w, h, bar, feather=None, max_alpha=200):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    start = h - bar
    # default: fade over the whole bar (original t^2 curve)
    feather = bar if feather is None else max(1, min(int(feather), bar))
    for y in range(start, h):
        dist = y - start
        if dist < feather:
            t = dist / feather
            a = int(min(max_alpha, t * t * (max_alpha + 10)))
        else:
            a = max_alpha
        for x in range(w):
            px[x, y] = (0, 0, 0, a)
    img.save(path)


def render_caption_png(text, size, path, fontsize):
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    font = naskh(fontsize)
    lines = [ln.strip() for ln in text.replace("\\N", "\n").split("\n") if ln.strip()]
    gap = int(fontsize * 0.28)
    draw = ImageDraw.Draw(img)
    widths, heights = [], []
    for ln in lines:
        b = draw.textbbox((0, 0), ln, font=font, language="ar", direction="rtl")
        widths.append(b[2] - b[0])
        heights.append(b[3] - b[1])
    block_w = max(widths) if widths else 0
    block_h = sum(heights) + gap * (len(lines) - 1)
    pad_x, pad_y = 36, 18
    margin_b = 54 if h <= 1080 else 120
    plate = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(plate)
    x0 = (w - block_w) // 2 - pad_x
    y0 = h - margin_b - block_h - pad_y
    x1 = (w + block_w) // 2 + pad_x
    y1 = h - margin_b + pad_y
    pd.rounded_rectangle((x0, y0, x1, y1), radius=18, fill=(0, 0, 0, 170))
    plate = plate.filter(ImageFilter.GaussianBlur(0.6))
    img = Image.alpha_composite(img, plate)
    draw = ImageDraw.Draw(img)
    y = h - margin_b - block_h
    cx = w // 2
    for ln, hh in zip(lines, heights):
        draw.text(
            (cx, y + hh / 2), ln, font=font, fill=(245, 236, 214, 255),
            anchor="mm", language="ar", direction="rtl", align="center",
            stroke_width=3, stroke_fill=(16, 10, 4, 255),
        )
        y += hh + gap
    img.save(path)
    return path


def render_overlay_png(main, sub, size, path, main_sz, sub_sz):
    """Properly shaped center typography (RAQM + Noto Kufi)."""
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    mf = kufi(main_sz)
    # measure
    mb = draw.textbbox((0, 0), main, font=mf, language="ar", direction="rtl")
    mw, mh = mb[2] - mb[0], mb[3] - mb[1]
    sh = 0
    sf = None
    sw = 0
    if sub:
        sf = kufi(sub_sz)
        sb = draw.textbbox((0, 0), sub, font=sf, language="ar", direction="rtl")
        sw, sh = sb[2] - sb[0], sb[3] - sb[1]
    gap = int(main_sz * 0.22) if sub else 0
    block_h = mh + (gap + sh if sub else 0)
    cy = int(h * 0.52)
    cx = w // 2
    # dark plate to fully hide disconnected baked-in letters
    pad_x, pad_y = 48, 28
    plate = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(plate)
    box_w = max(mw, sw) if sub else mw
    x0 = cx - box_w // 2 - pad_x
    y0 = cy - block_h // 2 - pad_y
    x1 = cx + box_w // 2 + pad_x
    y1 = cy + block_h // 2 + pad_y
    pd.rounded_rectangle((x0, y0, x1, y1), radius=22, fill=(0, 0, 0, 110))
    plate = plate.filter(ImageFilter.GaussianBlur(1.2))
    img = Image.alpha_composite(img, plate)
    draw = ImageDraw.Draw(img)
    y_main = cy - block_h // 2 + mh / 2
    draw.text(
        (cx, y_main), main, font=mf, fill=(247, 214, 150, 255),
        anchor="mm", language="ar", direction="rtl",
        stroke_width=5, stroke_fill=(16, 10, 4, 255),
    )
    if sub:
        y_sub = y_main + mh / 2 + gap + sh / 2
        draw.text(
            (cx, y_sub), sub, font=sf, fill=(212, 168, 64, 255),
            anchor="mm", language="ar", direction="rtl",
            stroke_width=3, stroke_fill=(16, 10, 4, 255),
        )
    img.save(path)
    return path


def map_box_9x16(box, src_w=1920, src_h=1080, out_w=1080, out_h=1920):
    """Map a 16:9 box through scale=3414:1920, crop=1080:1920 (center)."""
    x, y, bw, bh = box
    scale = out_h / src_h  # 1920/1080
    scaled_w = src_w * scale  # 3414
    crop_x = (scaled_w - out_w) / 2
    nx = x * scale - crop_x
    ny = y * scale
    nw = bw * scale
    nh = bh * scale
    # clamp to frame
    x0 = max(0, int(nx))
    y0 = max(0, int(ny))
    x1 = min(out_w, int(nx + nw))
    y1 = min(out_h, int(ny + nh))
    return (x0, y0, max(2, x1 - x0), max(2, y1 - y0))



def render_l3_png(text, size, path, fontsize):
    """Small top-center episode lower-third, RAQM-shaped."""
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    font = kufi(fontsize)
    draw = ImageDraw.Draw(img)
    b = draw.textbbox((0, 0), text, font=font, language="ar", direction="rtl")
    tw, th = b[2] - b[0], b[3] - b[1]
    pad_x, pad_y = 28, 12
    y = 72 if h <= 1080 else 140
    cx = w // 2
    plate = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(plate)
    x0 = cx - tw // 2 - pad_x
    y0 = y - th // 2 - pad_y
    x1 = cx + tw // 2 + pad_x
    y1 = y + th // 2 + pad_y
    pd.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=(0, 0, 0, 150))
    # thin gold underline
    pd.rectangle((cx - tw // 2, y1 - 4, cx + tw // 2, y1 - 2), fill=(247, 199, 74, 220))
    plate = plate.filter(ImageFilter.GaussianBlur(0.5))
    img = Image.alpha_composite(img, plate)
    draw = ImageDraw.Draw(img)
    draw.text(
        (cx, y), text, font=font, fill=(247, 214, 150, 255),
        anchor="mm", language="ar", direction="rtl",
        stroke_width=2, stroke_fill=(16, 10, 4, 255),
    )
    img.save(path)
    return path


def build_mafaza_source(out: Path):
    """A (kneeling) then B (wide desert). fadeblack hides leftover source xfade;
    audio is cut on silence then the complete «جيش كامل...» line."""
    tmp = out.parent
    a = tmp / "maf_a.mp4"
    b = tmp / "maf_b.mp4"
    for ss, dur, dest in ((MAF_A_SS, MAF_A_DUR, a), (MAF_B_SS, MAF_B_DUR, b)):
        run([
            "ffmpeg", "-y", "-ss", f"{ss:.3f}", "-i", str(MAF_SRC),
            "-t", f"{dur:.3f}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "14",
            "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "256k",
            "-avoid_negative_ts", "make_zero",
            str(dest),
        ])
    offset = MAF_A_DUR - MAF_XFADE
    # video: fadeblack. audio: trim A to the overlap start (silence),
    # then B at full level so «جيش» onset is not faded.
    fc = (
        f"[0:v][1:v]xfade=transition=fadeblack:duration={MAF_XFADE:.3f}:offset={offset:.3f}[v];"
        f"[0:a]afade=t=out:st={max(0, offset - 0.05):.3f}:d=0.05,"
        f"atrim=0:{offset:.3f},asetpts=PTS-STARTPTS[a0];"
        f"[1:a]aformat=fltp:48000:stereo[a1];"
        f"[a0][a1]concat=n=2:v=0:a=1[a]"
    )
    run([
        "ffmpeg", "-y", "-i", str(a), "-i", str(b),
        "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "14",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "256k",
        "-movflags", "+faststart",
        str(out),
    ])
    print("MAFAZA combined", out, "dur", probe_dur(out), "expected", MAF_DUR)
    return out


def encode_clip(spec, grad, out, w, h, crop_9x16, cap_dir):
    src, ss, dur = spec["src"], spec["ss"], spec["dur"]
    caps, overlays = spec["caps"], spec.get("overlays") or []
    blur_box = spec.get("blur_box")
    blur_times = spec.get("blur_times")
    l3 = spec.get("l3")

    for a, b, t in caps:
        if b - a < 1.2 - 1e-6:
            raise SystemExit(f"caption too short ({b-a:.2f}s): {t}")

    fade_in = float(spec.get("fade_in", AUDIO_FADE))
    fade_out = float(spec.get("fade_out", AUDIO_FADE))
    video_fade_in = float(spec.get("video_fade_in", VIDEO_FADE_IN))
    video_fade_out = float(spec.get("video_fade_out", VIDEO_FADE_OUT))
    af = (
        f"afade=t=in:st=0:d={fade_in},"
        f"afade=t=out:st={max(0, dur - fade_out):.4f}:d={fade_out},"
        f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    )
    blur_luma = spec.get("blur_luma", 10)
    blur_chroma = spec.get("blur_chroma", 8)
    if crop_9x16:
        vf_geo = "scale=3414:1920:flags=lanczos,crop=1080:1920"
        blur_h = spec.get("blur_h_9", 280)
        fsize = 56
        osize_main, osize_sub = 92, 44
        l3size = 40
        bar_h = spec.get("bar_9")
    else:
        vf_geo = f"scale={w}:{h}:flags=lanczos,setsar=1"
        blur_h = spec.get("blur_h_16", 220)
        fsize = 58
        osize_main, osize_sub = 100, 48
        l3size = 42
        bar_h = spec.get("bar_16")

    grad_path = grad
    if bar_h is not None:
        grad_path = out.parent / f"grad_{spec['id']}.png"
        make_gradient(
            grad_path, w, h, int(bar_h),
            feather=spec.get("grad_feather"),
            max_alpha=spec.get("grad_alpha", 200),
        )

    inputs = ["-ss", f"{ss:.3f}", "-i", str(src), "-loop", "1", "-i", str(grad_path)]
    cap_files = []
    for i, (a, b, text) in enumerate(caps):
        png = cap_dir / f"cap_{out.stem}_{i}.png"
        render_caption_png(text, (w, h), png, fsize)
        cap_files.append(png)
        inputs.extend(["-loop", "1", "-i", str(png)])
    ov_files = []
    for i, (a, b, main, sub) in enumerate(overlays):
        png = cap_dir / f"ov_{out.stem}_{i}.png"
        render_overlay_png(main, sub, (w, h), png, osize_main, osize_sub)
        ov_files.append(png)
        inputs.extend(["-loop", "1", "-i", str(png)])
    l3_file = None
    if l3:
        png = cap_dir / f"l3_{out.stem}.png"
        render_l3_png(l3[2], (w, h), png, l3size)
        l3_file = png
        inputs.extend(["-loop", "1", "-i", str(png)])

    fc = (
        f"[0:v]{vf_geo},format=yuv420p,split=2[base][forblur];"
        f"[forblur]crop=iw:{blur_h}:0:ih-{blur_h},boxblur={blur_luma}:{blur_chroma}[blurred];"
        f"[base][blurred]overlay=0:H-h[cov];"
    )
    last = "cov"
    if blur_box is not None:
        if crop_9x16:
            bx, by, bw, bh = map_box_9x16(blur_box)
        else:
            bx, by, bw, bh = blur_box
        t0, t1 = blur_times
        en = f"enable='between(t,{t0:.3f},{t1:.3f})'"
        fc += (
            f"[{last}]split=2[keep][reg];"
            f"[reg]crop={bw}:{bh}:{bx}:{by},boxblur=24:16[blurtxt];"
            f"[keep][blurtxt]overlay={bx}:{by}:{en}[hid];"
        )
        last = "hid"

    fc += f"[1:v]scale={w}:{h},format=rgba[g];[{last}][g]overlay=0:0[covg];"
    last = "covg"
    idx = 2

    def fade_overlay(idx, a, b, nxt, last):
        # alpha fade on the still so captions never flash
        fi = min(OVERLAY_FADE, max(0.05, (b - a) * 0.25))
        fo = fi
        st_out = max(a, b - fo)
        return (
            f"[{idx}:v]format=rgba,fade=t=in:st={a:.3f}:d={fi:.3f}:alpha=1,"
            f"fade=t=out:st={st_out:.3f}:d={fo:.3f}:alpha=1[f{nxt}];"
            f"[{last}][f{nxt}]overlay=0:0:enable='between(t,{a:.3f},{b:.3f})'[{nxt}];"
        ), nxt

    for i, (a, b, _t) in enumerate(caps):
        nxt = f"c{i}"
        chunk, last = fade_overlay(idx, a, b, nxt, last)
        fc += chunk
        idx += 1
    for i, (a, b, _m, _s) in enumerate(overlays):
        nxt = f"v{i}"
        chunk, last = fade_overlay(idx, a, b, nxt, last)
        fc += chunk
        idx += 1
    if l3:
        a, b, _ = l3
        nxt = "l3"
        chunk, last = fade_overlay(idx, a, b, nxt, last)
        fc += chunk
        idx += 1

    vfades = []
    if video_fade_in > 0:
        vfades.append(f"fade=t=in:st=0:d={video_fade_in:.3f}")
    if video_fade_out > 0:
        vst = max(0.0, dur - video_fade_out)
        vfades.append(f"fade=t=out:st={vst:.3f}:d={video_fade_out:.3f}")
    vfades.append("format=yuv420p")
    fc += f"[{last}]" + ",".join(vfades) + "[v]"

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-t", f"{dur:.3f}",
        "-filter_complex", fc,
        "-map", "[v]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "16",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-af", af,
        "-movflags", "+faststart",
        str(out),
    ]
    run(cmd)


def encode_card(png, dur, out, w, h, fade_in=0.20, fade_out=0.20):
    vf = (
        f"scale={w}:{h}:flags=lanczos,fps={FPS},format=yuv420p,setsar=1,"
        f"fade=t=in:st=0:d={fade_in:.3f},"
        f"fade=t=out:st={max(0, dur - fade_out):.3f}:d={fade_out:.3f}"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(png),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-t", f"{dur:.3f}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "16",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        str(out),
    ]
    run(cmd)


def encode_end(base_png, cta_png, dur, out, w, h):
    """End card: title first, subscribe CTA fades in, cinematic fades."""
    fade_in, fade_out = 0.35, 0.45
    cta_at = 1.60
    cta_fi = 0.45
    fc = (
        f"[0:v]scale={w}:{h}:flags=lanczos,fps={FPS},format=rgba,setsar=1[base];"
        f"[1:v]scale={w}:{h}:flags=lanczos,format=rgba,"
        f"fade=t=in:st={cta_at:.3f}:d={cta_fi:.3f}:alpha=1[cta];"
        f"[base][cta]overlay=0:0,"
        f"fade=t=in:st=0:d={fade_in:.3f},"
        f"fade=t=out:st={max(0, dur - fade_out):.3f}:d={fade_out:.3f},"
        f"format=yuv420p[v]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(base_png),
        "-loop", "1", "-i", str(cta_png),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-t", f"{dur:.3f}",
        "-filter_complex", fc,
        "-map", "[v]", "-map", "2:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "16",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        str(out),
    ]
    run(cmd)


def concat_video(paths, out):
    lst = SEG / (out.stem + "_list.txt")
    lst.write_text("".join(f"file '{p}'\n" for p in paths))
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
        "-c:v", "libx264", "-preset", "fast", "-crf", "17",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-movflags", "+faststart",
        str(out),
    ]
    run(cmd)


def build_ambience(dur: float, out: Path):
    """Continuous non-musical bed: wind + distant battle rumble + faint horses + low rumble."""
    SFX.mkdir(parents=True, exist_ok=True)
    rumble = SFX / "rumble.wav"
    run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"anoisesrc=color=brown:sample_rate=48000:duration={dur+1:.2f}:amplitude=0.35",
        "-af", "lowpass=f=80,highpass=f=20,alimiter=limit=0.4,aformat=fltp:48000:stereo",
        str(rumble),
    ])
    stems = [
        (FACTORY_SFX / "wind_1.ogg", 0.45, "lowpass=f=1200,highpass=f=80"),
        (FACTORY_SFX / "wind_2.ogg", 0.28, "lowpass=f=900,highpass=f=60"),
        (FACTORY_SFX / "battle_2.ogg", 0.22, "lowpass=f=450,highpass=f=40"),
        (FACTORY_SFX / "horses_3.ogg", 0.10, "lowpass=f=2000,highpass=f=80"),
    ]
    prepared = [rumble]
    vols = [0.22]
    for i, (src, vol, filt) in enumerate(stems):
        p = SFX / f"stem_{i}.wav"
        run([
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(src),
            "-t", f"{dur+0.5:.3f}",
            "-af", f"{filt},aformat=fltp:48000:stereo,volume={vol}",
            str(p),
        ])
        prepared.append(p)
        vols.append(1.0)
    n = len(prepared)
    inputs = []
    for p in prepared:
        inputs.extend(["-i", str(p)])
    filt = "".join(f"[{i}:a]aformat=fltp:48000:stereo,volume={vols[i]}[s{i}];" for i in range(n))
    mix = "".join(f"[s{i}]" for i in range(n))
    filt += f"{mix}amix=inputs={n}:duration=first:dropout_transition=0:normalize=0,"
    filt += f"atrim=0:{dur:.3f},alimiter=limit=0.6,aformat=fltp:48000:stereo[a]"
    run([
        "ffmpeg", "-y", *inputs, "-filter_complex", filt, "-map", "[a]",
        str(out),
    ])
    print("ambience", out, "dur", probe_dur(out))
    return out


def build_hits(cut_times, dur, out: Path):
    """Whoosh + impact on every transition (open, cards, end). No musical tones."""
    SFX.mkdir(parents=True, exist_ok=True)
    whooshes, thuds = [], []
    for i in range(len(cut_times)):
        wp = SFX / f"whoosh_{i}.wav"
        tp = SFX / f"thud_{i}.wav"
        write_wav(str(wp), whoosh(dur=0.55, f0=300 + i * 18, f1=2300 + i * 70, seed=10 + i * 3))
        write_wav(str(tp), thud(dur=0.75, seed=20 + i * 5))
        whooshes.append(wp)
        thuds.append(tp)
    n = int(48000 * (dur + 1))
    acc = np.zeros((n, 2), np.float32)

    def read_mono(path):
        raw = subprocess.check_output([
            "ffmpeg", "-v", "error", "-i", str(path),
            "-ac", "1", "-ar", "48000", "-f", "f32le", "-",
        ])
        return np.frombuffer(raw, dtype=np.float32)

    for i, t in enumerate(cut_times):
        wh = read_mono(whooshes[i]) * 0.72
        th = read_mono(thuds[i]) * 0.88
        # whoosh leads the dip, thud lands on the cut
        for sig, off in ((wh, t - 0.16), (th, t)):
            start = int(max(0, off) * 48000)
            sl = sig[: max(0, n - start)]
            acc[start:start + len(sl), 0] += sl
            acc[start:start + len(sl), 1] += sl
    peak = float(np.abs(acc).max()) or 1.0
    if peak > 0.95:
        acc *= 0.95 / peak
    raw = acc[: int(dur * 48000)].clip(-1, 1).astype(np.float32).tobytes()
    p = subprocess.run([
        "ffmpeg", "-y", "-f", "f32le", "-ar", "48000", "-ac", "2", "-i", "-",
        str(out),
    ], input=raw, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if p.returncode != 0:
        raise RuntimeError("hits encode failed")
    print("hits", out, "at", [round(t, 3) for t in cut_times])
    return out


def mux_mix(video, narration_src, ambience, hits, out, dur):
    """Mix narration + bed + hits, loudnorm to -14 LUFS, mux with video."""
    premix = SFX / (out.stem + "_premix.wav")
    fc = (
        f"[0:a]aformat=fltp:48000:stereo,volume=1.15[nar];"
        f"[1:a]aformat=fltp:48000:stereo,volume=0.55[bed];"
        f"[2:a]aformat=fltp:48000:stereo,volume=0.82[hit];"
        f"[nar][bed][hit]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,"
        f"alimiter=limit=0.95[a]"
    )
    run([
        "ffmpeg", "-y",
        "-i", str(narration_src), "-i", str(ambience), "-i", str(hits),
        "-filter_complex", fc, "-map", "[a]", "-t", f"{dur:.3f}",
        str(premix),
    ])
    meas = subprocess.check_output([
        "ffmpeg", "-i", str(premix),
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
        "-f", "null", "-",
    ], stderr=subprocess.STDOUT, text=True)
    import json, re
    m = re.search(r"\{[\s\S]*\}", meas)
    if not m:
        print("loudnorm measure failed, raw:\n", meas[-1500:])
        raise SystemExit("loudnorm measure failed")
    j = json.loads(m.group(0))
    print("loudnorm measure", {k: j.get(k) for k in (
        "input_i", "input_tp", "input_lra", "input_thresh", "target_offset")})
    ln = (
        f"loudnorm=I=-14:TP=-1.5:LRA=11:"
        f"measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
        f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:"
        f"offset={j['target_offset']}:linear=true:print_format=summary"
    )
    mixed = SFX / (out.stem + "_mixed.wav")
    run([
        "ffmpeg", "-y", "-i", str(premix), "-af", ln, str(mixed),
    ])
    run([
        "ffmpeg", "-y", "-i", str(video), "-i", str(mixed),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(out),
    ])
    return out


def build(kind: str, mafaza_src: Path):
    if kind == "16x9":
        w, h = 1920, 1080
        suffix = "16x9"
        crop = False
        out = ROOT / "trailer_16x9_v4.mp4"
    else:
        w, h = 1080, 1920
        suffix = "9x16"
        crop = True
        out = ROOT / "trailer_9x16_v4.mp4"

    work = SEG / f"{kind}_v4"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    grad = work / "grad.png"
    make_gradient(grad, w, h, 230 if not crop else 320)

    specs = []
    for s in CLIPS_SPEC:
        d = dict(s)
        if d["src"] == "MAFAZA_COMBINED":
            d["src"] = mafaza_src
        specs.append(d)

    pieces = []
    cut_times = []  # visual cuts where whoosh/thud land
    t = 0.0

    # opening series card
    open_png = CARDS / f"open_{suffix}.png"
    open_mp4 = work / "open.mp4"
    encode_card(open_png, OPEN_DUR, open_mp4, w, h, fade_in=0.40, fade_out=0.28)
    pieces.append(open_mp4)
    cut_times.append(0.12)  # opening hit
    t += OPEN_DUR
    cut_times.append(t)  # into first clip

    card_starts = []
    for i, spec in enumerate(specs):
        if i > 0:
            card_png = CARDS / f"{CARD_IDS[i-1]}_{suffix}.png"
            card_mp4 = work / f"card_{i:02d}.mp4"
            encode_card(card_png, CARD_DUR, card_mp4, w, h, fade_in=0.20, fade_out=0.20)
            pieces.append(card_mp4)
            card_starts.append(t)
            cut_times.append(t)  # card in (whoosh covers the dip)
            t += CARD_DUR
            # no second hit 1s later — it would overlap the card-in whoosh
        mp4 = work / f"clip_{i:02d}.mp4"
        encode_clip(spec, grad, mp4, w, h, crop, work)
        pieces.append(mp4)
        t += spec["dur"]

    end_base = CARDS / f"end_base_{suffix}.png"
    end_cta = CARDS / f"end_cta_{suffix}.png"
    end_mp4 = work / "end.mp4"
    encode_end(end_base, end_cta, END_DUR, end_mp4, w, h)
    end_start = t
    pieces.append(end_mp4)
    cut_times.append(end_start)
    t += END_DUR
    print(f"{kind} planned duration {t:.3f}s  cards at {[round(x,3) for x in card_starts]}  end {end_start:.3f}")

    raw = work / "concat_raw.mp4"
    concat_video(pieces, raw)
    actual = probe_dur(raw)
    print("concat", raw, actual)

    amb = SFX / f"ambience_{kind}_v4.wav"
    build_ambience(actual, amb)
    hits = SFX / f"hits_{kind}_v4.wav"
    build_hits(cut_times, actual, hits)
    mux_mix(raw, raw, amb, hits, out, actual)
    final_d = probe_dur(out)
    print("OUT", out, "duration", final_d)
    return out, final_d, card_starts, end_start, cut_times


def main():
    kinds = sys.argv[1:] or ["16x9", "9x16"]
    for s in CLIPS_SPEC:
        for a, b, t in s["caps"]:
            if b - a < 1.2 - 1e-6:
                raise SystemExit(f"short caption in {s['id']}: {b-a:.2f}s {t}")
    planned = (
        OPEN_DUR + sum(s["dur"] for s in CLIPS_SPEC) + CARD_DUR * 6 + END_DUR
    )
    print("planned total", round(planned, 3))
    if not (60 <= planned <= 80):
        raise SystemExit(f"duration {planned} outside 60–80s")

    maf = SEG / "mafaza_combined_v4.mp4"
    if "16x9" in kinds or "9x16" in kinds:
        # rebuild combined source once
        if not maf.exists() or "rebuild-maf" in sys.argv:
            build_mafaza_source(maf)
        elif abs(probe_dur(maf) - MAF_DUR) > 0.12:
            build_mafaza_source(maf)
        else:
            print("reuse", maf, probe_dur(maf))

    results = []
    for kind in kinds:
        if kind not in ("16x9", "9x16"):
            continue
        results.append(build(kind, maf))
    print("DONE", [(str(r[0]), r[1]) for r in results])


if __name__ == "__main__":
    main()
