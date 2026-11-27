# -*- coding: utf-8 -*-
"""قياس النسبة الحيّة (مقاطع GenerateVideo فقط) ومنع بديل kb3d الصامت.

أمر المالك 2026-11-27 ثم رُفع الحدّ إلى 75٪: حركة kb3d لا تُحسب. الثابت الواحد
`MIN_LIVE_SHARE` مصدر العتبة في `motion_plan lint` وفي `measure`.

    python3 tools/live_share.py lint    <proj>
    python3 tools/live_share.py measure <proj> [film.mp4]
"""
from __future__ import annotations

import json
import os
import re
import subprocess as sp
import sys

# الثابت الواحد — الحدّ الأدنى لنسبة المقاطع الحيّة (GenerateVideo) من مدّة الفيلم.
# kb3d لا يُحسب. غيّر هذه القيمة وحدها لضبط العتبة في lint والقياس معاً.
MIN_LIVE_SHARE = 0.75

_CLIP_MIN_BYTES = 10000


def load_waivers(proj: str) -> dict:
    """id → سبب. يدعم قاموساً أو قائمة معرّفات أو قائمة كائنات {id, reason}."""
    path = os.path.join(proj, 'live_waivers.json')
    if not os.path.exists(path):
        return {}
    raw = json.load(open(path, encoding='utf-8'))
    if isinstance(raw, dict):
        return {str(k): ('' if v is None else str(v) if not isinstance(v, dict) else str(v.get('reason', '')))
                for k, v in raw.items() if k not in ('_doc', 'comment')}
    out = {}
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                out[item] = ''
            elif isinstance(item, dict) and item.get('id'):
                out[str(item['id'])] = str(item.get('reason') or '')
    return out


def clip_path(proj: str, sid: str) -> str | None:
    root = re.sub(r'_\d+$', '', sid)
    for name in (root + '_av', root, sid, root + '_raw', sid + '_raw'):
        p = os.path.join(proj, 'clips', name + '.mp4')
        if os.path.isfile(p) and os.path.getsize(p) > _CLIP_MIN_BYTES:
            return p
    return None


def shot_durations(shots: list, timeline=None, real_timing=None) -> list[float] | None:
    if timeline:
        d = []
        for s in shots:
            v = timeline.get(s['id'])
            if not v or len(v) < 2:
                return None
            d.append(float(v[1]))
        return d
    if real_timing and real_timing.get('bt'):
        bt = real_timing['bt']
        d = []
        for s in shots:
            blocks = s.get('blocks') or []
            if not blocks or blocks[0] not in bt or blocks[-1] not in bt:
                return None
            d.append(float(bt[blocks[-1]][1]) - float(bt[blocks[0]][0]))
        return d
    return None


def _in_waiver(sid: str, waivers: dict | None) -> bool:
    if not waivers:
        return False
    root = re.sub(r'_\d+$', '', sid)
    return sid in waivers or root in waivers


def plan_share(shots: list, durations: list, waivers: dict | None = None) -> tuple:
    """نسبة اللقطات `kind=live` من المدّة. الإعفاء وkb3d يُحسبان ضدّ النسبة."""
    waivers = waivers or {}
    total = float(sum(durations)) or 1.0
    live = 0.0
    details = []
    for s, d in zip(shots, durations):
        sid = s.get('id', '')
        is_live = s.get('kind') == 'live' and not s.get('still') and not _in_waiver(sid, waivers)
        if is_live:
            live += float(d)
        details.append((sid, float(d), is_live))
    return live / total, live, total, details


def plan_errors(shots: list, durations: list, waivers: dict | None = None) -> list[str]:
    share, live, total, _ = plan_share(shots, durations, waivers)
    if share + 1e-9 < MIN_LIVE_SHARE:
        return ['نسبة التحريك الحيّ (GenerateVideo) %.1f%% من %.0f ث < %.0f٪ — حركة kb3d لا تُحسب (أمر المالك)'
                % (100 * share, total, 100 * MIN_LIVE_SHARE)]
    return []


