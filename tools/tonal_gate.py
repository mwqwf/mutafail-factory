# -*- coding: utf-8 -*-
"""كشف محلي لمحتوى لحني/نغمي في طبقة المؤثّرات — أمر المالك 2026-11-22.

الموسيقى والآلات (ومنها الطبول والأبواق الحربية النغمية) ممنوعة. لا يُستدعى جيميناي.
الفحص: طيف جيبي مستقر (ذروة ضيّقة طويلة) في ملف موجي أو ogg عبر ffmpeg+numpy.

الاستعمال: python tools/tonal_gate.py <ملف.wav|ogg> [...]
خروج 1 إن رُصد مسار نغمي محتمل.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import numpy as np

SR = 16000


def _pcm(path: str) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def verdict(path: str, win_s: float = 0.5) -> tuple[bool, str]:
    """True = يبدو نغمياً/لحنياً (مرفوض)."""
    try:
        x = _pcm(path)
    except (OSError, subprocess.CalledProcessError) as e:
        return False, "تعذّرت القراءة: %s" % e
    if len(x) < SR // 2:
        return False, "قصير"
    n = int(win_s * SR)
    hop = n // 2
    # نافذة: إن بقيت الذروة في حزمة ضيّقة (< 3 صناديق) فوق 80Hz لأكثر من نصف النوافذ بطاقة كافية
    tonal = 0
    voiced = 0
    for i in range(0, len(x) - n, hop):
        w = x[i:i + n] * np.hanning(n)
        rms = float(np.sqrt(np.mean(w * w)))
        if rms < 0.02:
            continue
        voiced += 1
        spec = np.abs(np.fft.rfft(w))
        # تجاهل تحت 80 Hz (ارتطام وريح)
        freqs = np.fft.rfftfreq(n, 1 / SR)
        spec[freqs < 80] = 0
        if spec.max() <= 0:
            continue
        k = int(np.argmax(spec))
        band = spec[max(0, k - 2):k + 3].sum()
        if band > 0.35 * spec.sum() and 80 <= freqs[k] <= 2000:
            tonal += 1
    if voiced and tonal / voiced >= 0.55 and tonal >= 4:
        return True, "ذروة طيفية ضيّقة في %d/%d نافذة — شبهة مسار نغمي" % (tonal, voiced)
    return False, "لا شبهة لحن (نغمي %d من %d)" % (tonal, voiced)


def check_paths(paths: list[str]) -> int:
    bad = []
    for p in paths:
        if not p or not os.path.exists(p):
            continue
        hit, why = verdict(p)
        print("%s: %s" % (os.path.basename(p), why))
        if hit:
            bad.append(p)
    if bad:
        print("⛔ طبقة نغمية/موسيقية محتملة في: %s — الموسيقى والآلات ممنوعة" % ", ".join(map(os.path.basename, bad)))
        return 1
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    return check_paths(argv)


if __name__ == "__main__":
    sys.exit(main())
