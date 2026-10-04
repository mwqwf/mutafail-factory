# -*- coding: utf-8 -*-
"""الكتابة المتحرّكة بأسلوب العروض التقديمية — أمر المالك 2026-10-04 (فيلم «الأرك»).

نصُّ الأمر: «حاول تعويض التحريك بأي شيء… استعمل طرقاً مبتكرة، مثلاً أحياناً تحريكٌ للكتابة والصور مثل نوعية ما
يُستعمل في العروض التقديمية (البوربوينت)، كأنّ الكتابة تُكتب أثناء الإلقاء، وغيرها من الأساليب التي لم نجربها».
ثم في اليوم نفسه: «الصور ممنوعة عليك اتركها لكوديكس… حتى البطاقات المكتوبة اتركها لكوديكس».

⛔ لا يرسم هذا الملفّ حرفاً: كلّ كتابةٍ بطاقةُ PNG شفّافة يصنعها كوديكس (tools/cards.py يحصرها ويُلحقها بالطابور)،
وهنا تُقصّ وتُحجَّم وتُحرَّك فقط. البطاقة الغائبة يُتخطّى عنصرها ولا يُرسم بديلٌ عنها.
يُستدعى من tools/mont_hybrid.py لكلّ لقطةٍ فيها حقلٌ مما يلي:

  kt     كتابةٌ تُكشف سطراً سطراً **لحظةَ نطقه** من اليمين: lower · center · quote · letter (على رقٍّ من كوديكس)
         · poem (شطران متقابلان) · list (بنودٌ تنزلق بنداً بنداً)
  slam   ضربةٌ مكتوبة بتكبيرٍ وارتجاجٍ وومضة عند كلمتها
  cards  صورُ كوديكس مصغّرةً في إطارٍ تطير واحدةً بعد أخرى، وتحت كلٍّ بطاقةُ اسمها
  labels تسمياتٌ على مواضعها من الصورة (خريطة التشكيل)
  name   بطاقةُ اسمٍ سفلية · date ختمٌ زمنيّ يُكشف من اليمين
  flash  ومضةٌ بيضاء · shake ارتجاجٌ عند كلمات · punch تكبيرٌ خاطف عند كلمات
  _chapter عنوان الفصل أعلى أوّل لقطةٍ فيه (يضعه mont_hybrid من sections.json)

التوقيت: زمنُ كلّ كلمةٍ من صوت كتلتها نفسه — مواضعُ الصمت (silencedetect) تُطابَق بعلامات الوقف في النصّ
(… ، . ؟ !) ثم تُوزَّع الكلمات بين المرتكزات بعدد حروفها. وإن تعذّر الكشف فبنسبة الحروف وحدها.
"""
from __future__ import annotations

import math
import os
import re
import subprocess as sp
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cards  # noqa: E402
import envpaths  # noqa: E402
from PIL import Image, ImageChops, ImageDraw  # noqa: E402

W, H, FPS = 1920, 1080, 25
TEMPO = 1.05                      # mont_hybrid يسرّع مسار الصوت كلّه 1.05
FX_KEYS = ('kt', 'slam', 'cards', 'labels', 'name', 'date', 'flash', 'shake', 'punch', '_chapter')
HARAKAT = re.compile('[ً-ْٰـ]')
PUNCT = '…،,.؟?!:؛«»"“”()-—'
PAUSE_MARKS = '…،,.؟?!:؛'


def has_fx(s: dict) -> bool:
    return any(s.get(k) for k in FX_KEYS)


def plain(t: str) -> str:
    return HARAKAT.sub('', t or '')


def bare(w: str) -> str:
    """الكلمة بلا تشكيل ولا علامات — للمطابقة بين حقول fx والنصّ المنطوق."""
    return plain(w).strip(PUNCT + ' ').replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')


