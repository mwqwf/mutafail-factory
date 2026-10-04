# -*- coding: utf-8 -*-
"""انتقالاتٌ متداخلة بين اللقطات بحسب الموقف — أمر المالك 2026-10-04 (فيلم «الأرك»).

نصُّ الأمر الأوّل: «استعمل أساليب متعدّدة لم نجرّبها من قبل… مثل تلاشي الصور وظهور الجديدة، وانقسام صورة ثم ظهور الجديدة
مكانها، والكثير الكثير من الأساليب حسب الموقف».
ثم حكمه على العيّنة في اليوم نفسه: «بعد انقسام الصور اختفاء صورة وظهور أخرى بشكلٍ مفاجئ، بدلاً منها صورٌ متداخلة احترافية».

⭐ الإصدار الثاني:
  • انتقالٌ متداخل عند كلّ حدٍّ تقريباً (كان نصف الحدود قطعاً حادّاً)، والقطع الحادّ لا يبقى إلا حيث الومضة أو الضربة هي الانتقال.
  • لا إطار مجمَّد: كلّ لقطةٍ تُصيَّر بمقبضين حيّين (HF إطاراً قبل بدايتها وبعد نهايتها) فتتحرّك الصورتان كلتاهما أثناء التداخل
    (كان xfade يمدّ آخر إطارٍ وأوّل إطارٍ فتتجمّد الصورة نصف الانتقال).
  • الانتقالات نفسها تُحسب إطاراً إطاراً بـnumpy وcv2: ذوبانٌ سينمائيّ، وذوبانٌ بالضوء (الأفتح يظهر أوّلاً)، وتكبيرٌ عابرٌ مغبَّش،
    وذوبانٌ مغبَّش، وخطفةُ كاميرا بغبش الحركة، ودفعٌ ناعم، وومضةٌ بيضاء، وتعتيمٌ إلى السواد، وانقسامٌ وانفتاحٌ دائريّ بحوافّ ناعمة
    مع ذوبانٍ متزامن (فلا يبقى «انقسامٌ ثم ظهورٌ مفاجئ»).
  • مُجمِّعٌ واحد يقرأ اللقطات بالتتابع ويكتب الفيلم الصامت مرّةً واحدة (assemble) — لا مقاطع وسيطة ولا ربط.

كيف يبقى الصوت متزامناً؟ الانتقال T يتمركز على نقطة القطع: آخر T/2 من اللقطة الأولى وأوّل T/2 من الثانية، ومعهما من المقبضين
ما يكمل التداخل (T/2 بعد نهاية الأولى من مقبضها، وT/2 قبل بداية الثانية من مقبضها). فعدد إطارات الفيلم = مجموع إطارات اللقطات
بلا زيادةٍ ولا نقص، وبدايات اللقطات في timeline.json كما هي. T من مضاعفات 0.08 ث فيقع T/2 على إطارٍ كامل، ولا يزيد على 2×HF.

السياسة (plan):
  • أوّل لقطةٍ في فصلٍ جديد ← تعتيمٌ إلى السواد (fadeblack)
  • لقطةٌ على الصورة نفسها التي قبلها ← ذوبانٌ ناعم
  • لقطةٌ فيها ومضةٌ أو ضربةٌ في أوّلها، أو مزامنةُ شفاه، أو بعد لقطة تحوّلٍ (end_image) ← قطعٌ حادّ (الومضة هي الانتقال)
  • المعركة ← انتقالاتٌ خاطفة 0.32–0.40 ث تتناوب (خطفة، تكبير، ذوبان، ومضة، دفع، غبش)
  • خارج المعركة ← تداخلٌ طويل 0.64–0.96 ث تتناوب أنواعه، أغلبها ذوبانٌ بأشكاله
  • والحقل tr في اللقطة يغلب السياسة: "cut" أو اسم انتقال أو [الاسم، المدّة]. أسماء ffmpeg القديمة تُترجم إلى نظائرها الناعمة.
"""
from __future__ import annotations

