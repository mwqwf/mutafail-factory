"""تقسيم الكتل الطويلة عند وقفات الصوت الطبيعية (thrill_gate: متوسط ≤6 ث ولا لقطة >10 ث) بلا صوتٍ جديد.
يقصّ كلّ كتلةٍ عند منتصف وقفةٍ ≥0.34 ث ويحذف 0.30 ث منها (يعيدها GAP في المونتاج) فلا يتغيّر التوقيت.
ثم يعيد ربط المؤثّرات بالكتل الفرعية (بالوقت نفسه) ويقسم اللقطات لقطةً لكل كتلة فرعية بحركةٍ مختلفة.
يُشغَّل بعد build_voice.py ثم build_plan.py. المصدر proj/audio_full (نسخة build_voice)."""
import json, os, re, shutil, sys, wave
import numpy as np
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); P = os.path.join(D, 'proj')
FAC = os.environ.get('MF_TOOLS', '/workspace/mutafail-factory/tools'); sys.path.insert(0, FAC)
import sfx_cues, motion_plan as mp
GAP, T = 0.30, 1.05
A, AF = os.path.join(P, 'audio'), os.path.join(P, 'audio_full')
blocks = json.load(open(os.path.join(P, 'blocks.json'), encoding='utf-8'))
if not os.path.isdir(AF):
    os.makedirs(AF)
    for b in blocks: shutil.copy(os.path.join(A, b['id'] + '.wav'), AF)
def rd(f):
    w = wave.open(f); a = np.frombuffer(w.readframes(w.getnframes()), np.int16); return a, w.getframerate()