# ══════════ توقيت الكلمات من الصوت ══════════
def silences(wav: str, noise: str = '-34dB', mind: float = 0.13) -> tuple[list[tuple[float, float]], float]:
    try:
        o = sp.run([envpaths.FF, '-hide_banner', '-nostats', '-i', wav, '-af', 'silencedetect=noise=%s:d=%.2f' % (noise, mind),
                    '-f', 'null', '-'], capture_output=True, text=True, timeout=60).stderr
        d = sp.run([envpaths.FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', wav],
                   capture_output=True, text=True, timeout=30).stdout.strip()
        dur = float(d)
    except Exception:
        return [], 0.0
    st = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', o)]
    en = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', o)]
    if len(en) < len(st):
        en.append(dur)
    return list(zip(st, en)), dur


def tokens(text: str) -> list[tuple[str, bool]]:
    """كلماتٌ وعلاماتُ وقف بترتيبها: (النصّ، هل هو علامة وقف)."""
    t = plain(text).replace('…', ' … ')
    out = []
    for tok in t.split():
        core = tok.rstrip(PAUSE_MARKS + '»"”')
        if tok == '…':
            out.append(('…', True)); continue
        if core:
            out.append((tok.strip('«»"“”') or core, False))
        if core != tok and any(c in PAUSE_MARKS for c in tok[len(core):]):
            out.append((tok[len(core):], True))
    return out


def block_word_times(text: str, wav: str | None, dur: float) -> list[tuple[str, float, float]]:
    """أزمنة كلمات الكتلة بالثواني من أوّل ملفّها (قبل تسريع 1.05): [(الكلمة المعروضة، بداية، نهاية)]."""
    toks = tokens(text)
    words = [w for w, p in toks if not p]
    if not words:
        return []
    sil, d0 = silences(wav) if wav and os.path.exists(wav) else ([], 0.0)
    dur = d0 or dur
    lead = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0
    tail = sil[-1][0] if sil and sil[-1][1] >= dur - 0.05 and sil[-1][0] > lead else dur
    inner = [(a, b) for a, b in sil if a > lead + 0.05 and b < tail - 0.05]
    # مواضعُ علامات الوقف بعدد الحروف قبلها
    nchar = lambda w: len(bare(w)) + 1
    total = sum(nchar(w) for w in words)
    marks, acc = [], 0
    for w, p in toks:
        if p:
            if acc and acc < total: marks.append(acc)
        else:
            acc += nchar(w)
    # مطابقةُ كلّ علامةٍ بصمتٍ داخليّ قريبٍ من موضعها المتوقّع، بترتيبٍ لا يرجع
    anchors, used, k = [(0, lead)], -1, 0
    span = max(0.2, tail - lead)
    for m in marks:
        exp = lead + span * m / total
        best = None
        for j in range(used + 1, len(inner)):
            mid = (inner[j][0] + inner[j][1]) / 2
            if abs(mid - exp) < span * 0.18 and (best is None or abs(mid - exp) < abs((inner[best][0] + inner[best][1]) / 2 - exp)):
                best = j
        if best is not None:
            anchors.append((m, inner[best][1], inner[best][0])); used = best
    anchors.append((total, tail))
    # توزيع الكلمات بين المرتكزات بعدد حروفها
    out, acc = [], 0
    for w in words:
        c0, c1 = acc, acc + nchar(w); acc = c1
        def at(c):
            for i in range(len(anchors) - 1):
                a, b = anchors[i], anchors[i + 1]
                if a[0] <= c <= b[0]:
                    t_a = a[1]; t_b = b[2] if len(b) > 2 else b[1]
                    return t_a + (t_b - t_a) * (c - a[0]) / max(1, b[0] - a[0])
            return tail
        out.append((w, at(c0), at(c1 - 1)))
    return out


def shot_word_times(proj: str, s: dict, texts: dict, durs: dict, gap: float) -> list[tuple[str, float, float]]:
    """أزمنة كلمات اللقطة في خطّها الزمنيّ النهائيّ (بعد 1.05)."""
    out, t0 = [], 0.0
    for bid in s.get('blocks', []):
        if bid not in texts:
            continue
        d = durs.get(bid, 0.0)
        for w, a, b in block_word_times(texts[bid], os.path.join(proj, 'audio', bid + '.wav'), d):
            out.append((w, (t0 + a) / TEMPO, (t0 + b) / TEMPO))
        t0 += d + gap
    return out


def find_word(wt: list, word: str | None, default: float) -> float:
    if not word:
        return default
    key = bare(word)
    for w, a, _ in wt:
        if bare(w) == key or (len(key) > 3 and key in bare(w)):
            return max(0.0, a - 0.05)
    return default


# ══════════ مشهدٌ من عناصر متحرّكة ══════════
def ease_out(p): return 1 - (1 - p) ** 3


def ease_back(p, s=1.9):
    p -= 1
    return p * p * ((s + 1) * p + s) + 1


class El:
    """عنصرٌ يظهر عند t0 بحركة دخول anim مدّتها d، ويختفي اختيارياً عند t1."""
    def __init__(self, img, x, y, t0=0.0, anim='fade', d=0.2, t1=None, z=1):
        self.img, self.x, self.y, self.t0, self.anim, self.d, self.t1, self.z = img, x, y, t0, anim, d, t1, z

    def frame_times(self):
        ts = [self.t0]
        if self.anim != 'none' and self.d > 0:
            ts += [self.t0 + k / FPS for k in range(1, int(math.ceil(self.d * FPS)) + 1)]
        if self.t1 is not None:
            ts += [self.t1 + k / FPS for k in range(0, int(0.3 * FPS) + 1)]
        return ts


def _alpha(im, a):
    if a >= 0.999:
        return im
    im = im.copy()
    im.putalpha(ImageChops.multiply(im.getchannel('A'), Image.new('L', im.size, int(255 * max(0.0, a)))))
    return im


def _paste(canvas, im, x, y):
    x, y = int(round(x)), int(round(y))
    l, t = max(0, x), max(0, y)
    r, b = min(W, x + im.width), min(H, y + im.height)
    if r <= l or b <= t:
        return
    canvas.alpha_composite(im.crop((l - x, t - y, r - x, b - y)), dest=(l, t))


def compose(els: list, t: float) -> Image.Image:
    cv = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for e in sorted(els, key=lambda e: e.z):
        if t + 1e-6 < e.t0:
            continue
        p = 1.0 if e.anim == 'none' or e.d <= 0 else min(1.0, (t - e.t0) / e.d)
        a, im, x, y = 1.0, e.img, e.x, e.y
        if e.t1 is not None and t >= e.t1:
            a = max(0.0, 1 - (t - e.t1) / 0.3)
        if e.anim == 'fade':
            a *= ease_out(p)
        elif e.anim == 'rise':
            a *= ease_out(p); y += 26 * (1 - ease_out(p))
        elif e.anim in ('zoom', 'slam'):
            k = (1 + 0.35 * (1 - ease_out(p))) if e.anim == 'zoom' else max(0.6, 2.3 - 1.3 * ease_back(p))
            a *= min(1.0, p * 3)
            if abs(k - 1) > 0.01:
                nw, nh = max(1, int(im.width * k)), max(1, int(im.height * k))
                im = im.resize((nw, nh), Image.BILINEAR)
                x, y = x - (nw - e.img.width) / 2, y - (nh - e.img.height) / 2
        elif e.anim == 'slide':                 # من اليمين (اتجاه القراءة العربية)
            a *= min(1.0, p * 2); x += (1 - ease_out(p)) * 380
        elif e.anim == 'wipe':                  # كتابةٌ تُخطّ من اليمين إلى اليسار
            cut = int(im.width * (1 - ease_out(p) if p < 1 else 0))
            if cut > 0:
                im = im.copy(); ImageDraw.Draw(im).rectangle([0, 0, cut, im.height], fill=(0, 0, 0, 0))
        if a > 0.003:
            _paste(cv, _alpha(im, a), x, y)
    return cv


def render_track(els: list, span: float, work: str, name: str) -> str | None:
    """يكتب حالات المشهد صوراً متتابعة بمددها (concat) — لا تُكتب إلا لحظات التغيّر."""
    if not els:
        return None
    ts = sorted({round(min(max(0.0, t), span - 0.02), 3) for e in els for t in e.frame_times()} | {0.0})
    d = os.path.join(work, 'kin_' + name); os.makedirs(d, exist_ok=True)
    lst = os.path.join(d, 'list.txt')
    with open(lst, 'w', encoding='utf-8') as fh:
        for i, t in enumerate(ts):
            f = os.path.join(d, '%04d.png' % i)
            compose(els, t).save(f, compress_level=1)
            nxt = ts[i + 1] if i + 1 < len(ts) else span
            fh.write("file '%s'\nduration %.3f\n" % (f.replace('\\', '/'), max(0.04, nxt - t)))
        fh.write("file '%s'\n" % f.replace('\\', '/'))
    return lst


# ══════════ بطاقات كوديكس ══════════
_CARDS: dict = {}
_MISSING: set = set()


def keyout(im: Image.Image) -> Image.Image:
    """بطاقةٌ بلا شفافيةٍ حقيقية (خلفيةٌ موحّدة): تُعزل خلفيتها بلون زواياها — قصٌّ ومونتاج لا رسم."""
    rgb = im.convert('RGB')
    w, h = rgb.size
    pts = [rgb.getpixel((x, y)) for x, y in ((2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3))]
    if max(max(abs(a[i] - b[i]) for i in range(3)) for a in pts for b in pts) > 40:
        return im                                  # الزوايا مختلفة: ليست خلفيةً موحّدة، تُترك كما هي
    bg = tuple(sum(p[i] for p in pts) // 4 for i in range(3))
    diff = ImageChops.difference(rgb, Image.new('RGB', rgb.size, bg)).convert('L')
    alpha = diff.point(lambda v: 0 if v < 28 else (255 if v > 70 else int((v - 28) * 255 / 42)))
    out = im.convert('RGBA')
    out.putalpha(alpha)
    return out


def card(proj: str, key: str) -> Image.Image | None:
    """بطاقة كوديكس cards/<المفتاح>.png مقصوصةً إلى حدود ما فيها؛ None إن غابت (ويُتخطّى عنصرها)."""
    if key in _CARDS:
        return _CARDS[key]
    path = os.path.join(proj, 'cards', key + '.png')
    if not os.path.exists(path):
        if key not in _MISSING:
            _MISSING.add(key)
            print('⚠ بطاقةٌ غائبة يُتخطّى عنصرها:', key, flush=True)
        _CARDS[key] = None
        return None
    im = Image.open(path).convert('RGBA')
    if im.getchannel('A').getextrema()[0] >= 250:
        im = keyout(im)
    bb = im.getchannel('A').point(lambda v: 255 if v > 16 else 0).getbbox()
    if bb:
        im = im.crop(bb)
    _CARDS[key] = im
    return im


def fit(im: Image.Image, maxw: float, maxh: float, up: float = 1.8) -> Image.Image:
    k = min(maxw / im.width, maxh / im.height, up)
    return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)


def dim_el(alpha: float, t0: float = 0.0, d: float = 0.3, z: int = 0):
    return El(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * alpha))), 0, 0, t0, 'fade', d, z=z)


