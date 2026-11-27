# -*- coding: utf-8 -*-
# يصيّر مسار المؤثّرات على الأوقات الحقيقية، ويقيس مستوى كل إشارة نسبةً إلى الكلام، ثم يطبّق بوّابة المزج (sfx_cues.mix_gate)
import json, sys, os
sys.path.insert(0, os.environ.get('MF_TOOLS', '/workspace/mutafail-factory/tools'))
import sfx_cues as S
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); P = os.path.join(H, 'proj')
blocks = json.load(open(os.path.join(P, 'blocks.json'), encoding='utf-8'))
sheet = json.load(open(os.path.join(P, 'sfx_cues.json'), encoding='utf-8'))
bt = {k: tuple(v) for k, v in json.load(open(os.path.join(P, 'real_timing.json')))['bt'].items()}
voice = S._pcm(os.path.join(H, 'mix', 'voice.wav'))
errs = S.lint(sheet, blocks, bt)
by = {b['id']: b for b in blocks}
spans = [S.cue_window(c, bt, by) + (S.EVENTS[c['event']][1], c['event'], c.get('id', '?')) for c in sheet['cues']]
errs += S.reuse_errors(spans, S.pick_files(sheet['cues'], spans))
if errs: print('\n'.join(errs)); sys.exit(1)
out = os.path.join(H, 'mix', 'sfx_stem.wav')
S.render(sheet, blocks, bt, voice, out)
stem = S._pcm(out)
vref = S.active_db(voice, -35.0)
print('id event kind start target measured(dB rel. voice)')
for (a, b, kind, ev, cid), c in zip(spans, sheet['cues']):
    seg = stem[int(a * S.SR):int(b * S.SR)]
    print(cid, ev, kind, round(a, 1), c.get('level', S.EVENTS[c['event']][2]), round(S.active_db(seg, -70.0) - vref, 1) if len(seg) else None)
keys = S.key_blocks(sheet, blocks)
g = S.mix_gate(voice, stem, [bt[k] for k in keys if k in bt])
print('MIX GATE', 'OK' if not g else g)
sys.exit(1 if g else 0)
