# -*- coding: utf-8 -*-
"""هوية عائلة «المتفائل» — نظام الحلقة المشتركة (الخيار 2)، 2026-11-27.

يصيّر بالكود كل الأصول النهائية للقناتين من مصادر بلا كتابة في src/:
  history/  قناة المتفائل للمعارك (UCda-VgyvZwAH5_Pl1elVEnw)
  hikayat/  قناة المتفائل | حكايات (UC7owFa1Z0P8vv5tSzhRYfPw) — ملفات فقط، لا يُلمس شيء فيها من هنا
الحلقة والكلمة «المتفائل» واحدة في القناتين حرفياً (المواصفة RING_SPEC.md).
النص يُركَّب بالكود (RAQM + نصّ منطقيّ) بعد tools/text_gate.py؛ لا كتابة مولَّدة.
طبقات الغلاف محفوظة منفصلة لإعادة التحرير (layers/). التشغيل:
  python3 ops/branding/2026-11-27/compose.py
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import text_gate  # noqa: E402

# ───────────────────────── الثوابت المشتركة (مطابقة لـ RING_SPEC.md) ─────────────────────────
FONT_WORDMARK = os.path.join(ROOT, "assets", "Amiri-Bold.ttf")          # OFL
FONT_TAG = "/usr/share/fonts/truetype/sand-box/google/Noto Naskh Arabic/NotoNaskhArabic-VariableFont_wght.ttf"  # OFL
WORDMARK = "المتفائل"

GOLD_STOPS = [  # تدرّج الذهب المعدنيّ عمودياً (0 أعلى ← 1 أسفل)
    (0.00, (255, 241, 184)),
    (0.30, (242, 199, 92)),
    (0.52, (184, 134, 43)),
    (0.70, (232, 192, 100)),
    (1.00, (154, 111, 34)),
]
GOLD_DARK = (58, 40, 10)        # حدّ خارجيّ وأخاديد
S = 800                         # الشبكة المرجعية للحلقة
RING = dict(outer=376, inner=336, groove_out=368, groove_in=344, groove_w=2.5,
            edge_w=2.0, accent_r=326, accent_w=3.0, studs=8, stud_r=356, stud_size=9.0)

CHANNELS = {
    "history": dict(
        channel_id="UCda-VgyvZwAH5_Pl1elVEnw",
        field_center=(14, 38, 76), field_edge=(4, 12, 30), glow=(40, 170, 180),
        accent=(59, 195, 201),              # فيروزي
        tag="معارك الإسلام وبطولات أبطاله", tag_color=(236, 241, 238), tag_line=(59, 195, 201),
        corner=(4, 12, 30),
    ),
    "hikayat": dict(
        channel_id="UC7owFa1Z0P8vv5tSzhRYfPw",
        field_center=(18, 92, 70), field_edge=(5, 38, 29), glow=(243, 233, 210),
        accent=(243, 233, 210),             # كريميّ
        tag="حكايات إسلامية بمصادرها", tag_color=(243, 233, 210), tag_line=(243, 233, 210),
        corner=(5, 38, 29),
    ),
}

SAFE = (507, 508, 2053, 931)    # الشريط الآمن 1546×423 في وسط 2560×1440


# ───────────────────────── أدوات ─────────────────────────
def gold_gradient(h: int, w: int, top: float = 0.0, height: float | None = None) -> np.ndarray:
    height = height or h
    ys = (np.arange(h, dtype=np.float32) - top) / max(height, 1)
    ys = np.clip(ys, 0, 1)
    out = np.zeros((h, 3), np.float32)
    for c in range(3):
        out[:, c] = np.interp(ys, [s[0] for s in GOLD_STOPS], [s[1][c] for s in GOLD_STOPS])
    return np.repeat(out[:, None, :], w, axis=1)


def fill_mask(mask: Image.Image, rgb_arr: np.ndarray) -> Image.Image:
    rgba = np.dstack([rgb_arr.astype(np.uint8), np.asarray(mask, np.uint8)])
    return Image.fromarray(rgba, "RGBA")


def solid(mask: Image.Image, rgb, alpha: float = 1.0) -> Image.Image:
    a = (np.asarray(mask, np.float32) * alpha).astype(np.uint8)
    h, w = a.shape
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., :3] = rgb
    arr[..., 3] = a
    return Image.fromarray(arr, "RGBA")


def font(path: str, size: int, wght: int | None = None) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    if wght is not None:
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
    return f


def text_mask(text: str, f: ImageFont.FreeTypeFont, pad: int = 40) -> Image.Image:
    """نصّ منطقيّ يُشكَّل بـ RAQM (اتجاه RTL) — لا قلب يدويّ، فلا قلب مزدوج."""
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    bb = probe.textbbox((0, 0), text, font=f, direction="rtl", language="ar")
    w, h = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).text((pad - bb[0], pad - bb[1]), text, font=f, fill=255, direction="rtl", language="ar")
    return m.crop(m.getbbox())


def radial(size, c_in, c_out, cx=None, cy=None, r=None, power=1.25) -> np.ndarray:
    w, h = size
    cx = w / 2 if cx is None else cx
    cy = h / 2 if cy is None else cy
    r = r or math.hypot(w / 2, h / 2)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = np.clip(np.hypot(xx - cx, yy - cy) / r, 0, 1) ** power
    a = np.array(c_in, np.float32)
    b = np.array(c_out, np.float32)
    return a[None, None] * (1 - t[..., None]) + b[None, None] * t[..., None]


# ───────────────────────── الحلقة (مشتركة حرفياً) ─────────────────────────
def ring_layer(accent, ss: int = 4) -> Image.Image:
    """الحلقة الذهبية بالمقاس 800 مرسومة بدقة ×4 ثم مصغّرة بـ Lanczos."""
    N = S * ss
    c = N / 2
    sc = ss
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    rr = np.hypot(xx - c, yy - c) / sc
    ang = np.arctan2(yy - c, xx - c)

    def band(r0, r1, soft=0.6):
        return np.clip((rr - r0) / soft + 0.5, 0, 1) * np.clip((r1 - rr) / soft + 0.5, 0, 1)

    body = band(RING["inner"], RING["outer"])
    # معدن: تدرّج عمودي + لمعة مخروطية (ضوء من أعلى اليسار) + تحدّب شعاعيّ
    grad = gold_gradient(N, 1, 0, N)[:, 0, :]
    metal = np.repeat(grad[:, None, :], N, axis=1)
    cone = 0.5 + 0.5 * np.cos(ang - math.radians(-135))          # 1 عند أعلى اليسار
    bevel = np.sin(np.clip((rr - RING["inner"]) / (RING["outer"] - RING["inner"]), 0, 1) * math.pi)
    shade = 0.78 + 0.22 * cone + 0.12 * (bevel - 0.5)
    metal = np.clip(metal * shade[..., None], 0, 255)
    rgb = metal
    alpha = body.copy()

    def paint(mask, color):
        nonlocal rgb, alpha
        m = mask[..., None]
        rgb = rgb * (1 - m) + np.array(color, np.float32)[None, None] * m
        alpha = np.maximum(alpha, mask)

    gw = RING["groove_w"] / 2
    paint(band(RING["groove_out"] - gw, RING["groove_out"] + gw), GOLD_DARK)
    paint(band(RING["groove_in"] - gw, RING["groove_in"] + gw), GOLD_DARK)
    ew = RING["edge_w"]
    paint(band(RING["outer"] - ew, RING["outer"] + 0.5), GOLD_DARK)
    paint(band(RING["inner"] - 0.5, RING["inner"] + ew), GOLD_DARK)
    aw = RING["accent_w"] / 2
    paint(band(RING["accent_r"] - aw, RING["accent_r"] + aw), accent)

    # أزرار معيّنية بين الأخدودين (8 عند 0°،45°…) — نجمة الثمانية لا صليب
    img = Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(img)
    for k in range(RING["studs"]):
        a = math.radians(k * 360 / RING["studs"] - 90)
        x = c + math.cos(a) * RING["stud_r"] * sc
        y = c + math.sin(a) * RING["stud_r"] * sc
        s = RING["stud_size"] * sc
        ca, sa = math.cos(a), math.sin(a)
        pts = [(x + ca * s, y + sa * s), (x - sa * s * 0.62, y + ca * s * 0.62),
               (x - ca * s, y - sa * s), (x + sa * s * 0.62, y - ca * s * 0.62)]
        d.polygon(pts, fill=GOLD_DARK + (255,))
        inner = [(x + (px - x) * 0.6, y + (py - y) * 0.6) for px, py in pts]
        d.polygon(inner, fill=(255, 236, 170, 255))
    return img.resize((S, S), Image.LANCZOS)


def field_layer(ch: dict) -> Image.Image:
    arr = radial((S, S), ch["field_center"], ch["field_edge"], r=RING["inner"], power=1.1)
    glow = radial((S, S), (1, 1, 1), (0, 0, 0), cy=S * 0.46, r=230, power=1.6)[..., 0]
    arr = arr + np.array(ch["glow"], np.float32)[None, None] * glow[..., None] * 0.16
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    rr = np.hypot(xx - S / 2, yy - S / 2)
    mask = np.clip((RING["inner"] + 1 - rr) / 1.0, 0, 1)
    return Image.fromarray(np.dstack([np.clip(arr, 0, 255), mask * 255]).astype(np.uint8), "RGBA")


# ───────────────────────── الرموز ─────────────────────────
def key_out(img: Image.Image, bg, lo=8, hi=34) -> np.ndarray:
    a = np.asarray(img.convert("RGB"), np.float32)
    d = np.sqrt(((a - np.array(bg, np.float32)) ** 2).sum(2))
    return np.clip((d - lo) / (hi - lo), 0, 1)


def history_symbol() -> Image.Image:
    """سيفان مستقيمان وترس وراية سادة — يُحذف إطار المصدر ونطاق الفرسان الصغار أسفل."""
    src = Image.open(os.path.join(SRC, "history_emblem_source.jpg")).convert("RGB")
    a = np.asarray(src, np.float32)
    bg = a[8:20, 8:20].reshape(-1, 3).mean(0)
    alpha = key_out(src, bg, 10, 40)
    H, W = alpha.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = 512.0, 524.0
    rr = np.hypot(xx - cx, yy - cy)
    region = np.clip((390 - rr) / 6, 0, 1)                        # داخل إطار المصدر فقط
    spear = ((xx > 486) & (xx < 540) & (yy < 140)).astype(np.float32)  # رأس الراية فوق الإطار
    region = np.maximum(region, spear)
    fade = np.clip((720 - yy) / 70, 0, 1)                          # إخفاء الفرسان والغبار أسفل الترس
    value = a.max(2)
    # ذهب/فولاذ يُحفظ؛ التراب البنيّ في الأسفل يُحذف (ليس صليباً ولا وجهاً، لكنه أثر بشريّ)
    is_steel = (a[:, :, 2] >= a[:, :, 0] * 0.80) & (value > 70)
    is_gold = (a[:, :, 0] > 150) & (a[:, :, 1] > 110) & (a[:, :, 0] > a[:, :, 2] + 40)
    # الذهب يُحفظ فوق خط الترس فقط؛ أسفله لا يُستثنى إلا الفولاذ (نصل السيف)،
    # لأن غبار الميدان والفرسان في المصدر ذهبيتهم قريبة من الذهب.
    alpha = alpha * region
    alpha = np.where(is_steel, alpha, alpha * fade)
    alpha = np.where((yy > 735) & ~is_steel, 0, alpha)
    rgba = np.dstack([a, alpha * 255]).astype(np.uint8)
    im = Image.fromarray(rgba, "RGBA")
    return im.crop(im.getbbox())


def hikayat_symbol() -> Image.Image:
    """فانوس فوق كتاب مفتوح — من أصل قناة الحكايات، بلا كتابة."""
    src = Image.open(os.path.join(SRC, "hikayat_emblem_source.jpg")).convert("RGB")
    a = np.asarray(src, np.float32)
    bg = a[8:20, 8:20].reshape(-1, 3).mean(0)
    alpha = key_out(src, bg, 8, 34)
    rgba = np.dstack([a, alpha * 255]).astype(np.uint8)
    im = Image.fromarray(rgba, "RGBA")
    return im.crop(im.getbbox())


def place_symbol(sym: Image.Image, max_w: float, max_h: float, cy: float) -> Image.Image:
    s = min(max_w / sym.width, max_h / sym.height)
    big = sym.resize((max(1, round(sym.width * s)), max(1, round(sym.height * s))), Image.LANCZOS)
    big = big.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    layer.alpha_composite(big, (round(S / 2 - big.width / 2), round(cy - big.height / 2)))
    # قصّ داخل الحقل
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    m = np.clip((RING["accent_r"] - 4 - np.hypot(xx - S / 2, yy - S / 2)) / 1.0, 0, 1)
    arr = np.asarray(layer).copy()
    arr[..., 3] = (arr[..., 3] * m).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


SYMBOL_FIT = {  # (أقصى عرض، أقصى ارتفاع، مركز عمودي) على شبكة 800
    "history": (560, 600, 396),
    "hikayat": (630, 580, 418),
}


def render_mark(name: str) -> Image.Image:
    """العلامة الدائرية الشفافة خارج الحلقة (RGBA 800)."""
    ch = CHANNELS[name]
    sym = history_symbol() if name == "history" else hikayat_symbol()
    mw, mh, cy = SYMBOL_FIT[name]
    mark = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mark.alpha_composite(field_layer(ch))
    # ظلّ خفيف للرمز
    symL = place_symbol(sym, mw, mh, cy)
    sh = symL.split()[3].filter(ImageFilter.GaussianBlur(8))
    mark.alpha_composite(solid(sh, (0, 0, 0), 0.45), (0, 6))
    mark.alpha_composite(symL)
    # ظلّ داخليّ تحت الحلقة
    ringL = ring_layer(ch["accent"])
    rs = ringL.split()[3].filter(ImageFilter.GaussianBlur(6))
    mark.alpha_composite(solid(rs, (0, 0, 0), 0.55), (0, 4))
    mark.alpha_composite(ringL)
    return mark


def render_icon(name: str, mark: Image.Image) -> Image.Image:
    ch = CHANNELS[name]
    base = Image.new("RGBA", (S, S), ch["corner"] + (255,))
    base.alpha_composite(mark)
    return base.convert("RGB")


def render_seal(name: str, mark: Image.Image) -> Image.Image:
    """نسخة الأحجام الكبيرة: «المتفائل» على لوح ذهبيّ يقطع أسفل الحلقة."""
    ch = CHANNELS[name]
    seal = mark.copy()
    d = ImageDraw.Draw(seal)
    pw, ph, cy = 330, 92, S / 2 + RING["outer"] - 20
    x0, y0, x1, y1 = S / 2 - pw / 2, cy - ph / 2, S / 2 + pw / 2, cy + ph / 2
    d.rounded_rectangle((x0 - 4, y0 - 4, x1 + 4, y1 + 4), radius=ph / 2 + 4, fill=GOLD_DARK + (255,))
    plate = Image.new("L", (S, S), 0)
    ImageDraw.Draw(plate).rounded_rectangle((x0, y0, x1, y1), radius=ph / 2, fill=255)
    seal.alpha_composite(fill_mask(plate, gold_gradient(S, S, y0, ph)))
    d.rounded_rectangle((x0 + 6, y0 + 6, x1 - 6, y1 - 6), radius=ph / 2 - 6, fill=ch["corner"] + (255,))
    m = text_mask(WORDMARK, font(FONT_WORDMARK, 64))
    tx, ty = round(S / 2 - m.width / 2), round(cy - m.height / 2 - 2)
    big = Image.new("L", (S, S), 0)
    big.paste(m, (tx, ty))
    seal.alpha_composite(fill_mask(big, gold_gradient(S, S, ty, m.height)))
    return seal


# ───────────────────────── الغلاف ─────────────────────────
def upscale_bg(path: str) -> Image.Image:
    im = Image.open(path).convert("RGB")
    up = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)          # 1280×720 → 2560×1440
    up = up.resize((2560, 1440), Image.LANCZOS) if up.size != (2560, 1440) else up
    up = up.filter(ImageFilter.UnsharpMask(radius=2.0, percent=55, threshold=3))
    return up


def hikayat_bg() -> Image.Image:
    """خلفية زمرّدية مصنوعة بالكود: نجمة ثمانية متكرّرة خافتة + ضوء ذهبيّ — بلا كتابة ولا مبانٍ."""
    W, H = 2560, 1440
    arr = radial((W, H), (16, 84, 64), (3, 26, 20), r=1500, power=1.2)
    img = Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")
    pat = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(pat)
    step = 160
    for gy in range(-step, H + step, step):
        for gx in range(-step, W + step, step):
            cx, cy, r = gx + (step / 2 if (gy // step) % 2 else 0), gy, 58
            sq1 = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in (0, 90, 180, 270)]
            sq2 = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in (45, 135, 225, 315)]
            d.polygon(sq1, outline=255, width=2)
            d.polygon(sq2, outline=255, width=2)
    # يخفت في الوسط ليبقى الشريط الآمن هادئاً
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    calm = np.clip((np.hypot((xx - W / 2) / 1.6, yy - H / 2) - 260) / 600, 0, 1)
    pa = (np.asarray(pat, np.float32) * 0.10 * calm).astype(np.uint8)
    img.alpha_composite(solid(Image.fromarray(pa), (214, 178, 96)))
    glow = radial((W, H), (1, 1, 1), (0, 0, 0), r=900, power=1.8)[..., 0]
    img.alpha_composite(solid(Image.fromarray((glow * 70).astype(np.uint8)), (243, 220, 160)))
    return img.convert("RGB")


def banner(name: str, mark: Image.Image, outdir: str) -> dict:
    ch = CHANNELS[name]
    W, H = 2560, 1440
    bg = upscale_bg(os.path.join(SRC, "history_banner_bg_source.jpg")) if name == "history" else hikayat_bg()
    layers = os.path.join(outdir, "layers")
    os.makedirs(layers, exist_ok=True)
    bg.save(os.path.join(layers, "L0_background_2560x1440.jpg"), quality=95, subsampling=0)

    # L1 تعتيم بيضاويّ خلف الكتلة لقراءة النص فوق الفجر
    scrim = radial((W, H), (1, 1, 1), (0, 0, 0), r=1000, power=1.0)[..., 0]
    sa = np.clip(scrim * 1.25, 0, 1) * (0.62 if name == "history" else 0.30)
    L1 = solid(Image.fromarray((sa * 255).astype(np.uint8)), (2, 8, 20) if name == "history" else (2, 20, 15))

    # الكتلة داخل الشريط الآمن بهامش 24 بكسل (الظلال مشمولة)
    pad = 24
    inner = (SAFE[0] + pad, SAFE[1] + pad, SAFE[2] - pad, SAFE[3] - pad)
    mark_h = 318
    mk = mark.resize((mark_h, mark_h), Image.LANCZOS)
    f_wm = font(FONT_WORDMARK, 196)
    f_tag = font(FONT_TAG, 64, wght=700)
    wm = text_mask(WORDMARK, f_wm)
    tg = text_mask(ch["tag"], f_tag)
    gap, rule_gap = 70, 34
    text_w = max(wm.width, tg.width)
    total_w = mark_h + gap + text_w
    x_left = round(W / 2 - total_w / 2)
    cy = round((inner[1] + inner[3]) / 2)
    block_h = wm.height + rule_gap * 2 + 4 + tg.height
    y_top = round(cy - block_h / 2)
    tx_c = x_left + text_w / 2
    mx = x_left + text_w + gap
    my = round(cy - mark_h / 2)

    L2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    msh = mk.split()[3].filter(ImageFilter.GaussianBlur(7))
    L2.alpha_composite(solid(msh, (0, 0, 0), 0.5), (mx, my + 5))
    L2.alpha_composite(mk, (mx, my))

    L3 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    wx, wy = round(tx_c - wm.width / 2), y_top
    big = Image.new("L", (W, H), 0)
    big.paste(wm, (wx, wy))
    L3.alpha_composite(solid(big.filter(ImageFilter.GaussianBlur(7)), (0, 0, 0), 0.7), (0, 4))
    edge = big.filter(ImageFilter.MaxFilter(5))
    L3.alpha_composite(solid(edge, GOLD_DARK))
    L3.alpha_composite(fill_mask(big, gold_gradient(H, W, wy, wm.height)))
    ry = wy + wm.height + rule_gap
    rl = Image.new("L", (W, H), 0)
    rd = ImageDraw.Draw(rl)
    rw = round(text_w * 0.78)
    rd.line([(tx_c - rw / 2, ry), (tx_c + rw / 2, ry)], fill=255, width=4)
    for sx in (tx_c - rw / 2 - 18, tx_c + rw / 2 + 18):
        rd.polygon([(sx - 10, ry), (sx, ry - 10), (sx + 10, ry), (sx, ry + 10)], fill=255)
    L3.alpha_composite(solid(rl, ch["tag_line"], 0.95))
    gx, gy = round(tx_c - tg.width / 2), ry + rule_gap
    tb = Image.new("L", (W, H), 0)
    tb.paste(tg, (gx, gy))
    L3.alpha_composite(solid(tb.filter(ImageFilter.GaussianBlur(4)), (0, 0, 0), 0.75), (0, 3))
    L3.alpha_composite(solid(tb, ch["tag_color"]))

    L1.save(os.path.join(layers, "L1_scrim.png"), optimize=True)
    L2.save(os.path.join(layers, "L2_mark.png"), optimize=True)
    L3.save(os.path.join(layers, "L3_text.png"), optimize=True)

    out = bg.convert("RGBA")
    for L in (L1, L2, L3):
        out.alpha_composite(L)
    final = out.convert("RGB")
    p = os.path.join(outdir, f"{name}_banner_2560x1440.jpg")
    final.save(p, quality=93, subsampling=0, optimize=True, progressive=True)

    combo = Image.alpha_composite(L2, L3)
    arr = np.asarray(combo)[..., 3]
    ys, xs = np.where(arr >= 16)
    content = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    margin = (content[0] - SAFE[0], content[1] - SAFE[1], SAFE[2] - content[2], SAFE[3] - content[3])
    if any(m < 8 for m in margin):
        raise SystemExit(f"⛔ محتوى الغلاف ({name}) خارج الهامش الآمن 8px: bbox={content} margin={margin}")
    layout = dict(canvas=[W, H], safe_area=list(SAFE), content_bbox=list(content), safe_margin=list(margin),
                  mark=dict(x=mx, y=my, size=mark_h), wordmark=dict(text=WORDMARK, font="Amiri-Bold", size=230, x=wx, y=wy),
                  tagline=dict(text=ch["tag"], font="Noto Naskh Arabic wght700", size=74, x=gx, y=gy),
                  rule_y=ry, order="L0_background → L1_scrim → L2_mark → L3_text")
    json.dump(layout, open(os.path.join(layers, "layout.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return dict(path=p, layout=layout, final=final)


def crop_preview(name: str, final: Image.Image, outdir: str):
    W, H = 2560, 1440
    pv = final.copy().convert("RGBA")
    ov = Image.new("RGBA", pv.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    zones = [("TV 2560x1440", (0, 0, 2559, 1439), (255, 255, 255, 230)),
             ("Desktop max 2560x423", (0, 508, 2559, 931), (255, 200, 60, 255)),
             ("Tablet 1855x423", (352, 508, 2207, 931), (80, 220, 255, 255)),
             ("Mobile/safe 1546x423", SAFE, (255, 80, 80, 255))]
    # تظليل ما خارج الشريط الآمن
    shade = Image.new("L", pv.size, 120)
    ImageDraw.Draw(shade).rectangle(SAFE, fill=0)
    ov.alpha_composite(solid(shade, (0, 0, 0)))
    lab = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    for t, box, col in zones:
        d.rectangle(box, outline=col, width=6)
    # مفتاح في السماء أعلى اليسار، بعيداً عن الشريط
    lx, ly = 40, 40
    d.rounded_rectangle((lx, ly, 640, 230), radius=12, fill=(0, 0, 0, 180))
    for i, (t, box, col) in enumerate(zones):
        yy = ly + 16 + i * 44
        d.rectangle((lx + 18, yy + 8, lx + 54, yy + 32), fill=col)
        d.text((lx + 70, yy), t, font=lab, fill=(255, 255, 255, 255))
    pv.alpha_composite(ov)
    pv = pv.convert("RGB").resize((1280, 720), Image.LANCZOS)
    p = os.path.join(outdir, f"{name}_banner_crop_zones_preview.jpg")
    pv.save(p, quality=90)
    mob = final.crop(SAFE)
    mob.save(os.path.join(outdir, f"{name}_banner_mobile_safe_crop.jpg"), quality=92)
    return p


def circle_alpha(img: Image.Image) -> Image.Image:
    n = img.width
    ss = 4
    m = Image.new("L", (n * ss, n * ss), 0)
    ImageDraw.Draw(m).ellipse((0, 0, n * ss - 1, n * ss - 1), fill=255)
    m = m.resize((n, n), Image.LANCZOS)
    out = img.convert("RGBA")
    out.putalpha(m)
    return out


def sizes_preview(icons: dict, outdir: str) -> str:
    sizes = [800, 88, 48, 24]
    pad = 40
    W = pad + sum(s + pad for s in sizes) + 2 * (24 * 4 + pad) + (48 * 4 + pad)
    rows = len(icons) * 2
    H = pad + rows * (800 + pad)
    H = pad + len(icons) * 2 * (800 + pad)
    canvas = Image.new("RGB", (W, len(icons) * 2 * 880 + pad), (255, 255, 255))
    d = ImageDraw.Draw(canvas)
    lab = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    y = pad
    for name, icon in icons.items():
        for bgc, bgname in (((255, 255, 255), "light"), ((15, 15, 15), "dark")):
            d.rectangle((0, y - 20, W, y + 840), fill=bgc)
            x = pad
            for s in sizes:
                im = circle_alpha(icon.resize((s, s), Image.LANCZOS))
                canvas.paste(im, (x, y + (800 - s) // 2), im)
                d.text((x, y + 806), f"{name} {s}px", font=lab, fill=(128, 128, 128))
                x += s + pad
            for s in (48, 24):  # تكبير بلا تنعيم لفحص المقروئية
                im = circle_alpha(icon.resize((s, s), Image.LANCZOS)).resize((s * 4, s * 4), Image.NEAREST)
                canvas.paste(im, (x, y + (800 - s * 4) // 2), im)
                d.text((x, y + 806), f"{s}px x4", font=lab, fill=(128, 128, 128))
                x += s * 4 + pad
            y += 880
    p = os.path.join(HERE, "preview", "icons_side_by_side_800_88_48_24.png")
    canvas.save(p, optimize=True)
    # مقارنة مضغوطة جنباً إلى جنب (كما في الاقتراحات)
    strip = Image.new("RGB", (2 * (88 + 48 + 24) + 7 * 30, 140), (255, 255, 255))
    x = 30
    for name, icon in icons.items():
        for s in (88, 48, 24):
            im = circle_alpha(icon.resize((s, s), Image.LANCZOS))
            strip.paste(im, (x, (140 - s) // 2), im)
            x += s + 30
    strip.resize((strip.width * 3, strip.height * 3), Image.NEAREST).save(
        os.path.join(HERE, "preview", "icons_small_sizes_x3.png"))
    return p


def main() -> int:
    lines = [WORDMARK] + [c["tag"] for c in CHANNELS.values()]
    if text_gate.check_lines([(f"L{i}", t) for i, t in enumerate(lines, 1)], require_tashkeel=False):
        print("⛔ بوّابة النصّ أوقفت التصيير")
        return 1
    icons = {}
    report = {}
    for name in CHANNELS:
        od = os.path.join(HERE, name)
        os.makedirs(od, exist_ok=True)
        mark = render_mark(name)
        mark.save(os.path.join(od, f"{name}_mark_transparent_800.png"), optimize=True)
        icon = render_icon(name, mark)
        icons[name] = icon
        icon.save(os.path.join(od, f"{name}_youtube_icon_800x800.png"), optimize=True)
        icon.resize((512, 512), Image.LANCZOS).save(os.path.join(od, f"{name}_bot_avatar_512x512.png"), optimize=True)
        wm = mark.resize((150, 150), Image.LANCZOS).filter(ImageFilter.UnsharpMask(0.8, 50, 1))
        wm.save(os.path.join(od, f"{name}_watermark_150x150.png"), optimize=True)
        render_seal(name, mark).save(os.path.join(od, f"{name}_seal_wordmark_800.png"), optimize=True)
        b = banner(name, mark, od)
        crop_preview(name, b["final"], od)
        report[name] = dict(banner=b["path"], content_bbox=b["layout"]["content_bbox"])
    sizes_preview(icons, HERE)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
