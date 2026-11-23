#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v4 title cards: opening series card, stronger end card with subscribe button."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = Path("/workspace/series_trailer/cards")
OUT.mkdir(parents=True, exist_ok=True)
KUFI = "/workspace/series_trailer/text/NotoKufiArabic-ExtraBold.ttf"
NASKH = "/workspace/series_trailer/text/NotoNaskhArabic-SemiBold.ttf"
GOLD = (247, 199, 74)
GOLD_DIM = (212, 168, 64)
CREAM = (245, 236, 214)
BLACK = (0, 0, 0)
RED = (196, 28, 28)
RED_DK = (140, 16, 16)
WHITE = (255, 255, 255)


def load(path, size):
    return ImageFont.truetype(path, size=size, layout_engine=ImageFont.Layout.RAQM)


def fit_font(draw, text, path, max_size, max_width, language="ar"):
    lo, hi = 22, max_size
    best = load(path, 22)
    while lo <= hi:
        mid = (lo + hi) // 2
        font = load(path, mid)
        bbox = draw.textbbox((0, 0), text, font=font, language=language, direction="rtl")
        w = bbox[2] - bbox[0]
        if w <= max_width:
            best = font
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def wrap_rtl(draw, text, path, size, max_width):
    font = load(path, size)
    bbox = draw.textbbox((0, 0), text, font=font, language="ar", direction="rtl")
    if bbox[2] - bbox[0] <= max_width:
        return [text]
    for sep in ("…", " — ", "،", "|"):
        if sep in text:
            parts = [p.strip() for p in text.split(sep) if p.strip()]
            if sep == "…":
                if len(parts) >= 2:
                    parts[0] = parts[0] + "…"
            if sep == "|":
                parts = [p.strip() for p in text.split("|")]
            lines = []
            ok = True
            for p in parts:
                bbox = draw.textbbox((0, 0), p, font=font, language="ar", direction="rtl")
                if bbox[2] - bbox[0] > max_width:
                    ok = False
                    break
                lines.append(p)
            if ok and 1 <= len(lines) <= 3:
                return lines
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        bbox = draw.textbbox((0, 0), trial, font=font, language="ar", direction="rtl")
        if bbox[2] - bbox[0] <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]


def draw_centered(draw, lines, font, fill, cx, cy, gap=18, stroke=2, stroke_fill=(20, 12, 0)):
    heights, widths = [], []
    for ln in lines:
        b = draw.textbbox((0, 0), ln, font=font, language="ar", direction="rtl")
        widths.append(b[2] - b[0])
        heights.append(b[3] - b[1])
    total_h = sum(heights) + gap * (len(lines) - 1)
    y = cy - total_h / 2
    for ln, h in zip(lines, heights):
        draw.text((cx, y + h / 2), ln, font=font, fill=fill, anchor="mm",
                  language="ar", direction="rtl", align="center",
                  stroke_width=stroke, stroke_fill=stroke_fill)
        y += h + gap
    return total_h


def ornaments(draw, w, h, cy, half_block):
    y1 = cy - half_block - 36
    y2 = cy + half_block + 36
    for y in (y1, y2):
        draw.rectangle((w * 0.32, y, w * 0.68, y + 2), fill=GOLD)
        for x in (w * 0.32, w * 0.68):
            r = 4
            draw.polygon([(x, y + 1 - r), (x + r, y + 1), (x, y + 1 + r), (x - r, y + 1)], fill=GOLD)


