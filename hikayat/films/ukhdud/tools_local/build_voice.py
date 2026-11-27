import re,json
B='/workspace/hikayat-factory/film1/'
NAR=("# AUDIO PROFILE: a calm, warm Arabic storyteller (male) narrating an authentic Islamic story from Sahih Muslim.\n"
"## THE SCENE: a quiet, reverent documentary told at night; natural ambience only.\n### DIRECTOR'S NOTES\n"
"Style: grounded, sincere and suspenseful, never theatrical; slight weight on questions.\n"
"Pace: natural, measured; honour every '…' as a short breath pause and every comma as a micro-pause.\n"
"Language: clear classical Arabic (fusha), pronounce every vowel and case ending exactly as written.\n"
"Read ONLY the transcript below. Do not read these notes aloud.")
HAD=("# AUDIO PROFILE: the same calm Arabic storyteller (male) now reading the exact words of a hadith of the Prophet, peace be upon him.\n"
"## THE SCENE: a reverent reading of a narrated text inside a documentary.\n### DIRECTOR'S NOTES\n"
"Style: reverent, steady and clear; read the words exactly, no acting, no character voices, no emotion added.\n"
"Pace: slightly slower than the narration; clean pause at every comma.\n"
"Language: clear classical Arabic (fusha), every vowel and case ending exactly as written.\n"
"Read ONLY the transcript below. Do not read these notes aloud.")
CTA=NAR.replace("Style: grounded, sincere and suspenseful, never theatrical; slight weight on questions.","Style: friendly, soft and brief, like a quiet aside; no salesmanship.")
blocks=[]
for l in open(B+'script.md'):
    m=re.match(r'(d_\d+)\|(\w)\|(.*)',l.strip())
    if not m: continue
    i,r,t=m.groups()
    d = HAD if r=='Q' else (CTA if 'اشْتِرَاكُكَ' in t else NAR)
    pause = 1200 if r=='Q' else (900 if t.rstrip('.').endswith(('؟','…')) else 450)
    blocks.append({"id":i,"role":r,"voice":"Charon","text":t.replace('«','').replace('»',''),"director":d,
                   "sfx":"silent" if (r=='Q' or '«' in t) else "ambient","pause_after_ms":pause})
json.dump({"slug":"ashab-alukhdud-full","model":"gemini-3.1-flash-tts-preview","note":"صوت واحد للفيلم كله، والمالك يولّده بنفسه. لا تُخلط النماذج. علامات «» محذوفة من النص المنطوق فقط.","variants":{"full":blocks}},open(B+'voice_ready.json','w'),ensure_ascii=False,indent=1)
with open(B+'voice_ready.txt','w') as f:
    f.write("# النص الجاهز للصوت — كتلة في كل سطر — gemini-3.1-flash-tts-preview · Charon\n# [ح] = لفظ حديث: توجيه HAD وصمت المؤثرات · [ms] = الوقفة بعد الكتلة\n\n")
    for b in blocks: f.write(f"{b['id']} {'[ح]' if b['role']=='Q' else '   '} [{b['pause_after_ms']}] {b['text']}\n")
print(len(blocks),'blocks')
