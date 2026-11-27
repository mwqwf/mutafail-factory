# -*- coding: utf-8 -*-
"""سجلّ مكتبة المؤثّرات المقيس (أمر المالك 2026-11-27: «المؤثّرات مزعجة في بعض الأماكن»).

كان المونتاج يشغّل كلّ ملفٍّ بمستوى ثابت (0.22) مهما كانت جهارته، والمكتبة تتفاوت من −44 إلى −13 LUFS
(31 وحدة)، وبعضها مقصوص الذروة (+4 dBFS) وبعضها حادّ (76–92٪ من طاقته بين 2 و6 كيلوهرتز). فكان الصوت نفسه
يُسمع همساً في لقطة وصراخاً في أخرى. هنا يُقاس كلّ ملفّ مرّة ويُكتب في `assets/sfx/manifest.json`:
الجهارة، والذروة، وحصّة الحدّة، وحكم `tonal_gate`، وكسبٌ يرفعه أو يخفضه إلى جهارة مرجعية واحدة (REF_LUFS)،
ومرشّحٌ يروّض الحدّة، وحالة: ok · tamed (يُستعمل بالمرشّح) · reject (لا يُستعمل أبداً).

    python3 tools/sfx_library.py build     # يقيس ويكتب manifest.json
    python3 tools/sfx_library.py check     # يفشل إن وُجد ملفّ بلا سطر رخصة أو بلا قياس
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX = os.path.join(ROOT, 'assets', 'sfx')
MANIFEST = os.path.join(SFX, 'manifest.json')
REF_LUFS = -23.0          # كلّ ملفّ يُرفع/يُخفض إليها قبل مستوى الإشارة النسبيّ في ورقة الإشارات
HARSH_MAX = 0.45          # حصّة 2–6 كيلوهرتز فوقها ⇒ مرشّح ترويض إلزاميّ
HARSH_REJECT = 0.80       # فوقها ⇒ لا يُستعمل (صفير/صرير يجرح الأذن حتى بعد الترويض)
METAL = ('swords', 'sworddraw', 'battle')   # المعدن حادٌّ بطبعه: يُروَّض ولا يُرفض بالحدّة وحدها
QUIET_REJECT = -50.0      # أخفت من هذا ⇒ رفعه يُظهر ضجيج التسجيل
TAME = 'lowpass=f=4200,equalizer=f=3200:t=q:w=1.2:g=-6'
SR = 48000


def pcm(path: str) -> np.ndarray:
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def loudness(path: str, af: str | None = None) -> tuple[float, float]:
    """(LUFS متكامل، الذروة الحقيقية dBTP) بـebur128."""
    chain = (af + ',' if af else '') + 'ebur128=peak=true'
    e = subprocess.run(['ffmpeg', '-nostats', '-i', path, '-af', chain, '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    i = re.findall(r'I:\s+(-?[\d.]+|-inf) LUFS', e)
    p = re.findall(r'Peak:\s+(-?[\d.]+|-inf) dBFS', e)
    f = lambda v: -70.0 if v == '-inf' else float(v)
    return f(i[-1]) if i else -70.0, f(p[-1]) if p else -70.0


def harsh_share(x: np.ndarray) -> float:
    """حصّة الطاقة بين 2 و6 كيلوهرتز في النوافذ المسموعة (لا في الصمت)."""
    n = int(0.4 * SR)
    tot = band = 0.0
    for i in range(0, max(1, len(x) - n), n):
        w = x[i:i + n]
        if len(w) < n or float(np.sqrt(np.mean(w * w))) < 1e-3:
            continue
        S = np.abs(np.fft.rfft(w * np.hanning(n))) ** 2
        f = np.fft.rfftfreq(n, 1 / SR)
        tot += S.sum(); band += S[(f >= 2000) & (f < 6000)].sum()
    return float(band / tot) if tot else 0.0


def measure(path: str) -> dict:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tonal_gate
    lufs, peak = loudness(path)
    hs = harsh_share(pcm(path))
    tonal, _why = tonal_gate.verdict(path)
    status, eq = 'ok', None
    if hs > HARSH_MAX:
        status, eq = 'tamed', TAME
    cat = os.path.basename(path).rsplit('_', 1)[0]
    if tonal or (hs > HARSH_REJECT and cat not in METAL) or lufs < QUIET_REJECT:
        status = 'reject'
    if eq:
        lufs_eq, _ = loudness(path, eq)
    else:
        lufs_eq = lufs
    gain = float(np.clip(REF_LUFS - lufs_eq, -24.0, 24.0))
    return {'file': os.path.basename(path), 'category': os.path.basename(path).rsplit('_', 1)[0],
            'lufs': round(lufs, 1), 'peak_dbfs': round(peak, 1), 'harsh_2_6k': round(hs, 2), 'tonal': bool(tonal),
            'clipped_source': peak > -0.1, 'status': status, 'eq': eq, 'gain_db': round(gain, 1)}


def build() -> dict:
    out = {'ref_lufs': REF_LUFS, 'files': {}}
    for p in sorted(glob.glob(os.path.join(SFX, '*.ogg'))):
        m = measure(p)
        out['files'][m['file']] = m
        print('%-18s %-6s %6.1f LUFS  ذروة %5.1f  حدّة %.2f  %s' % (m['file'], m['status'], m['lufs'], m['peak_dbfs'], m['harsh_2_6k'],
                                                               'نغمي!' if m['tonal'] else ''))
    json.dump(out, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return out


def load() -> dict:
    return json.load(open(MANIFEST, encoding='utf-8'))


def check() -> int:
    lic = open(os.path.join(SFX, 'LICENSES.md'), encoding='utf-8').read()
    man = load()['files'] if os.path.exists(MANIFEST) else {}
    errs = []
    for p in sorted(glob.glob(os.path.join(SFX, '*.ogg'))):
        b = os.path.basename(p)
        if '| %s |' % b not in lic:
            errs.append('بلا سطر رخصة CC0: ' + b)
        if b not in man:
            errs.append('بلا قياس في manifest.json: ' + b)
    for e in errs:
        print('⛔', e)
    return 1 if errs else 0


if __name__ == '__main__':
    cmd = (sys.argv[1:] or ['check'])[0]
    sys.exit(0 if cmd == 'build' and build() else check())