def enforce_live_clips(proj, shots, has_clip, allow=None, waivers=None):
    """يرفض اللقطة الحيّة بلا مقطع إلا مع ALLOW_LIVE_FALLBACK=1 أو إعفاء مسجّل، ويُنذر في الحالتين.

    العائد: (fallback_ids, waiver_ids, warnings). يرفع SystemExit عند الرفض.
    """
    if allow is None:
        allow = os.environ.get('ALLOW_LIVE_FALLBACK') == '1'
    if waivers is None:
        waivers = load_waivers(proj)
    missing, waiver_ids, warns = [], [], []
    for s in shots:
        if s.get('kind') != 'live' or s.get('still'):
            continue
        sid = s['id']
        if has_clip(sid) or has_clip(re.sub(r'_\d+$', '', sid)):
            continue
        if _in_waiver(sid, waivers):
            reason = waivers.get(sid) or waivers.get(re.sub(r'_\d+$', '', sid), '')
            waiver_ids.append(sid)
            warns.append('⚠️ إعفاء live_waivers.json: اللقطة الحيّة %s بلا مقطع (%s) — تُحسب ضدّ النسبة الحيّة'
                         % (sid, reason or 'بلا سبب مكتوب'))
        else:
            missing.append(sid)
    fallback_ids = []
    if missing and allow:
        fallback_ids = list(missing)
        warns.append('⚠️ ALLOW_LIVE_FALLBACK=1: لقطات live بلا مقطع تُستبدل بـ kb3d للمعاينة فقط، '
                     'والفيلم غير صالح للنشر: ' + ', '.join(missing))
        missing = []
    if missing:
        raise SystemExit(
            '⛔ لقطات live بلا مقطع حيّ ولا إعفاء: %s — ولّد GenerateVideo أو سجّل الإعفاء في '
            'live_waivers.json أو ALLOW_LIVE_FALLBACK=1 للمعاينة فقط' % ', '.join(missing))
    return fallback_ids, waiver_ids, warns


def apply_kb3d_reserve(shots, reserve, waivers=None, allow=None):
    """لا يُطبَّق الاحتياطي صامتاً: يلزم إعفاء أو ALLOW_LIVE_FALLBACK=1، مع تحذير واضح."""
    if allow is None:
        allow = os.environ.get('ALLOW_LIVE_FALLBACK') == '1'
    waivers = waivers or {}
    applied, warns, pending = [], [], []
    for s in shots:
        sid = s.get('id')
        if sid not in reserve:
            continue
        if allow or _in_waiver(sid, waivers):
            s['move3d'], s['energy'], s['ease'] = reserve[sid]
            applied.append(sid)
        else:
            pending.append(sid)
    if applied:
        why = 'ALLOW_LIVE_FALLBACK=1' if allow else 'إعفاء live_waivers.json'
        warns.append('⚠️ طُبقت حركة kb3d احتياطية (%s) على: %s — لا تُحسب حيّةً، وقد يكون الفيلم غير صالح للنشر'
                     % (why, ', '.join(applied)))
    if pending:
        warns.append('⚠️ لقطات live لها حركة احتياطية غير مُطبَّقة صامتاً (يُرفض المونتاج بلا مقطع أو إعفاء أو '
                     'ALLOW_LIVE_FALLBACK=1): ' + ', '.join(pending))
    return applied, warns


