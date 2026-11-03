# مقطع مصحفك المتحرّك (الإصدار الثاني) لاكس: موشن جرافيك من لقطات التطبيق الحقيقية ونصوصٍ حركية، بلا توليد صور ولا موسيقى.
# python3 motion2.py <مجلد: shots/ وlogo.png> <durations.json> <voice.mp3> <out.mp4>
import json, math, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
S, DUR, AUD, OUT = sys.argv[1:5]
F = '/home/claude/quranrafiq/app/src/main/res/font/'
W, H, FPS = 1080, 1350, 30
NAVY1, NAVY2 = (6, 16, 32), (18, 46, 78)
GOLD, GOLD2, WHITE, SOFT, GREEN, RED = (222, 184, 92), (247, 218, 146), (252, 250, 244), (196, 206, 222), (72, 190, 120), (226, 92, 84)
_fc = {}
def font(n, s):
    if (n, s) not in _fc: _fc[(n, s)] = ImageFont.truetype(F + n, s)
    return _fc[(n, s)]
AM, PB, PS, PM = 'amiri_bold.ttf', 'ibm_plex_sans_arabic_bold.ttf', 'ibm_plex_sans_arabic_semibold.ttf', 'ibm_plex_sans_arabic_medium.ttf'
def cl(t): return max(0.0, min(1.0, t))
def ease(t): t = cl(t); return 1 - (1 - t) ** 3
def inout(t): t = cl(t); return t * t * (3 - 2 * t)
def spring(t):
    if t <= 0: return 0.0
    return 1 - math.exp(-7 * t) * math.cos(10 * t)

# ── الخلفية: تدرّجٌ ونقشٌ وأشعّةٌ وغبارٌ ذهبيّ ──
def make_bg():
    im = Image.new('RGB', (W, H), NAVY1)
    g = Image.new('L', (W, H), 0); ImageDraw.Draw(g).ellipse((-250, 250, W + 250, H + 350), fill=255)
    im = Image.composite(Image.new('RGB', (W, H), NAVY2), im, g.filter(ImageFilter.GaussianBlur(240)))
    p = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(p)
    for x in range(-60, W + 60, 120):
        for y in range(-60, H + 60, 120):
            d.regular_polygon((x, y, 46), 8, rotation=22.5, outline=(222, 184, 92, 13), width=2)
    im.paste(p, (0, 0), p); return im.convert('RGBA')
BG = make_bg()
RAYS = Image.new('RGBA', (W * 2, H * 2), (0, 0, 0, 0))
d = ImageDraw.Draw(RAYS)
for k in range(14):
    a = k * math.pi * 2 / 14
    d.polygon([(W, H), (W + 2400 * math.cos(a - 0.06), H + 2400 * math.sin(a - 0.06)), (W + 2400 * math.cos(a + 0.06), H + 2400 * math.sin(a + 0.06))], fill=(247, 218, 146, 10))
RAYS = RAYS.filter(ImageFilter.GaussianBlur(18))
random.seed(7)
DUST = [(random.uniform(0, W), random.uniform(0, H), random.uniform(1.5, 4.5), random.uniform(8, 30), random.uniform(0, 6.28)) for _ in range(70)]