def band_el(y0: int, t0=0.0):
    """تدرّجٌ معتمٌ أسفل الإطار لقراءة الكتابة."""
    g = Image.new('L', (1, H - y0))
    for i in range(H - y0):
        g.putpixel((0, i), int(205 * (i / (H - y0)) ** 0.8))
    im = Image.new('RGBA', (W, H - y0), (0, 0, 0, 255)); im.putalpha(g.resize((W, H - y0)))
    return El(im, 0, y0, t0, 'fade', 0.3, z=0)


def spread(n: int, t0: float, t1: float) -> list[float]:
    if n <= 0:
        return []
    step = max(0.0, t1 - t0) / n
    return [t0 + i * step for i in range(n)]


def line_times(specs: list, wt: list, speech0: float, speech1: float, nwords: int) -> list[tuple[float, float]]:
    """بداية كلّ سطرٍ ونهايته من أزمنة كلماته المنطوقة، وإلا فبالتوزيع على الكلام."""
    if specs and all(c.get('spoken') for c in specs) and len(wt) == nwords:
        return [(wt[c['idx'][0]][1], wt[c['idx'][-1]][2]) for c in specs]
    ts = spread(len(specs), speech0, speech1)
    return [(t, (ts[i + 1] if i + 1 < len(ts) else speech1)) for i, t in enumerate(ts)]


