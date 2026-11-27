# -*- coding: utf-8 -*-
"""يقسم كتل الصوت عند الوقفات الطبيعية إلى أجزاءٍ بعدد لقطاتها (خطة subjects.py + extra.py)، ويكتب
proj/blocks.json (الكتل الفرعية) وproj/real_timing.json وproj/shots.json (لقطةٌ لكلّ جزء، بمعرّفٍ فريد ومقطعٍ خاصّ).
مبنيّ على split_blocks.py لفيلم خالد: القصّ عند منتصف وقفة ويُحذف منها ≤0.30 ث يعيدها GAP في المونتاج."""
import json, os, re, shutil, sys, wave
import numpy as np
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); P = os.path.join(D, 'proj')
sys.path.insert(0, os.path.join(D, 'plan'))
import extra
GAP, T = 0.30, 1.05
A, AF = os.path.join(P, 'audio'), os.path.join(P, 'audio_full')
B0 = json.load(open(os.path.join(P, 'blocks_full.json') if os.path.exists(os.path.join(P, 'blocks_full.json')) else os.path.join(P, 'blocks.json'), encoding='utf-8'))
json.dump(B0, open(os.path.join(P, 'blocks_full.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if not os.path.isdir(AF):
    os.makedirs(AF)
    for b in B0: shutil.copy(os.path.join(A, b['id'] + '.wav'), AF)
draft = json.load(open(os.path.join(D, 'plan', 'shots_draft.json'), encoding='utf-8'))
# ترتيب اللقطات داخل كلّ كتلة، مع الإضافات
per = {}
for s in draft: per.setdefault(s['block'], []).append(dict(s))
for k, x in extra.X.items():
    lst = per[x['block']]; lst.insert(x['part'], dict(x, id=k, kind='live'))
for b, lst in per.items():
    for i, s in enumerate(lst): s['part'], s['nparts'] = i, len(lst)
def rd(f):
    w = wave.open(f); a = np.frombuffer(w.readframes(w.getnframes()), np.int16); return a, w.getframerate()
def wr(f, a, sr):
    w = wave.open(f, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(a.astype(np.int16).tobytes()); w.close()
def pauses(a, sr, thr):
    x = a.astype(float) / 32768; hop = int(.02 * sr)
    e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)]); s = e < .01; out = []; i = 0
    while i < len(s):
        if s[i]:
            j = i
            while j < len(s) and s[j]: j += 1
            if (j - i) * .02 >= thr and i > 0 and j < len(s): out.append(((i + j) / 2 * .02, (j - i) * .02))
            i = j
        else: i += 1
    return out
for f in os.listdir(A):
    if re.fullmatch(r'd_\d+_\d+\.wav', f): os.remove(os.path.join(A, f))
nb, durs, shots, report = [], {}, [], []
for b in B0:
    a, sr = rd(os.path.join(AF, b['id'] + '.wav')); d = len(a) / sr
    lst = per[b['id']]; n = len(lst)
    cuts, rem = [], []
    if n > 1:
        pz = pauses(a, sr, .14)
        last = 0.0
        for j in range(1, n):
            tgt = last + (d - last) / (n - j + 1)
            c = [(p, l) for p, l in pz if p > last + 1.0 and d - p > 1.0 * (n - j)]
            assert c, (b['id'], j, pz)
            p, l = min(c, key=lambda x: abs(x[0] - tgt)); cuts.append(p); rem.append(min(GAP, max(0.0, l - .04))); last = p
    ws = b['text'].split(); edges = [0.0] + cuts + [d]
    cl = [len(re.sub(r'[\u064B-\u0652\u0670]', '', w)) + 1 for w in ws]; C = np.concatenate([[0], np.cumsum(cl)])
    pd = [edges[j + 1] - edges[j] for j in range(len(edges) - 1)]; rate = C[-1] / d; m = len(ws)
    best = {(0, 0): (0.0, None)}
    for j in range(1, n + 1):
        for e in range(j, m - (n - j) + 1):
            cc = [(best[(j - 1, s0)][0] + ((C[e] - C[s0]) / rate - pd[j - 1]) ** 2, s0) for s0 in range(j - 1, e) if (j - 1, s0) in best]
            if cc: best[(j, e)] = min(cc)
    wb = [m]; j, e = n, m
    while j > 0:
        e = best[(j, e)][1]; j -= 1; wb.append(e)
    wb = wb[::-1]
    for j in range(n):
        sid = b['id'] if j == 0 else '%s_%d' % (b['id'], j + 1)
        s0 = int((edges[j] + (rem[j - 1] / 2 if j else 0)) * sr); s1 = int((edges[j + 1] - (rem[j] / 2 if j < n - 1 else 0)) * sr)
        wr(os.path.join(A, sid + '.wav'), a[s0:s1], sr); durs[sid] = (s1 - s0) / sr
        nb.append(dict(b, id=sid, text=' '.join(ws[wb[j]:wb[j + 1]])))
        s = lst[j]
        sh = {k: v for k, v in s.items() if k not in ('block', 'part', 'nparts')}
        sh['blocks'] = [sid]; sh['file'] = s['id'] + '.jpg'
        shots.append(sh)
bt, t = {}, 0.0
for b in nb: bt[b['id']] = [t / T, (t + durs[b['id']]) / T]; t += durs[b['id']] + GAP
json.dump(nb, open(os.path.join(P, 'blocks.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump({'bt': bt, 'split_from': {b['id']: [x['id'] for x in nb if x['id'] == b['id'] or x['id'].startswith(b['id'] + '_')] for b in B0}},
          open(os.path.join(P, 'real_timing.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(shots, open(os.path.join(P, 'shots_split.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
L = [(s['id'], durs[s['blocks'][0]] / T + GAP / T) for s in shots]
print('blocks %d→%d shots %d  total %.1f s  avg %.2f  max %s  min %s' % (len(B0), len(nb), len(shots), t / T, sum(l for _, l in L) / len(L),
      max(L, key=lambda x: x[1]), min(L, key=lambda x: x[1])))
print('>10:', [(i, round(l, 1)) for i, l in L if l > 10])
print('first30:', sum(1 for s in shots if bt[s['blocks'][0]][0] < 30))