def wr(f, a, sr):
    w = wave.open(f, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(a.astype(np.int16).tobytes()); w.close()
def pauses(a, sr, thr=.28):
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
TGT, MINP = 5.5, 2.2     # طول الجزء المستهدف والأدنى (زمن الفيلم)
orig_bt, t = {}, 0.0
for b in blocks:
    a, sr = rd(os.path.join(AF, b['id'] + '.wav')); d = len(a) / sr; orig_bt[b['id']] = (t / T, (t + d) / T); t += d + GAP
nb, sub_of, durs = [], {}, {}
for b in blocks:
    for f in os.listdir(A):
        if re.fullmatch(re.escape(b['id']) + r'_\d+\.wav', f): os.remove(os.path.join(A, f))
    a, sr = rd(os.path.join(AF, b['id'] + '.wav')); d = len(a) / sr
    cuts, rem, last = [], [], 0.0
    op = orig_bt[b['id']][0] < 30.0      # الافتتاح (thrill_gate: ≥12 لقطة في أوّل 30 ث): قطعٌ عند كلّ وقفةٍ ولو قصيرة
    pz = pauses(a, sr, .18 if op else .28); mn, cap, ch = (1.4, 2.6, 2.6) if op else (MINP, 7.0, 6.0)
    while (d - last) / T > cap:
        R = (d - last) / T; tgt = R / -(-R // ch)
        c = [(p, l) for p, l in pz if mn <= (p - last) / T <= 7.5 and (d - p) / T >= mn]
        if not c: break
        p, l = min(c, key=lambda x: abs((x[0] - last) / T - tgt)); cuts.append(p); rem.append(min(GAP, l - .04)); last = p
    ws = b['text'].split(); edges = [0.0] + cuts + [d]
    # النصّ: نسبة الزمن الصوتيّ → حدّ كلمة، يُفضَّل حدٌّ بعد علامة ترقيم قريبة
    wb = [0]
    for c in cuts:
        cum = np.cumsum([len(w) + 1 for w in ws]); k = int(np.searchsorted(cum, cum[-1] * c / d)) + 1   # نسبة الحروف لا الكلمات
        cand = [i for i in range(max(1, k - 2), min(len(ws), k + 3)) if re.search(r'[.،,؛:!؟…»]$', ws[i - 1])]
        k = min(cand, key=lambda i: abs(i - k)) if cand else k; wb.append(max(wb[-1] + 1, min(k, len(ws) - 1)))
    wb.append(len(ws)); sub_of[b['id']] = []
    for j in range(len(edges) - 1):
        sid = b['id'] if j == 0 else '%s_%d' % (b['id'], j + 1)
        s0 = int((edges[j] + (rem[j - 1] / 2 if j else 0)) * sr); s1 = int((edges[j + 1] - (rem[j] / 2 if j < len(edges) - 2 else 0)) * sr)
        wr(os.path.join(A, sid + '.wav'), a[s0:s1], sr); durs[sid] = (s1 - s0) / sr
        nbk = dict(b, id=sid, text=' '.join(ws[wb[j]:wb[j + 1]])); nb.append(nbk); sub_of[b['id']].append(sid)
bt, t = {}, 0.0
for b in nb: bt[b['id']] = [t / T, (t + durs[b['id']]) / T]; t += durs[b['id']] + GAP
drift = max(abs(bt[k][0] - orig_bt[k][0]) for k in orig_bt)
# المؤثّرات: نفس اللحظة على الكتلة الفرعية الحاوية
cues = json.load(open(os.path.join(P, 'sfx_cues.json'), encoding='utf-8'))
oby = {b['id']: b for b in blocks}
for c in cues['cues']:
    st = sfx_cues.cue_window(c, {k: v for k, v in orig_bt.items()}, oby)[0] - float(c.get('offset', 0.0))
    subs = sub_of[c['block']]
    if len(subs) == 1: continue
    sid = [s for s in subs if bt[s][0] <= st + 1e-6][-1] if st >= bt[subs[0]][0] else subs[0]
    c.pop('anchor', None); c['block'] = sid; c['at'] = round(max(0.0, st - bt[sid][0]), 3)
cues['key_blocks'] = sorted({s for k in cues.get('key_blocks', []) for s in sub_of.get(k, [k])})
# اللقطات: لقطة لكل كتلة فرعية؛ الحيّة تكمل مقطعها نفسه (clip_ss) ثم kb3d، وغيرها kb3d بحركة مختلفة
shots = json.load(open(os.path.join(P, 'shots.json'), encoding='utf-8'))
cdur = lambda i: float(os.popen("ffprobe -v error -show_entries format=duration -of csv=p=0 '%s'" % os.path.join(P, 'clips', i + '.mp4')).read() or 0) if os.path.exists(os.path.join(P, 'clips', i + '.mp4')) else 0
out = []
ALLM = ['dolly_in', 'dolly_out', 'truck_l', 'truck_r', 'crane_up', 'push_tilt', 'reveal']
grp = {}
for i, s in enumerate(shots): grp.setdefault(tuple(s['blocks']), []).append(i)
for i, s in enumerate(shots):
    parts = [x for b in s['blocks'] for x in sub_of[b]]
    g = grp[tuple(s['blocks'])]
    if len(g) > 1:   # لقطتان على كتلةٍ واحدة: تُوزَّع الأجزاء بينهما (كان المونتاج يكرّر الكتلة فيطول الفيديو)
        n = len(g); k0 = g.index(i); parts = parts[k0 * len(parts) // n:(k0 + 1) * len(parts) // n]
        assert parts, s['id']; s = dict(s, blocks=[parts[0]]) if len(parts) == 1 else s
    if len(parts) == 1: out.append(dict(s, blocks=parts)); continue
    if len(parts) == 1: out.append(s); continue
    moves = mp.EMOTIONS[s['emotion']][0]; nxt = shots[i + 1].get('move3d') if i + 1 < len(shots) else None
    out.append(dict(s, blocks=[parts[0]])); prev = s.get('move3d'); live = s.get('kind') == 'live'
    src = s.get('clip') or s['id']; cd = cdur(src); off = float(s.get('clip_ss', 0)) + (bt[parts[0]][1] - bt[parts[0]][0] + GAP / T)
    for k, b in enumerate(parts[1:], 1):
        last = k == len(parts) - 1
        em = 'journey' if s['emotion'] == 'map' else s['emotion']; mv = mp.EMOTIONS[em][0]
        m = next((m for m in mv if m != prev and not (last and m == nxt)), None) or next((m for m in mv if m != prev), mv[0])
        sub = {x: v for x, v in s.items() if x not in ('key', 'hook', 'climax', 'qa', 'clip', 'clip_ss', 'map')}
        sub.update(id='%s_%d' % (s['id'], k + 1), blocks=[b], file=s.get('file') or s['id'] + '.jpg', move3d=m, ease='soft',
                   energy=max(0.8, s.get('energy', 0.8)), tr='cut' if em == 'action' else 'fade', emotion=em, kind='live' if live else 'kb3d')
        if not live: sub.pop('video_prompt', None)
        if live and cd and cd - off >= 2.0: sub.update(clip=src, clip_ss=round(off, 2))
        out.append(sub); prev = m; off += bt[b][1] - bt[b][0] + GAP / T
for i in range(1, len(out)):     # تجاورُ حركتين متماثلتين عند حدّ اللقطة الأصلية: يُعدَّل الجزء الفرعيّ
    if out[i].get('move3d') and out[i].get('move3d') == out[i - 1].get('move3d'):
        j = i - 1 if '_' in out[i - 1]['id'] else i
        nb_ = {out[k].get('move3d') for k in (j - 1, j + 1) if 0 <= k < len(out)}
        for em in [out[j]['emotion'], 'aftermath', 'revelation', 'awe', 'journey']:
            m = next((m for m in mp.EMOTIONS[em][0] if m not in nb_), None)
            if m: out[j].update(move3d=m, emotion=em); break
json.dump(nb, open(os.path.join(P, 'blocks.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(cues, open(os.path.join(P, 'sfx_cues.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(out, open(os.path.join(P, 'shots.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump({'bt': bt, 'split_from': sub_of}, open(os.path.join(P, 'real_timing_split.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
L = [sum(bt[b][1] - bt[b][0] + GAP / T for b in s['blocks']) for s in out]
print('blocks %d→%d shots %d→%d drift %.3f avg %.2f max %.1f >10: %s' % (len(blocks), len(nb), len(shots), len(out), drift, sum(L) / len(L), max(L),
      [(s['id'], round(l, 1)) for s, l in zip(out, L) if l > 10]))
print('sfx', sfx_cues.lint(cues, nb, bt) or 'OK'); print('motion', mp.lint(out, [bt[s['blocks'][0]][0] for s in out]) or 'OK')
cov = {b for s in out for b in s['blocks']}; print('coverage', [b['id'] for b in nb if b['id'] not in cov] or 'OK')
