# -*- coding: utf-8 -*-
"""الكتابة المتحرّكة بأسلوب العروض التقديمية — أمر المالك 2026-10-04 (فيلم «الأرك»).

نصُّ الأمر: «حاول تعويض التحريك بأي شيء… استعمل طرقاً مبتكرة، مثلاً أحياناً تحريكٌ للكتابة والصور مثل نوعية ما
يُستعمل في العروض التقديمية (البوربوينت)، كأنّ الكتابة تُكتب أثناء الإلقاء، وغيرها من الأساليب التي لم نجربها».

⛔ نصٌّ وتنسيقٌ مركَّبان فوق صور كوديكس وقصٌّ لها فقط — لا يُرسم به محتوى صورة (أمر المالك 2026-09-29).
كلُّ ما هنا مجانيّ (PIL + ffmpeg على عدّاء GitHub)، ويُستدعى من tools/mont_hybrid.py لكلّ لقطةٍ فيها حقلٌ مما يلي:

  kt     كتابةٌ تظهر كلمةً كلمةً **لحظةَ نطقها**: lower (شريطٌ سفليّ) · center (وسطٌ مع تعتيم) · quote (قولٌ مأثور)
         · letter (رسالةٌ تُكتب على ورقة) · poem (شطران متقابلان) · list (قائمةٌ تظهر بنداً بنداً)
  slam   رقمٌ أو كلمةٌ تُضرب على الشاشة بتكبيرٍ وارتجاجٍ وومضة عند كلمتها
  cards  بطاقاتُ صورٍ تطير إلى الشاشة واحدةً بعد أخرى عند كلماتها (عرضٌ تقديميّ)
  labels تسمياتٌ على مواضعها من الصورة (خريطة التشكيل)
  name   بطاقةُ اسمٍ سفلية (قائدٌ، حصن، مدينة) · date ختمٌ زمنيّ يُكتب حرفاً حرفاً
  flash  ومضةٌ بيضاء في أوّل اللقطة · shake ارتجاجٌ عند كلمات · punch تكبيرٌ خاطف عند كلمات
  _chapter عنوان الفصل يُكتب أعلى أوّل لقطةٍ فيه (يضعه mont_hybrid من sections.json)

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
import envpaths  # noqa: E402
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont  # noqa: E402

W, H, FPS = 1920, 1080, 25
TEMPO = 1.05                      # mont_hybrid يسرّع مسار الصوت كلّه 1.05
GOLD, WHITE, CREAM, INK = (247, 199, 74, 255), (255, 255, 255, 255), (245, 236, 214, 255), (52, 34, 16, 255)
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KUFI = os.path.join(REPO, 'assets', 'fonts', 'NotoKufiArabic[wght].ttf')
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


# ══════════ الخطوط ══════════
_FONTS: dict = {}


def kufi(size: int, weight: str = 'Bold'):
    """نوتو كوفي (رخصة OFL في assets/fonts) بمحرّك BASIC — يمنع القلب المزدوج (envpaths)."""
    key = ('k', size, weight)
    if key not in _FONTS:
        if os.path.exists(KUFI):
            f = ImageFont.truetype(KUFI, size, layout_engine=ImageFont.Layout.BASIC)
            try:
                f.set_variation_by_name(weight)
            except Exception:
                pass
        else:                                   # بديلٌ لا يُسقط المونتاج
            f = envpaths.arfont(size)
        _FONTS[key] = f
    return _FONTS[key]


def naskh(size: int):
    key = ('a', size)
    if key not in _FONTS:
        _FONTS[key] = envpaths.arfont(size, path=envpaths.font(bold=True))
    return _FONTS[key]


# ══════════ رسم النصّ ══════════
_PROBE = ImageDraw.Draw(Image.new('RGBA', (8, 8)))


def text_w(t: str, f) -> float:
    return _PROBE.textlength(envpaths.ar(t), font=f)


def sprite(t: str, f, fill=WHITE, stroke: int = 0, stroke_fill=(0, 0, 0, 255), shadow: int = 0, pad: int = 0) -> Image.Image:
    """صورةٌ شفّافة لنصٍّ واحد (كلمة أو سطر)، بحدٍّ أسود وظلٍّ ناعم اختياريّين.
    ⭐ خطّ الصعود (ascender) على ارتفاع pad دائماً، فتصطفّ كلماتُ السطر الواحد على خطٍّ واحد مهما اختلفت حروفها."""
    s = envpaths.ar(t)
    l, _, r, _ = _PROBE.textbbox((0, 0), s, font=f, anchor='la', stroke_width=stroke)
    asc, desc = f.getmetrics()
    pad = pad or (stroke + shadow * 2 + 6)
    w, h = int(r - l + 2 * pad), int(asc + desc + 2 * pad + stroke)
    im = Image.new('RGBA', (max(1, w), max(1, h)), (0, 0, 0, 0))
    org = (pad - l, pad)
    if shadow:
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((org[0] + 3, org[1] + 4), s, font=f, anchor='la', fill=(0, 0, 0, 170),
                                stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(shadow)))
    ImageDraw.Draw(im).text(org, s, font=f, anchor='la', fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return im


def wrap(words: list[str], f, maxw: float) -> list[list[int]]:
    """يلفّ الكلمات (بترتيبها المنطقيّ) أسطراً لا يتجاوز عرضها maxw — يعيد أرقام الكلمات في كلّ سطر."""
    sp_w = text_w(' ', f)
    lines, cur, cw = [], [], 0.0
    for i, w in enumerate(words):
        ww = text_w(w, f)
        if cur and cw + sp_w + ww > maxw:
            lines.append(cur); cur, cw = [], 0.0
        cw += (sp_w if cur else 0) + ww; cur.append(i)
    return lines + ([cur] if cur else [])


def layout_rtl(words: list[str], f, maxw: float, cx: float, top: float, lh: float, align: str = 'center'):
    """مواضعُ الكلمات (يمين ← يسار) في أسطرٍ ملفوفة: [(رقم الكلمة، x، y)] و(عدد الأسطر)."""
    sp_w = text_w(' ', f)
    out, lines = [], wrap(words, f, maxw)
    for li, idx in enumerate(lines):
        widths = [text_w(words[i], f) for i in idx]
        tw = sum(widths) + sp_w * (len(idx) - 1)
        right = cx + tw / 2 if align == 'center' else cx        # align='right' ⇒ cx حافّة اليمين
        x = right
        for i, wd in zip(idx, widths):
            x -= wd
            out.append((i, x, top + li * lh))
            x -= sp_w
    return out, len(lines)


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


# ══════════ مكوّنات العرض ══════════
def dim_el(alpha: float, t0: float = 0.0, d: float = 0.3, z: int = 0):
    return El(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * alpha))), 0, 0, t0, 'fade', d, z=z)


def band_el(y0: int, t0=0.0):
    """تدرّجٌ معتمٌ أسفل الإطار لقراءة الكتابة."""
    g = Image.new('L', (1, H - y0))
    for i in range(H - y0):
        g.putpixel((0, i), int(205 * (i / (H - y0)) ** 0.8))
    im = Image.new('RGBA', (W, H - y0), (0, 0, 0, 255)); im.putalpha(g.resize((W, H - y0)))
    return El(im, 0, y0, t0, 'fade', 0.3, z=0)


def panel(w, h, fill=(10, 10, 14, 175), radius=26, border=None):
    im = Image.new('RGBA', (int(w), int(h)), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, int(w) - 1, int(h) - 1], radius=radius, fill=fill,
                                         outline=border, width=3 if border else 0)
    return im


def word_els(words, times, f, maxw, cx, top, lh, hl=(), anim='rise', fill=WHITE, stroke=4, shadow=6, align='center', z=2, ad=0.18):
    hlb = {bare(h) for h in hl}
    pos, n = layout_rtl(words, f, maxw, cx, top, lh, align)
    els = []
    for i, x, y in pos:
        col = GOLD if bare(words[i]) in hlb else fill
        sp_ = sprite(words[i], f, col, stroke=stroke, shadow=shadow)
        pad = stroke + shadow * 2 + 6
        els.append(El(sp_, x - pad, y - pad, times[i], anim, ad, z=z))
    return els, n


def spread(n: int, t0: float, t1: float) -> list[float]:
    if n <= 0:
        return []
    step = max(0.0, t1 - t0) / n
    return [t0 + i * step for i in range(n)]


def kt_els(kt: dict, wt: list, span: float) -> list:
    style = kt.get('style', 'lower')
    speech0 = wt[0][1] if wt else 0.2
    speech1 = wt[-1][2] if wt else max(0.4, span - 0.3)
    hl = kt.get('hl', [])
    text = kt.get('text')
    if style == 'list':
        items = text if isinstance(text, list) else [text or '']
        keep = int(kt.get('keep', 0))
        f = kufi(54, 'Bold'); lh = 96
        maxw = max(text_w('• ' + it, f) for it in items) + 90
        top = 300 if len(items) > 2 else 380
        els = [El(panel(maxw, lh * len(items) + 60), W - 80 - maxw, top - 30, 0.0, 'fade', 0.25, z=1)]
        ts = [0.0] * min(keep, len(items)) + spread(len(items) - keep, speech0, speech1 * 0.9)
        for i, it in enumerate(items):
            sp_ = sprite('• ' + it, f, GOLD if i == len(items) - 1 and i >= keep else WHITE, stroke=3, shadow=4)
            els.append(El(sp_, W - 80 - 40 - sp_.width, top + i * lh, ts[i], 'none' if ts[i] == 0.0 and i < keep else 'slide', 0.3, z=2))
        return els
    if style == 'poem':
        h1, h2 = (text + ['', ''])[:2] if isinstance(text, list) else (text or '', '')
        size = 78
        while size > 44 and max(text_w(h1, naskh(size)), text_w(h2, naskh(size))) > 840: size -= 4
        f = naskh(size)
        els = [dim_el(0.55)]
        mid = (speech0 + speech1) / 2
        for h, cx, t0, t1 in ((h1, 1440, speech0, mid), (h2, 480, mid, speech1)):
            sp_ = sprite(h, f, GOLD, stroke=3, shadow=6)
            els.append(El(sp_, cx - sp_.width / 2, 470 - sp_.height / 2, t0, 'wipe', max(0.4, t1 - t0) * 0.9, z=2))
        if kt.get('src'):
            s2 = sprite('— ' + kt['src'], kufi(36, 'Medium'), WHITE, stroke=2, shadow=3)
            els.append(El(s2, W / 2 - s2.width / 2, 600, speech0, 'fade', 0.4, z=2))
        return els
    if style == 'letter':
        words = (text if isinstance(text, str) else None) or ' '.join(w.rstrip('.،,:؛') for w, _, _ in wt)
        words = words.split()
        f = naskh(78)
        lh = 122
        pos, n = layout_rtl(words, f, 1240, W / 2, 0, lh)
        cw = min(1400, max(760, (max(text_w(' '.join(words[i] for i in ln), f) for ln in wrap(words, f, 1240)) if words else 600) + 160))
        ph = n * lh + 150
        top = (H - ph) / 2
        card = panel(cw, ph, fill=(239, 227, 200, 236), radius=18, border=(150, 118, 70, 255))
        els = [dim_el(0.35), El(card, (W - cw) / 2, top, 0.0, 'fade', 0.25, z=1)]
        times = [a for _, a, _ in wt] if not isinstance(text, str) and len(wt) == len(words) else spread(len(words), speech0, speech1)
        ends = times[1:] + [speech1]
        hlb = {bare(h) for h in hl}
        for (i, x, y) in pos:
            sp_ = sprite(words[i], f, (150, 30, 20, 255) if bare(words[i]) in hlb else INK, stroke=0, shadow=0, pad=8)
            els.append(El(sp_, x - 8, top + 60 + y - 8, times[i], 'wipe', max(0.15, min(0.55, ends[i] - times[i])), z=2))
        if kt.get('src'):
            s2 = sprite('— ' + kt['src'], kufi(32, 'Medium'), (120, 86, 40, 255), pad=6)
            els.append(El(s2, (W - cw) / 2 + 40, top + ph - 62, 0.0, 'fade', 0.3, z=2))
        return els
    # lower · center · quote: كلمةٌ كلمةٌ لحظةَ نطقها
    if isinstance(text, str):
        words = text.split(); times = spread(len(words), speech0, speech1)
    else:
        words = [w.rstrip('.،,:؛') for w, _, _ in wt]; times = [a for _, a, _ in wt]
    if not words:
        return []
    if style == 'center':
        size = 96
        while size > 56 and len(wrap(words, kufi(size), 1500)) > 3: size -= 6
        f = kufi(size, 'Bold'); lh = size * 1.55
        n = len(wrap(words, f, 1500))
        els, _ = word_els(words, times, f, 1500, W / 2, H / 2 - n * lh / 2, lh, hl, 'zoom', stroke=5, shadow=8)
        return [dim_el(0.55)] + els
    if style == 'quote':
        size = 84
        while size > 50 and len(wrap(words, naskh(size), 1450)) > 3: size -= 6
        f = naskh(size); lh = size * 1.6
        n = len(wrap(words, f, 1450))
        top = H / 2 - n * lh / 2 - 30
        els, _ = word_els(words, times, f, 1450, W / 2, top, lh, hl, 'fade', fill=CREAM, stroke=3, shadow=7, ad=0.25)
        out = [dim_el(0.6)] + els
        if kt.get('src'):
            s2 = sprite('— ' + kt['src'], kufi(38, 'Medium'), GOLD, stroke=2, shadow=3)
            out.append(El(s2, W / 2 - s2.width / 2, top + n * lh + 20, speech0, 'fade', 0.4, z=2))
        return out
    # lower
    size = 60
    while size > 42 and len(wrap(words, kufi(size), 1640)) > 2: size -= 4
    f = kufi(size, 'Bold'); lh = size * 1.6
    n = len(wrap(words, f, 1640))
    els, _ = word_els(words, times, f, 1640, W / 2, H - 70 - n * lh, lh, hl, 'rise', stroke=4, shadow=6)
    return [band_el(640)] + els


def slam_els(sl: dict, t: float, span: float, top: bool = False) -> list:
    """top: الضربة أعلى الشاشة وأصغر قليلاً، حين تشاركها بطاقاتُ صورٍ في اللقطة نفسها (لا تغطّيها)."""
    size = 140 if top else 176
    while size > 90 and text_w(sl['text'], kufi(size, 'Black')) > 1700: size -= 8
    big = sprite(sl['text'], kufi(size, 'Black'), sl.get('color') and tuple(sl['color']) or GOLD, stroke=9, shadow=10)
    y = 30 if top else H / 2 - big.height / 2 - (40 if sl.get('sub') else 0)
    els = [dim_el(0.38, t, 0.15), El(big, W / 2 - big.width / 2, y, t, 'slam', 0.24, z=3)]
    if sl.get('sub'):
        sub = sprite(sl['sub'], kufi(58, 'Bold'), WHITE, stroke=4, shadow=5)
        els.append(El(sub, W / 2 - sub.width / 2, y + big.height - 10, min(span - 0.1, t + 0.25), 'rise', 0.25, z=3))
    return els


def name_els(nm: dict, t: float) -> list:
    a = sprite(nm['text'], kufi(64, 'Bold'), WHITE, stroke=3, shadow=5)
    b = sprite(nm['sub'], kufi(38, 'Medium'), GOLD, stroke=2, shadow=4) if nm.get('sub') else None
    w = max(a.width, b.width if b else 0) + 70
    h = a.height + (b.height if b else 0) + 30
    x, y = W - 90 - w, H - 120 - h
    els = [El(panel(w, h, fill=(8, 8, 12, 190), radius=14), x, y, t, 'slide', 0.35, z=1),
           El(panel(10, h, fill=GOLD, radius=4), W - 90 - 10, y, t, 'slide', 0.35, z=2),
           El(a, W - 90 - 40 - a.width, y + 8, t + 0.1, 'wipe', 0.4, z=2)]
    if b:
        els.append(El(b, W - 90 - 40 - b.width, y + 8 + a.height - 8, t + 0.3, 'fade', 0.3, z=2))
    return els


def date_els(dt: dict) -> list:
    a = sprite(dt['text'], kufi(54, 'Bold'), WHITE, stroke=3, shadow=5)
    b = sprite(dt['sub'], kufi(34, 'Medium'), GOLD, stroke=2, shadow=3) if dt.get('sub') else None
    w = max(a.width, b.width if b else 0) + 60
    h = a.height + (b.height if b else 0) + 24
    y0 = 200                                    # تحت شعار القناة (أعلى اليمين 46–166)
    els = [El(panel(w, h, fill=(8, 8, 12, 165), radius=12), W - 46 - w, y0, 0.15, 'fade', 0.25, z=1),
           El(a, W - 46 - 30 - a.width, y0 + 6, 0.25, 'wipe', 0.8, z=2)]
    if b:
        els.append(El(b, W - 46 - 30 - b.width, y0 + 6 + a.height - 6, 0.9, 'wipe', 0.5, z=2))
    return els


def label_els(labels: list, wt: list) -> list:
    els = []
    for lb in labels:
        t = find_word(wt, lb.get('word'), 0.0) if lb.get('word') else 0.0
        s_ = sprite('• ' + lb['text'], kufi(42, 'Bold'), WHITE, stroke=3, shadow=4)
        bg = panel(s_.width + 24, s_.height + 8, fill=(8, 8, 12, 160), radius=12)
        x, y = lb['x'] - s_.width / 2, lb['y'] - s_.height / 2
        anim = 'zoom' if lb.get('word') else 'none'
        els += [El(bg, x - 12, y - 4, t, anim, 0.25, z=1), El(s_, x, y, t, anim, 0.25, z=2)]
    return els


def card_els(proj: str, cards: list, wt: list, span: float, low: bool = False) -> list:
    """low: البطاقات أسفل الوسط لتفسح أعلى الشاشة لضربةٍ مكتوبة في اللقطة نفسها."""
    n = len(cards)
    cw, ch_ = (440, 248) if n <= 3 else (380, 214)
    gap = 40
    total = n * cw + (n - 1) * gap
    t_first = min([find_word(wt, c.get('word'), 0.3) for c in cards] or [0.3])
    els = [dim_el(0.5, t_first, 0.3)]
    for i, c in enumerate(cards):
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
        lab = sprite(c['label'], kufi(40 if n <= 3 else 36, 'Bold'), GOLD, stroke=3, shadow=4)
        els.append(El(lab, x + cw / 2 - lab.width / 2, y + ch_ + 18, t + 0.12, 'rise', 0.25, z=2))
    return els


def chapter_els(title: str, span: float) -> list:
    a = sprite(title, kufi(50, 'Bold'), GOLD, stroke=4, shadow=6)
    t1 = min(span - 0.35, 3.6)
    line = panel(min(a.width + 80, 1500), 5, fill=GOLD, radius=2)
    return [El(a, W / 2 - a.width / 2, 70, 0.2, 'wipe', 0.9, t1=t1, z=2),
            El(line, W / 2 - line.width / 2, 70 + a.height + 4, 0.35, 'wipe', 0.8, t1=t1, z=2)]


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


def shot_els(proj: str, s: dict, wt: list, span: float) -> tuple[list, list, list, list]:
    """عناصر العرض للّقطة وأزمنة الارتجاج والتكبير والومضات — مشتركةٌ بين المونتاج والمعاينة الثابتة."""
    els, shakes, punches, flashes = [], [], [], []
    both = bool(s.get('slam') and s.get('cards'))   # K09f في الأرك: الضربة كانت تغطّي البطاقات
    if s.get('flash'):
        flashes.append(0.0)
    if s.get('kt'):
        els += kt_els(s['kt'], wt, span)
    if s.get('date'):
        els += date_els(s['date'])
    if s.get('labels'):
        els += label_els(s['labels'], wt)
    if s.get('cards'):
        els += card_els(proj, s['cards'], wt, span, low=both)
    if s.get('name'):
        els += name_els(s['name'], find_word(wt, s['name'].get('word'), 0.3))
    if s.get('slam'):
        sl = s['slam']
        t = float(sl['at']) if 'at' in sl else find_word(wt, sl.get('word'), 0.25)
        t = min(t, max(0.0, span - 0.5))
        els += slam_els(sl, t, span, top=both); shakes.append(t); flashes.append(t)
    if s.get('_chapter'):
        els += chapter_els(s['_chapter'], span)
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
    els, shakes, punches, flashes = shot_els(proj, s, wt, span)
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
