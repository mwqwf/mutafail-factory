# -*- coding: utf-8 -*-
"""ريلز «قوي» من لقطات الفيلم المتحرّكة نفسها (Kling والمجسَّم) بدل الصور الثابتة، مع ترجمةٍ كبيرة للكلام.
(أمر المالك 2026-09-28: «ريلزات قوية 2 كالمعتاد لكن أقوى من كل ما سبق»)
الاستعمال: python mkreel_film.py <proj> <reelId>
reels.json: {"id":"r1","title":"...","blocks":["r_001",...],"shots":["Z049","Z052",...]}
يحتاج film.mp4 وtimeline.json (mont_hybrid.py) وصوت الكتل في audio/."""
import json, os, sys, subprocess as sp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envpaths
from PIL import Image, ImageDraw, ImageFilter
from envpaths import ar

PROJ, RID = os.path.abspath(sys.argv[1]), sys.argv[2]
P = lambda *a: os.path.join(PROJ, *a)
FF, FP, FB = envpaths.FF, envpaths.FP, envpaths.font(bold=True)
W, H, GAP = 1080, 1920, 0.25
R = {r['id']: r for r in json.load(open(P('reels.json'), encoding='utf-8'))}[RID]
TL = json.load(open(P('timeline.json'), encoding='utf-8'))
TXT = {b['id']: b['text'] for b in json.load(open(P('blocks.json'), encoding='utf-8'))}
WORK = P('reelwork', RID); os.makedirs(WORK, exist_ok=True); os.makedirs(P('reels'), exist_ok=True)
dur = lambda f: float(sp.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', f],
                             capture_output=True, text=True).stdout.strip())

# ① الصوت: الكتل متتابعة بفاصلٍ قصير، مسرَّعة 1.05 كالفيلم؛ وتوقيت كل كتلة للترجمة
sil = os.path.join(WORK, 'sil.wav')
sp.run([FF, '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono', '-t', str(GAP), sil], check=True)
times, t = [], 0.0
with open(os.path.join(WORK, 'a.txt'), 'w', encoding='utf-8') as fh:
    for b in R['blocks']:
        a = P('audio', b + '.wav'); d = dur(a) / 1.05
        times.append((b, t, d)); t += d + GAP / 1.05
        fh.write("file '%s'\nfile '%s'\n" % (a, sil))
voice = os.path.join(WORK, 'v.wav')
sp.run([FF, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', os.path.join(WORK, 'a.txt'),
        '-filter:a', 'atempo=1.05,dynaudnorm', '-ar', '48000', voice], check=True)
VD = dur(voice)

