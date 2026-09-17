# -*- coding: utf-8 -*-
"""المصغّرة 1280×720 — سطر أبيض + سطر ذهبي + شريط أحمر + شعار دائري.
الاستعمال: python mkthumb.py <bg.jpg> <out.jpg> "السطر الأبيض" "السطر الذهبي" ["الشريط الأحمر"]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envpaths
from PIL import Image, ImageDraw, ImageFont, ImageFilter
# ⛔ التهيئةُ والقلبُ وإلزامُ محرّك BASIC — كلُّها في envpaths، ولا تُكرَّر هنا
# (القلبُ المزدوج مع RAQM على لينكس كان يعكس العناوين — انظر envpaths.py).
from envpaths import ar

BG, OUT = sys.argv[1], sys.argv[2]
L1 = sys.argv[3]; L2 = sys.argv[4]
BADGE = sys.argv[5] if len(sys.argv) > 5 else ""
FB = envpaths.font(bold=True)
LOGO = envpaths.logo()
W, H = 1280, 720

im = Image.open(BG).convert("RGB")
r = max(W / im.width, H / im.height)
im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
x = (im.width - W) // 2; y = (im.height - H) // 2
im = im.crop((x, y, x + W, y + H))

# تعتيم متدرّج من اليمين (اتجاه القراءة)
ov = Image.new("L", (W, H), 0)
dv = ImageDraw.Draw(ov)
for i in range(W):
    t = i / W
    dv.line([(i, 0), (i, H)], fill=int(238 * max(0.0, min(1.0, (t - 0.02) / 0.72))))
im = Image.composite(Image.new("RGB", (W, H), (6, 8, 14)), im, ov)

d = ImageDraw.Draw(im)
def fit(text, size, maxw):
    while size > 26:
        f = envpaths.arfont(size, path=FB)
        if d.textlength(ar(text), font=f) <= maxw: return f
        size -= 2
    return envpaths.arfont(26, path=FB)

MX = W - 58; MAXW = W - 130
f1 = fit(L1, 82, MAXW); f2 = fit(L2, 96, MAXW)
def draw_r(txt, f, ytop, fill):
    t = ar(txt); w = d.textlength(t, font=f)
    for dx, dy in ((-3,0),(3,0),(0,-3),(0,3),(-2,-2),(2,2),(-2,2),(2,-2)):
        d.text((MX - w + dx, ytop + dy), t, font=f, fill=(0, 0, 0))
    d.text((MX - w, ytop), t, font=f, fill=fill)

draw_r(L1, f1, 158, (255, 255, 255))
draw_r(L2, f2, 158 + f1.size + 34, (247, 199, 74))

if BADGE:
    fb = envpaths.arfont(44, path=FB); t = ar(BADGE)
    tw = d.textlength(t, font=fb)
    bx1, by1 = MX + 16, 158 + f1.size + 34 + f2.size + 56
    d.rounded_rectangle([bx1 - tw - 44, by1, bx1, by1 + 76], 10, fill=(196, 30, 30))
    d.text((bx1 - tw - 22, by1 + 10), t, font=fb, fill=(255, 255, 255))

# ⛔ الشعارُ لازمٌ: غيابُه أسقط الشوطَ في envpaths.logo()
lg = Image.open(LOGO).convert("RGB").resize((132, 132), Image.LANCZOS)
m = Image.new("L", (528, 528), 0)
ImageDraw.Draw(m).ellipse([6, 6, 522, 522], fill=255)
m = m.filter(ImageFilter.GaussianBlur(4)).resize((132, 132), Image.LANCZOS)
im.paste(lg, (46, H - 178), m)

im.save(OUT, quality=93)
print("saved", OUT)