def kt_els(proj: str, kt: dict, specs: list, wt: list, span: float, nwords: int) -> list:
    style = kt.get('style', 'lower')
    speech0 = wt[0][1] if wt else 0.2
    speech1 = wt[-1][2] if wt else max(0.4, span - 0.3)
    lines = [c for c in specs if c['role'] in ('line', 'item')]
    src = next((c for c in specs if c['role'] == 'src'), None)
    els: list = []
    if style == 'list':
        imgs = [(c, card(proj, c['key'])) for c in lines]
        imgs = [(c, fit(im, 1100, 92)) for c, im in imgs if im is not None]
        if not imgs:
            return []
        keep = int(kt.get('keep', 0))
        lh, top = 110, (300 if len(imgs) > 2 else 380)
        ts = [0.0] * min(keep, len(imgs)) + spread(len(imgs) - keep, speech0, speech1 * 0.9)
        for i, (c, im) in enumerate(imgs):
            els.append(El(im, W - 80 - im.width, top + i * lh, ts[i], 'none' if ts[i] == 0.0 and i < keep else 'slide', 0.3, z=2))
        return els
    if style == 'poem':
        mid = (speech0 + speech1) / 2
        for c, (cx, t0, t1) in zip(lines[:2], ((1440, speech0, mid), (480, mid, speech1))):
            im = card(proj, c['key'])
            if im is None:
                continue
            im = fit(im, 840, 130)
            els.append(El(im, cx - im.width / 2, 470 - im.height / 2, t0, 'wipe', max(0.4, t1 - t0) * 0.9, z=2))
        if els and src and card(proj, src['key']) is not None:
            im = fit(card(proj, src['key']), 900, 56)
            els.append(El(im, W / 2 - im.width / 2, 600, speech0, 'fade', 0.4, z=2))
        return [dim_el(0.55)] + els if els else []
    times = line_times(lines, wt, speech0, speech1, nwords)
    pairs = [(c, card(proj, c['key']), tt) for c, tt in zip(lines, times)]
    pairs = [(c, im, tt) for c, im, tt in pairs if im is not None]
    if not pairs:
        return []
    if style == 'letter':
        bg = card(proj, 'letter_bg')
        n = len(pairs)
        lh = 112
        bw = 1480
        bh = min(980, n * lh + 190)
        top = (H - bh) / 2
        if bg is not None:
            els += [dim_el(0.35), El(bg.resize((bw, int(bh)), Image.LANCZOS), (W - bw) / 2, top, 0.0, 'fade', 0.3, z=1)]
        else:
            els.append(dim_el(0.45))
        for i, (c, im, (t0, t1)) in enumerate(pairs):
            im = fit(im, bw - 220, 92)
            els.append(El(im, W / 2 - im.width / 2, top + 95 + i * lh, t0, 'wipe', max(0.3, min(3.0, t1 - t0)), z=2))
        if src and card(proj, src['key']) is not None:
            im = fit(card(proj, src['key']), 640, 50)
            els.append(El(im, (W - bw) / 2 + 70, top + bh - 75, 0.0, 'fade', 0.3, z=2))
        return els
    if style in ('center', 'quote'):
        maxw, maxh, lh = (1600, 128, 152) if style == 'center' else (1500, 116, 140)
        n = len(pairs)
        top = H / 2 - n * lh / 2 - (30 if src else 0)
        els.append(dim_el(0.55 if style == 'center' else 0.6))
        for i, (c, im, (t0, t1)) in enumerate(pairs):
            im = fit(im, maxw, maxh)
            els.append(El(im, W / 2 - im.width / 2, top + i * lh + (lh - im.height) / 2, t0, 'wipe', max(0.3, min(2.6, t1 - t0)), z=2))
        if src and card(proj, src['key']) is not None:
            im = fit(card(proj, src['key']), 900, 56)
            els.append(El(im, W / 2 - im.width / 2, top + n * lh + 14, speech0, 'fade', 0.4, z=2))
        return els
    # lower
    n = len(pairs)
    lh = 100
    els.append(band_el(640))
    for i, (c, im, (t0, t1)) in enumerate(pairs):
        im = fit(im, 1640, 84)
        els.append(El(im, W / 2 - im.width / 2, H - 70 - (n - i) * lh + (lh - im.height) / 2, t0, 'wipe', max(0.3, min(2.4, t1 - t0)), z=2))
    return els


