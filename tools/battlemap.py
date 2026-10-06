# -*- coding: utf-8 -*-
"""🗺️ خريطة المعركة الحيّة — أمر المالك 2026-10-04 («سجّله لنستفيد منه للأفلام القادمة»)، ومواصفتها في
ops/research/motion_wow_2026-10-04.md §١: «الأقوى، وأنسب علاجٍ لـ"أفلامٌ لا تركّز على المعركة"».

⛔ لا يرسم هذا الملفّ شيئاً (أمر المالك 2026-09-29: «يُمنع على Claude صناعةُ أيّ صورةٍ بنفسه»):
- الخريطة صورة اللقطة نفسها (file).
- والأسهم ورموز الوحدات صورٌ شفّافة يصنعها كوديكس بمقاس الخريطة وفي مواضعها.
- وأسماء المواضع بطاقاتٌ من tools/cards.py (نوع label).
- وهنا تُمال الخريطة وتُقرَّب، ويُكشف السهم على طوله، وينبض الرمز، وتُسقَط البطاقة على موضعها. قصٌّ وتحجيمٌ وتحريكٌ فقط.

حقل map في اللقطة:
  "map": {"focus": [x, y], "tilt": 28, "zoom": [1.05, 1.25],
          "layers": [{"file": "map/arrow_charge.png", "kind": "arrow", "tail": [x, y], "word": "وحمل", "dur": 1.5},
                     {"file": "map/unit_right.png", "kind": "unit", "word": "ميمنة"},
                     {"file": "map/unit_rum.png", "kind": "unit"}],
          "labels": [{"text": "مؤتة", "x": 470, "y": 180}]}
- الإحداثيات بنقاط الخريطة الأصلية.
- focus نقطة الالتحام: تتقدّم الكاميرا نحوها ويُعتَّم ما بعُد عنها.
- السهم يُكشف من ذيله إلى رأسه في dur ثانية (1.2–2) مع فعله المنطوق. والكشف ببعد كلّ نقطةٍ عن الذيل داخل قناع السهم
  (تمديدٌ مقيَّد)، بحافّةٍ ناعمة.
- الرمز ينبض عند ذكره. وما لا كلمة له ظاهرٌ من أوّل اللقطة، وما كُشف يبقى.
- البطاقة تظهر بنابضٍ على موضعها بعد الإسقاط، مستويةً لا مائلة، فلا تفسد حروفها.
"""
from __future__ import annotations

import math
import os
import subprocess as sp
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VERSION = 1
W, H, FPS = 1920, 1080, 25
BG = np.array([12, 11, 9], np.float32) / 255.0          # خلفيةٌ داكنة خارج اللوح (BGR)
SOFT = 0.045                                            # نعومة حافّة الكشف (نسبةٌ من طول السهم)
DIM = 0.30                                              # تعتيم ما بعُد عن نقطة الالتحام
POP = 0.36                                              # مدّة نبضة الرمز والبطاقة (ث)


def ease(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def pop_scale(dt: float) -> float:
    """نابض: من 0.6 يتجاوز إلى نحو 1.12 ثم يستقرّ على 1 في POP ثانية (منحنى «الرجوع إلى الخلف» للخروج)."""
    if dt <= 0:
        return 0.6
    if dt >= POP:
        return 1.0
    x, c1 = dt / POP - 1.0, 3.0
    return 0.6 + 0.4 * (1 + (c1 + 1) * x ** 3 + c1 * x ** 2)


def load_rgba(path: str, size: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """(لون BGR بقيم 0–1، ألفا 0–1) بمقاس الخريطة."""
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im is None:
        raise FileNotFoundError(path)
    if im.ndim == 2:
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGRA)
    if im.shape[2] == 3:
        im = np.dstack([im, np.full(im.shape[:2], 255, np.uint8)])
    if (im.shape[1], im.shape[0]) != size:
        im = cv2.resize(im, size, interpolation=cv2.INTER_AREA)
    f = im.astype(np.float32) / 255.0
    return f[..., :3], f[..., 3]


def tail_distance(alpha: np.ndarray, tail, scale: float = 0.5, limit: int = 8000) -> np.ndarray:
    """البعد الجيوديسيّ لكلّ نقطةٍ من قناع السهم عن ذيله، مطبَّعاً إلى [0، 1]. يُحسب بنصف الدقّة ثم يُكبَّر،
    بتمديدٍ مقيَّدٍ بالقناع: يمشي الكشف داخل السهم وحده فيلتفّ معه إن انحنى."""
    m = (alpha > 0.08).astype(np.uint8)
    small = cv2.resize(m, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    ys, xs = np.nonzero(small)
    out = np.zeros(alpha.shape, np.float32)
    if len(xs) == 0:
        return out
    tx, ty = tail[0] * scale, tail[1] * scale
    k = int(np.argmin((xs - tx) ** 2 + (ys - ty) ** 2))
    reached = np.zeros_like(small)
    reached[ys[k], xs[k]] = 1
    dist = np.full(small.shape, -1, np.int32)
    dist[ys[k], xs[k]] = 0
    kern = np.ones((3, 3), np.uint8)
    it = 0
    while it < limit:
        nxt = cv2.dilate(reached, kern) & small
        new = (nxt > 0) & (reached == 0)
        if not new.any():
            break
        it += 1
        dist[new] = it
        reached = nxt
    d = dist.astype(np.float32)
    d[d < 0] = it                                       # جزءٌ منفصل عن الذيل يُكشف آخراً
    d /= max(1, it)
    return cv2.resize(d, (alpha.shape[1], alpha.shape[0]), interpolation=cv2.INTER_LINEAR)


def reveal(dist: np.ndarray, p: float) -> np.ndarray:
    """قناع الكشف عند التقدّم p (0–1): ما بعُد عن الذيل أقلّ من p ظاهر، بحافّةٍ ناعمة."""
    if p <= 0:
        return np.zeros_like(dist)
    if p >= 1:
        return np.ones_like(dist)
    e = SOFT
    return np.clip((p * (1 + e) - dist) / e, 0.0, 1.0)


def tilt_matrix(w: int, h: int, deg: float) -> np.ndarray:
    """لوحٌ مائل: تضيق الحافّة العليا وتنزل قليلاً، كأنّ الكاميرا تنظر إلى الخريطة من أمامها."""
    s = math.sin(math.radians(deg))
    k, drop = 0.42 * s, 0.10 * s
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[w * k / 2, h * drop], [w - w * k / 2, h * drop], [w, h], [0, h]])
    return cv2.getPerspectiveTransform(src, dst)