import math
import os
import subprocess as sp
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envpaths  # noqa: E402

FPS = 25
HF = 12                       # مقبض كلّ لقطة بالإطارات (قبلها وبعدها) = 0.48 ث ⇒ أطول انتقالٍ 0.96 ث
KINDS = {'fade', 'luma', 'zoom', 'blur', 'whip', 'whipr', 'push', 'flash', 'fadeblack', 'fadewhite', 'open_v', 'open_h',
         'circle', 'wipe'}
# أسماء xfade القديمة (في tr للأفلام السابقة) ← أقرب نظيرٍ ناعم متداخل
ALIAS = {'dissolve': 'fade', 'fadegrays': 'luma', 'distance': 'luma', 'fadefast': 'fade', 'fadeslow': 'fade',
         'zoomin': 'zoom', 'squeezeh': 'zoom', 'squeezev': 'zoom', 'hblur': 'blur', 'pixelize': 'blur',
         'slideleft': 'whip', 'smoothleft': 'push', 'coverleft': 'push', 'revealleft': 'push',
         'slideright': 'whipr', 'smoothright': 'push', 'coverright': 'push', 'revealright': 'push',
         'slideup': 'push', 'slidedown': 'push', 'smoothup': 'push', 'smoothdown': 'push',
         'wipeleft': 'wipe', 'wiperight': 'wipe', 'wipeup': 'wipe', 'wipedown': 'wipe', 'hlslice': 'wipe', 'hrslice': 'wipe',
         'vuslice': 'wipe', 'vdslice': 'wipe', 'diagtl': 'luma', 'diagtr': 'luma', 'diagbl': 'luma', 'diagbr': 'luma',
         'vertopen': 'open_v', 'vertclose': 'open_v', 'horzopen': 'open_h', 'horzclose': 'open_h',
         'circleopen': 'circle', 'circleclose': 'circle', 'circlecrop': 'circle', 'rectcrop': 'circle', 'radial': 'luma'}
# الدورتان: (النوع، المدّة)
SOFT = [('fade', 0.80), ('luma', 0.96), ('zoom', 0.72), ('blur', 0.80), ('fade', 0.88), ('push', 0.72), ('luma', 0.88),
        ('fade', 0.72), ('zoom', 0.80)]
FAST = [('whip', 0.40), ('zoom', 0.40), ('fade', 0.32), ('flash', 0.32), ('whipr', 0.40), ('blur', 0.40), ('push', 0.40)]


def q(T: float) -> float:
    """مدّةٌ من مضاعفات 0.08 ث (فنصفها إطارٌ كامل)، بين 0.16 و2×HF إطاراً."""
    return min(2 * HF / FPS, max(0.16, round(T / 0.08) * 0.08))


def kind(name: str | None) -> str | None:
    if not name:
        return None
    name = ALIAS.get(name, name)
    return name if name in KINDS else None


def sections_of(shots: list, sections: list) -> list:
    """فصل كلّ لقطة: يتغيّر عند أوّل لقطةٍ تبدأ بالكتلة الأولى لفصلٍ من sections.json."""
    first = {x['id']: x.get('phase') or x.get('id') for x in sections}
    cur, out = None, []
    for s in shots:
        b = (s.get('blocks') or [None])[0]
        if b in first:
            cur = first[b]
        out.append(cur)
    return out