def slam_els(proj: str, spec: dict, t: float, top: bool = False) -> list:
    """top: الضربة أعلى الشاشة وأصغر قليلاً حين تشاركها بطاقاتُ صورٍ في اللقطة نفسها (لا تغطّيها)."""
    im = card(proj, spec['key'])
    if im is None:
        return []
    im = fit(im, 1300, 300) if top else fit(im, 1560, 420)
    y = 40 if top else H / 2 - im.height / 2
    return [dim_el(0.38, t, 0.15), El(im, W / 2 - im.width / 2, y, t, 'slam', 0.24, z=3)]


def name_els(proj: str, spec: dict, t: float) -> list:
    im = card(proj, spec['key'])
    if im is None:
        return []
    im = fit(im, 860, 190)
    return [El(im, W - 90 - im.width, H - 120 - im.height, t, 'slide', 0.35, z=2)]


def date_els(proj: str, spec: dict) -> list:
    im = card(proj, spec['key'])
    if im is None:
        return []
    im = fit(im, 680, 160)
    return [El(im, W - 46 - im.width, 200, 0.25, 'wipe', 0.9, z=2)]       # تحت شعار القناة (أعلى اليمين 46–166)


def label_els(proj: str, specs: list, wt: list) -> list:
    els = []
    for c in specs:
        im = card(proj, c['key'])
        if im is None:
            continue
        im = fit(im, 640, 78)
        t = find_word(wt, c.get('word'), 0.0) if c.get('word') else 0.0
        els.append(El(im, c['x'] - im.width / 2, c['y'] - im.height / 2, t, 'zoom' if c.get('word') else 'none', 0.25, z=2))
    return els