def _cam(z: float, a: float, focus: tuple[float, float]) -> np.ndarray:
    fx, fy = focus
    tx, ty = fx + (W / 2 - fx) * a, fy + (H / 2 - fy) * a
    return np.array([[z, 0, tx - z * fx], [0, z, ty - z * fy], [0, 0, 1]], np.float64)


def covered(M: np.ndarray, margin: float = 1.0) -> bool:
    """هل يملأ اللوحُ الإطارَ كلّه؟ (زوايا الإطار الأربع داخل الخريطة بعد عكس التحويل؛ وكلاهما محدَّب فتكفي الزوايا)"""
    Mi = np.linalg.inv(M)
    for x, y in ((0, 0), (W, 0), (W, H), (0, H)):
        u, v = project(Mi, x, y)
        if not (-margin <= u <= W + margin and -margin <= v <= H + margin):
            return False
    return True


def camera(tn: float, focus: tuple[float, float], z0: float, z1: float, T: np.ndarray | None = None) -> np.ndarray:
    """تقريبٌ ناعمٌ حول نقطة الالتحام، وهي تنزاح نحو وسط الإطار جزئيّاً.
    ومع T (الميل) يُرفع التقريب إلى أدناه الذي يملأ الإطار، فلا تظهر حوافّ اللوح ولا فراغٌ أسود (مراجعة الإطار الأوّل)."""
    e = ease(tn)
    z, a = z0 + (z1 - z0) * e, 0.20 + 0.45 * e
    if T is None or covered(_cam(z, a, focus) @ T):
        return _cam(z, a, focus)
    lo, hi = z, 6.0
    for _ in range(30):
        mid = (lo + hi) / 2
        if covered(_cam(mid, a, focus) @ T):
            hi = mid
        else:
            lo = mid
    return _cam(hi, a, focus)


def project(M: np.ndarray, x: float, y: float) -> tuple[float, float]:
    v = M @ np.array([x, y, 1.0])
    return float(v[0] / v[2]), float(v[1] / v[2])


def _bbox(a: np.ndarray, pad: int = 4) -> tuple[int, int, int, int]:
    ys, xs = np.nonzero(a > 0.02)
    if len(xs) == 0:
        return 0, 0, 0, 0
    return (max(0, xs.min() - pad), max(0, ys.min() - pad), min(a.shape[1], xs.max() + pad + 1),
            min(a.shape[0], ys.max() + pad + 1))


class Layer:
    def __init__(self, proj: str, spec: dict, size: tuple[int, int], t: float | None):
        self.kind = spec.get('kind', 'unit')
        self.rgb, self.a = load_rgba(os.path.join(proj, spec['file']), size)
        self.t = t                                          # None: ظاهرٌ من أوّل اللقطة
        self.dur = float(spec.get('dur', 1.5))
        self.box = _bbox(self.a)
        x0, y0, x1, y1 = self.box
        self.c = ((x0 + x1) / 2, (y0 + y1) / 2)
        self.dist = tail_distance(self.a, spec.get('tail') or (x0, (y0 + y1) / 2)) if self.kind == 'arrow' else None

    def state(self, t: float) -> tuple[np.ndarray, np.ndarray] | None:
        """(اللون، الألفا) عند الزمن المحلّيّ t، أو None إن لم يظهر بعد."""
        if self.t is None:
            return self.rgb, self.a
        dt = t - self.t
        if dt <= 0:
            return None
        if self.kind == 'arrow':
            return self.rgb, self.a * reveal(self.dist, ease(dt / self.dur))
        s = pop_scale(dt)
        al = min(1.0, dt / 0.15)
        if abs(s - 1.0) < 1e-3:
            return self.rgb, self.a * al
        M = cv2.getRotationMatrix2D(self.c, 0.0, s)
        size = (self.a.shape[1], self.a.shape[0])
        rgb = cv2.warpAffine(self.rgb, M, size, flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0))
        a = cv2.warpAffine(self.a, M, size, flags=cv2.INTER_LINEAR, borderValue=0)
        return rgb, a * al


