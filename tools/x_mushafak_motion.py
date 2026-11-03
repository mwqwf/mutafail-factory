# مقطع مصحفك المتحرّك لاكس: تركيبٌ وتحريكٌ للقطات التطبيق الحقيقية مع نصوصٍ مركّبة، بلا توليد صور.
# التعليق من ops/voice/mushafak-x.json (صوت الراوي Algenib بحصّة Gemini المجّانية، شوط voice-sample.yml).
# python3 motion.py <مجلد> <durations.json: {"m1": ث, ...}> <الصوت.wav> <المخرج.mp4>
import json, math, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
S, DUR, AUD, OUT = sys.argv[1:5]
F = '/home/claude/quranrafiq/app/src/main/res/font/'
W, H, FPS = 1080, 1350, 30
NAVY1, NAVY2 = (8, 20, 38), (16, 42, 70)
GOLD, GOLD2, WHITE, SOFT = (222, 184, 92), (245, 214, 140), (250, 248, 240), (190, 200, 215)
fc = {}
def font(n, s):
    k = (n, s)
    if k not in fc: fc[k] = ImageFont.truetype(F + n, s)
    return fc[k]
AM, PB, PS, PM = 'amiri_bold.ttf', 'ibm_plex_sans_arabic_bold.ttf', 'ibm_plex_sans_arabic_semibold.ttf', 'ibm_plex_sans_arabic_medium.ttf'

def ease(t): t = max(0, min(1, t)); return 1 - (1 - t) ** 3
def spring(t):
    t = max(0, min(1, t)); return 1 - math.exp(-6 * t) * math.cos(9 * t)

def make_bg():
    im = Image.new('RGB', (W, H + 240), NAVY1)
    g = Image.new('L', im.size, 0); d = ImageDraw.Draw(g)
    d.ellipse((-300, 300, W + 300, H + 500), fill=255); g = g.filter(ImageFilter.GaussianBlur(220))
    im = Image.composite(Image.new('RGB', im.size, NAVY2), im, g)
    p = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(p)
    for x in range(-60, W + 60, 120):
        for y in range(-60, H + 300, 120):
            d.regular_polygon((x, y, 46), 8, rotation=22.5, outline=(222, 184, 92, 16), width=2)
    im.paste(p, (0, 0), p); return im
BG = make_bg()

def shot(name, top=0.045):
    im = Image.open('%s/shots/%s.png' % (S, name)).convert('RGB'); w, h = im.size
    return im.crop((0, int(h * top), w, h))

PH = {}
def phone_img(name, w):
    k = (name, w)
    if k in PH: return PH[k]
    img = shot(name); sw, sh = img.size; h = int(w * sh / sw)
    b = max(10, w // 26); r = int(w * 0.12); PW, PHh = w + 2 * b, h + 2 * b
    ph = Image.new('RGBA', (PW + 100, PHh + 100), (0, 0, 0, 0))
    a = Image.new('L', ph.size, 0); ImageDraw.Draw(a).rounded_rectangle((50, 70, 50 + PW, 70 + PHh), radius=r, fill=140)
    ph.putalpha(a.filter(ImageFilter.GaussianBlur(26)))
    fr = Image.new('RGBA', (PW, PHh), (0, 0, 0, 0)); d = ImageDraw.Draw(fr)
    d.rounded_rectangle((0, 0, PW - 1, PHh - 1), radius=r, fill=(18, 18, 22), outline=GOLD, width=3)
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=r - b, fill=255)
    fr.paste(img.resize((w, h), Image.LANCZOS), (b, b), m)
    ph.alpha_composite(fr, (50, 50)); PH[k] = ph; return ph

def put(c, img, cx, cy, scale=1.0, alpha=1.0, angle=0):
    if scale != 1.0: img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BILINEAR)
    if angle: img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
    if alpha < 1: a = img.split()[3].point(lambda v: int(v * alpha)); img = img.copy(); img.putalpha(a)
    c.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))

def text_img(s, f, fill):
    d0 = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    bb = d0.textbbox((0, 0), s, font=f, direction='rtl', language='ar')
    im = Image.new('RGBA', (bb[2] - bb[0] + 40, bb[3] - bb[1] + 40), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20 - bb[0], 20 - bb[1]), s, font=f, fill=fill, direction='rtl', language='ar')
    return im
TC = {}
def T(s, f, fill):
    k = (s, f, fill)
    if k not in TC: TC[k] = text_img(s, f, fill)
    return TC[k]

def chip_img(s, f):
    t = T(s, f, GOLD2); w, h = t.width + 30, t.height + 6
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=(222, 184, 92, 40), outline=GOLD, width=2)
    im.alpha_composite(t, (15, 3)); return im

LOGO = Image.open(S + '/logo.png').convert('RGBA')
def logo(sz): return LOGO.resize((sz, sz), Image.LANCZOS)
LG = {s: logo(s) for s in (150, 220)}

dur = json.load(open(DUR))
GAP = 0.6
starts, t = {}, 0.35
for k in ['m1', 'm2', 'm3', 'm4', 'm5', 'm6']:
    starts[k] = t; t += dur[k] + GAP
TOTAL = t + 1.2

def scene(k, tt):
    """tt: الزمن من بداية مقطع k. يرجع ما يُرسم."""
    return tt

