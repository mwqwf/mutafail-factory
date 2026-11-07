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
K = ['a%02d' % i for i in range(1, 11)]
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
def bubble(s, f, fg, fill, w=760):
    t = T(s, f, fg, shadow=False); h = t.height + 10
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), radius=34, fill=fill)
    im.alpha_composite(t, (w - t.width - 4, 5)); return im
_bb = {}
XX = Image.new('RGBA', (170, 170), (0, 0, 0, 0)); _d = ImageDraw.Draw(XX)
_d.line((22, 22, 148, 148), fill=RED, width=26); _d.line((148, 22, 22, 148), fill=RED, width=26)
def BB(s, size, fg, fill, w=760):
    k = (s, size, fg, fill, w)
    if k not in _bb: _bb[k] = bubble(s, font(PM, size), fg, fill, w)
    return _bb[k]

def frame(tm):
    k = K[0]
    for kk in K:
        if tm >= st[kk] - GAP / 2: k = kk
    a = tm - st[k]; d_ = dur[k]; out = ease((tm - (nxt(k) - 0.3)) / 0.3)
    rays = {'a03': 1.0, 'a06': 0.8, 'a10': 1.0}.get(k, 0.3)
    c = background(tm, rays)
    if k in ('a01', 'a02'):
        # محادثةٌ عامّة مع ذكاءٍ اصطناعيّ عامّ (رسمٌ توضيحيّ لا تطبيقٌ بعينه)
        sh = 0 if k == 'a01' else 8 * math.sin(a * 37) * (1 - ease(a / 0.6))
        put(c, BB('ما تفسير هذه الآية؟', 40, NAVY1, (247, 218, 146, 240), 620), W / 2 + 140 + sh, 640, alpha=ease(a / 0.3) * (1 - out) if k == 'a01' else 1 - out)
        rep = BB('… ' * 3 + 'جوابٌ واثقٌ بلا مصدر', 40, WHITE, (70, 80, 100, 235), 700)
        ra = a - 0.6 if k == 'a01' else 9
        put(c, rep, W / 2 - 90 + sh, 790, alpha=ease(ra / 0.3) * (1 - out))
        if k == 'a01':
            kinetic(c, 'هل سئمت من أخطاء'.split(), font(AM, 92), WHITE, 250, a, 0.6, out)
            kinetic(c, 'الذكاء الاصطناعي؟'.split(), font(AM, 100), GOLD2, 390, a - 0.5, 0.4, out)
            put(c, T('حين تسأله عن دينك', font(PS, 50), SOFT), W / 2, 1050, alpha=ease((a - d_ * 0.6) / 0.3) * (1 - out))
        else:
            put(c, T('يخمّن…', font(AM, 110), RED), W / 2, 300, scale=0.6 + 0.4 * spring(a / 0.5), alpha=ease(a / 0.15) * (1 - out))
            b = a - d_ * 0.35
            kinetic(c, 'ويجيبك بثقةٍ بلا مصدر'.split(), font(PB, 56), WHITE, 1010, b, 0.7, out)
            put(c, XX, W / 2 - 330, 790, scale=1 + 1.2 * (1 - ease((a - 0.3) / 0.25)), alpha=ease((a - 0.3) / 0.1) * (1 - out), angle=-10)
    elif k == 'a03':
        glow(c, W / 2, 470, 280, ease(a / 0.4) * (1 - out))
        kinetic(c, 'جئناك بالحلّ'.split(), font(AM, 110), WHITE, 230, a, 0.4, out)
        put(c, LG[260], W / 2, 520, scale=0.3 + 0.7 * spring((a - 0.4) / 0.8), alpha=ease((a - 0.4) / 0.2) * (1 - out))
        put(c, T('المساعد الذكي', font(AM, 130), GOLD2), W / 2, 790, scale=0.8 + 0.2 * spring((a - d_ * 0.45) / 0.6), alpha=ease((a - d_ * 0.45) / 0.25) * (1 - out))
        put(c, T('في مصحفك', font(PB, 60), WHITE), W / 2, 930, alpha=ease((a - d_ * 0.7) / 0.25) * (1 - out))
    elif k == 'a04':
        title(c, a, d_, 'في كلّ ما يتّصل بدينك', 'على منهج أهل السنّة', out)
        ph = tilt(phone('promo_22_ask_fiqh_end', 470, top=0.03), -0.9 * (1 - ease(a / 0.9)))
        put(c, ph, W / 2 + 200 - 600 * (1 - ease(a / 0.7)) - 600 * out, 800)
        for i, s_ in enumerate(['التفسير', 'الحديث', 'الفقه', 'العقيدة', 'السيرة']):
            ta = a - d_ * (0.12 + 0.13 * i)
            put(c, CH(s_, 40), 210, 470 + i * 120, scale=spring(ta / 0.45), alpha=ease(ta / 0.12) * (1 - out))
    elif k == 'a05':
        title(c, a, d_, 'لا نتيجة بلا مصدر', 'وينسب كلّ قولٍ إلى قائله', out)
        ph = tilt(phone('promo_23_ask_fiqh_up', 480, top=0.03), 0.9 * (1 - ease(a / 0.9)))
        put(c, ph, W / 2, 820 + 700 * (1 - ease(a / 0.7)) + 700 * out)
        ta = a - d_ * 0.55
        put(c, XX, W / 2 + 330, 470, scale=0.6 * spring(ta / 0.4), alpha=ease(ta / 0.1) * (1 - out) * 0)
    elif k == 'a06':
        title(c, a, d_, 'بحثٌ معمّق', 'باحثٌ ناقدٌ دقيق… لا يتساهل في الأصول', out)
        cx, cy = W / 2, 760
        glow(c, cx, cy, 160, ease((a - 0.3) / 0.4) * (1 - out))
        put(c, LG[170], cx, cy, scale=spring((a - 0.2) / 0.6), alpha=ease((a - 0.2) / 0.2) * (1 - out))
        nodes = [('مصادر التطبيق', cx, cy - 330), ('المكتبة الشاملة', cx + 300, cy + 250), ('الإنترنت', cx - 300, cy + 250)]
        L = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(L)
        for i, (s_, x, y) in enumerate(nodes):
            ta = a - (0.6 + i * d_ * 0.18); p_ = ease(ta / 0.4)
            if p_ > 0: dd.line((cx, cy, cx + (x - cx) * 0.72 * p_, cy + (y - cy) * 0.72 * p_), fill=(247, 218, 146, int(200 * (1 - out))), width=5)
        c.alpha_composite(L)
        for i, (s_, x, y) in enumerate(nodes):
            ta = a - (0.9 + i * d_ * 0.18)
            put(c, CH(s_, 40), x, y, scale=spring(ta / 0.45), alpha=ease(ta / 0.12) * (1 - out))
    elif k == 'a07':
        title(c, a, d_, 'يعرف مصحفك كلّه', 'ويشرح لك أيّ ميزةٍ فيه', out)
        ph = tilt(phone('promo_24_ask_app_end', 480, top=0.03), -0.9 * (1 - ease(a / 0.9)))
        put(c, ph, W / 2, 820 + 700 * (1 - ease(a / 0.7)) + 700 * out)
    elif k == 'a08':
        title(c, a, d_, 'بصوتك… أو بصورةٍ أو ملفّ', None, out)
        put(c, tilt(phone('dict_2_recording', 400, top=0.03), 0.6), W / 2 + 220 - 700 * (1 - ease(a / 0.7)), 760, angle=4 * ease(a / 0.7), alpha=1 - out)
        put(c, tilt(phone('promo_30_ask_attach', 400, top=0.03), -0.6), W / 2 - 220 + 700 * (1 - ease((a - 0.2) / 0.7)), 760, angle=-4 * ease((a - 0.2) / 0.7), alpha=1 - out)
        for i, (s_, x) in enumerate(zip(['بصوتك', 'صورة', 'PDF أو Word'], [W / 2 + 300, W / 2, W / 2 - 300])):
            ta = a - d_ * (0.15 + 0.2 * i)
            put(c, CH(s_, 40), x, 1235, scale=spring(ta / 0.5), alpha=ease(ta / 0.15) * (1 - out))
    elif k == 'a09':
        title(c, a, d_, 'لا يكتب نصّ القرآن بنفسه', 'الآيات تُعرض من مصحفك', out)
        ph = tilt(phone('promo_03_mushaf', 480), 0.9 * (1 - ease(a / 0.9)))
        put(c, ph, W / 2, 820 + 700 * (1 - ease(a / 0.7)) + 700 * out)
    else:
        glow(c, W / 2, 420, 260, ease(a / 0.4))
        put(c, LG[260], W / 2, 400, scale=0.4 + 0.6 * spring(a / 0.6), alpha=ease(a / 0.2))
        put(c, T('جرّبه الآن', font(AM, 120), GOLD2), W / 2, 680, scale=0.8 + 0.2 * spring((a - 0.3) / 0.5), alpha=ease((a - 0.3) / 0.2))
        put(c, T('واسأله ما شئت', font(PB, 66), WHITE), W / 2, 830, alpha=ease((a - d_ * 0.45) / 0.25))
        pulse = 1 + 0.04 * math.sin(max(0, a - 2) * 6)
        put(c, CH('Google Play', 52, fg=NAVY1, fill=(247, 218, 146, 245)), W / 2, 990, scale=pulse * spring((a - d_ * 0.6) / 0.5), alpha=ease((a - d_ * 0.6) / 0.15))
        put(c, T('الرابط في الردّ', font(PM, 36), SOFT), W / 2, 1110, alpha=ease((a - d_ * 0.8) / 0.3))
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