def thumb_els(proj: str, items: list, specs: list, wt: list, span: float, low: bool = False) -> list:
    """صورٌ مصغّرة من كوديكس في إطارٍ أبيض (قصٌّ وتحجيم)، وتحت كلٍّ بطاقةُ اسمها من كوديكس.
    low: البطاقات أسفل الوسط لتفسح أعلى الشاشة لضربةٍ مكتوبة في اللقطة نفسها."""
    n = len(items)
    cw, ch_ = (440, 248) if n <= 3 else (380, 214)
    gap = 40
    total = n * cw + (n - 1) * gap
    t_first = min([find_word(wt, c.get('word'), 0.3) for c in items] or [0.3])
    els = [dim_el(0.5, t_first, 0.3)]
    labs = {c['n']: c for c in specs}
    for i, c in enumerate(items):
        src = None
        for d in ('images', 'img'):
            for e in ('jpg', 'png'):
                p = os.path.join(proj, d, '%s.%s' % (c['img'], e))
                if os.path.exists(p): src = p; break
            if src: break
        x = (W + total) / 2 - (i + 1) * cw - i * gap          # البطاقة الأولى يميناً
        y = H / 2 - ch_ / 2 + (110 if low else -40)
        t = find_word(wt, c.get('word'), 0.3 + i * 0.6)
        if src:
            im = Image.open(src).convert('RGB')
            sc = max(cw / im.width, ch_ / im.height)
            im = im.resize((int(im.width * sc) + 1, int(im.height * sc) + 1), Image.LANCZOS)
            im = im.crop(((im.width - cw) // 2, (im.height - ch_) // 2, (im.width - cw) // 2 + cw, (im.height - ch_) // 2 + ch_))
            fr = Image.new('RGBA', (cw + 12, ch_ + 12), (255, 255, 255, 255)); fr.paste(im, (6, 6))
            els.append(El(fr, x - 6, y - 6, t, 'slide', 0.35, z=2))
        lab = labs.get(i)
        im2 = card(proj, lab['key']) if lab else None
        if im2 is not None:
            im2 = fit(im2, cw, 62)
            els.append(El(im2, x + cw / 2 - im2.width / 2, y + ch_ + 16, t + 0.12, 'rise', 0.25, z=2))
    return els


def chapter_els(proj: str, spec: dict, span: float) -> list:
    im = card(proj, spec['key'])
    if im is None:
        return []
    im = fit(im, 1400, 110)
    t1 = min(span - 0.35, 3.6)
    return [El(im, W / 2 - im.width / 2, 60, 0.2, 'wipe', 0.9, t1=t1, z=2)]


# ══════════ المؤثّرات على المقطع نفسه ══════════
def base_filters(shakes: list[float], punches: list[float], span: float) -> str:
    f = []
    if punches:
        z = '+'.join("if(between(in_time,%.3f,%.3f),0.11*exp(-7*(in_time-%.3f)),0)" % (t, t + 0.6, t) for t in punches)
        f.append("zoompan=z='1+%s':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=%dx%d:fps=%d" % (z, W, H, FPS))
    if shakes:
        sx = '+'.join("if(between(t,%.3f,%.3f),26*sin(75*(t-%.3f))*exp(-7*(t-%.3f)),0)" % (t, t + 0.55, t, t) for t in shakes)
        sy = '+'.join("if(between(t,%.3f,%.3f),18*cos(90*(t-%.3f))*exp(-7*(t-%.3f)),0)" % (t, t + 0.55, t, t) for t in shakes)
        f.append("crop=w=iw-64:h=ih-64:x='32+%s':y='32+%s',scale=%d:%d" % (sx, sy, W, H))
    return ','.join(f)


def shot_els(proj: str, s: dict, wt: list, span: float, texts: dict | None = None) -> tuple[list, list, list, list]:
    """عناصر العرض للّقطة وأزمنة الارتجاج والتكبير والومضات — مشتركةٌ بين المونتاج والمعاينة الثابتة.
    texts: نصوص الكتل (لتقسيم أسطر الكلام كما قسّمها tools/cards.py فتُعرف أزمنتها)."""
    els, shakes, punches, flashes = [], [], [], []
    specs = cards.shot_cards(s, texts or {}, s.get('_chapter'))
    by = lambda *roles: [c for c in specs if c['role'] in roles]
    nwords = len(cards.shot_words(s, texts or {})[0])
    both = bool(s.get('slam') and s.get('cards'))   # K09f في الأرك: الضربة كانت تغطّي البطاقات
    if s.get('flash'):
        flashes.append(0.0)
    if s.get('kt'):
        els += kt_els(proj, s['kt'], by('line', 'item', 'src', 'bg'), wt, span, nwords)
    if s.get('date') and by('date'):
        els += date_els(proj, by('date')[0])
    if s.get('labels'):
        els += label_els(proj, by('label'), wt)
    if s.get('cards'):
        els += thumb_els(proj, s['cards'], by('clabel'), wt, span, low=both)
    if s.get('name') and by('name'):
        els += name_els(proj, by('name')[0], find_word(wt, s['name'].get('word'), 0.3))
    if s.get('slam') and by('slam'):
        sl = s['slam']
        t = float(sl['at']) if 'at' in sl else find_word(wt, sl.get('word'), 0.25)
        t = min(t, max(0.0, span - 0.5))
        els += slam_els(proj, by('slam')[0], t, top=both); shakes.append(t); flashes.append(t)
    if s.get('_chapter') and by('chapter'):
        els += chapter_els(proj, by('chapter')[0], span)
    for w in s.get('shake', []) or []:
        shakes.append(min(find_word(wt, w, 0.2), max(0.0, span - 0.4)))
    for w in s.get('punch', []) or []:
        punches.append(min(find_word(wt, w, 0.2), max(0.0, span - 0.4)))
    return els, shakes, punches, flashes


def apply(proj: str, s: dict, seg: str, span: float, texts: dict, durs: dict, gap: float, work: str, enc: list) -> str:
    """يركّب مؤثّرات العرض على مقطع اللقطة ويعيد مسار الناتج (يُستأنف إن وُجد بالمدّة نفسها)."""
    res = seg[:-4] + '_kin.mp4'
    if os.path.exists(res) and abs(_dur(res) - span) < 0.08:
        return res
    wt = shot_word_times(proj, s, texts, durs, gap)
    els, shakes, punches, flashes = shot_els(proj, s, wt, span, texts)
    name = os.path.basename(seg)[:-4]
    lst = render_track(els, span, work, name)
    cmd = [envpaths.FF, '-v', 'error', '-y', '-i', seg]
    chain, last = [], '[0:v]'
    bf = base_filters(sorted(set(round(x, 2) for x in shakes)), sorted(set(round(x, 2) for x in punches)), span)
    if bf:
        chain.append('%s%s[b0]' % (last, bf)); last = '[b0]'
    k = 0
    if lst:
        k += 1; cmd += ['-f', 'concat', '-safe', '0', '-i', lst]
        chain.append('[%d:v]format=rgba[ov]' % k)
        chain.append('%s[ov]overlay=0:0:eof_action=pass:format=auto[b1]' % last); last = '[b1]'
    for i, t in enumerate(sorted(set(round(x, 2) for x in flashes))):
        k += 1; cmd += ['-f', 'lavfi', '-i', 'color=c=white:s=%dx%d:r=%d:d=%.3f' % (W, H, FPS, span)]
        chain.append('[%d:v]format=rgba,colorchannelmixer=aa=0.85,fade=t=in:st=%.3f:d=0.04:alpha=1,fade=t=out:st=%.3f:d=0.22:alpha=1[w%d]'
                     % (k, max(0.0, t - 0.02), t + 0.04, i))
        chain.append('%s[w%d]overlay=0:0:format=auto[f%d]' % (last, i, i)); last = '[f%d]' % i
    if not chain:
        return seg
    chain.append('%sformat=yuv420p[v]' % last)
    sp.run(cmd + ['-filter_complex', ';'.join(chain), '-map', '[v]', '-t', '%.3f' % span] + enc + [res], check=True)
    return res


def _dur(f: str) -> float:
    o = sp.run([envpaths.FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', f], capture_output=True, text=True)
    try:
        return float(o.stdout.strip())
    except ValueError:
        return 0.0


def reuse_clip(proj: str, s: dict) -> str | None:
    """مقطعٌ حيّ مدفوعٌ للقطةٍ أخرى (حقل clip) يُقصّ من clip_ss ويُستعمل بلا طلبٍ جديد لـfal."""
    src = os.path.join(proj, 'clips', '%s.mp4' % s['clip'])
    if not os.path.exists(src):
        return None
    out = os.path.join(proj, 'clips', '%s_reuse.mp4' % s['id'])
    if not os.path.exists(out):
        sp.run([envpaths.FF, '-v', 'error', '-y', '-ss', '%.3f' % float(s.get('clip_ss', 0.0)), '-i', src, '-an',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', out], check=True)
    return out
