#!/usr/bin/env python3
"""وضوح النطق في تجربة Chatterbox (2026-11-03): نسبة الكلمات التي يسمعها faster-whisper صحيحةً، لـGemini ولـChatterbox
بالتشكيل وبدونه، على الجمل نفسها. مقياسٌ مساعدٌ لا حَكَم: الأذن تحكم.
    python tools/exp/asr_score.py <مجلد المشروع> <مجلد عيّنات cb> <الناتج.json>
"""
import difflib, json, os, re, sys
from faster_whisper import WhisperModel
T = re.compile('[ؐ-ًؚ-ٰٟۖ-ۭـ]')
def norm(s):
    s = T.sub('', s); s = re.sub('[أإآٱ]', 'ا', s).replace('ة', 'ه').replace('ى', 'ي')
    return re.sub('[^ء-ي ]', ' ', s).split()
def acc(ref, hyp):
    sm = difflib.SequenceMatcher(None, ref, hyp, autojunk=False)
    return round(sum(n for _, _, n in sm.get_matching_blocks()) / max(1, len(ref)), 3)
proj, cb, out = sys.argv[1:4]
m = WhisperModel('large-v3', device='cpu', compute_type='int8', cpu_threads=4)
key = json.load(open(os.path.join(cb, 'blind_key.json'), encoding='utf-8'))
res = {}
for i, k in key.items():
    ref = norm(k['text']); r = {}
    for lab, f in (('gemini', os.path.join(proj, 'audio', i + '.wav')), ('cb_tashkeel', os.path.join(cb, 'cb_%s_tashkeel.wav' % i)),
                   ('cb_bare', os.path.join(cb, 'cb_%s_bare.wav' % i))):
        segs, _ = m.transcribe(f, language='ar', beam_size=5, vad_filter=False)
        hyp = ' '.join(s.text for s in segs)
        r[lab] = {'acc': acc(ref, norm(hyp)), 'heard': hyp.strip()}
    res[i] = r; print(i, {a: b['acc'] for a, b in r.items()}, flush=True)
json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
