# تركيب صور مصحفك الدعائية لاكس من لقطات المتجر الحقيقية (لا توليد): python3 tools/x_mushafak_images.py <مجلد فيه shots/ وlogo.png>
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

# ── الصورة ١: الواجهة ──
im = bg().convert('RGBA'); d = ImageDraw.Draw(im)
logo(im, W // 2, 105, 120)
text(d, (W // 2, 225), 'مصحفك', font(AM, 108), GOLD2)
text(d, (W // 2, 318), 'مصحفٌ يعرف صاحبه', font(PS, 46), WHITE)
text(d, (W // 2, 378), 'اقرأ بروايتك · احفظ بخطة · سمّع فيكشف خطأك', font(PM, 31), SOFT)
phone(im, shot('01-riwayat'), 245, 840, 300, angle=7)
phone(im, shot('02-tasmi'), 835, 840, 300, angle=-7)
phone(im, shot('03-mushaf'), 540, 815, 380)
CANVAS[0] = im; d = ImageDraw.Draw(im)
chips(d, 1215, ['٦ روايات', 'تسميع بلا إنترنت', 'مئات القرّاء', 'مجاناً'], font(PS, 30))
text(d, (W // 2, 1295), 'حمّله الآن من Google Play', font(PB, 34), GOLD2)
im.convert('RGB').save(S + '/x1.png')

# ── الصورة ٢: المزايا ──
im = bg().convert('RGBA'); d = ImageDraw.Draw(im)
text(d, (W // 2, 80), 'كلّ ما تحتاجه مع القرآن', font(AM, 62), GOLD2)
text(d, (W // 2, 150), 'في تطبيقٍ واحد', font(PS, 38), WHITE)
cards = [('02-tasmi', 'سمّع من حفظك', 'يتابعك كلمةً كلمة ويريك خطأك'),
         ('05-hifz', 'احفظ بخطةٍ يومية', 'تعيد عليك الآية قبل أن تُنسى'),
         ('01-riwayat', 'قارن الروايات', 'حفص وورش وقالون وغيرها'),
         ('08-adhkar', 'الأذكار بمصادرها', 'والمواقيت والقبلة والتجويد')]
CW, CH, G = 486, 500, 28; X0 = (W - 2 * CW - G) // 2; Y0 = 205
for i, (n, t1, t2) in enumerate(cards):
    col, row = 1 - i % 2, i // 2   # الأولى يميناً
    x, y = X0 + col * (CW + G), Y0 + row * (CH + G)
    rr(im, (x, y, x + CW, y + CH), 34, (255, 255, 255, 16), (222, 184, 92, 140), 2)
    pw = 300; ph_ = 330
    sc = shot(n, top=0.045)
    sc = sc.crop((0, 0, sc.width, int(sc.width * ph_ / pw)))
    scr = sc.resize((pw, ph_), Image.LANCZOS)
    fade = Image.new('L', (pw, ph_), 255); fd = ImageDraw.Draw(fade)
    for k in range(120): fd.line((0, ph_ - 120 + k, pw, ph_ - 120 + k), fill=int(255 * (1 - k / 120) ** 1.5))
    m = Image.new('L', scr.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, pw - 1, ph_ + 40), radius=24, fill=255)
    from PIL import ImageChops
    m = ImageChops.multiply(m, fade)
    im.paste(scr, (x + (CW - pw) // 2, y + 26), m)
    d = ImageDraw.Draw(im)
    text(d, (x + CW // 2, y + CH - 100), t1, font(PB, 40), GOLD2)
    text(d, (x + CW // 2, y + CH - 46), t2, font(PM, 27), SOFT)
CANVAS[0] = im; d = ImageDraw.Draw(im)
chips(d, 1290, ['بلا إنترنت', 'بلا حساب', 'المصحف بلا إعلان'], font(PS, 30))
im.convert('RGB').save(S + '/x2.png')
