# -*- coding: utf-8 -*-
"""انتقالاتٌ بين اللقطات بحسب الموقف — أمر المالك 2026-10-04 (فيلم «الأرك»).

نصُّ الأمر: «استعمل أساليب متعدّدة لم نجرّبها من قبل… مثل تلاشي الصور وظهور الجديدة، وانقسام صورة ثم ظهور الجديدة
مكانها، والكثير الكثير من الأساليب حسب الموقف».

كيف يبقى الصوت متزامناً؟ الانتقال مدّته T يتمركز على نقطة القطع نفسها: آخر T/2 من اللقطة الأولى (مع تثبيت آخر إطارٍ
منها T/2) يمتزج بأوّل T/2 من الثانية (مع تثبيت أوّل إطارٍ منها T/2) عبر xfade في مقطعٍ مستقلّ مدّته T، وتُقصّ اللقطتان
بقدر T/2 من جهة الانتقال. فعدد الإطارات الكلّيّ لا يتغيّر إطاراً واحداً، وتبقى بدايات اللقطات في timeline.json كما هي.
T من مضاعفات 0.08 ث فيقع T/2 على إطارٍ كامل (25 إطاراً/ث).

السياسة (plan) — تختار ولا تُكثر:
  • أوّل لقطةٍ في فصلٍ جديد ← تعتيمٌ إلى السواد (fadeblack)
  • لقطةٌ على الصورة نفسها التي قبلها ← ذوبانٌ ناعم (dissolve)
  • لقطةٌ فيها ومضةٌ أو ضربةٌ في أوّلها ← قطعٌ حادّ (الومضة هي الانتقال)
  • المعركة ← قطعٌ حادّ غالباً، وكلّ رابع قطعٍ خطفةٌ سريعة (slideleft · smoothleft · hblur · wipeleft)
  • خارج المعركة ← تلاشٍ متقاطع كلّ ثاني قطع (fade · dissolve)، وأسلوبٌ مختلف كلّ سادس (coverleft · revealleft · zoomin · …)
  • والحقل tr في اللقطة يغلب السياسة: "cut" أو اسم انتقال أو [الاسم، المدّة] — للحظات الكشف مثلاً:
    vertopen/horzopen (انقسام الصورة ثم ظهور الجديدة مكانها)، circleopen، radial، hlslice …
"""
from __future__ import annotations

import os
import subprocess as sp
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envpaths  # noqa: E402

FPS = 25
WHIP = ['slideleft', 'smoothleft', 'hblur', 'wipeleft']
SOFT = ['fade', 'dissolve']
STYLE = ['coverleft', 'revealleft', 'zoomin', 'squeezeh', 'diagtl', 'circleopen']
KNOWN = set(WHIP + SOFT + STYLE + ['fadeblack', 'fadewhite', 'vertopen', 'vertclose', 'horzopen', 'horzclose',
                                   'circleclose', 'radial', 'hlslice', 'hrslice', 'vuslice', 'vdslice', 'pixelize',
                                   'smoothright', 'smoothup', 'smoothdown', 'slideright', 'slideup', 'slidedown',
                                   'wiperight', 'wipeup', 'wipedown', 'coverright', 'revealright', 'squeezev', 'fadegrays',
                                   'distance', 'rectcrop', 'circlecrop', 'diagtr', 'diagbl', 'diagbr'])