def write_film_meta(path, share, fallback_ids=None, waiver_ids=None, allow=False,
                    segments=None, warnings=None):
    fallback_ids = fallback_ids or []
    waiver_ids = waiver_ids or []
    publishable = (not fallback_ids) and (share + 1e-9 >= MIN_LIVE_SHARE)
    meta = {
        'min_live_share': MIN_LIVE_SHARE,
        'live_share': share,
        'publishable': publishable,
        'live_fallback': bool(fallback_ids) or bool(allow and fallback_ids),
        'allow_live_fallback': bool(allow),
        'fallback_shots': fallback_ids,
        'waivers': waiver_ids,
        'segments': segments or [],
        'warnings': warnings or [],
    }
    if not publishable:
        meta['note'] = 'غير صالح للنشر: نسبة حيّة دون العتبة أو بديل kb3d بـ ALLOW_LIVE_FALLBACK=1'
    json.dump(meta, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return meta


def _frame_png(path, t, w=320):
    from PIL import Image
    import io
    o = sp.run(['ffmpeg', '-v', 'error', '-ss', '%.3f' % max(0, t), '-i', path,
                '-frames:v', '1', '-vf', 'scale=%d:-2' % w, '-f', 'image2pipe', '-vcodec', 'png', '-'],
               capture_output=True)
    if not o.stdout:
        return None
    return Image.open(io.BytesIO(o.stdout)).convert('RGB')


def _ncc(a, b):
    import numpy as np
    if a.size != b.size:
        b = b.resize(a.size)
    aa = np.asarray(a.convert('RGB'), dtype=float)
    bb = np.asarray(b.convert('RGB'), dtype=float)
    la = aa.mean(axis=2).ravel()
    lb = bb.mean(axis=2).ravel()
    la0, lb0 = la - la.mean(), lb - lb.mean()
    n = float(np.linalg.norm(la0) * np.linalg.norm(lb0))
    if n < 1e-6:
        # إطار شبه موحّد: نقارن متوسط اللون (ارتباط الرمادي ينهار عند تباين صفر)
        dist = float(np.linalg.norm(aa.mean(axis=(0, 1)) - bb.mean(axis=(0, 1)))) / 255.0
        return max(0.0, 1.0 - dist / 0.35)
    return float(la0 @ lb0 / n)


# عتبة ارتباط الإطار في الفيلم بمقطع GenerateVideo (تحت هذا لا تُحسب اللقطة حيّة ظاهرة).
_VISIBLE_NCC = 0.45


def measure_film(proj, film=None, timeline=None, shots=None):
    """النسبة الحيّة الظاهرة فعلاً في الملف النهائي: تطابق مقطع GenerateVideo في زمن اللقطة. kb3d لا يُحسب."""
    P = lambda *a: os.path.join(proj, *a)
    shots = shots or json.load(open(P('shots.json'), encoding='utf-8'))
    timeline = timeline or (json.load(open(P('timeline.json'), encoding='utf-8')) if os.path.exists(P('timeline.json')) else {})
    film = film or P('film.mp4')
    if not timeline:
        raise SystemExit('⛔ لا timeline.json — لا يُقاس نصيب حيّ بلا جدول أزمنة')
    if not os.path.isfile(film):
        raise SystemExit('⛔ لا ملف فيلم: %s' % film)
    base = {s['id']: s for s in shots}
    total = sum(float(v[1]) for v in timeline.values()) or 1.0
    live = 0.0
    visible = []
    for sid, (st, dur) in timeline.items():
        s = base.get(sid) or base.get(re.sub(r'_\d+$', '', sid), {})
        if s.get('kind') != 'live' or s.get('still'):
            continue
        clip = clip_path(proj, s.get('id', sid))
        if not clip:
            continue
        t_film = float(st) + max(0.2, float(dur) * 0.5)
        # منتصف المقطع المصدر (قد يكون أقصر من اللقطة)
        try:
            from envpaths import FP
        except Exception:
            FP = 'ffprobe'
        o = sp.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', clip],
                    capture_output=True, text=True)
        try:
            cd = float(o.stdout.strip())
        except ValueError:
            cd = float(dur)
        t_clip = min(cd * 0.5, max(0.0, cd - 0.05))
        fr_f = _frame_png(film, t_film)
        fr_c = _frame_png(clip, t_clip)
        if fr_f is None or fr_c is None:
            continue
        score = _ncc(fr_f, fr_c)
        if score >= _VISIBLE_NCC:
            live += float(dur)
            visible.append((sid, score))
    share = live / total
    return {
        'share': share,
        'live_sec': live,
        'total_sec': total,
        'ok': share + 1e-9 >= MIN_LIVE_SHARE,
        'min_live_share': MIN_LIVE_SHARE,
        'visible': visible,
        'film': film,
    }


def _load_proj(proj):
    shots = json.load(open(os.path.join(proj, 'shots.json'), encoding='utf-8'))
    tl = None
    p = os.path.join(proj, 'timeline.json')
    if os.path.exists(p):
        tl = json.load(open(p, encoding='utf-8'))
    rt = None
    p = os.path.join(proj, 'real_timing.json')
    if os.path.exists(p):
        rt = json.load(open(p, encoding='utf-8'))
    return shots, shot_durations(shots, tl, rt), load_waivers(proj)


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) < 2 or a[0] not in ('lint', 'measure'):
        print(__doc__); return 2
    proj = a[1]
    shots, durs, waivers = _load_proj(proj)
    if a[0] == 'lint':
        if not durs:
            print('⛔ لا يمكن حساب المدد (timeline.json أو real_timing.json)'); return 1
        share, live, total, _ = plan_share(shots, durs, waivers)
        print('التخطيط الحيّ: %.1f%% من %.0f ث (المطلوب ≥ %.0f٪، kb3d لا يُحسب)'
              % (100 * share, total, 100 * MIN_LIVE_SHARE))
        errs = plan_errors(shots, durs, waivers)
        for e in errs:
            print('⛔', e)
        return 1 if errs else 0
    film = a[2] if len(a) > 2 else os.path.join(proj, 'film.mp4')
    res = measure_film(proj, film)
    print('النسبة الحيّة الظاهرة في %s: %.1f%% من %.0f ث (المطلوب ≥ %.0f٪)'
          % (os.path.basename(res['film']), 100 * res['share'], res['total_sec'], 100 * res['min_live_share']))
    if not res['ok']:
        print('⛔ دون العتبة — حركة kb3d لا تُحسب، ولا يُنشر حتى تُستكمل مقاطع GenerateVideo')
        return 1
    print('✓ النسبة الحيّة الظاهرة بلغت العتبة')
    return 0


if __name__ == '__main__':
    sys.exit(main())