# ② الصورة: مقطعٌ من كل لقطةٍ في الفيلم، بالتساوي، بدءاً من منتصف ما بعد أولها (حيث الحركة)
per = VD / len(R['shots'])
segs = []
for n, sid in enumerate(R['shots']):
    st, sp_ = TL[sid]
    s0 = st + max(0.0, min(0.6, sp_ - per))
    out = os.path.join(WORK, 's%02d.mp4' % n)
    sp.run([FF, '-v', 'error', '-y', '-ss', '%.3f' % s0, '-t', '%.3f' % per, '-i', P('film.mp4'), '-an',
            '-vf', 'tpad=stop_mode=clone:stop_duration=%.2f,fps=30' % per, '-t', '%.3f' % per,
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', out], check=True)
    segs.append(out)
open(os.path.join(WORK, 'v.txt'), 'w').write(''.join("file '%s'\n" % s for s in segs))
raw = os.path.join(WORK, 'raw.mp4')
sp.run([FF, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', os.path.join(WORK, 'v.txt'), '-c', 'copy', raw], check=True)


def lines(d, text, f, maxw):
    out, cur = [], ''
    for w in text.split():
        c = (cur + ' ' + w).strip()
        if d.textlength(ar(c), font=f) > maxw and cur: out.append(cur); cur = w
        else: cur = c
    return out + ([cur] if cur else [])


def draw(d, y, ln, f, fill, stroke=4):
    t = ar(ln); tw = d.textlength(t, font=f)
    d.text(((W - tw) / 2, y), t, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 255))


# ③ الطبقات: العنوان أعلى، والترجمة الكبيرة تحت الإطار، ونداء «الفيلم كاملاً» آخر 3 ث
top = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(top)
ft = envpaths.arfont(78, path=FB); y = 150
for i, ln in enumerate(lines(d, R['title'], ft, W - 100)[:3]):
    draw(d, y, ln, ft, (247, 199, 74, 255) if i else (255, 255, 255, 255)); y += 100
lg = Image.open(envpaths.logo()).convert('RGBA').resize((110, 110))
m = Image.new('L', (110, 110), 0); ImageDraw.Draw(m).ellipse([2, 2, 108, 108], fill=255); top.paste(lg, ((W - 110) // 2, H - 170), m)
top.save(os.path.join(WORK, 'top.png'))

import re
DIAC = re.compile('[ً-ْٰ]')
fc = envpaths.arfont(72, path=FB); caps = []
for b, st, d_ in times:
    words = DIAC.sub('', TXT[b]).split()
    chunks = [' '.join(words[i:i + 4]) for i in range(0, len(words), 4)]
    total = sum(len(c) for c in chunks); tt = st
    for k, c in enumerate(chunks):
        cd = d_ * len(c) / total
        im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(im); y = 1250
        for ln in lines(dd, c, fc, W - 120)[:2]:
            draw(dd, y, ln, fc, (255, 255, 255, 255), 5); y += 96
        f = os.path.join(WORK, 'c_%s_%d.png' % (b, k)); im.save(f); caps.append((f, tt, tt + cd)); tt += cd

cta = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(cta)
fcta = envpaths.arfont(70, path=FB); t_ = ar('الفيلم كاملاً على القناة'); tw = d.textlength(t_, font=fcta)
d.rounded_rectangle([(W - tw) / 2 - 60, 1090, (W + tw) / 2 + 60, 1220], radius=40, fill=(200, 32, 34, 240))
d.text(((W - tw) / 2, 1112), t_, font=fcta, fill=(255, 255, 255, 255))
cta.save(os.path.join(WORK, 'cta.png'))

inp = [FF, '-v', 'error', '-y', '-i', raw, '-i', voice, '-loop', '1', '-i', os.path.join(WORK, 'top.png'),
       '-loop', '1', '-i', os.path.join(WORK, 'cta.png')]
flt = ['[0:v]split[a][b]', '[a]scale=-2:%d,crop=%d:%d,boxblur=28:3,eq=brightness=-0.15[bg]' % (H, W, H),
       # إطارٌ أطول من 16:9 (1080×1000، قصٌّ من الوسط) ليملأ الشاشة أكثر على الهاتف
       '[b]scale=-2:1000,crop=%d:1000[fg]' % W, '[bg][fg]overlay=0:400:shortest=1[v0]', '[v0][2:v]overlay=0:0:shortest=1[v1]']
last = 'v1'
for i, (f, a, b) in enumerate(caps):
    inp += ['-loop', '1', '-t', '%.3f' % VD, '-i', f]
    flt.append('[%s][%d:v]overlay=0:0:enable=\'between(t,%.3f,%.3f)\'[c%d]' % (last, 4 + i, a, b, i)); last = 'c%d' % i
flt.append('[3:v]format=rgba,fade=t=in:st=%.2f:d=0.3:alpha=1[cta]' % max(0, VD - 3))
flt.append('[%s][cta]overlay=0:0:shortest=1,fps=30,setsar=1,format=yuv420p[v]' % last)
out = P('reels', RID + '.mp4')
sp.run(inp + ['-filter_complex', ';'.join(flt), '-map', '[v]', '-map', '1:a', '-t', '%.3f' % VD,
              '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-c:a', 'aac', '-b:a', '192k', out], check=True)
print('✅ %s | %.1f ث | %d لقطة | %d سطر ترجمة' % (out, VD, len(segs), len(caps)))