def compose(base: np.ndarray, layers: list, t: float) -> np.ndarray:
    out = base.copy()
    for ly in layers:
        st = ly.state(t)
        if st is None:
            continue
        rgb, a = st
        x0, y0, x1, y1 = _bbox(a, 2) if ly.kind == 'unit' and ly.t is not None else ly.box
        if x1 <= x0:
            continue
        A = a[y0:y1, x0:x1, None]
        out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - A) + rgb[y0:y1, x0:x1] * A
    return out


def vignette(focus: tuple[float, float]) -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((xx - focus[0]) ** 2 + (yy - focus[1]) ** 2) / W
    k = np.clip((d - 0.30) / 0.45, 0.0, 1.0)
    return (1.0 - DIM * k * k * (3 - 2 * k))[..., None]


def label_cards(proj: str, labels: list) -> list:
    """بطاقات أسماء المواضع من كوديكس (tools/cards.py نوع label)؛ الغائبة يُتخطّى عنصرها كما في kinetic."""
    import cards
    import kinetic
    out = []
    for lb in labels or []:
        key = cards.key('label', {'t': cards.plain(lb['text']), 's': None, 'h': None})
        im = kinetic.card(proj, key)
        if im is None:
            continue
        im = kinetic.fit(im, 560, 70)
        arr = np.asarray(im).astype(np.float32) / 255.0
        out.append((lb, arr[..., [2, 1, 0]], arr[..., 3]))
    return out


def paste(frame: np.ndarray, rgb: np.ndarray, a: np.ndarray, cx: float, cy: float, s: float, al: float) -> None:
    if s != 1.0:
        rgb = cv2.resize(rgb, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR)
        a = cv2.resize(a, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR)
    h, w = a.shape
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    A = a[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0, None] * al
    frame[fy0:fy1, fx0:fx1] = frame[fy0:fy1, fx0:fx1] * (1 - A) + rgb[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0] * A


def event_time(wt: list, word: str | None, default: float | None) -> float | None:
    if not word:
        return default
    import kinetic
    return kinetic.find_word(wt, word, default if default is not None else 0.3)


def render(proj: str, s: dict, out: str, total: float, head: float = 0.0, wt: list | None = None) -> str:
    """يكتب مقطع اللقطة: total ثانية، وإطاره الأوّل عند الزمن المحلّيّ -head (المقبض قبل بداية اللقطة)."""
    import envpaths
    spec = s['map']
    img = os.path.join(proj, 'images', s['file']) if s.get('file') else None
    if not (img and os.path.exists(img)):
        img = os.path.join(proj, 'images', os.path.splitext(s.get('file', ''))[0] + '.png')
    base_rgb, _ = load_rgba(img, (W, H))
    wt = wt or []
    layers, arrows = [], 0
    for ly in spec.get('layers') or []:
        dflt = (0.3 + 0.8 * arrows) if ly.get('kind') == 'arrow' else None
        arrows += ly.get('kind') == 'arrow'
        layers.append(Layer(proj, ly, (W, H), event_time(wt, ly.get('word'), dflt)))
    labels = [(lb, rgb, a, event_time(wt, lb.get('word'), None)) for lb, rgb, a in label_cards(proj, spec.get('labels'))]
    T = tilt_matrix(W, H, float(spec.get('tilt', 28)))
    fpt = project(T, *spec.get('focus', (W / 2, H / 2)))
    z0, z1 = spec.get('zoom', (1.05, 1.25))
    n = int(round(total * FPS))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    tmp = out + '.part.mp4'
    p = sp.Popen([envpaths.FF, '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '%dx%d' % (W, H),
                  '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', tmp],
                 stdin=sp.PIPE)
    vig = None
    try:
        for i in range(n):
            t = i / FPS - head
            board = compose(base_rgb, layers, t)
            M = camera((i / max(1, n - 1)), fpt, z0, z1, T) @ T
            fr = cv2.warpPerspective(board, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                                     borderValue=tuple(float(v) for v in BG))
            if vig is None:
                vig = vignette(project(camera(1.0, fpt, z0, z1, T), *fpt))
            fr *= vig
            for lb, rgb, a, t0 in labels:
                dt = 1.0 if t0 is None else t - t0
                if dt <= 0:
                    continue
                cx, cy = project(M, lb['x'], lb['y'])
                paste(fr, rgb, a, cx, cy, pop_scale(dt), min(1.0, dt / 0.15))
            p.stdin.write((np.clip(fr, 0, 1) * 255).astype(np.uint8).tobytes())
    finally:
        p.stdin.close()
        p.wait()
    if p.returncode != 0:
        raise RuntimeError('تعذّر ترميز خريطة %s' % s.get('id'))
    os.replace(tmp, out)
    return out
