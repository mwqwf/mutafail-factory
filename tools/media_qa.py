#!/usr/bin/env python3
"""🔍 فحصُ الوسائط قبل العرض على المالك: المدّة والأبعاد والجهارة والسواد والتجمّد والصمت وتساوي مساري الصورة والصوت.

درس مؤتة 2026-10-07: كان فحصي بـ`ffmpeg -v error` فكتم مرشّحات blackdetect وfreezedetect وsilencedetect (تكتب نتائجها
بمستوى info) فبدت «سليمة» وهي لم تُفحص، وفاتني تجمّدُ آخر كلّ ريلز 5–7 ث. هنا تُقرأ النتائج من مستوى info دائماً،
والتجمّد يُقاس في وسط الإطار (crop) لأنّ شريط التقدّم والترجمة المتحرّكة يُخفيانه عن المرشّح.

    python3 tools/media_qa.py <ملف>... [--reel]      # --reel: عموديّ ≤ 175 ث، والجهارة لكلّ ملف
الخروج 1 إن وُجد عيبٌ مانع، و0 إن سلم كلّ شيء — والتقرير سطرٌ لكلّ ملف.
"""
from __future__ import annotations

import json
import re
import subprocess as sp
import sys

LUFS_RANGE = (-15.5, -12.5)      # معيار يوتيوب −14 ± 1.5
FREEZE_MAX, BLACK_MAX, SILENCE_MAX = 2.0, 1.0, 2.0


def probe(f: str) -> dict:
    o = sp.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height,r_frame_rate,duration',
                '-of', 'json', f], capture_output=True, text=True, check=True).stdout
    return json.loads(o)


def measure(f: str, w: int, h: int) -> dict:
    """تمريرةٌ واحدة: التجمّد في وسط الإطار، والسواد، والصمت، والجهارة — بمستوى info لا error."""
    # من 20٪ إلى 70٪ من الارتفاع: فوق ترجمة الريلز المتحرّكة وتحت شريط تقدّمه، فلا تُخفي حركتُهما تجمّدَ الصورة
    cw, ch, cy = int(w * 0.8) // 2 * 2, int(h * 0.5) // 2 * 2, int(h * 0.2)
    vf = 'crop=%d:%d:(iw-%d)/2:%d,freezedetect=n=0.003:d=1' % (cw, ch, cw, cy)
    err = sp.run(['ffmpeg', '-hide_banner', '-nostats', '-i', f, '-vf', vf, '-af', 'silencedetect=n=-45dB:d=1.5,ebur128=peak=true',
                  '-f', 'null', '-'], capture_output=True, text=True).stderr
    blk = sp.run(['ffmpeg', '-hide_banner', '-nostats', '-i', f, '-an', '-vf', 'blackdetect=d=0.3:pic_th=0.97:pix_th=0.08',
                  '-f', 'null', '-'], capture_output=True, text=True).stderr
    end = float(probe(f)['format']['duration'])

    def spans(text, start_key, dur_key):
        starts = [float(x) for x in re.findall(start_key + r':\s*([0-9.]+)', text)]
        durs = [float(x) for x in re.findall(dur_key + r':\s*([0-9.]+)', text)]
        # مقطعٌ بلا مدّة يمتدّ إلى نهاية الملف (التجمّد أو الصمت حتى آخره)
        return [(s, durs[i] if i < len(durs) else round(end - s, 3)) for i, s in enumerate(starts)]

    summ = err[err.rfind('Summary:'):] if 'Summary:' in err else ''
    lufs = re.search(r'I:\s*(-?[0-9.]+) LUFS', summ)
    peak = re.search(r'Peak:\s*(-?[0-9.inf]+) dBFS', summ)
    return {'freeze': spans(err, 'freeze_start', 'freeze_duration'),
            'silence': spans(err, 'silence_start', 'silence_duration'),
            'black': [(float(a), float(b) - float(a)) for a, b in re.findall(r'black_start:([0-9.]+) black_end:([0-9.]+)', blk)],
            'lufs': float(lufs.group(1)) if lufs else None, 'peak': peak.group(1) if peak else None}


def check(f: str, reel: bool = False) -> tuple[list[str], dict]:
    p = probe(f)
    v = next((s for s in p['streams'] if s['codec_type'] == 'video'), None)
    a = next((s for s in p['streams'] if s['codec_type'] == 'audio'), None)
    d = float(p['format']['duration'])
    errs: list[str] = []
    if not v:
        return ['لا مسار صورة'], {}
    w, h = int(v['width']), int(v['height'])
    m = measure(f, w, h)
    if a and v.get('duration') and a.get('duration') and float(a['duration']) - float(v['duration']) > 0.5:
        errs.append('الصورة أقصر من الصوت بـ%.1f ث' % (float(a['duration']) - float(v['duration'])))
    errs += ['تجمّدٌ %.1f ث عند %.1f' % (du, s) for s, du in m['freeze'] if du >= FREEZE_MAX]
    errs += ['سوادٌ %.1f ث عند %.1f' % (du, s) for s, du in m['black'] if du >= BLACK_MAX]
    errs += ['صمتٌ %.1f ث عند %.1f' % (du, s) for s, du in m['silence'] if du >= SILENCE_MAX]
    if a and m['lufs'] is not None and not (LUFS_RANGE[0] <= m['lufs'] <= LUFS_RANGE[1]):
        errs.append('الجهارة %.1f LUFS خارج %s' % (m['lufs'], LUFS_RANGE))
    if reel and not (h > w and d <= 175):
        errs.append('ليس ريلزاً عموديّاً دون 175 ث (%dx%d · %.1f ث)' % (w, h, d))
    info = {'مدّة': round(d, 2), 'أبعاد': '%dx%d' % (w, h), 'إطارات/ث': v.get('r_frame_rate'), 'LUFS': m['lufs'], 'ذروة': m['peak'],
            'تجمّد': m['freeze'], 'سواد': m['black'], 'صمت': m['silence']}
    return errs, info


def main(argv: list[str]) -> int:
    reel = '--reel' in argv
    files = [x for x in argv if not x.startswith('--')]
    bad = 0
    for f in files:
        errs, info = check(f, reel)
        print(('⛔ ' if errs else '✅ ') + f + ' · ' + json.dumps(info, ensure_ascii=False) + (' · ' + '؛ '.join(errs) if errs else ''))
        bad += bool(errs)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
