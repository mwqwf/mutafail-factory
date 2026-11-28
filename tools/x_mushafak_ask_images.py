import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
S = sys.argv[1]; F = '/home/claude/quranrafiq/app/src/main/res/font/'
NAVY1, NAVY2 = (8, 20, 38), (16, 42, 70)
GOLD, GOLD2, WHITE, SOFT = (222, 184, 92), (245, 214, 140), (250, 248, 240), (190, 200, 215)
def font(n, s): return ImageFont.truetype(F + n, s)
AM, PB, PS, PM = 'amiri_bold.ttf', 'ibm_plex_sans_arabic_bold.ttf', 'ibm_plex_sans_arabic_semibold.ttf', 'ibm_plex_sans_arabic_medium.ttf'
W, H = 1080, 1350

def bg():
    im = Image.new('RGB', (W, H), NAVY1)
    g = Image.new('L', (W, H), 0); d = ImageDraw.Draw(g)
    d.ellipse((-300, 250, W + 300, H + 300), fill=255)
    g = g.filter(ImageFilter.GaussianBlur(220))
    im = Image.composite(Image.new('RGB', (W, H), NAVY2), im, g)
    # نقشٌ هندسيّ خفيف
    p = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(p)
    for x in range(-60, W + 60, 120):
        for y in range(-60, H + 60, 120):
            d.regular_polygon((x, y, 46), 8, rotation=22.5, outline=(222, 184, 92, 14), width=2)
    im.paste(p, (0, 0), p)
    return im

def shot(name, top=0.045, bottom=1.0):
    im = Image.open('%s/shots/%s.png' % (S, name)).convert('RGB'); w, h = im.size
    return im.crop((0, int(h * top), w, int(h * bottom)))

def phone(canvas, img, cx, cy, w, angle=0):
    sw, sh = img.size; h = int(w * sh / sw)
    b = max(10, w // 26); r = int(w * 0.12)
    PW, PH = w + 2 * b, h + 2 * b
    ph = Image.new('RGBA', (PW, PH), (0, 0, 0, 0)); d = ImageDraw.Draw(ph)
    d.rounded_rectangle((0, 0, PW - 1, PH - 1), radius=r, fill=(18, 18, 22), outline=GOLD, width=3)
    scr = img.resize((w, h), Image.LANCZOS)
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=r - b, fill=255)
    ph.paste(scr, (b, b), m)
    if angle: ph = ph.rotate(angle, resample=Image.BICUBIC, expand=True)
    sh_ = Image.new('RGBA', (ph.width + 120, ph.height + 120), (0, 0, 0, 0))
    a = ph.split()[3].point(lambda v: 150 if v else 0)
    sh_.paste((0, 0, 0, 255), (60, 80), a); sh_ = sh_.filter(ImageFilter.GaussianBlur(28))
    canvas.paste(sh_, (cx - sh_.width // 2, cy - sh_.height // 2 + 10), sh_)
    canvas.paste(ph, (cx - ph.width // 2, cy - ph.height // 2), ph)

def text(d, xy, s, f, fill, anchor='mm'):
    d.text(xy, s, font=f, fill=fill, anchor=anchor, direction='rtl', language='ar')

def rr(im, box, radius, fill, outline=None, width=0):
    L = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(L).rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    im.alpha_composite(L)

CANVAS = [None]
def chip(d, cx, cy, s, f, fill=(222, 184, 92, 40), fg=GOLD2):
    w = d.textlength(s, font=f, direction='rtl', language='ar') + 48
    rr(CANVAS[0], (cx - w / 2, cy - 31, cx + w / 2, cy + 31), 31, fill, GOLD, 2)
    text(ImageDraw.Draw(CANVAS[0]), (cx, cy - 2), s, f, fg)
    return w

def chips(d, y, items, f, gap=16):
    ws = [d.textlength(s, font=f, direction='rtl', language='ar') + 44 for s in items]
    x = (W - sum(ws) - gap * (len(ws) - 1)) / 2
    for s, w in zip(reversed(items), reversed(ws)):  # من اليمين
        pass
    xr = W - x
    for s, w in zip(items, ws):
        chip(d, xr - w / 2, y, s, f); xr -= w + gap

def logo(canvas, cx, cy, size):
    lg = Image.open(S + '/logo.png').convert('RGBA').resize((size, size), Image.LANCZOS)
    canvas.paste(lg, (cx - size // 2, cy - size // 2), lg)


# ── الصورة ١: المساعد يجيب من المصادر ──
im = bg().convert('RGBA'); d = ImageDraw.Draw(im); CANVAS[0] = im
logo(im, W // 2, 100, 110)
text(d, (W // 2, 215), 'المساعد الذكي', font(AM, 100), GOLD2)
text(d, (W // 2, 305), 'يجيبك من المصادر… ولا يخمّن', font(PS, 46), WHITE)
phone(im, shot('dict_2_recording'), 245, 850, 290, angle=7)
phone(im, shot('dict_4_result'), 835, 850, 290, angle=-7)
phone(im, shot('ask'), 540, 820, 370)
d = ImageDraw.Draw(im)
chips(d, 1260, ['بالإحالة إلى المصدر', 'لا يكتب نصّ القرآن', 'بصوتك أو بصورة'], font(PM, 32))
im.convert('RGB').save(S + '/ask_x1.png')

# ── الصورة ٢: البحث المعمّق واشرح أخطائي ──
im = bg().convert('RGBA'); d = ImageDraw.Draw(im); CANVAS[0] = im
text(d, (W // 2, 120), 'بحثٌ معمّق… وشرحٌ لأخطائك', font(AM, 84), GOLD2)
text(d, (W // 2, 215), 'يقارن المصادر وينقدها، ولا يتساهل في الأصول', font(PS, 40), WHITE)
phone(im, shot('errors'), 300, 800, 380, angle=4)
d = ImageDraw.Draw(im)
for i, s_ in enumerate(['مصادر التطبيق', 'المكتبة الشاملة', 'الإنترنت']):
    chip(d, 790, 420 + i * 90, s_, font(PM, 34))
text(d, (790, 705), 'اشرح أخطائي', font(PB, 50), GOLD2)
text(d, (790, 765), 'بعد التسميع يبيّن لك أخطاءك', font(PM, 32), SOFT)
text(d, (790, 880), 'ويناسبك', font(PB, 50), GOLD2)
for i, s_ in enumerate(['طول الجواب', 'مذهبك المفضّل', 'أسلوب اللغة']):
    chip(d, 790, 965 + i * 88, s_, font(PM, 34))
text(d, (W // 2, 1290), 'ليس مفتياً: أسئلة الفتوى يحيلها إلى أهل العلم', font(PM, 32), SOFT)
im.convert('RGB').save(S + '/ask_x2.png')
