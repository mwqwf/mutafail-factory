# -*- coding: utf-8 -*-
"""الكتابة المتحرّكة بأسلوب العروض التقديمية — أمر المالك 2026-10-04 (فيلم «الأرك»).

نصُّ الأمر: «حاول تعويض التحريك بأي شيء… استعمل طرقاً مبتكرة، مثلاً أحياناً تحريكٌ للكتابة والصور مثل نوعية ما
يُستعمل في العروض التقديمية (البوربوينت)، كأنّ الكتابة تُكتب أثناء الإلقاء، وغيرها من الأساليب التي لم نجربها».
ثم في اليوم نفسه: «الصور ممنوعة عليك اتركها لكوديكس… حتى البطاقات المكتوبة اتركها لكوديكس».

⛔ لا يرسم هذا الملفّ حرفاً: كلّ كتابةٍ بطاقةُ PNG شفّافة يصنعها كوديكس (tools/cards.py يحصرها ويُلحقها بالطابور)،
وهنا تُقصّ وتُحجَّم وتُحرَّك فقط. البطاقة الغائبة يُتخطّى عنصرها ولا يُرسم بديلٌ عنها.
يُستدعى من tools/mont_hybrid.py لكلّ لقطةٍ فيها حقلٌ مما يلي:

  kt     كتابةٌ تظهر **كلمةً كلمة لحظةَ نطقها** (الإصدار الثاني): lower · center · quote · letter (تُخطّ بالحبر على رقٍّ
         من كوديكس) · poem (شطران متقابلان) · list (بنودٌ تنزلق بنداً بنداً)
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
from PIL import Image, ImageChops  # noqa: E402

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
# ⭐ الإصدار الثاني (حكم المالك 2026-10-04 على عيّنة الأرك: «الكتابة المتحرّكة أو أثناء الإلقاء لازالت بعيدةً جداً عمّا أطمح إليه…
#    أيّ مبتدئٍ عاديّ باستخدام كاب كات أو بوربوينت يصنع شيئاً أفضل بأضعاف»):
#    • كلُّ كلمةٍ عنصرٌ وحدها — قصاصةٌ من بطاقة كوديكس نفسها في موضعها (word_spans) — تدخل لحظةَ نطقها بحركةٍ مرنةٍ تتجاوز
#      ثم تستقرّ، وتنتفخ قليلاً ما دامت تُنطق، والكلمة المبرَزة (hl) أكبر دخولاً وتمرّ عليها لمعةُ ضوء.
#    • الرسالة تُخطّ بالحبر كلمةً كلمة، وشطرا البيت يصعدان كلمةً كلمة، والمجموعة كلّها تقترب ببطءٍ ما دامت على الشاشة، ثم تخرج
#      قبل الانتقال (لا تُقطع مع الصورة).
#    • الضربة بأثرٍ خلفها وتوهّجٍ ولمعة، والاسم ينزلق بتجاوزٍ ويخرج، والختم يُختم بدورانٍ، والصور المصغّرة تُرمى ثم تستقرّ مائلة.
#    • التصيير 25 إطاراً/ث كاملةً على إطارات المقطع نفسه (cv2: تحويلٌ تآلفيّ بمواضع كسرية فلا رعشة، ومزجٌ بألفا مضروبة مسبقاً)
#      بدل صورٍ لا تُكتب إلا عند التغيّر — فالحركة المستمرّة ممكنةٌ والارتجاجُ يهزّ الكتابة مع الصورة.
#    ⛔ لا يُرسم حرف: كلُّ ما يظهر قصٌّ وتحجيمٌ وتحريكٌ لبطاقات كوديكس، ومؤثّراتٌ عليها (توهّجٌ من ألفاها، لمعة، تعتيم).
def ease_out(p): return 1 - (1 - p) ** 3


def ease_back(p, s=1.9):
    p -= 1
    return p * p * ((s + 1) * p + s) + 1


def _cl(p):
    return 0.0 if p < 0 else (1.0 if p > 1 else p)


def _smooth(p):
    p = _cl(p)
    return p * p * (3 - 2 * p)


SWEEP_D = 0.65                     # مدّة لمعة الضوء على البطاقة


class El:
    """عنصرٌ يدخل عند t0 بحركة anim مدّتها d، ويخرج اختيارياً عند t1 بحركة ex مدّتها od.
    grow/piv/g0: تقريبٌ بطيءٌ مستمرّ للمجموعة حول محورها منذ g0 · act=(بداية، نهاية) نطق الكلمة: انتفاخٌ بقدر actk أثناءه ·
    sweep: زمن لمعة الضوء · glow: قوّة توهّجٍ من ألفا البطاقة نفسها خلفها · rot: زاوية الاستقرار · amp: سعة الدخول.
    kind: img (بطاقة) · dim (تعتيمٌ للإطار كلّه بقدر lvl) · band (تدرّجٌ معتمٌ أسفل الإطار من y)."""
    def __init__(self, img, x, y, t0=0.0, anim='fade', d=0.2, t1=None, z=1, ex='fade', od=0.3, grow=0.0, piv=None, g0=None,
                 act=None, actk=0.06, sweep=None, glow=0.0, rot=0.0, amp=1.0, kind='img', lvl=1.0):
        self.img, self.x, self.y, self.t0, self.anim, self.d, self.t1, self.z = img, x, y, t0, anim, d, t1, z
        self.ex, self.od, self.grow, self.piv, self.g0 = ex, od, grow, piv, g0
        self.act, self.actk, self.sweep, self.glow, self.rot, self.amp = act, actk, sweep, glow, rot, amp
        self.kind, self.lvl = kind, lvl
        self._arr = self._glw = None

    def frame_times(self):
        """لحظات التغيّر (للمعاينة الثابتة)."""
        ts = [self.t0]
        if self.anim != 'none' and self.d > 0:
            ts += [self.t0 + k / FPS for k in range(1, int(math.ceil(self.d * FPS)) + 1)]
        if self.t1 is not None:
            ts += [self.t1 + k / FPS for k in range(0, int(self.od * FPS) + 1)]
        return ts

    def arr(self):
        """البطاقة مصفوفةً RGBA بألفا مضروبةٍ مسبقاً (uint8) — فلا تظهر حوافّ داكنة عند التحجيم بمواضع كسرية."""
        if self._arr is None:
            import numpy as np
            a = np.asarray(self.img.convert('RGBA')).astype(np.float32)
            a[..., :3] *= a[..., 3:4] / 255.0
            self._arr = a.round().astype(np.uint8)
        return self._arr

    def glw(self):
        if self._glw is None:
            import cv2
            import numpy as np
            a = self.arr()
            pad = 40
            big = np.zeros((a.shape[0] + 2 * pad, a.shape[1] + 2 * pad, 4), np.uint8)
            big[pad:-pad, pad:-pad] = a
            g = cv2.GaussianBlur(big, (0, 0), 16).astype(np.float32) * 1.6
            self._glw = (np.clip(g, 0, 255).astype(np.uint8), pad)
        return self._glw

    def st(self, t):
        """الحالة عند t: (ألفا، إزاحة س، إزاحة ص، تحجيم، دوران، كشف، تقريب المجموعة) أو None قبل الدخول."""
        if t + 1e-6 < self.t0:
            return None
        p = 1.0 if self.anim == 'none' or self.d <= 0 else _cl((t - self.t0) / self.d)
        a, ox, oy, k, r, rev, m = 1.0, 0.0, 0.0, 1.0, self.rot, 1.0, self.amp
        an = self.anim
        if an == 'fade':
            a = ease_out(p)
        elif an == 'rise':
            a = ease_out(p); oy = 34 * m * (1 - ease_out(p))
        elif an == 'pop':                       # تكبيرٌ من الصغر بتجاوزٍ ثم استقرار
            a = _cl(p * 3); k = 1 - 0.45 * m + 0.45 * m * ease_back(p, 2.6); oy = 16 * (1 - ease_out(p))
        elif an == 'drop':                      # تصغيرٌ من الكبر إلى موضعها بارتدادٍ خفيف
            a = _cl(p * 2.6); k = 1 + 0.62 * m * (1 - ease_back(p, 1.7))
        elif an == 'zoom':
            a = _cl(p * 3); k = 1 + 0.35 * m * (1 - ease_out(p))
        elif an == 'settle':                    # خلفيةٌ تستقرّ (الرقّ)
            a = ease_out(p); k = 1 + 0.06 * (1 - ease_out(p))
        elif an == 'slam':
            a = _cl(p * 3); k = max(0.6, 2.3 - 1.3 * ease_back(p))
        elif an == 'slide':                     # من اليمين (اتجاه القراءة) بتجاوزٍ قليل
            a = _cl(p * 2); ox = 420 * (1 - ease_back(p, 1.3))
        elif an == 'slidel':
            a = _cl(p * 2); ox = -420 * (1 - ease_back(p, 1.3))
        elif an == 'wipe':                      # تُخطّ من اليمين بحافّةٍ ناعمة
            rev = ease_out(p); ox = 14 * (1 - ease_out(p))
        elif an == 'ink':                       # حبرٌ يجري على الكلمة بطول نطقها
            rev = _smooth(p) * 0.85 + p * 0.15
        elif an == 'stamp':                     # ختمٌ يهبط دائراً ثم يستقرّ
            a = _cl(p * 4); k = 1.9 - 0.9 * ease_back(p, 2.2); r += -9 * (1 - ease_out(p))
        elif an == 'toss':                      # صورةٌ تُرمى من أسفل يمين ثم تستقرّ مائلة
            a = _cl(p * 3); ox = 150 * (1 - ease_out(p)); oy = 240 * (1 - ease_back(p, 1.2)); r += 11 * (1 - ease_out(p))
        if self.t1 is not None and t >= self.t1:
            q = _cl((t - self.t1) / max(0.04, self.od)); e = q * q
            if self.ex == 'up':
                oy -= 46 * e; a *= 1 - q
            elif self.ex == 'shrink':
                k *= 1 - 0.14 * e; a *= 1 - q
            elif self.ex == 'slide':
                ox += 560 * e; a *= 1 - e
            else:
                a *= 1 - q
        if self.act:                            # الكلمة ما دامت تُنطق
            ws, we = self.act
            k *= 1 + self.actk * _cl((t - ws) / 0.08) * (1 - _cl((t - we) / 0.2))
        g = 1.0
        if self.grow:
            g = 1 + self.grow * max(0.0, t - (self.t0 if self.g0 is None else self.g0))
        return a, ox, oy, k, r, rev, g


def _reveal(arr, rev):
    """كشفٌ من اليمين إلى اليسار بحافّةٍ ناعمة (على ألفا مضروبةٍ مسبقاً تُضرب القنوات كلّها)."""
    import numpy as np
    w = arr.shape[1]
    e = max(18.0, 0.10 * w)
    u = np.arange(w, dtype=np.float32)
    m = np.clip((u - (w + e) * (1 - rev) + e) / e, 0, 1)
    return (arr * m[None, :, None]).astype(np.uint8)


def _sweep(arr, qq):
    """لمعة ضوءٍ مائلة تعبر البطاقة من اليمين إلى اليسار (تُضاء الحروف وحدها)."""
    import numpy as np
    h, w = arr.shape[:2]
    bw = max(40.0, 0.16 * w)
    pos = (1 - qq) * (w + 2 * bw) - bw
    u = np.arange(w, dtype=np.float32)[None, :]
    v = np.arange(h, dtype=np.float32)[:, None]
    band = np.clip(1 - np.abs(u - pos + 0.45 * (v - h / 2)) / bw, 0, 1) ** 2 * 0.65
    out = arr.astype(np.float32)
    out[..., :3] += (out[..., 3:4] - out[..., :3]) * band[..., None]
    return out.astype(np.uint8)


def _place(e, t, mul=1.0):
    """المصفوفة الجاهزة ومصفوفة التحويل والألفا للعنصر عند t، أو None."""
    import numpy as np
    s = e.st(t)
    if s is None:
        return None
    a, ox, oy, k, r, rev, g = s
    a *= mul
    if a <= 0.003 or rev <= 0.002:
        return None
    arr = e.arr()
    if rev < 0.998:
        arr = _reveal(arr, rev)
    if e.sweep is not None and e.sweep <= t <= e.sweep + SWEEP_D:
        arr = _sweep(arr, (t - e.sweep) / SWEEP_D)
    h, w = arr.shape[:2]
    cx, cy = e.x + w / 2 + ox, e.y + h / 2 + oy
    if g != 1.0 and e.piv is not None:
        cx, cy = e.piv[0] + (cx - e.piv[0]) * g, e.piv[1] + (cy - e.piv[1]) * g
        k *= g
    th = math.radians(r)
    c, sn = math.cos(th) * k, math.sin(th) * k
    M = np.float32([[c, -sn, cx - c * w / 2 + sn * h / 2], [sn, c, cy - sn * w / 2 - c * h / 2]])
    return arr, M, a, (cx, cy, k, th)


def _blit(dst, arr, M, a, dsta=None):
    """يحوّل arr بـM ويمزجه فوق dst (uint8 RGB، أو float32 مضروبٌ مسبقاً مع dsta لألفا اللوحة)."""
    import cv2
    import numpy as np
    H_, W_ = dst.shape[:2]
    h, w = arr.shape[:2]
    pts = M @ np.float32([[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]]).T
    x0, y0 = max(0, int(math.floor(pts[0].min())) - 1), max(0, int(math.floor(pts[1].min())) - 1)
    x1, y1 = min(W_, int(math.ceil(pts[0].max())) + 2), min(H_, int(math.ceil(pts[1].max())) + 2)
    if x1 <= x0 or y1 <= y0:
        return
    M2 = M.copy(); M2[0, 2] -= x0; M2[1, 2] -= y0
    wp = cv2.warpAffine(arr, M2, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    al = wp[..., 3:4].astype(np.float32) * (a / 255.0)
    src = wp[..., :3].astype(np.float32) * a
    if dsta is None:
        roi = dst[y0:y1, x0:x1].astype(np.float32)
        dst[y0:y1, x0:x1] = np.clip(src + roi * (1 - al), 0, 255).astype(np.uint8)
    else:
        dst[y0:y1, x0:x1] = src + dst[y0:y1, x0:x1] * (1 - al)
        dsta[y0:y1, x0:x1] = al[..., 0] + dsta[y0:y1, x0:x1] * (1 - al[..., 0])


def _layer_alpha(e, t):
    """ألفا طبقة التعتيم/التدرّج عند t (دخولٌ بتلاشٍ وخروجٌ مع المجموعة)."""
    if t + 1e-6 < e.t0:
        return 0.0
    a = ease_out(_cl((t - e.t0) / e.d)) if e.d > 0 else 1.0
    if e.t1 is not None and t >= e.t1:
        a *= 1 - _cl((t - e.t1) / max(0.04, e.od))
    return a * e.lvl


def draw(dst, els: list, t: float, dsta=None) -> None:
    """يرسم عناصر المشهد عند t فوق dst — إطار المقطع (uint8 RGB) أو لوحةٌ شفّافة (float32 مع dsta)."""
    import cv2
    import numpy as np
    for e in sorted(els, key=lambda e: e.z):
        if e.kind == 'dim':
            a = _layer_alpha(e, t)
            if a > 0.003:
                if dsta is None:
                    dst[:] = cv2.convertScaleAbs(dst, alpha=1 - a)
                else:
                    dst *= 1 - a; dsta[:] = a + dsta * (1 - a)
            continue
        if e.kind == 'band':
            a = _layer_alpha(e, t)
            if a > 0.003:
                g = np.asarray(e.img, np.float32)[:, None] * a          # img هنا تدرّج الألفا عمودياً
                if dsta is None:
                    dst[e.y:] = (dst[e.y:].astype(np.float32) * (1 - g[..., None])).astype(np.uint8)
                else:
                    dst[e.y:] *= (1 - g[..., None]); dsta[e.y:] = g + dsta[e.y:] * (1 - g)
            continue
        if e.anim == 'slam' and 0 <= t - e.t0 < e.d:           # أثرٌ خلف الضربة في اندفاعها
            for dt, mul in ((0.08, 0.2), (0.04, 0.38)):
                pl = _place(e, t - dt, mul)
                if pl:
                    _blit(dst, pl[0], pl[1], pl[2], dsta)
        pl = _place(e, t)
        if not pl:
            continue
        arr, M, a, (cx, cy, k, th) = pl
        if e.glow > 0:                                           # توهّجٌ من البطاقة نفسها خلفها
            gl, pad = e.glw()
            gh, gw = gl.shape[:2]
            c, sn = math.cos(th) * k, math.sin(th) * k
            Mg = np.float32([[c, -sn, cx - c * gw / 2 + sn * gh / 2], [sn, c, cy - sn * gw / 2 - c * gh / 2]])
            _blit(dst, gl, Mg, a * e.glow, dsta)
        _blit(dst, arr, M, a, dsta)


def compose(els: list, t: float) -> Image.Image:
    """المشهد عند t صورةً شفّافة RGBA (للمعاينة الثابتة والاختبارات) — بالرسم نفسه الذي يُصيَّر به الفيلم."""
    import numpy as np
    dst = np.zeros((H, W, 3), np.float32)
    dsta = np.zeros((H, W), np.float32)
    draw(dst, els, t, dsta)
    rgb = np.where(dsta[..., None] > 1e-4, dst / np.maximum(dsta[..., None], 1e-4), 0)
    out = np.dstack([np.clip(rgb, 0, 255), np.clip(dsta * 255, 0, 255)]).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')


# ══════════ بطاقات كوديكس ══════════
_CARDS: dict = {}
_MISSING: set = set()
_SPANS: dict = {}


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


# ══════════ تقسيم البطاقة إلى كلمات ══════════
def _runs(v):
    import numpy as np
    d = np.diff(np.concatenate([[0], v.astype(np.int8), [0]]))
    return list(zip(np.where(d == 1)[0].tolist(), np.where(d == -1)[0].tolist()))


def _fill(arr):
    """قناع حشوة الحروف: الأفتح حين تحيط بها حافّةٌ داكنة (ليفصل الفراغُ بين الكلمات وإن وصلتها الحافّة والظلّ)،
    وإلا فالمعتم كلّه (حبرٌ بلا حافّة، وقد تُلوَّن فيه كلمةٌ مبرَزة بلونٍ أفتح)."""
    import numpy as np
    a = arr[..., 3].astype(np.float32) / 255.0
    op = a > 0.85
    if op.sum() < 50:
        return a > 0.5
    lum = 0.3 * arr[..., 0] + 0.59 * arr[..., 1] + 0.11 * arr[..., 2]
    p10, p80 = np.percentile(lum[op], [10, 80])
    if p80 - p10 > 70:
        bright = op & (lum > (p10 + p80) / 2)
        if bright.sum() > 0.35 * op.sum():
            return bright
    return op


def word_spans(im: Image.Image, words: list) -> list | None:
    """حدود كلمات البطاقة أفقياً [(س0، س1)] بترتيب نطقها (الأولى يميناً)، تقسّم عرضها كلّه بلا فجوة؛ None إن تعذّر.
    القطع n-1 فراغاً عمودياً في الحشوة يُختار بالبرمجة الديناميكية: عرضُ الفراغ، وقربُه من موضعه المتوقّع بعدد الحروف،
    ولا كلمة أضيق من ثلث ما يُتوقّع لها."""
    try:
        import numpy as np
    except ImportError:                              # بلا numpy (عدّاء الاختبارات الخفيف): السطر كلّه يُخطّ من اليمين
        return None
    n = len(words)
    if n < 2:
        return None
    arr = np.asarray(im.convert('RGBA'))
    fm = _fill(arr)
    rows = fm.any(axis=1)
    if not rows.any():
        return None
    # السطر الأطول ارتفاعاً (البطاقة السطرية سطرٌ واحد؛ وما تحته من سطرٍ صغير لا يُقسَم)
    rr = _runs(rows)
    mg = max(4, int(0.04 * fm.shape[0]))
    merged = [list(rr[0])]
    for a0, b0 in rr[1:]:
        if a0 - merged[-1][1] < mg:
            merged[-1][1] = b0
        else:
            merged.append([a0, b0])
    y0, y1 = max(merged, key=lambda x: x[1] - x[0])
    col = fm[y0:y1].any(axis=0)
    xs = np.where(col)[0]
    x0, x1 = int(xs[0]), int(xs[-1]) + 1
    gaps = [(a0 + x0, b0 + x0) for a0, b0 in _runs(~col[x0:x1]) if b0 - a0 >= 2]
    if len(gaps) < n - 1:
        return None
    wts = [len(bare(w)) + 0.6 for w in words]
    tot = sum(wts)
    exp, acc = [], 0.0
    for w in wts[:-1]:
        acc += w
        exp.append(x1 - (x1 - x0) * acc / tot)                 # من اليمين
    G = sorted(gaps, key=lambda g: -g[0])
    gw = [b - a for a, b in G]; gc = [(a + b) / 2 for a, b in G]
    span = float(x1 - x0); wmax = float(max(gw))
    minw = [max(6.0, (x1 - x0) * w / tot / 3) for w in wts]
    INF = 1e18
    K = n - 1
    cost = [[INF] * len(G) for _ in range(K)]
    prev = [[-1] * len(G) for _ in range(K)]
    c = lambda k, j: -gw[j] / wmax + 2.2 * abs(gc[j] - exp[k]) / span
    for j in range(len(G)):
        if x1 - gc[j] >= minw[0]:
            cost[0][j] = c(0, j)
    for k in range(1, K):
        for j in range(len(G)):
            for i in range(j):
                if cost[k - 1][i] < INF and gc[i] - gc[j] >= minw[k] and cost[k - 1][i] + c(k, j) < cost[k][j]:
                    cost[k][j] = cost[k - 1][i] + c(k, j); prev[k][j] = i
    best = [j for j in range(len(G)) if cost[K - 1][j] < INF and gc[j] - x0 >= minw[-1]]
    if not best:
        return None
    j = min(best, key=lambda j: cost[K - 1][j])
    sel = [j]
    for k in range(K - 1, 0, -1):
        j = prev[k][j]; sel.append(j)
    cuts = [int(round(gc[j])) for j in reversed(sel)]           # من اليمين إلى اليسار
    edges = [im.width] + cuts + [0]
    return [(edges[i + 1], edges[i]) for i in range(n)]


def spans_of(proj: str, key: str, words: list, width: int) -> list | None:
    """حدود الكلمات لبطاقةٍ محجَّمةٍ إلى العرض width (التقسيم على البطاقة الأصلية بدقّتها ثم يُحجَّم)."""
    ck = (key, tuple(words))
    if ck not in _SPANS:
        im = card(proj, key)
        _SPANS[ck] = (word_spans(im, words), im.width) if im is not None else (None, 1)
    sp_, w0 = _SPANS[ck]
    if not sp_:
        return None
    k = width / w0
    return [(int(round(a * k)), int(round(b * k))) for a, b in sp_]


# ══════════ عناصر العرض ══════════
def dim_el(alpha: float, t0: float = 0.0, d: float = 0.3, z: int = 0):
    return El(None, 0, 0, t0, 'fade', d, z=z, kind='dim', lvl=alpha)


def band_el(y0: int, t0=0.0):
    """تدرّجٌ معتمٌ أسفل الإطار لقراءة الكتابة (img هنا ألفا التدرّج عمودياً)."""
    g = [0.80 * (i / (H - y0)) ** 0.8 for i in range(H - y0)]
    return El(g, 0, int(y0), t0, 'fade', 0.3, z=0, kind='band')


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


def word_times(c: dict, wt: list, nwords: int, t0: float, t1: float) -> list[tuple[float, float]]:
    """زمن نطق كلّ كلمةٍ في السطر: من أزمنة الصوت إن كان السطر منطوقاً، وإلا بالتوزيع بعدد الحروف بين t0 وt1."""
    words = c['text'].split()
    idx = c.get('idx') or []
    if c.get('spoken') and len(idx) == len(words) and len(wt) == nwords:
        return [(wt[j][1], wt[j][2]) for j in idx]
    wts = [len(bare(w)) + 0.6 for w in words]
    tot = sum(wts) or 1.0
    out, acc = [], t0
    for w in wts:
        d = (t1 - t0) * w / tot
        out.append((acc, acc + d)); acc += d
    return out


def line_els(proj: str, c: dict, im: Image.Image, x: float, y: float, times: list, anim: str, d: float, z: int = 2,
             act: float = 0.06, ink: bool = False) -> list:
    """عناصر كلمات سطرٍ: كلُّ كلمةٍ قصاصةٌ من بطاقتها في موضعها تدخل لحظة نطقها؛ والكلمة المبرَزة أكبر دخولاً وتلمع.
    إن تعذّر التقسيم فالسطر كلّه يُخطّ من اليمين من أوّل كلماته إلى آخرها."""
    words = c['text'].split()
    sp_ = spans_of(proj, c['key'], words, im.width)
    t0, t1 = times[0][0], times[-1][1]
    if not sp_:
        return [El(im, x, y, t0, 'wipe', max(0.3, min(2.6, t1 - t0)), z=z)]
    hl = {bare(h) for h in (c.get('hl') or [])}
    els = []
    for (a, b), (ws, we), w in zip(sp_, times, words):
        if b - a < 2:
            continue
        big = bare(w) in hl
        dd = max(0.25, min(1.1, we - ws)) if ink else d * (1.15 if big else 1.0)
        els.append(El(im.crop((a, 0, b, im.height)), x + a, y, max(0.0, ws - 0.04), anim, dd, z=z,
                      act=(ws, we) if act else None, actk=act, amp=1.4 if big else 1.0,
                      sweep=(ws + 0.22) if big else None))
    return els


def group(els: list, grow: float, t_exit: float | None, ex: str = 'fade', od: float = 0.3) -> list:
    """تقريبٌ بطيءٌ مشترك للمجموعة حول مركزها منذ أوّل دخول، وخروجٌ مشترك عند t_exit."""
    imgs = [e for e in els if e.kind == 'img']
    if imgs:
        x0 = min(e.x for e in imgs); x1 = max(e.x + e.img.width for e in imgs)
        y0 = min(e.y for e in imgs); y1 = max(e.y + e.img.height for e in imgs)
        g0 = min(e.t0 for e in imgs)
        for e in imgs:
            e.grow, e.piv, e.g0 = grow, ((x0 + x1) / 2, (y0 + y1) / 2), g0
    if t_exit is not None:
        for e in els:
            e.t1, e.ex, e.od = t_exit, (ex if e.kind == 'img' else 'fade'), od
    return els


def exit_at(span: float, last: float, lead: float = 0.34) -> float | None:
    """موعد خروج الكتابة قبل الانتقال: بعد آخر كلمةٍ بنصف ثانيةٍ على الأقل، وإلا فلا خروج."""
    t = max(last + 0.6, span - lead)
    return t if t < span - 0.06 else None


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
            els.append(El(im, W - 80 - im.width, top + i * lh, ts[i], 'none' if ts[i] == 0.0 and i < keep else 'slide', 0.45, z=2))
        return group(els, 0.006, exit_at(span, ts[-1]), 'up')
    if style == 'poem':
        mid = (speech0 + speech1) / 2
        for c, (cx, t0, t1, an) in zip(lines[:2], ((1440, speech0, mid, 'rise'), (480, mid, speech1, 'rise'))):
            im = card(proj, c['key'])
            if im is None:
                continue
            im = fit(im, 840, 130)
            x, y = cx - im.width / 2, 470 - im.height / 2
            els += line_els(proj, c, im, x, y, word_times(c, wt, nwords, t0, t1 - 0.1), an, 0.5, act=0.0)
        if els and src and card(proj, src['key']) is not None:
            im = fit(card(proj, src['key']), 900, 56)
            els.append(El(im, W / 2 - im.width / 2, 600, max(speech0 + 0.8, speech1 - 0.6), 'rise', 0.5, z=2))
        if not els:
            return []
        return group([dim_el(0.55)] + els, 0.010, exit_at(span, speech1 - 0.3), 'fade')
    times = line_times(lines, wt, speech0, speech1, nwords)
    pairs = [(c, card(proj, c['key']), tt) for c, tt in zip(lines, times)]
    pairs = [(c, im, tt) for c, im, tt in pairs if im is not None]
    if not pairs:
        return []
    last = max(t0 for _, _, (t0, _) in pairs)
    if style == 'letter':
        bg = card(proj, 'letter_bg')
        n = len(pairs)
        lh = 132
        bw = 1560
        bh = min(980, n * lh + 200)
        top = (H - bh) / 2
        if bg is not None:
            els += [dim_el(0.35), El(bg.resize((bw, int(bh)), Image.LANCZOS), (W - bw) / 2, top, 0.0, 'settle', 0.5, z=1)]
        else:
            els.append(dim_el(0.45))
        for i, (c, im, (t0, t1)) in enumerate(pairs):
            im = fit(im, bw - 200, 112)
            els += line_els(proj, c, im, W / 2 - im.width / 2, top + 92 + i * lh, word_times(c, wt, nwords, t0, t1), 'ink', 0.5,
                            act=0.0, ink=True)
        if src and card(proj, src['key']) is not None:
            im = fit(card(proj, src['key']), 640, 50)
            els.append(El(im, (W - bw) / 2 + 70, top + bh - 75, 0.3, 'fade', 0.4, z=2))
        return group(els, 0.006, exit_at(span, last), 'fade')
    if style in ('center', 'quote'):
        maxw, maxh, lh = (1680, 150, 178) if style == 'center' else (1560, 132, 158)
        n = len(pairs)
        top = H / 2 - n * lh / 2 - (30 if src else 0)
        els.append(dim_el(0.55 if style == 'center' else 0.6))
        anim, d = ('drop', 0.34) if style == 'center' else ('rise', 0.42)
        for i, (c, im, (t0, t1)) in enumerate(pairs):
            im = fit(im, maxw, maxh)
            els += line_els(proj, c, im, W / 2 - im.width / 2, top + i * lh + (lh - im.height) / 2, word_times(c, wt, nwords, t0, t1),
                            anim, d)
        if src and card(proj, src['key']) is not None:
            im = fit(card(proj, src['key']), 900, 56)
            els.append(El(im, W / 2 - im.width / 2, top + n * lh + 14, max(speech0 + 0.6, last), 'rise', 0.45, z=2))
        return group(els, 0.012 if style == 'center' else 0.008, exit_at(span, last), 'shrink' if style == 'center' else 'up')
    # lower
    n = len(pairs)
    lh = 100
    els.append(band_el(640))
    for i, (c, im, (t0, t1)) in enumerate(pairs):
        im = fit(im, 1640, 84)
        els += line_els(proj, c, im, W / 2 - im.width / 2, H - 70 - (n - i) * lh + (lh - im.height) / 2,
                        word_times(c, wt, nwords, t0, t1), 'pop', 0.28)
    return group(els, 0.004, exit_at(span, last, 0.24), 'fade', 0.22)


def slam_els(proj: str, spec: dict, t: float, top: bool = False, span: float | None = None) -> list:
    """top: الضربة أعلى الشاشة وأصغر قليلاً حين تشاركها بطاقاتُ صورٍ في اللقطة نفسها (لا تغطّيها)."""
    im = card(proj, spec['key'])
    if im is None:
        return []
    im = fit(im, 1300, 300) if top else fit(im, 1560, 420)
    y = 40 if top else H / 2 - im.height / 2
    e = El(im, W / 2 - im.width / 2, y, t, 'slam', 0.26, z=3, sweep=t + 0.3, glow=0.5)
    els = [dim_el(0.38, t, 0.15), e]
    return group(els, 0.02, exit_at(span, t + 0.6, 0.26) if span else None, 'shrink', 0.26)


def name_els(proj: str, spec: dict, t: float, span: float | None = None) -> list:
    im = card(proj, spec['key'])
    if im is None:
        return []
    im = fit(im, 860, 190)
    e = El(im, W - 90 - im.width, H - 120 - im.height, t, 'slide', 0.5, z=2, sweep=t + 0.45)
    if span and span - t > 1.8:
        e.t1, e.ex, e.od = max(t + 1.3, span - 0.5), 'slide', 0.4
    return [e]


def date_els(proj: str, spec: dict, span: float | None = None) -> list:
    im = card(proj, spec['key'])
    if im is None:
        return []
    im = fit(im, 680, 160)
    e = El(im, W - 46 - im.width, 200, 0.25, 'stamp', 0.42, z=2, sweep=0.8)       # تحت شعار القناة (أعلى اليمين 46–166)
    if span:
        e.t1 = exit_at(span, 0.9, 0.32)
    return [e]


def label_els(proj: str, specs: list, wt: list) -> list:
    els = []
    for i, c in enumerate(specs):
        im = card(proj, c['key'])
        if im is None:
            continue
        im = fit(im, 640, 78)
        t = find_word(wt, c.get('word'), 0.0) if c.get('word') else 0.15 + 0.12 * i
        els.append(El(im, c['x'] - im.width / 2, c['y'] - im.height / 2, t, 'pop', 0.32, z=2))
    return els


def thumb_els(proj: str, items: list, specs: list, wt: list, span: float, low: bool = False) -> list:
    """صورٌ مصغّرة من كوديكس في إطارٍ أبيض (قصٌّ وتحجيم) تُرمى ثم تستقرّ مائلةً قليلاً، وتحت كلٍّ بطاقةُ اسمها من كوديكس.
    low: البطاقات أسفل الوسط لتفسح أعلى الشاشة لضربةٍ مكتوبة في اللقطة نفسها."""
    n = len(items)
    cw, ch_ = (440, 248) if n <= 3 else (380, 214)
    gap = 40
    total = n * cw + (n - 1) * gap
    t_first = min([find_word(wt, c.get('word'), 0.3) for c in items] or [0.3])
    els = [dim_el(0.5, t_first, 0.3)]
    labs = {c['n']: c for c in specs}
    tilt = [-2.4, 1.8, -1.3, 2.2, -1.8]
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
            els.append(El(fr, x - 6, y - 6, t, 'toss', 0.5, z=2, rot=tilt[i % len(tilt)]))
        lab = labs.get(i)
        im2 = card(proj, lab['key']) if lab else None
        if im2 is not None:
            im2 = fit(im2, cw, 62)
            els.append(El(im2, x + cw / 2 - im2.width / 2, y + ch_ + 16, t + 0.15, 'rise', 0.3, z=2))
    return group(els, 0.008, None)


def chapter_els(proj: str, spec: dict, span: float) -> list:
    im = card(proj, spec['key'])
    if im is None:
        return []
    im = fit(im, 1400, 110)
    t1 = min(span - 0.35, 3.6)
    return [El(im, W / 2 - im.width / 2, 60, 0.2, 'wipe', 0.8, t1=t1, ex='up', od=0.35, z=2, sweep=1.05, glow=0.35)]


# ══════════ الكاميرا والومضات على الإطار كلّه ══════════
def cam(t: float, shakes: list, punches: list) -> tuple[float, float, float]:
    """(تكبير، إزاحة س، إزاحة ص) للإطار المركَّب عند t: ارتجاجٌ عند كلمات shake والضربات، وتكبيرٌ خاطف عند كلمات punch.
    التكبير الأساسيّ 1.035 طوال اللقطة إن كان فيها ارتجاج (فلا تظهر حوافّ ولا قفزة عند بدئه)."""
    z = 1.035 if shakes else 1.0
    dx = dy = 0.0
    for tp in punches:
        if tp <= t <= tp + 0.6:
            z += 0.11 * math.exp(-7 * (t - tp))
    for ts in shakes:
        if ts <= t <= ts + 0.55:
            u = t - ts; env = math.exp(-7 * u) * _cl(u / 0.02)
            dx += 26 * math.sin(75 * u) * env
            dy += 18 * math.sin(90 * u + 1.2) * env
    return z, dx, dy


def flash_alpha(t: float, flashes: list) -> float:
    a = 0.0
    for tf in flashes:
        if tf - 0.02 <= t <= tf + 0.26:
            a = max(a, 0.85 * (_cl((t - tf + 0.02) / 0.04) if t < tf + 0.02 else 1 - _cl((t - tf - 0.04) / 0.22)))
    return a


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
        els += date_els(proj, by('date')[0], span)
    if s.get('labels'):
        els += label_els(proj, by('label'), wt)
    if s.get('cards'):
        els += thumb_els(proj, s['cards'], by('clabel'), wt, span, low=both)
    if s.get('name') and by('name'):
        els += name_els(proj, by('name')[0], find_word(wt, s['name'].get('word'), 0.3), span)
    if s.get('slam') and by('slam'):
        sl = s['slam']
        t = float(sl['at']) if 'at' in sl else find_word(wt, sl.get('word'), 0.25)
        t = min(t, max(0.0, span - 0.5))
        els += slam_els(proj, by('slam')[0], t, top=both, span=span); shakes.append(t); flashes.append(t)
    if s.get('_chapter') and by('chapter'):
        els += chapter_els(proj, by('chapter')[0], span)
    for w in s.get('shake', []) or []:
        shakes.append(min(find_word(wt, w, 0.2), max(0.0, span - 0.4)))
    for w in s.get('punch', []) or []:
        punches.append(min(find_word(wt, w, 0.2), max(0.0, span - 0.4)))
    return els, sorted(set(round(x, 2) for x in shakes)), sorted(set(round(x, 2) for x in punches)), \
        sorted(set(round(x, 2) for x in flashes))


def render(seg: str, res: str, n: int, head: float, els: list, shakes: list, punches: list, flashes: list, enc: list) -> None:
    """يقرأ إطارات المقطع ويرسم عليها المشهد إطاراً إطاراً (الزمن المحلّي t = i/FPS - head) ثم يكتبها مرمَّزة."""
    import cv2
    import numpy as np
    dec = sp.Popen([envpaths.FF, '-v', 'error', '-i', seg, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-'],
                   stdout=sp.PIPE, stderr=sp.DEVNULL)                 # يُقتل بعد حاجته منه
    out = sp.Popen([envpaths.FF, '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS),
                    '-i', '-'] + enc + ['-frames:v', str(n), res], stdin=sp.PIPE)
    last = np.zeros((H, W, 3), np.uint8)
    white = np.full((H, W, 3), 255, np.uint8)
    for i in range(n):
        buf = dec.stdout.read(W * H * 3)
        if len(buf) == W * H * 3:
            last = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        fr = last.copy()
        t = i / FPS - head
        draw(fr, els, t)
        z, dx, dy = cam(t, shakes, punches)
        if z != 1.0 or dx or dy:
            M = np.float32([[z, 0, (1 - z) * W / 2 + dx], [0, z, (1 - z) * H / 2 + dy]])
            fr = cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        fa = flash_alpha(t, flashes)
        if fa > 0.003:
            fr = cv2.addWeighted(fr, 1 - fa, white, fa, 0.0)
        out.stdin.write(fr.tobytes())
    try:
        dec.stdout.close()
    except OSError:
        pass
    dec.kill(); dec.wait()
    out.stdin.close(); out.wait()
    if out.returncode:
        raise RuntimeError('⛔ تعذّر ترميز %s' % res)


def apply(proj: str, s: dict, seg: str, span: float, texts: dict, durs: dict, gap: float, work: str, enc: list,
          head: float = 0.0, total: float | None = None) -> str:
    """يركّب مؤثّرات العرض على مقطع اللقطة ويعيد مسار الناتج (يُستأنف إن وُجد بالمدّة نفسها).
    head: ثواني المقبض قبل بداية اللقطة في المقطع (إطاره الأوّل عند الزمن المحلّي -head)؛ total: مدّة المقطع كلّه."""
    total = span if total is None else total
    res = seg[:-4] + '_k2.mp4'
    n = int(round(total * FPS))
    if os.path.exists(res) and abs(_dur(res) - n / FPS) < 0.06:
        return res
    wt = shot_word_times(proj, s, texts, durs, gap)
    els, shakes, punches, flashes = shot_els(proj, s, wt, span, texts)
    if not (els or shakes or punches or flashes):
        return seg
    render(seg, res, n, head, els, shakes, punches, flashes, enc)
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
