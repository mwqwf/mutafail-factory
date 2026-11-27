# -*- coding: utf-8 -*-
"""معيار التحريك وبوّابة مراجعته — أمر المالك 2026-11-27: «التحريك يجب أن يكون بأقصى احترافية ممكنة».

ما كان (تدقيق 2026-11-27): حركة kb3d تُختار بالبذرة (رقم اللقطة % 8) لا بالشعور، فيدور «المدار» (orbit) في لقطة دعاء
ويُسحب «الكشف» في لقطة توتّر؛ والانتقالات تتناوب بالترتيب لا بالموقف؛ ولا فحص للرعشة أو التجمّد بعد التصيير.

الآن لكلّ لقطةٍ في shots.json حقل `emotion` (من EMOTIONS)، ومنه:
  • `move3d` من الحركات المسموحة لذلك الشعور، و`ease` (منحنى التسارع)، و`energy` (شدّة الإزاحة).
  • `tr` الانتقال إليها من الانتقالات المسموحة للشعور (لا خطفة في سكينة، ولا ذوبان بطيء في التحام).
  • اللقطة المهمّة (`key`، أو في أوّل 30 ث، أو ذروة) ⇒ `live` (جروك GenerateVideo) إلزاماً؛ kb3d للمستثنى فقط.
البوّابة `lint` تفشل عند: شعورٍ غائب أو مجهول، حركةٍ خارج المسموح، حركتين متطابقتين متجاورتين في kb3d، لقطةٍ مهمّة غير حيّة،
انتقالٍ غير مسوَّغ للشعور. و`clip_check` على المقطع المصيَّر تفشل عند الرعشة (تسارعٌ متقطّع في الحركة الكلّية) أو التجمّد.

    python3 tools/motion_plan.py apply <proj>        # يملأ move3d/ease/energy/tr الناقصة من emotion (لا يغيّر ما كُتب يدوياً)
    python3 tools/motion_plan.py lint  <proj>
    python3 tools/motion_plan.py clip  <kb3d|live|action> <clip.mp4> [...]
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

# الشعور ⇒ (الحركات المسموحة بالترتيب المفضّل، منحنى التسارع، الشدّة، الانتقالات المسموحة إلى اللقطة)
EMOTIONS = {
    'awe':        (['crane_up', 'reveal', 'dolly_out'], 'out', 0.8, ['fade', 'luma', 'fadeblack', 'fadewhite', None]),
    'tension':    (['dolly_in', 'push_tilt', 'truck_l', 'truck_r'], 'in', 0.9, ['fade', 'blur', 'push', None]),
    'action':     (['truck_r', 'truck_l', 'dolly_in', 'push_tilt'], 'soft', 1.25, ['whip', 'whipr', 'zoom', 'flash', 'push', None]),
    'journey':    (['truck_r', 'truck_l', 'dolly_in'], 'soft', 0.8, ['fade', 'luma', 'push', None]),
    'reflection': (['dolly_in', 'dolly_out'], 'inout', 0.55, ['fade', 'luma', 'blur', 'fadeblack', None]),
    'grief':      (['dolly_out', 'crane_up'], 'inout', 0.5, ['fade', 'fadeblack', 'luma', None]),
    'revelation': (['dolly_in', 'reveal', 'crane_up'], 'out', 0.75, ['fadewhite', 'luma', 'fade', None]),
    'aftermath':  (['dolly_out', 'crane_up', 'truck_l'], 'inout', 0.6, ['fade', 'fadeblack', 'luma', None]),
    'map':        (['dolly_in'], 'inout', 0.4, ['fade', None]),
}
LIVE_FIRST_S = 30.0          # كلّ لقطةٍ تبدأ قبل الثانية 30 مهمّة (الافتتاح يمسك المشاهد)
JERK_P95_MAX = 0.35          # بكسل/إطار² على صورةٍ عرضها 480 — فوقه رعشة مرئية (kb3d المقيس في أجنادين ≤ 0.03)
# المقاطع الحيّة (جروك): المقيس في أجنادين وسيط ~0.1، وما فوق 2 كان كلّه «handheld/fast push» وأسوؤها 5.4 في لقطةٍ هادئة.
LIVE_P95_MAX = 1.0           # مقطعٌ حيّ في شعورٍ غير القتال
ACTION_P95_MAX = 3.0         # القتال: اهتزازٌ مقصود مقبول إلى هذا الحدّ فقط
FREEZE_MAX_S = 0.6           # أطول تجمّدٍ مقبول داخل لقطة متحرّكة


def apply(shots: list) -> list:
    last = None
    for s in shots:
        e = EMOTIONS.get(s.get('emotion'))
        if not e:
            continue
        moves, ease, energy, trs = e
        if s.get('kind', 'kb3d') != 'live':
            if not s.get('move3d'):
                s['move3d'] = next((m for m in moves if m != last), moves[0])
            s.setdefault('ease', ease)
            s.setdefault('energy', energy)
            last = s['move3d']
        else:
            last = None
        if 'tr' not in s:
            s['tr'] = trs[0] if trs[0] else 'cut'
    return shots


def important(s: dict, start: float | None) -> bool:
    return bool(s.get('key') or s.get('climax') or s.get('hook') or (start is not None and start < LIVE_FIRST_S))


def lint(shots: list, starts: list | None = None) -> list[str]:
    errs = []
    prev = None
    for i, s in enumerate(shots):
        sid = s.get('id', '#%d' % i)
        em = s.get('emotion')
        if em not in EMOTIONS:
            errs.append('%s: شعور اللقطة غائب أو مجهول «%s» (%s)' % (sid, em, ' '.join(EMOTIONS))); prev = None; continue
        moves, _ease, _en, trs = EMOTIONS[em]
        kind = s.get('kind', 'kb3d')
        st = starts[i] if starts and i < len(starts) else None
        if important(s, st) and kind != 'live' and not s.get('map') and em != 'map':
            errs.append('%s: لقطة مهمّة (مفتاح/ذروة/أول 30 ث) بلا تحريك حيّ — الافتراض live (أمر 2026-11-22)' % sid)
        if kind != 'live':
            mv = s.get('move3d')
            if mv not in moves:
                errs.append('%s: الحركة «%s» لا تناسب شعور %s (المسموح: %s)' % (sid, mv, em, ' '.join(moves)))
            if mv and mv == prev:
                errs.append('%s: الحركة %s نفسها في لقطتين متجاورتين — رتابة' % (sid, mv))
            if float(s.get('energy', 1.0)) > 1.4:
                errs.append('%s: شدّة %.2f فوق 1.4 — تمطّط عند حوافّ العمق' % (sid, float(s['energy'])))
            prev = mv
        else:
            prev = None
            if not (s.get('video_prompt') or s.get('clip')):
                errs.append('%s: لقطة حيّة بلا وصف حركة (video_prompt)' % sid)
        tr = s.get('tr', 'auto')
        name = None if tr in ('cut', None) else (tr[0] if isinstance(tr, (list, tuple)) else tr)
        if i > 0 and tr != 'auto' and name not in trs:
            errs.append('%s: الانتقال «%s» غير مسوَّغ لشعور %s (المسموح: %s)' % (sid, name or 'cut', em,
                                                                          ' '.join(x or 'cut' for x in trs)))
    return errs


def _frames(path: str, w: int = 480):
    import cv2
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        h = int(f.shape[0] * w / f.shape[1])
        out.append(cv2.cvtColor(cv2.resize(f, (w, h), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32))
    cap.release()
    return out, fps


def clip_check(path: str, mode: str = 'kb3d') -> list[str]:
    """رعشة: تسارع الإزاحة الكلّية بين الإطارات (phase correlation) — الحركة الناعمة تسارعها قريب من الصفر.
    تجمّد: إطاراتٌ متطابقة متتالية أطول من FREEZE_MAX_S."""
    import cv2
    fr, fps = _frames(path)
    if len(fr) < 4:
        return ['%s: مقطع قصير أو تالف' % os.path.basename(path)]
    win = cv2.createHanningWindow(fr[0].shape[::-1], cv2.CV_32F)
    v, still, run = [], 0, 0
    for a, b in zip(fr, fr[1:]):
        (dx, dy), _r = cv2.phaseCorrelate(a, b, win)
        v.append((dx, dy))
        run = run + 1 if float(np.abs(a - b).mean()) < 0.05 else 0
        still = max(still, run)
    v = np.array(v)
    jerk = np.linalg.norm(np.diff(v, axis=0), axis=1)
    errs = []
    p95 = float(np.percentile(jerk, 95)) if len(jerk) else 0.0
    lim = JERK_P95_MAX if mode == 'kb3d' else (ACTION_P95_MAX if mode == 'action' else LIVE_P95_MAX)
    if p95 > lim:
        errs.append('%s: رعشة — تسارعٌ متقطّع p95=%.2f بكسل (الحدّ %.2f لـ%s) — أعِد التوليد بحركة كاميرا ثابتة' % (
            os.path.basename(path), p95, lim, mode))
    if still / fps > FREEZE_MAX_S:
        errs.append('%s: تجمّد %.1f ث' % (os.path.basename(path), still / fps))
    return errs


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) < 2:
        print(__doc__); return 2
    if a[0] == 'clip':                     # clip <kb3d|live|action> <mp4>...
        mode = a[1] if a[1] in ('kb3d', 'live', 'action') else 'kb3d'
        errs = [e for p in a[1 + (a[1] == mode):] for e in clip_check(p, mode)]
    else:
        sp = os.path.join(a[1], 'shots.json')
        shots = json.load(open(sp, encoding='utf-8'))
        if a[0] == 'apply':
            json.dump(apply(shots), open(sp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print('✓ مُلئت حقول التحريك من الشعور'); return 0
        starts = None
        tl = os.path.join(a[1], 'timeline.json')
        if os.path.exists(tl):
            t = json.load(open(tl, encoding='utf-8'))
            starts = [t.get(s['id'], [None])[0] for s in shots]
        errs = lint(shots, starts)
    for e in errs:
        print('⛔', e)
    if not errs:
        print('✓ التحريك سليم')
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main())