def plan(shots: list, sections: list) -> list:
    """لكلّ حدٍّ بين لقطتين (i، i+1): None للقطع الحادّ أو (نوع الانتقال، المدّة)."""
    secs = sections_of(shots, sections)
    firsts = {x['id'] for x in sections[1:]}
    starts = {i for i, s in enumerate(shots) if (s.get('blocks') or [None])[0] in firsts}
    out: list = []
    kf = ks = 0
    for i in range(len(shots) - 1):
        a, b = shots[i], shots[i + 1]
        tr = b.get('tr', 'auto')
        if tr in (None, 'cut'):
            out.append(None); continue
        if tr != 'auto':
            name, T = (tr[0], float(tr[1])) if isinstance(tr, (list, tuple)) else (tr, 0.80)
            k = kind(name)
            out.append((k, q(T)) if k else None); continue
        if i + 1 in starts:
            out.append(('fadeblack', 0.96)); continue
        if b.get('flash') or (b.get('slam') and float(b['slam'].get('at', 1.0)) < 0.3) or b.get('lipsync') or a.get('end_image'):
            out.append(None); continue
        if b.get('file') and b.get('file') == a.get('file'):
            out.append(('fade', 0.64)); continue
        if secs[i + 1] == 'battle':
            out.append(FAST[kf % len(FAST)]); kf += 1
        else:
            out.append(SOFT[ks % len(SOFT)]); ks += 1
    return out


def frames(f: str) -> int:
    o = sp.run([envpaths.FP, '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=nb_read_packets',
                '-of', 'csv=p=0', f], capture_output=True, text=True).stdout.strip()
    try:
        return int(o.split(',')[0])
    except ValueError:
        return 0


def fit(nfr: list, tplan: list, hf: int = HF) -> list:
    """أنصاف الانتقالات بالإطارات بعد مواءمتها: لا يزيد نصفٌ على المقبض، ويبقى لكلّ لقطةٍ إطاران خاصّان على الأقل
    (وإلا قُصّر الانتقال الأطول بخطوة 0.08 ث، وما قصر عن 0.16 ث صار قطعاً حادّاً)."""
    half = [min(hf, int(round(p[1] * FPS / 2))) if p else 0 for p in tplan]
    for _ in range(64):
        bad = False
        for i, n in enumerate(nfr):
            hp = half[i - 1] if i > 0 else 0
            hn = half[i] if i < len(half) else 0
            if hp + hn > n - 2:
                bad = True
                j = i - 1 if hp >= hn else i
                half[j] = half[j] - 1 if half[j] > 2 else 0
        if not bad:
            break
    return half


# ══════════ الانتقالات إطاراً إطاراً ══════════
def _smooth(p):
    p = min(1.0, max(0.0, p))
    return p * p * (3 - 2 * p)


def _ein(p):
    p = min(1.0, max(0.0, p))
    return p * p * p


def _eout(p):
    p = min(1.0, max(0.0, p))
    return 1 - (1 - p) ** 3


def _mix(A, B, e):
    import cv2
    return cv2.addWeighted(A, 1.0 - e, B, e, 0.0)


def _mask_mix(A, B, m):
    """مزجٌ بقناعٍ لكلّ بكسل (H×W، 0..1)."""
    import cv2
    import numpy as np
    m = m.astype(np.float32)
    return cv2.blendLinear(A, B, 1.0 - m, m)