def background(tm, rays=0.0):
    c = BG.copy()
    if rays > 0.01:
        r = RAYS.rotate(tm * 6, resample=Image.BILINEAR)
        r = r.crop((W // 2, H // 2 - 100, W // 2 + W, H // 2 - 100 + H))
        if rays < 1: r.putalpha(r.split()[3].point(lambda v: int(v * rays)))
        c.alpha_composite(r)
    L = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(L)
    for x, y, s, sp, ph in DUST:
        yy = (y - tm * sp) % H; xx = x + 14 * math.sin(tm * 0.7 + ph)
        a = int(90 + 80 * math.sin(tm * 2 + ph))
        dd.ellipse((xx - s, yy - s, xx + s, yy + s), fill=(247, 218, 146, max(0, a)))
    c.alpha_composite(L.filter(ImageFilter.GaussianBlur(1.2)))
    return c

# ── عناصر ──
def text_img(s, f, fill, shadow=True):
    d0 = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    bb = d0.textbbox((0, 0), s, font=f, direction='rtl', language='ar')
    w, h = bb[2] - bb[0] + 60, bb[3] - bb[1] + 60
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    if shadow:
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((30 - bb[0], 36 - bb[1]), s, font=f, fill=(0, 0, 0, 170), direction='rtl', language='ar')
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    ImageDraw.Draw(im).text((30 - bb[0], 30 - bb[1]), s, font=f, fill=fill, direction='rtl', language='ar')
    return im
_tc = {}
def T(s, f, fill, shadow=True):
    k = (s, id(f), fill, shadow)
    if k not in _tc: _tc[k] = text_img(s, f, fill, shadow)
    return _tc[k]

def put(c, img, cx, cy, scale=1.0, alpha=1.0, angle=0.0):
    if alpha <= 0.01 or scale <= 0.01: return
    if abs(scale - 1) > 0.002: img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BILINEAR)
    if abs(angle) > 0.05: img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
    if alpha < 0.999: img = img.copy(); img.putalpha(img.split()[3].point(lambda v: int(v * alpha)))
    c.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))

def kinetic(c, words, f, fill, cy, a, span, out=0.0, gap=18, maxw=980):
    """كلماتٌ تقفز تباعاً من اليمين إلى اليسار على أسطر، وتختفي معاً."""
    ims = [T(w, f, fill) for w in words]
    lines, cur, cw = [], [], 0
    for im in ims:
        if cur and cw + im.width - 60 + gap > maxw: lines.append(cur); cur, cw = [], 0
        cur.append(im); cw += im.width - 60 + gap
    if cur: lines.append(cur)
    lh = ims[0].height - 40
    y0 = cy - (len(lines) - 1) * lh / 2; i = 0
    n = len(ims)
    for li, ln in enumerate(lines):
        tw = sum(im.width - 60 for im in ln) + gap * (len(ln) - 1)
        x = W / 2 + tw / 2
        for im in ln:
            ww = im.width - 60
            ta = a - span * i / max(1, n)
            s = 0.4 + 0.6 * spring(ta / 0.55)
            put(c, im, x - ww / 2, y0 + li * lh + 30 * (1 - ease(ta / 0.3)), scale=s, alpha=ease(ta / 0.18) * (1 - out))
            x -= ww + gap; i += 1