def vignette_bg(w, h, fill=32):
    img = Image.new("RGB", (w, h), BLACK)
    vig = Image.new("L", (w, h), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse((-w * 0.1, -h * 0.2, w * 1.1, h * 1.2), fill=fill)
    vig = vig.filter(ImageFilter.GaussianBlur(90))
    base = Image.new("RGB", (w, h), (8, 6, 2))
    return Image.composite(base, img, vig)


def draw_bell(draw, cx, cy, s, fill):
    """Simple notification bell, no brand marks."""
    # top nub
    draw.ellipse((cx - 0.12 * s, cy - 0.72 * s, cx + 0.12 * s, cy - 0.48 * s), fill=fill)
    # dome
    draw.pieslice((cx - 0.42 * s, cy - 0.58 * s, cx + 0.42 * s, cy + 0.28 * s),
                  180, 0, fill=fill)
    # body / flare
    draw.polygon([
        (cx - 0.42 * s, cy - 0.05 * s),
        (cx + 0.42 * s, cy - 0.05 * s),
        (cx + 0.58 * s, cy + 0.38 * s),
        (cx - 0.58 * s, cy + 0.38 * s),
    ], fill=fill)
    # lip
    draw.rectangle((cx - 0.58 * s, cy + 0.30 * s, cx + 0.58 * s, cy + 0.40 * s), fill=fill)
    # clapper
    draw.ellipse((cx - 0.13 * s, cy + 0.34 * s, cx + 0.13 * s, cy + 0.60 * s), fill=fill)


def draw_subscribe_button(img, cx, cy, label, scale=1.0):
    """Generic red rounded subscribe button with bell + Arabic label."""
    draw = ImageDraw.Draw(img)
    font = load(KUFI, int((42 if img.size[0] >= 1920 else 40) * scale))
    b = draw.textbbox((0, 0), label, font=font, language="ar", direction="rtl")
    tw, th = b[2] - b[0], b[3] - b[1]
    bell_s = int(28 * scale)
    pad_x, pad_y = int(36 * scale), int(18 * scale)
    gap = int(16 * scale)
    bw = tw + pad_x * 2 + bell_s + gap
    bh = max(th, int(bell_s * 1.4)) + pad_y * 2
    x0, y0 = int(cx - bw / 2), int(cy - bh / 2)
    x1, y1 = int(cx + bw / 2), int(cy + bh / 2)
    # shadow
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((x0 + 4, y0 + 6, x1 + 4, y1 + 6), radius=int(18 * scale),
                         fill=(0, 0, 0, 140))
    shadow = shadow.filter(ImageFilter.GaussianBlur(4))
    if img.mode != "RGBA":
        base = img.convert("RGBA")
        base = Image.alpha_composite(base, shadow)
        img.paste(base.convert("RGB"))
        draw = ImageDraw.Draw(img)
    else:
        img.alpha_composite(shadow)
        draw = ImageDraw.Draw(img)
    # body
    draw.rounded_rectangle((x0, y0, x1, y1), radius=int(18 * scale), fill=RED)
    # slight top highlight
    draw.rounded_rectangle((x0 + 2, y0 + 2, x1 - 2, y0 + max(8, int(bh * 0.22))),
                           radius=int(12 * scale), fill=(220, 50, 50))
    # RTL: text on the right, bell on the left inside the button
    text_cx = x1 - pad_x - tw / 2
    bell_cx = x0 + pad_x + bell_s / 2
    draw_bell(draw, bell_cx, cy + int(1 * scale), bell_s, WHITE)
    draw.text((text_cx, cy), label, font=font, fill=WHITE, anchor="mm",
              language="ar", direction="rtl",
              stroke_width=1, stroke_fill=RED_DK)
    return img


def make_open(size, outname):
    w, h = size
    img = vignette_bg(w, h, 36)
    draw = ImageDraw.Draw(img)
    title = "سِلْسِلَةُ سَيْفِ اللَّهِ"
    sub = "إِعْلَانُ السِّلْسِلَةِ"
    max_w = int(w * 0.88)
    f1 = fit_font(draw, title, KUFI, 128 if w >= 1920 else 100, max_w)
    f2 = fit_font(draw, sub, NASKH, 58 if w >= 1920 else 50, max_w)
    cy = h * 0.46
    draw_centered(draw, [title], f1, GOLD, w // 2, cy - (70 if w >= 1920 else 110),
                  gap=0, stroke=3)
    # gold rule
    yrule = cy + 8
    draw.rectangle((w * 0.34, yrule, w * 0.66, yrule + 2), fill=GOLD)
    for x in (w * 0.34, w * 0.66):
        r = 5
        draw.polygon([(x, yrule + 1 - r), (x + r, yrule + 1), (x, yrule + 1 + r), (x - r, yrule + 1)], fill=GOLD)
    draw_centered(draw, [sub], f2, CREAM, w // 2, cy + (80 if w >= 1920 else 120),
                  gap=0, stroke=2)
    path = OUT / outname
    img.save(path, quality=95)
    print("wrote", path)
    return path


def make_end_base(size, outname):
    """Title + series line only (CTA fades in later)."""
    w, h = size
    img = vignette_bg(w, h, 34)
    draw = ImageDraw.Draw(img)
    title = "سَيْفُ اللَّهِ  |  خَالِدُ بْنُ الْوَلِيدِ"
    # split for two-line title on both canvases for balance
    t1, t2 = "سَيْفُ اللَّهِ", "خَالِدُ بْنُ الْوَلِيدِ"
    sub = "سِلْسِلَةٌ كَامِلَةٌ عَلَى قَنَاةِ الْمُتَفَائِلِ"
    max_w = int(w * 0.88)
    f1 = fit_font(draw, t1, KUFI, 132 if w >= 1920 else 108, max_w)
    f1b = fit_font(draw, t2, KUFI, 86 if w >= 1920 else 74, max_w)
    f2 = fit_font(draw, sub, NASKH, 50 if w >= 1920 else 44, max_w)
    if w >= 1920:
        y1, y2, y3 = h * 0.28, h * 0.42, h * 0.56
    else:
        y1, y2, y3 = h * 0.24, h * 0.34, h * 0.46
    draw_centered(draw, [t1], f1, GOLD, w // 2, y1, gap=0, stroke=3)
    # rule
    yrule = (y1 + y2) / 2 + (8 if w >= 1920 else 0)
    draw.rectangle((w * 0.33, yrule, w * 0.67, yrule + 2), fill=GOLD)
    draw_centered(draw, [t2], f1b, GOLD, w // 2, y2, gap=0, stroke=2)
    draw_centered(draw, wrap_rtl(draw, sub, NASKH, f2.size, max_w), f2, CREAM,
                  w // 2, y3, gap=14, stroke=2)
    path = OUT / outname
    img.save(path, quality=95)
    print("wrote", path)
    return path


def make_end_cta(size, outname):
    """Transparent overlay: subscribe button, CTA, recommended start."""
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cta = "اشْتَرِكْ فِي الْقَنَاةِ وَفَعِّلِ الْجَرَسَ"
    start = "ابْدَأْ مِنْ هُنَا: أَيْنَ خَالِدُ بْنُ الْوَلِيدِ"
    max_w = int(w * 0.90)
    f3 = fit_font(draw, cta, KUFI, 44 if w >= 1920 else 40, max_w)
    f4 = fit_font(draw, start, NASKH, 40 if w >= 1920 else 36, max_w)
    if w >= 1920:
        y_btn, y_cta, y_start = h * 0.70, h * 0.82, h * 0.90
        scale = 1.0
    else:
        y_btn, y_cta, y_start = h * 0.62, h * 0.74, h * 0.84
        scale = 1.15
    draw_subscribe_button(img, w // 2, y_btn, "اشْتَرِكْ", scale=scale)
    draw = ImageDraw.Draw(img)
    draw_centered(draw, [cta], f3, GOLD, w // 2, y_cta, gap=0, stroke=2)
    draw_centered(draw, wrap_rtl(draw, start, NASKH, f4.size, max_w), f4, CREAM,
                  w // 2, y_start, gap=10, stroke=2)
    path = OUT / outname
    img.save(path)
    print("wrote", path)
    return path


def make_end_static(size, outname):
    """Composite base+cta for a single preview / fallback still."""
    w, h = size
    suffix = "16x9" if w >= 1920 else "9x16"
    base = Image.open(OUT / f"end_base_{suffix}.png").convert("RGBA")
    cta = Image.open(OUT / f"end_cta_{suffix}.png").convert("RGBA")
    img = Image.alpha_composite(base, cta).convert("RGB")
    path = OUT / outname
    img.save(path, quality=95)
    print("wrote", path)
    return path


def main():
    for size, tag in (((1920, 1080), "16x9"), ((1080, 1920), "9x16")):
        make_open(size, f"open_{tag}.png")
        make_end_base(size, f"end_base_{tag}.png")
        make_end_cta(size, f"end_cta_{tag}.png")
        make_end_static(size, f"end_v4_{tag}.png")


if __name__ == "__main__":
    main()
