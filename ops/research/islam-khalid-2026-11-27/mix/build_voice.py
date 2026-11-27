# -*- coding: utf-8 -*-
# يبني مسار الكلام من صوت CI الكامل (كل كتلة + 0.6 ث حشو) على صيغة mont_hybrid: فجوة 0.30 ث ثم atempo 1.05.
# الكتلة تُقصّ من 30 م ث قبل بدايتها (الكلام يبدأ فوراً، وآخرها صمت ≥ 250 م ث)، وتُروَّض البدايات الحادّة المعزولة
# (قفزة > 8000 بعد صمت — «نقرات» audio_checks في d_006/d_015/d_044/d_049) بمنحدر 8 م ث. ويكتب proj/audio/<id>.wav لفحص audio_checks.
import re, subprocess, numpy as np, os
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 24000
d = [(m[1], float(m[2])) for m in re.finditer(r'full/(d_\d+): ([\d.]+)', open(os.path.join(H, 'voice_full/durations.txt')).read())]
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(H, 'voice_full/islam-khalid-full-voice-full.mp3'), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32).copy()
os.makedirs(os.path.join(H, 'proj/audio'), exist_ok=True)
off = 0; parts = []; fixed = {}
for i, (k, du) in enumerate(d):
    if off:
        a = int(round((off - 0.03) * SR)); seg = x[a:a + int(round(du * SR))].copy()
    else:
        seg = np.concatenate([np.zeros(int(0.03 * SR), np.float32), x[:int(round(du * SR)) - int(0.03 * SR)]])
    s16 = (seg * 32768).astype(int); dd = np.abs(np.diff(s16)); idx = np.where(dd > 8000)[0]
    iso = sorted({int(j) for j in idx if j > 240 and np.abs(s16[j - 240:j - 24]).max() < 2000})
    done = -1
    for j in iso:
        if j <= done: continue
        r = int(0.008 * SR); st = max(0, j - 24)
        seg[st:st + r] *= np.linspace(0, 1, len(seg[st:st + r]), dtype=np.float32) ** 2
        done = st + r; fixed.setdefault(k, []).append(round(j / SR, 3))
    parts.append(seg)
    (np.clip(seg, -1, 1) * 32767).astype(np.int16).tofile('/tmp/b.s16')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '1', '-i', '/tmp/b.s16', os.path.join(H, 'proj/audio', k + '.wav')], check=True)
    if i < len(d) - 1: parts.append(np.zeros(int(0.3 * SR), np.float32))
    off += du + 0.6
np.concatenate(parts).astype(np.float32).tofile('/tmp/v.f32')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '/tmp/v.f32', '-af', 'atempo=1.05', '-ar', '48000', os.path.join(H, 'mix/voice.wav')], check=True)
print('onset ramps:', fixed)