def chip(s, f, fg=GOLD2, fill=(222, 184, 92, 46), outline=GOLD):
    t = T(s, f, fg, shadow=False); w, h = t.width - 20, t.height - 22
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=fill, outline=outline, width=3)
    tmp = Image.new('RGBA', (w, h), (0, 0, 0, 0)); tmp.paste(t, ((w - t.width) // 2, -13), t)
    im.alpha_composite(tmp); return im
_cc = {}
def CH(s, size=40, **k):
    key = (s, size, tuple(sorted(k.items())))
    if key not in _cc: _cc[key] = chip(s, font(PS, size), **k)
    return _cc[key]

def shot(name, top=0.045, bottom=1.0):
    im = Image.open('%s/shots/%s.png' % (S, name)).convert('RGB'); w, h = im.size
    return im.crop((0, int(h * top), w, int(h * bottom)))
_ph = {}
def phone(name, w, top=0.045):
    k = (name, w)
    if k in _ph: return _ph[k]
    img = shot(name, top); sw, sh = img.size; h = int(w * sh / sw)
    if h > w * 2.05: h = int(w * 2.05); img = img.crop((0, 0, sw, int(sw * 2.05)))
    b = max(10, w // 24); r = int(w * 0.13); PW, PHh = w + 2 * b, h + 2 * b
    ph = Image.new('RGBA', (PW + 120, PHh + 120), (0, 0, 0, 0))
    a = Image.new('L', ph.size, 0); ImageDraw.Draw(a).rounded_rectangle((60, 85, 60 + PW, 85 + PHh), radius=r, fill=160)
    ph = Image.merge('RGBA', (Image.new('L', ph.size, 0),) * 3 + (a.filter(ImageFilter.GaussianBlur(30)),))
    fr = Image.new('RGBA', (PW, PHh), (0, 0, 0, 0)); d = ImageDraw.Draw(fr)
    d.rounded_rectangle((0, 0, PW - 1, PHh - 1), radius=r, fill=(14, 14, 18), outline=GOLD, width=4)
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=r - b, fill=255)
    fr.paste(img.resize((w, h), Image.LANCZOS), (b, b), m)
    ph.alpha_composite(fr, (60, 60)); _ph[k] = ph; return ph

def coeffs(src, dst):
    A = []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    return np.linalg.solve(np.array(A, float), np.array([p for s in src for p in s], float)).tolist()
def tilt(img, k):
    """إمالةٌ منظوريّة حول المحور العمودي: k=0 مسطّح، k>0 يبتعد الطرف الأيسر."""
    if abs(k) < 0.01: return img
    w, h = img.size; dy = h * 0.09 * abs(k); dx = w * 0.10 * abs(k)
    if k > 0: dst = [(dx, dy), (w, 0), (w, h), (dx, h - dy)]
    else: dst = [(0, 0), (w - dx, dy), (w - dx, h - dy), (0, h)]
    return img.transform((w, h), Image.PERSPECTIVE, coeffs([(0, 0), (w, 0), (w, h), (0, h)], dst), Image.BICUBIC)

def flash(c, p):
    """شريطٌ ذهبيّ مائلٌ يمسح الشاشة عند الانتقال (p من 0 إلى 1)."""
    if not 0 < p < 1: return
    L = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    x = -500 + (W + 1000) * inout(p)
    d.polygon([(x - 160, 0), (x + 40, 0), (x - 260, H), (x - 460, H)], fill=(247, 218, 146, int(150 * math.sin(math.pi * p))))
    c.alpha_composite(L.filter(ImageFilter.GaussianBlur(30)))

def glow(c, cx, cy, r, a):
    if a <= 0: return
    L = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(L).ellipse((cx - r, cy - r, cx + r, cy + r), fill=(247, 218, 146, int(110 * a)))
    c.alpha_composite(L.filter(ImageFilter.GaussianBlur(r * 0.45)))

LOGO = Image.open(S + '/logo.png').convert('RGBA')
def icon(s):
    im = LOGO.resize((s, s), Image.LANCZOS); m = Image.new('L', (s, s), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * 0.23), fill=255); im.putalpha(m)
    fr = Image.new('RGBA', (s + 8, s + 8), (0, 0, 0, 0)); ImageDraw.Draw(fr).rounded_rectangle((0, 0, s + 7, s + 7), radius=int(s * 0.24), fill=GOLD)
    fr.alpha_composite(im, (4, 4)); return fr
LG = {s: icon(s) for s in (170, 260)}

# ── التوقيت ──
dur = json.load(open(DUR))
K = ['m%02d' % i for i in range(1, 12)]
LEAD = 0.4
# الفاصل الفعليّ بين الجمل في ملفّ الصوت (لا رقمٌ مفترض، وإلا انزاحت المشاهد عن التعليق)
_al = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', AUD]))
GAP = (_al - sum(dur[k] for k in K)) / (len(K) - 1)
st, t = {}, LEAD
for k in K: st[k] = t; t += dur[k] + GAP
TOTAL = t + 1.4
def nxt(k):
    i = K.index(k); return st[K[i + 1]] if i + 1 < len(K) else TOTAL + 9

def title(c, a, d_, main, sub=None, out=0.0, y=135):
    kinetic(c, main.split(), font(PB, 70), GOLD2, y, a, min(0.9, d_ * 0.4), out)
    if sub: put(c, T(sub, font(PM, 40), SOFT), W / 2, y + 92, alpha=ease((a - 0.5) / 0.4) * (1 - out))

def frame(tm):
    k = K[0]
    for kk in K:
        if tm >= st[kk] - GAP / 2: k = kk
    a = tm - st[k]; d_ = dur[k]; out = ease((tm - (nxt(k) - 0.3)) / 0.3)
    rays = {'m02': 1.0, 'm04': 1.0, 'm10': 1.0, 'm11': 1.0}.get(k, 0.35)
    c = background(tm, rays)
    if k == 'm01':
        kinetic(c, 'تحفظ السورة…'.split(), font(AM, 120), WHITE, 520, a, 0.5, out)
        kinetic(c, 'وبعد أسبوع'.split(), font(AM, 96), SOFT, 700, a - d_ * 0.38, 0.4, out)
        b = a - d_ * 0.62; fade = ease((a - d_ * 0.95) / 0.5)
        im = T('تنساها؟', font(AM, 150), GOLD2)
        jit = 6 * math.sin(a * 40) * ease(b / 0.2) * (1 - ease((b - 0.35) / 0.2))
        put(c, im.filter(ImageFilter.GaussianBlur(10 * fade)) if fade > 0.02 else im, W / 2 + jit, 880, scale=0.5 + 0.5 * spring(b / 0.5), alpha=ease(b / 0.15) * (1 - 0.6 * fade) * (1 - out))
    elif k == 'm02':
        glow(c, W / 2, 420, 260, ease(a / 0.5) * (1 - out))
        put(c, LG[260], W / 2, 420, scale=0.3 + 0.7 * spring(a / 0.8), alpha=ease(a / 0.2) * (1 - out), angle=-12 * (1 - ease(a / 0.7)))
        put(c, T('مصحفك', font(AM, 170), GOLD2), W / 2, 680, scale=0.8 + 0.2 * spring((a - 0.3) / 0.6), alpha=ease((a - 0.3) / 0.3) * (1 - out))
        kinetic(c, 'كلّ ما تحتاجه مع القرآن'.split(), font(PS, 54), WHITE, 860, a - d_ * 0.3, 0.6, out)
        kinetic(c, 'في تطبيقٍ واحد'.split(), font(PB, 62), GOLD2, 950, a - d_ * 0.62, 0.35, out)
    elif k == 'm03':
        title(c, a, d_, 'سمّع من حفظك', 'بروايتك… ويكشف خطأك كلمةً كلمة', out)
        ph = tilt(phone('02-tasmi', 470), -0.9 * (1 - ease(a / 0.9)))
        put(c, ph, W / 2 + 200 - 600 * (1 - ease(a / 0.7)) - 600 * out, 810)
        rw = ['حفص', 'ورش', 'قالون', 'شعبة', 'الدوري', 'السوسي']
        for i, s in enumerate(rw):
            ta = a - (d_ * 0.12 + i * d_ * 0.07)
            put(c, CH(s, 40), 190, 470 + i * 112, scale=spring(ta / 0.45), alpha=ease(ta / 0.12) * (1 - out))
    elif k == 'm04':
        glow(c, W / 2, 640, 330, ease(a / 0.4) * (1 - out))
        put(c, T('على جهازك', font(PS, 64), WHITE), W / 2, 420, alpha=ease(a / 0.3) * (1 - out))
        b = a - d_ * 0.35
        put(c, T('بلا إنترنت', font(AM, 190), GOLD2), W / 2, 640, scale=1.0 + 1.1 * (1 - ease(b / 0.25)), alpha=ease(b / 0.12) * (1 - out), angle=-3 * ease(b / 0.25))
        marks = [('✓', GREEN), ('✓', GREEN), ('×', RED), ('✓', GREEN)]
        for i, (s, col) in enumerate(marks):
            ta = a - (0.15 + i * 0.12)
            put(c, CH('كلمة ' + s, 38, fg=WHITE, fill=col + (220,), outline=col), W / 2 + 345 - i * 230, 900, scale=spring(ta / 0.4), alpha=ease(ta / 0.1) * (1 - out))
    elif k == 'm05':
        title(c, a, d_, 'قرابة مئتي قارئ', 'بستّ روايات… آيةً آية', out)
        ph = tilt(phone('03-mushaf', 470), 0.9 * (1 - ease(a / 0.9)))
        put(c, ph, W / 2 - 200 + 600 * (1 - ease(a / 0.7)) + 600 * out, 820)
        n = int(196 * ease((a - 0.3) / (d_ * 0.5)))
        put(c, T(str(n), font(PB, 150), GOLD2), 860, 560, alpha=ease((a - 0.3) / 0.2) * (1 - out))
        put(c, T('قارئاً', font(PS, 48), WHITE), 860, 680, alpha=ease((a - 0.5) / 0.2) * (1 - out))
        for i, s in enumerate(['آيةً آية', 'كرّر ما شئت']):
            ta = a - d_ * (0.45 + 0.25 * i)
            put(c, CH(s, 40), 860, 840 + i * 120, scale=spring(ta / 0.45), alpha=ease(ta / 0.12) * (1 - out))
    elif k == 'm06':
        title(c, a, d_, 'المساعد الذكي', 'يجيبك من التفاسير ومصادر التطبيق', out)
        ph = tilt(phone('ask', 470, top=0.03), -0.9 * (1 - ease(a / 0.9)))
        put(c, ph, W / 2 + 200 - 600 * (1 - ease(a / 0.7)) - 600 * out, 800)
        q = 'ما سبب نزول هذه الآية؟'
        nq = int(len(q) * cl((a - 0.5) / (d_ * 0.4)))
        if nq > 0:
            put(c, CH(q[:nq] + ('|' if nq < len(q) and int(a * 4) % 2 else ''), 36, fg=NAVY1, fill=(247, 218, 146, 240)), W / 2 - 120, 1170, alpha=1 - out)
        for i, s in enumerate(['من التفاسير', 'بالمصدر', 'لا يخمّن']):
            ta = a - d_ * (0.35 + 0.18 * i)
            put(c, CH(s, 38), 200, 520 + i * 120, scale=spring(ta / 0.45), alpha=ease(ta / 0.12) * (1 - out))
    elif k == 'm07':
        title(c, a, d_, 'خطّة حفظ يومية', 'تعيد عليك الآية قبل أن تنساها', out)
        ph = tilt(phone('05-hifz', 470), 0.9 * (1 - ease(a / 0.9)))
        put(c, ph, W / 2 - 200 + 600 * (1 - ease(a / 0.7)) + 600 * out, 810)
        days = ['س', 'ح', 'ن', 'ث', 'ر', 'خ', 'ج']
        for i, dn in enumerate(days):
            ta = a - (0.7 + i * d_ * 0.07); on = ease(ta / 0.2)
            col = GOLD if on > 0.5 else (60, 80, 110)
            put(c, CH(dn, 34, fg=NAVY1 if on > 0.5 else SOFT, fill=col + (235,), outline=col), 880, 500 + i * 100, scale=0.8 + 0.2 * spring(ta / 0.4), alpha=(0.5 + 0.5 * on) * (1 - out))
    elif k == 'm08':
        title(c, a, d_, 'تدرّب', 'اختبر حفظك · مختبر النطق والتجويد', out)
        ph = tilt(phone('06-tajweed', 500), -0.9 * (1 - ease(a / 0.9)))
        put(c, ph, W / 2, 830 + 700 * (1 - ease(a / 0.7)) + 700 * out)
        for i, (s, x) in enumerate([('اختبرني', W / 2 + 320), ('مختبر النطق', W / 2 - 320)]):
            ta = a - d_ * (0.1 + 0.4 * i)
            put(c, CH(s, 42), x, 1235, scale=spring(ta / 0.5), alpha=ease(ta / 0.15) * (1 - out))
    elif k == 'm09':
        title(c, a, d_, 'يومك مع القرآن', None, out)
        put(c, tilt(phone('07-wird', 380), 0.6), W / 2 + 230 - 700 * (1 - ease(a / 0.7)), 720, angle=4 * ease(a / 0.7), alpha=1 - out)
        put(c, tilt(phone('08-adhkar', 380), -0.6), W / 2 - 230 + 700 * (1 - ease((a - 0.2) / 0.7)), 720, angle=-4 * ease((a - 0.2) / 0.7), alpha=1 - out)
        for i, (s, x) in enumerate(zip(['وِردك', 'الأذكار', 'المواقيت', 'القبلة'], [W / 2 + 375, W / 2 + 125, W / 2 - 125, W / 2 - 375])):
            ta = a - d_ * (0.08 + 0.2 * i)
            put(c, CH(s, 40), x, 1225, scale=spring(ta / 0.5), alpha=ease(ta / 0.15) * (1 - out))
    elif k == 'm10':
        glow(c, W / 2, 600, 320, ease(a / 0.4) * (1 - out))
        put(c, T('المصحف كاملاً', font(PS, 60), WHITE), W / 2, 420, alpha=ease(a / 0.3) * (1 - out))
        b = a - d_ * 0.18
        put(c, T('مجّاناً', font(AM, 230), GOLD2), W / 2, 640, scale=1.0 + 1.2 * (1 - ease(b / 0.25)), alpha=ease(b / 0.12) * (1 - out), angle=-4 * ease(b / 0.25))
        b2 = a - d_ * 0.62
        put(c, CH('بلا إعلان', 60), W / 2, 900, scale=0.4 + 0.6 * spring(b2 / 0.5), alpha=ease(b2 / 0.1) * (1 - out))
    else:
        glow(c, W / 2, 400, 230, ease(a / 0.4))
        put(c, LG[170], W / 2, 400, scale=0.4 + 0.6 * spring(a / 0.7), alpha=ease(a / 0.2))
        put(c, T('مصحفك', font(AM, 160), GOLD2), W / 2, 620, alpha=ease((a - 0.2) / 0.3))
        put(c, T('حمّله الآن', font(PB, 80), WHITE), W / 2, 800, scale=0.85 + 0.15 * spring((a - 0.5) / 0.5), alpha=ease((a - 0.5) / 0.2))
        pulse = 1 + 0.04 * math.sin(max(0, a - 1.2) * 6)
        put(c, CH('Google Play', 54, fg=NAVY1, fill=(247, 218, 146, 245)), W / 2, 950, scale=pulse * spring((a - 0.9) / 0.5), alpha=ease((a - 0.9) / 0.15))
        put(c, T('الرابط في الردّ', font(PM, 38), SOFT), W / 2, 1090, alpha=ease((a - 1.5) / 0.3))
    for kk in K[1:]:
        p = (tm - (st[kk] - GAP / 2 - 0.25)) / 0.5
        if 0 < p < 1: flash(c, p)
    return c.convert('RGB')

# ── المؤثّرات: هبّةٌ خفيفة عند كلّ انتقال (ضجيجٌ مُرشَّح، لا موسيقى) ──
sfx = []
for kk in K[1:]:
    sfx.append(st[kk] - GAP / 2 - 0.2)
def whoosh_filter():
    parts, labels = [], []
    for i, t0 in enumerate(sfx):
        parts.append('anoisesrc=d=0.6:c=pink:a=0.5,highpass=f=500,lowpass=f=4500,afade=t=in:d=0.25,afade=t=out:st=0.25:d=0.35,volume=0.16,adelay=%d|%d[w%d]' % (t0 * 1000, t0 * 1000, i))
        labels.append('[w%d]' % i)
    return ';'.join(parts) + ';' + ''.join(labels) + 'amix=inputs=%d:normalize=0[sx]' % len(labels)

import os
if os.environ.get('PREVIEW'):
    for x in os.environ['PREVIEW'].split(','):
        frame(float(x)).save('%s/pv_%s.jpg' % (os.path.dirname(OUT) or '.', x), quality=80)
    sys.exit(0)
n = int(TOTAL * FPS)
fc = whoosh_filter() + ';[1:a]adelay=%d|%d,loudnorm=I=-14:TP=-1.5[vo];[vo][sx]amix=inputs=2:normalize=0:duration=first,apad[a]' % (LEAD * 1000, LEAD * 1000)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-',
                      '-i', AUD, '-filter_complex', fc, '-map', '0:v', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17',
                      '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', '-t', '%.2f' % TOTAL, OUT], stdin=subprocess.PIPE)
for i in range(n):
    p.stdin.write(frame(i / FPS).tobytes())
p.stdin.close(); p.wait()
json.dump({'starts': st, 'total': TOTAL}, open(OUT + '.json', 'w'))
print('ok', round(TOTAL, 2), 'rc', p.returncode)
