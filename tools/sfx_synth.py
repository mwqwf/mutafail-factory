# -*- coding: utf-8 -*-
"""مؤثّراتٌ صوتية طبيعية مركّبة من الضجيج — طلب المالك 2026-10-04: «أريده أقوى وأكثر إبهاراً».

حفيفُ الهواء (whoosh) حين تندفع كلمةٌ أو تنقلب الكاميرا، وارتطامٌ ثقيل (thud) حين تهبط الضربة المكتوبة أو يُختم التاريخ.
⛔ لا موسيقى ولا آلة ولا نغمة: كلّها ضجيجٌ مرشَّح (هواءٌ يندفع، وأرضٌ ترتطم ويتناثر غبارها) بلا أيّ ترددٍ ثابتٍ يُسمع نغماً —
فلا طبل ولا «بوم» لحنيّ. تُولَّد مرّةً لكلّ مونتاج في work/ وتُجدول في مسارٍ واحد (mont_hybrid: hits.wav).
"""
from __future__ import annotations

import math
import os
import wave

import numpy as np

SR = 48000


def _svf_bandpass(x, fc, q=0.9):
    """مرشّح حالةٍ متغيّرة بتردّد قطعٍ يتغيّر عيّنةً عيّنة (fc مصفوفة)."""
    low = band = 0.0
    out = np.empty_like(x)
    for i in range(len(x)):
        f = 2 * math.sin(math.pi * min(fc[i], SR / 6) / SR)
        high = x[i] - low - q * band
        band += f * high
        low += f * band
        out[i] = band
    return out


def _lowpass(x, fc):
    a = math.exp(-2 * math.pi * fc / SR)
    y = np.empty_like(x)
    s = 0.0
    for i in range(len(x)):
        s = (1 - a) * x[i] + a * s
        y[i] = s
    return y


def _norm(x, peak_db):
    m = float(np.abs(x).max()) or 1.0
    return x / m * (10 ** (peak_db / 20))


def whoosh(dur=0.55, f0=350.0, f1=2600.0, seed=0):
    """هواءٌ يندفع: ضجيجٌ بمرشّحٍ يصعد تردّده ثم يهبط (اقترابٌ ثم ابتعاد)، وغلافٌ يتصاعد ثم يخمد سريعاً."""
    rng = np.random.default_rng(seed)
    n = int(SR * dur)
    t = np.arange(n) / n
    peak = 0.62
    shape = np.where(t < peak, (t / peak) ** 2.2, 1 - np.clip((t - peak) / (1 - peak), 0, 1) ** 0.7)
    fc = f0 * (f1 / f0) ** np.clip(shape, 0, 1)
    x = _svf_bandpass(rng.normal(0, 1, n), fc, 0.7)
    body = _lowpass(rng.normal(0, 1, n), 220.0) * 2.5            # جسمٌ منخفض خفيف
    env = np.where(t < peak, (t / peak) ** 2.5, np.exp(-np.clip((t - peak) / (1 - peak), 0, 1) * 4.5))
    y = (x + 0.35 * body) * env
    fade = min(n, int(0.01 * SR))
    y[-fade:] *= np.linspace(1, 0, fade)
    return _norm(y, -4.0)


def thud(dur=0.9, seed=1):
    """ارتطامٌ ثقيل بالأرض: دفعةُ ضجيجٍ منخفضٍ تخمد سريعاً، ونقرةُ ارتطامٍ قصيرة، وتناثرُ غبارٍ خافت — بلا نغمة."""
    rng = np.random.default_rng(seed)
    n = int(SR * dur)
    t = np.arange(n) / SR
    low = _lowpass(_lowpass(rng.normal(0, 1, n), 140.0), 140.0) * np.exp(-t / 0.11) * 9.0
    click = rng.normal(0, 1, n) * np.exp(-t / 0.006)
    click = click - _lowpass(click, 900.0)                       # نقرةٌ عالية التردّد (ما فوق 900 هرتز)
    debris = _svf_bandpass(rng.normal(0, 1, n), np.full(n, 2200.0), 1.2) * np.exp(-t / 0.28) * 0.35
    y = low + 0.6 * click + debris
    att = int(0.002 * SR)
    y[:att] *= np.linspace(0, 1, att)
    return _norm(y, -2.0)


def write(path, y):
    pcm = (np.clip(y, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path


def bank(work):
    """يولّد بنك المؤثّرات في work/sfx إن لم يكن (حتميّ بالبذور، فالنتيجة نفسها في كلّ شوط)."""
    d = os.path.join(work, 'sfx'); os.makedirs(d, exist_ok=True)
    spec = {'whoosh_fast': lambda: whoosh(0.55, 380, 2800, 3),
            'whoosh_slow': lambda: whoosh(1.15, 180, 1300, 5),
            'thud': lambda: thud(0.9, 7),
            'thud_soft': lambda: thud(0.6, 11) * 0.7}
    out = {}
    for k, fn in spec.items():
        p = os.path.join(d, k + '.wav')
        if not os.path.exists(p):
            write(p, fn())
        out[k] = p
    return out


def mix(hits, dur, bank_paths, out):
    """يجمع المؤثّرات القصيرة [(بداية بالثواني، اسم المؤثّر، مستوى)] في مسارٍ واحدٍ بطول dur."""
    n = int(SR * dur) + SR
    acc = np.zeros(n, np.float32)
    cache = {}
    for st, name, vol in hits:
        if name not in cache:
            with wave.open(bank_paths[name], 'rb') as w:
                cache[name] = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32767
        y = cache[name] * vol
        i = int(max(0.0, st) * SR)
        j = min(n, i + len(y))
        if j > i:
            acc[i:j] += y[:j - i]
    peak = float(np.abs(acc).max())
    if peak > 0.98:                                              # تراكبٌ نادر: يُخفض المسار كلّه لا يُقصّ
        acc *= 0.98 / peak
    return write(out, acc[:int(SR * dur)])
