# -*- coding: utf-8 -*-
"""⛔ صورة كلّ لقطةٍ في كتلتها وحدها — أمر المالك 2026-11-27 (إسلام خالد): «مشهدٌ في غير موضعه خطأٌ في المعنى لا يُقبل».

الاستعمال: python tools/shot_image_gate.py <proj> [film.mp4]
١) فحصٌ ثابت: لا لقطة تحمل clip من لقطةٍ بصورةٍ أخرى (الاستعارة أُلغيت من mont_hybrid من جذورها).
٢) فحصٌ مرئيّ على الفيلم نفسه: إطارٌ من منتصف كلّ لقطة (timeline.json) يُقارن بمراجع كلّ صورة (الصورة + إطارات مقطعها الحيّ)؛
   يفشل إن كان شبهُ الإطار بصورة لقطةٍ أخرى يزيد على شبهه بصورته بأكثر من MARGIN (الصور المعتمة المتشابهة ≤ 0.14 في القياس).
يخرج بـ1 عند أيّ خطأ."""
import json, os, subprocess as sp, sys, tempfile
import numpy as np
from PIL import Image
MARGIN = 0.20
FF = os.environ.get('FFMPEG', 'ffmpeg')


def feat(im):
    v = np.asarray(im.convert('L').resize((48, 27)), float).ravel(); v -= v.mean()
    n = np.linalg.norm(v); return v / n if n else v


def main(proj, film=None):
    P = lambda *a: os.path.join(proj, *a)
    film = film or P('film.mp4')
    shots = json.load(open(P('shots.json'), encoding='utf-8')); SHOT = {s['id']: s for s in shots}
    tl = json.load(open(P('timeline.json'), encoding='utf-8'))

    def img(s):
        for n in (s['id'], os.path.splitext(s.get('file') or '')[0]):
            for d in ('images', 'img'):
                for e in ('jpg', 'png'):
                    if n and os.path.exists(P(d, '%s.%s' % (n, e))): return P(d, '%s.%s' % (n, e))
    stem = lambda s: os.path.splitext(os.path.basename(img(s) or s['id']))[0]
    errs = ['%s يستعير مقطع %s (صورةٌ أخرى)' % (s['id'], s['clip']) for s in shots
            if s.get('clip') and s['clip'] in SHOT and stem(SHOT[s['clip']]) != stem(s)]
    tmp = tempfile.mkdtemp(prefix='sig_')
    refs = {}
    for s in shots:
        k = stem(s)
        if k in refs or not img(s): continue
        refs[k] = [feat(Image.open(img(s)))]
        c = P('clips', k + '.mp4')
        if os.path.exists(c):
            sp.run([FF, '-v', 'error', '-y', '-i', c, '-vf', 'fps=1,scale=192:-1', os.path.join(tmp, k + '_%02d.png')], check=True)
            refs[k] += [feat(Image.open(os.path.join(tmp, f))) for f in sorted(os.listdir(tmp)) if f.startswith(k + '_')]
    bad = 0
    for s in shots:
        if s['id'] not in tl or not img(s): continue
        st, du = tl[s['id']][:2]
        f = os.path.join(tmp, 'f.png')
        sp.run([FF, '-v', 'error', '-y', '-ss', '%.2f' % (st + du / 2), '-i', film, '-frames:v', '1', '-vf', 'scale=192:-1', f], check=True)
        x = feat(Image.open(f)); k = stem(s)
        sc = {r: max(float(x @ v) for v in vs) for r, vs in refs.items()}
        best = max(sc, key=sc.get)
        if best != k and sc[best] - sc[k] > MARGIN:
            bad += 1; errs.append('%s عند %.1f ث يشبه صورة %s (%.2f) أكثر من صورته %s (%.2f)' % (s['id'], st, best, sc[best], k, sc[k]))
    for e in errs:
        print('⛔', e)
    print('✅ صورة كلّ لقطةٍ في كتلتها (%d لقطة)' % len(shots) if not errs else '⛔ shot_image_gate: %d خطأ' % len(errs))
    return 1 if errs else 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    sys.exit(main(*sys.argv[1:3]))
