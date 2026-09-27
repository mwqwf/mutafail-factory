# -*- coding: utf-8 -*-
"""بوّابة صوت Kling: كل مقطعٍ وُلّد بصوت يُصنَّف (gemini-3.5-flash) — مؤثّرات طبيعية فقط.
موسيقى/غناء/آلات/صوت امرأة ⇒ لا يدخل صوتُه الفيلم (يُكمَل من مكتبة المؤثّرات). المقبول يُعلَّم clips/<id>.ok
الاستعمال: python tools/sfx_gate.py <proj>   (المفاتيح من GEMINI_KEYS_JSON أو keys.txt)"""
import base64, io, json, os, re, subprocess as sp, sys, urllib.request

PROJ = sys.argv[1]
ledger = json.load(io.open(os.path.join(PROJ, 'fal_ledger.json'), encoding='utf-8')) if os.path.exists(os.path.join(PROJ, 'fal_ledger.json')) else []
txt = os.environ.get('GEMINI_KEYS_JSON') or open(os.path.expanduser('~/.claude/skills/video-factory/keys.txt'), encoding='utf-8').read()
keys = sorted(set(re.findall(r'(?:AIza|AQ\.)[\w\-\.]+', txt)))
Q = ('Classify this audio strictly. Answer ONE word only: MUSIC if there is any music, melody, singing, drums or '
     'musical instrument; FEMALE if any female voice; CLEAN if only natural sound effects (horses, elephants, swords, '
     'wind, fire, crowd of men, footsteps, arrows).')
for x in ledger:
    if not x.get('audio'): continue
    clip = os.path.join(PROJ, 'clips', x['shot'] + '.mp4'); ok = clip[:-4] + '.ok'
    if not os.path.exists(clip) or os.path.exists(ok) or os.path.exists(clip[:-4] + '.reject'): continue
    wav = sp.run(['ffmpeg', '-v', 'error', '-i', clip, '-vn', '-ac', '1', '-ar', '16000', '-f', 'wav', '-'], capture_output=True).stdout
    if len(wav) < 2000: open(clip[:-4] + '.reject', 'w').write('silent'); continue
    body = {'contents': [{'parts': [{'inline_data': {'mime_type': 'audio/wav', 'data': base64.b64encode(wav).decode()}}, {'text': Q}]}]}
    verdict = None
    for k in keys:
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key=' + k,
                json.dumps(body).encode(), {'content-type': 'application/json'}), timeout=300)
            verdict = json.load(r)['candidates'][0]['content']['parts'][0]['text'].strip().upper(); break
        except Exception:
            continue
    tag = 'CLEAN' if verdict and verdict.startswith('CLEAN') else 'reject'
    open(ok if tag == 'CLEAN' else clip[:-4] + '.reject', 'w').write(str(verdict))
    print(x['shot'], verdict, flush=True)