def frame(tm):
    c = BG.crop((0, int(120 + 100 * math.sin(tm / 9)), W, int(120 + 100 * math.sin(tm / 9)) + H)).convert('RGBA')
    def at(k): return tm - starts[k]
    def vis(k, nxt):
        return starts[k] - 0.2 <= tm < (starts[nxt] if nxt else 99)
    # ١ الخطّاف
    if tm < starts['m2']:
        a = at('m1'); out = ease((tm - (starts['m2'] - 0.35)) / 0.35)
        l1, l2 = T('تحفظ السورة…', font(AM, 104), WHITE), T('ثمّ تنساها بعد أسبوع؟', font(AM, 92), GOLD2)
        put(c, l1, W / 2, 560 - 40 * (1 - ease(a / 0.5)), alpha=ease(a / 0.5) * (1 - out))
        a2 = a - dur['m1'] * 0.45
        put(c, l2, W / 2, 720, scale=0.85 + 0.15 * spring(a2 / 0.7), alpha=ease(a2 / 0.3) * (1 - out))
    # ٢ الاسم
    elif tm < starts['m3']:
        a = at('m2'); out = ease((tm - (starts['m3'] - 0.35)) / 0.35)
        put(c, LG[220], W / 2, 470, scale=0.5 + 0.5 * spring(a / 0.9), alpha=ease(a / 0.3) * (1 - out))
        put(c, T('مصحفك', font(AM, 150), GOLD2), W / 2, 700, alpha=ease((a - 0.25) / 0.4) * (1 - out))
        put(c, T('مصحفٌ يعرف صاحبه', font(PS, 56), WHITE), W / 2, 850 + 30 * (1 - ease((a - 0.6) / 0.5)), alpha=ease((a - 0.6) / 0.5) * (1 - out))
    # ٣ التسميع ٤ الحفظ: هاتفٌ واحد ينزلق مع عنوان
    elif tm < starts['m5']:
        k = 'm3' if tm < starts['m4'] else 'm4'
        nxt = 'm4' if k == 'm3' else 'm5'
        a = at(k); out = ease((tm - (starts[nxt] - 0.35)) / 0.35)
        name = '02-tasmi' if k == 'm3' else '05-hifz'
        title, sub = (('سمّع من حفظك', 'يتابعك كلمةً كلمة ويريك خطأك'), ('احفظ بخطةٍ يومية', 'تعيد عليك الآية قبل أن تُنسى'))[k == 'm4']
        put(c, T(title, font(PB, 74), GOLD2), W / 2, 150, alpha=ease(a / 0.4) * (1 - out))
        put(c, T(sub, font(PM, 40), SOFT), W / 2, 240, alpha=ease((a - 0.2) / 0.4) * (1 - out))
        ph = phone_img(name, 470)
        y = 830 + 700 * (1 - ease(a / 0.7)) - 18 * min(1, a / 6) + 500 * out
        put(c, ph, W / 2, y, scale=1.0 + 0.03 * ease(a / 6))
        if k == 'm3':
            ch = chip_img('بلا إنترنت', font(PS, 36))
            put(c, ch, W / 2 + 330, 520, scale=spring((a - dur['m3'] * 0.7) / 0.6), alpha=ease((a - dur['m3'] * 0.7) / 0.2) * (1 - out))
    # ٥ الروايات والقرّاء والمساعد
    elif tm < starts['m6']:
        a = at('m5'); out = ease((tm - (starts['m6'] - 0.35)) / 0.35)
        put(c, phone_img('01-riwayat', 330), W / 2 - 300 * ease(a / 0.8), 760, angle=7 * ease(a / 0.8), alpha=1 - out)
        put(c, phone_img('06-tajweed', 330), W / 2 + 300 * ease(a / 0.8), 760, angle=-7 * ease(a / 0.8), alpha=1 - out)
        put(c, phone_img('03-mushaf', 390), W / 2, 740 - 10 * ease(a / 4), alpha=1 - out)
        items = ['٦ روايات', 'مئات القرّاء', 'مساعدٌ ذكي']
        for i, s in enumerate(items):
            ta = a - dur['m5'] * (0.05 + 0.3 * i)
            put(c, chip_img(s, font(PS, 40)), W / 2, 150 + 0 * i if False else 140, alpha=0)
        # الشارات في صفٍّ واحد تظهر تباعاً مع الكلام
        xs = [W / 2 + 330, W / 2, W / 2 - 330]
        for i, s in enumerate(items):
            ta = a - dur['m5'] * (0.02 + 0.3 * i)
            put(c, chip_img(s, font(PS, 40)), xs[i], 150, scale=spring(ta / 0.6), alpha=ease(ta / 0.2) * (1 - out))
    # ٦ الخاتمة
    else:
        a = at('m6')
        put(c, LG[150], W / 2, 400, scale=0.6 + 0.4 * spring(a / 0.8), alpha=ease(a / 0.3))
        put(c, T('مصحفك', font(AM, 140), GOLD2), W / 2, 600, alpha=ease((a - 0.2) / 0.4))
        put(c, T('حمّله مجّاناً', font(PB, 70), WHITE), W / 2, 780, scale=0.9 + 0.1 * spring((a - 0.6) / 0.6), alpha=ease((a - 0.6) / 0.3))
        put(c, chip_img('Google Play', font(PB, 48)), W / 2, 920, alpha=ease((a - 1.0) / 0.3))
        put(c, T('المصحف وتلاوته بلا إعلان · بلا حساب', font(PM, 34), SOFT), W / 2, 1060, alpha=ease((a - 1.4) / 0.4))
    return c.convert('RGB')

n = int(TOTAL * FPS)
p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-',
                      '-i', AUD, '-filter_complex', '[1:a]adelay=350|350,apad[a]', '-map', '0:v', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                      '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', '-t', '%.2f' % TOTAL, OUT], stdin=subprocess.PIPE)
for i in range(n):
    p.stdin.write(frame(i / FPS).tobytes())
p.stdin.close(); p.wait()
json.dump({'starts': starts, 'total': TOTAL}, open(OUT + '.json', 'w'))
print('ok', TOTAL)