def _scale(img, z, dx=0.0):
    import cv2
    import numpy as np
    h, w = img.shape[:2]
    M = np.float32([[z, 0, (1 - z) * w / 2 + dx], [0, z, (1 - z) * h / 2]])
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def _blur(img, r):
    """غبشٌ رخيص: يُصغَّر الإطار ربعاً ويُغبَّش ثم يُكبَّر، ويُمزج بالأصل بقدر r."""
    import cv2
    if r < 0.4:
        return img
    h, w = img.shape[:2]
    sm = cv2.resize(img, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    sm = cv2.GaussianBlur(sm, (0, 0), max(0.6, r / 4))
    big = cv2.resize(sm, (w, h), interpolation=cv2.INTER_LINEAR)
    return _mix(img, big, min(1.0, r / 5.0))


def _strip(A, B, o, rtl):
    """شريطٌ أفقيّ: A تخرج وB تدخل بإزاحة o من العرض (rtl: المحتوى يتحرّك يميناً)."""
    import numpy as np
    h, w = A.shape[:2]
    x = int(round(w * min(1.0, max(0.0, o))))
    v = np.empty_like(A)
    if not rtl:
        v[:, :w - x] = A[:, x:]; v[:, w - x:] = B[:, :x]
    else:
        v[:, x:] = A[:, :w - x]; v[:, :x] = B[:, w - x:]
    return v


def blend(name: str, A, B, p: float):
    """إطار الانتقال عند التقدّم p∈(0،1) بين إطارين متحرّكين A وB (uint8 H×W×3)."""
    import cv2
    import numpy as np
    h, w = A.shape[:2]
    if name == 'luma':                              # الأفتحُ في B يظهر أوّلاً — ذوبانٌ بالضوء
        sm = cv2.resize(cv2.cvtColor(B, cv2.COLOR_RGB2GRAY), (w // 8, h // 8), interpolation=cv2.INTER_AREA)
        L = cv2.resize(cv2.GaussianBlur(sm, (0, 0), 2.0), (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255.0
        s = 0.45
        m = np.clip((_smooth(p) * (1 + s) - (1 - L)) / s, 0.0, 1.0)
        return _mask_mix(A, B, m)
    if name == 'zoom':                              # تكبيرٌ عابر: A تندفع نحو العين مغبّشةً، وB تستقرّ من قربٍ إلى مكانها
        ea, eb = _ein(min(1.0, p * 1.3)), _eout(max(0.0, p * 1.3 - 0.3))
        a2 = _blur(_scale(A, 1 + 0.22 * ea), 9 * ea)
        b2 = _blur(_scale(B, 1.16 - 0.16 * eb), 9 * (1 - eb))
        return _mix(a2, b2, _smooth((p - 0.2) / 0.6))
    if name == 'blur':                              # ذوبانٌ مغبَّش: يبلغ الغبش ذروته في منتصفه
        r = 9 * math.sin(math.pi * p)
        return _mix(_blur(A, r), _blur(B, r), _smooth(p))
    if name in ('whip', 'whipr'):                   # خطفة كاميرا بغبش حركةٍ أفقيّ
        v = _strip(A, B, _smooth(p), name == 'whipr')
        k = 1 + int(150 * math.sin(math.pi * p))
        return cv2.blur(v, (k, 1)) if k > 2 else v
    if name == 'push':                              # دفعٌ ناعم مع ذوبانٍ خفيف عند خطّ الالتقاء
        v = _strip(A, B, _smooth(p), False)
        k = 1 + int(36 * math.sin(math.pi * p))
        return cv2.blur(v, (k, 1)) if k > 2 else v
    if name in ('flash', 'fadewhite'):
        white = np.full_like(A, 255)
        pk = 0.9 if name == 'flash' else 1.0
        return _mix(A, white, pk * _ein(p * 2)) if p < 0.5 else _mix(B, white, pk * (1 - _eout((p - 0.5) * 2)))
    if name == 'fadeblack':
        return cv2.convertScaleAbs(A, alpha=1 - _smooth(p * 2)) if p < 0.5 else cv2.convertScaleAbs(B, alpha=_smooth((p - 0.5) * 2))
    if name in ('open_v', 'open_h', 'circle', 'wipe'):   # كشفٌ بحافّةٍ ناعمة عريضة مع ذوبانٍ متزامن (لا انقسامٌ حادّ)
        e = _smooth(p)
        if name == 'open_v':
            d = np.abs(np.arange(w, dtype=np.float32) - w / 2) / (w / 2)
            m = np.clip((e * 1.35 - d) / 0.35, 0, 1)[None, :].repeat(h, 0)
        elif name == 'open_h':
            d = np.abs(np.arange(h, dtype=np.float32) - h / 2) / (h / 2)
            m = np.clip((e * 1.35 - d) / 0.35, 0, 1)[:, None].repeat(w, 1)
        elif name == 'circle':
            yy, xx = np.ogrid[0:h, 0:w]
            d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2).astype(np.float32) / 1.42
            m = np.clip((e * 1.35 - d) / 0.35, 0, 1)
        else:                                       # مسحٌ من اليمين إلى اليسار (اتجاه القراءة)
            d = (w - np.arange(w, dtype=np.float32)) / w
            m = np.clip((e * 1.35 - d) / 0.35, 0, 1)[None, :].repeat(h, 0)
        m = np.maximum(m, e * e * 0.6)              # ذوبانٌ متزامن يذيب الحافّة في الصورتين
        return _mask_mix(A, B, m)
    return _mix(A, B, _smooth(p))                   # fade: ذوبانٌ سينمائيّ


# ══════════ المُجمِّع ══════════
class _Reader:
    """يقرأ إطارات مقطعٍ بالتتابع (rgb24)، ويكرّر آخر إطارٍ إن قصر المقطع عمّا يُطلب منه."""
    def __init__(self, f, w, h):
        self.w, self.h, self.n, self.last = w, h, 0, None
        self.p = sp.Popen([envpaths.FF, '-v', 'error', '-i', f, '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                           '-s', '%dx%d' % (w, h), '-'], stdout=sp.PIPE, stderr=sp.DEVNULL)   # يُقتل بعد حاجته منه
        self.short = 0

    def read(self):
        import numpy as np
        buf = self.p.stdout.read(self.w * self.h * 3)
        if len(buf) == self.w * self.h * 3:
            self.last = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 3)
        else:
            self.short += 1
            if self.last is None:
                self.last = np.zeros((self.h, self.w, 3), np.uint8)
        self.n += 1
        return self.last

    def skip(self, k):
        for _ in range(k):
            self.read()

    def close(self):
        try:
            self.p.stdout.close()
        except OSError:
            pass
        self.p.kill(); self.p.wait()


def assemble(segs: list, nfr: list, tplan: list, out: str, enc: list, hf: int = HF, size=(1920, 1080)) -> int:
    """يكتب الفيلم الصامت من مقاطع اللقطات بمقابضها: segs[i] فيه hf إطاراً قبل اللقطة ثم nfr[i] ثم hf بعدها.
    tplan[i] انتقال الحدّ (i، i+1). يعيد عدد الإطارات المكتوبة = مجموع nfr."""
    import numpy as np
    w, h = size
    half = fit(nfr, tplan, hf)
    names = [p[0] if p and half[i] else None for i, p in enumerate(tplan)]
    e = sp.Popen([envpaths.FF, '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (w, h),
                  '-r', str(FPS), '-i', '-'] + enc + [out], stdin=sp.PIPE)
    wrote, short = 0, []
    tailA: list = []                                  # إطارات اللقطة السابقة التي تدخل الانتقال الجاري
    for i, f in enumerate(segs):
        r = _Reader(f, w, h)
        hp = half[i - 1] if i > 0 and names[i - 1] else 0
        hn = half[i] if i < len(half) and names[i] else 0
        if hp:
            r.skip(hf - hp)
            T = 2 * hp
            for k in range(T):
                B = r.read()
                fr = blend(names[i - 1], tailA[k], B, (k + 0.5) / T)
                e.stdin.write(np.ascontiguousarray(fr).tobytes()); wrote += 1
        else:
            r.skip(hf)
        for _ in range(nfr[i] - hp - hn):             # جسم اللقطة
            e.stdin.write(r.read().tobytes()); wrote += 1
        tailA = [r.read().copy() for _ in range(2 * hn)] if hn else []
        if r.short:
            short.append((os.path.basename(f), r.short))
        r.close()
    e.stdin.close(); e.wait()
    if short:
        print('⚠ مقاطع أقصر من مقابضها (كُرّر آخر إطار):', short[:8], flush=True)
    return wrote