def q(T: float) -> float:
    """مدّةٌ من مضاعفات 0.08 ث (فنصفها إطارٌ كامل)."""
    return max(0.16, round(T / 0.08) * 0.08)


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
    """لكلّ حدٍّ بين لقطتين (i، i+1): None للقطع الحادّ أو (اسم الانتقال، المدّة)."""
    secs = sections_of(shots, sections)
    starts = set()
    firsts = {x['id'] for x in sections[1:]}
    for i, s in enumerate(shots):
        if (s.get('blocks') or [None])[0] in firsts:
            starts.add(i)
    out: list = []
    kw = ks = kt = 0
    for i in range(len(shots) - 1):
        a, b = shots[i], shots[i + 1]
        tr = b.get('tr', 'auto')
        if tr in (None, 'cut'):
            out.append(None); continue
        if tr != 'auto':
            name, T = (tr[0], float(tr[1])) if isinstance(tr, (list, tuple)) else (tr, 0.64)
            out.append((name, q(T)) if name in KNOWN else None); continue
        if i + 1 in starts:
            out.append(('fadeblack', 0.8)); continue
        if b.get('flash') or (b.get('slam') and float(b['slam'].get('at', 1.0)) < 0.3) or b.get('lipsync'):
            out.append(None); continue
        if b.get('file') and b.get('file') == a.get('file'):
            out.append(('dissolve', 0.48)); continue
        if secs[i + 1] == 'battle':
            if i % 4 == 3:
                out.append((WHIP[kw % len(WHIP)], 0.32)); kw += 1
            else:
                out.append(None)
        else:
            if i % 6 == 4:
                out.append((STYLE[kt % len(STYLE)], 0.56)); kt += 1
            elif i % 2 == 1:
                out.append((SOFT[ks % len(SOFT)], 0.64)); ks += 1
            else:
                out.append(None)
    return out


def frames(f: str) -> int:
    o = sp.run([envpaths.FP, '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=nb_read_packets',
                '-of', 'csv=p=0', f], capture_output=True, text=True).stdout.strip()
    try:
        return int(o.split(',')[0])
    except ValueError:
        return 0


def apply(segs: list, tplan: list, work: str, enc: list, tag: str) -> list:
    """يعيد قائمة مقاطع للربط (concat -c copy): المقاطع مقصوصةً حول الانتقالات، وبينها مقاطع الانتقال.
    حدٌّ لا تتّسع لقطتاه للانتقال (أقصر من مدّته مرّتين) يبقى قطعاً حادّاً."""
    d = os.path.join(work, 'tr_' + tag); os.makedirs(d, exist_ok=True)
    nf = [frames(s) for s in segs]
    tp = list(tplan) + [None]
    for i, p in enumerate(tplan):                     # لا انتقال أطول من نصف أيٍّ من اللقطتين
        if p and (nf[i] < p[1] * FPS * 2 or nf[i + 1] < p[1] * FPS * 2):
            tp[i] = None
    out = []
    for i, seg in enumerate(segs):
        hp = int(round(tp[i - 1][1] * FPS / 2)) if i > 0 and tp[i - 1] else 0
        hn = int(round(tp[i][1] * FPS / 2)) if tp[i] else 0
        if hp or hn:
            tr = os.path.join(d, 'cut_%03d.mp4' % i)
            if not (os.path.exists(tr) and frames(tr) == nf[i] - hp - hn):
                sp.run([envpaths.FF, '-v', 'error', '-y', '-i', seg, '-vf',
                        'trim=start_frame=%d:end_frame=%d,setpts=PTS-STARTPTS' % (hp, nf[i] - hn), '-an'] + enc + [tr], check=True)
            out.append(tr)
        else:
            out.append(seg)
        if tp[i]:
            name, T = tp[i]
            h = int(round(T * FPS / 2)); n = 2 * h
            x = os.path.join(d, 'x_%03d_%s.mp4' % (i, name))
            if not (os.path.exists(x) and frames(x) == n):
                # إطاران زائدان في كلّ مدخل ثم -frames:v n: كان xfade يُسقط آخر إطار فيقصر الفيلم إطاراً عند كلّ انتقال
                fa = '[0:v]trim=start_frame=%d,setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop=%d,format=yuv420p,settb=AVTB[a]' % (nf[i] - h, h + 2)
                fb = '[1:v]trim=end_frame=%d,setpts=PTS-STARTPTS,tpad=start_mode=clone:start=%d,format=yuv420p,settb=AVTB[b]' % (h + 2, h)
                xf = '[a][b]xfade=transition=%s:duration=%.3f:offset=0,format=yuv420p[v]' % (name, n / FPS)
                sp.run([envpaths.FF, '-v', 'error', '-y', '-i', seg, '-i', segs[i + 1], '-filter_complex', ';'.join([fa, fb, xf]),
                        '-map', '[v]', '-frames:v', str(n), '-an'] + enc + [x], check=True)
            out.append(x)
    return out
