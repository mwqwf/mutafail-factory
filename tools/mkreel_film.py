# -*- coding: utf-8 -*-
"""ريلز دعائيّ «قويّ» من لقطات الفيلم المتحرّكة نفسها — الجيل الثاني (عين جالوت 2026-09-29).
أمر المالك: «الريلزات يجب أن تكون أقوى وأكثر جاذبية من السابقة». ما أُضيف على الجيل الأوّل:
  ① خطّافٌ مكتوبٌ كبيرٌ في أوّل 1.6 ث (hook) — أوّل ثانيتين تقرّران البقاء
  ② قطعٌ سريعٌ كلّ ~1.7 ث (لا لقطةً واحدةً لستّ ثوانٍ) مع اقترابٍ تدريجيّ وومضةٍ خاطفة عند كلّ قطع
  ③ ترجمةٌ كلمةً بكلمة: الكلمة المنطوقة تضيء ذهبيّاً (karaoke)
  ④ شريطُ تقدّمٍ ذهبيٌّ أعلى الشاشة (يُبقي المشاهد إلى النهاية)
  ⑤ طبقةُ مؤثّراتٍ طبيعيّة تحت الصوت (assets/sfx/<sfx>_*.ogg) — ⛔ بلا موسيقى
  ⑥ بطاقةُ ختام: سؤالٌ معلّق + «الجواب في الفيلم الكامل»
الاستعمال: python mkreel_film.py <proj> <reelId>
reels.json: {"id":"r1","title":"...","hook":"...","end_q":"...","sfx":"battle","blocks":["r_001",...],"shots":["F020",...]}
يحتاج film.mp4 وtimeline.json (mont_hybrid.py) وصوت الكتل في audio/."""
import glob, json, math, os, re, sys, subprocess as sp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envpaths
from PIL import Image, ImageDraw
from envpaths import ar

PROJ, RID = os.path.abspath(sys.argv[1]), sys.argv[2]
P = lambda *a: os.path.join(PROJ, *a)
FF, FP, FB = envpaths.FF, envpaths.FP, envpaths.font(bold=True)
W, H, GAP, CUT = 1080, 1920, 0.25, 1.7
FG_H, FG_Y = 1350, 330                              # الإطار الأفقي مكبَّراً في الوسط (يملأ 70٪ من الشاشة)
GOLD, WHITE = (247, 199, 74, 255), (255, 255, 255, 255)
R = {r['id']: r for r in json.load(open(P('reels.json'), encoding='utf-8'))}[RID]
TL = json.load(open(P('timeline.json'), encoding='utf-8'))
TXT = {b['id']: b['text'] for b in json.load(open(P('blocks.json'), encoding='utf-8'))}
WORK = P('reelwork', RID); os.makedirs(WORK, exist_ok=True); os.makedirs(P('reels'), exist_ok=True)
SFX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'sfx')
dur = lambda f: float(sp.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', f],
                             capture_output=True, text=True).stdout.strip())
run = lambda cmd: sp.run([FF, '-v', 'error', '-y'] + cmd, check=True)

# ① الصوت: الكتل متتابعة بفاصلٍ قصير، مسرَّعة 1.05 كالفيلم؛ وتوقيت كل كتلة للترجمة
sil = os.path.join(WORK, 'sil.wav')
run(['-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono', '-t', str(GAP), sil])
times, t = [], 0.0
with open(os.path.join(WORK, 'a.txt'), 'w', encoding='utf-8') as fh:
    for b in R['blocks']:
        a = P('audio', b + '.wav'); d = dur(a) / 1.05
        times.append((b, t, d)); t += d + GAP / 1.05
        fh.write("file '%s'\nfile '%s'\n" % (a, sil))
voice = os.path.join(WORK, 'v.wav')
run(['-f', 'concat', '-safe', '0', '-i', os.path.join(WORK, 'a.txt'), '-filter:a', 'atempo=1.05,adeclick,dynaudnorm', '-ar', '48000', voice])
VD = dur(voice) + 0.6                               # نَفَسٌ قصير بعد آخر كلمة تحت بطاقة الختام

# ② الصورة: قطعٌ كلّ CUT ثانية يدور على اللقطات؛ وفي كلّ دورةٍ جزءٌ آخر من اللقطة نفسها (حركةٌ جديدة لا تكرار)
n = max(1, math.ceil(VD / CUT)); per = VD / n; shots = R['shots']; segs = []
for k in range(n):
    sid = shots[k % len(shots)]; st, span = TL[sid]; rep = k // len(shots)
    s0 = st + min(max(0.0, span - per - 0.1), 0.3 + rep * per)
    out = os.path.join(WORK, 's%03d.mp4' % k)
    z = "zoompan=z='1.0+0.0022*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=%dx%d:fps=30" % (W, FG_H)
    run(['-ss', '%.3f' % s0, '-t', '%.3f' % per, '-i', P('film.mp4'), '-an', '-vf',
         'scale=-2:%d,crop=%d:%d,%s,fade=t=in:st=0:d=0.12:color=white,tpad=stop_mode=clone:stop_duration=%.2f' % (FG_H, W, FG_H, z, per),
         '-t', '%.3f' % per, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', out])
    segs.append(out)
open(os.path.join(WORK, 'v.txt'), 'w').write(''.join("file '%s'\n" % s for s in segs))
fg = os.path.join(WORK, 'fg.mp4')
run(['-f', 'concat', '-safe', '0', '-i', os.path.join(WORK, 'v.txt'), '-c', 'copy', fg])


def lines(d, text, f, maxw):
    out, cur = [], ''
    for w in text.split():
        c = (cur + ' ' + w).strip()
        if d.textlength(ar(c), font=f) > maxw and cur: out.append(cur); cur = w
        else: cur = c
    return out + ([cur] if cur else [])


def centered(d, y, text, f, fill, stroke=5, band=None):
    t = ar(text); tw = d.textlength(t, font=f)
    if band:
        d.rounded_rectangle([(W - tw) / 2 - 50, y - 18, (W + tw) / 2 + 50, y + f.size + 34], radius=36, fill=band)
    d.text(((W - tw) / 2, y), t, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 255))


# ③ الطبقات الثابتة: العنوان أعلى والشعار أسفل، والخطّاف، وبطاقة الختام
top = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(top)
ft = envpaths.arfont(64, path=FB); y = 120
for i, ln in enumerate(lines(d, R['title'], ft, W - 100)[:2]):
    centered(d, y, ln, ft, GOLD if i else WHITE); y += 84
lg = Image.open(envpaths.logo()).convert('RGBA').resize((110, 110))
m = Image.new('L', (110, 110), 0); ImageDraw.Draw(m).ellipse([2, 2, 108, 108], fill=255); top.paste(lg, ((W - 110) // 2, H - 150), m)
top.save(os.path.join(WORK, 'top.png'))

hook = Image.new('RGBA', (W, H), (0, 0, 0, 110)); d = ImageDraw.Draw(hook)
fh_ = envpaths.arfont(96, path=FB); hl = lines(d, R.get('hook') or R['title'], fh_, W - 140)[:3]; y = (H - len(hl) * 130) / 2
for ln in hl:
    centered(d, y, ln, fh_, WHITE, 6, band=(200, 32, 34, 235)); y += 150
hook.save(os.path.join(WORK, 'hook.png'))

end = Image.new('RGBA', (W, H), (0, 0, 0, 150)); d = ImageDraw.Draw(end)
fq = envpaths.arfont(80, path=FB); y = 700
for ln in lines(d, R.get('end_q') or 'ماذا حدث بعد ذلك؟', fq, W - 140)[:2]:
    centered(d, y, ln, fq, GOLD); y += 110
centered(d, y + 60, 'الجواب في الفيلم الكامل', envpaths.arfont(66, path=FB), WHITE, 4, band=(200, 32, 34, 245))
centered(d, y + 240, 'اشترك وفعّل الجرس', envpaths.arfont(54, path=FB), WHITE, 4)
end.save(os.path.join(WORK, 'end.png'))

# ④ الترجمة كلمةً بكلمة: ثلاث كلماتٍ في السطر، والكلمة المنطوقة ذهبيّة — صورٌ متتابعة بمُددها في مسارٍ واحد
DIAC = re.compile('[ً-ْٰ]')
fc = envpaths.arfont(76, path=FB); frames = []
blank = os.path.join(WORK, 'cap_blank.png'); Image.new('RGBA', (W, 300), (0, 0, 0, 0)).save(blank)
tcur = 0.0
for b, st, d_ in times:
    if st > tcur: frames.append((blank, st - tcur)); tcur = st
    words = DIAC.sub('', TXT[b]).replace('…', ' ').split()
    chunks = [words[i:i + 3] for i in range(0, len(words), 3)]
    total = sum(len(w) + 1 for w in words)
    for ci, ch in enumerate(chunks):
        for wi, w in enumerate(ch):
            wd = d_ * (len(w) + 1) / total
            im = Image.new('RGBA', (W, 300), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
            # يُرسم السطر كلمةً كلمةً من اليمين (ar() لكلّ كلمة) فتلوَّن المنطوقةُ وحدها
            parts = [ar(x) for x in ch]; sp_ = dd.textlength(' ', font=fc)
            widths = [dd.textlength(p, font=fc) for p in parts]; tw = sum(widths) + sp_ * (len(parts) - 1)
            x = (W + tw) / 2
            for j, p in enumerate(parts):
                x -= widths[j]
                dd.text((x, 80), p, font=fc, fill=GOLD if j == wi else WHITE, stroke_width=6, stroke_fill=(0, 0, 0, 255))
                x -= sp_
            f = os.path.join(WORK, 'cap_%s_%d_%d.png' % (b, ci, wi)); im.save(f)
            frames.append((f, wd)); tcur += wd
frames.append((blank, max(0.1, VD - tcur)))
with open(os.path.join(WORK, 'caps.txt'), 'w', encoding='utf-8') as fh:
    for f, dd_ in frames: fh.write("file '%s'\nduration %.3f\n" % (f, max(0.04, dd_)))
    fh.write("file '%s'\n" % frames[-1][0])

# ⑤ المؤثّرات تحت الصوت (مكتبة CC0) — ⛔ لا موسيقى
cands = sorted(glob.glob(os.path.join(SFX, R.get('sfx', 'battle') + '_*.ogg')))
ain = ['-i', voice] + (['-stream_loop', '-1', '-i', cands[0]] if cands else [])
amix = ('[1:a]volume=1.0[vo];[2:a]atrim=0:%.3f,volume=0.22,afade=t=out:st=%.3f:d=0.8[fx];[vo][fx]amix=inputs=2:duration=first:normalize=0,apad=whole_dur=%.3f[au]'
        % (VD, VD - 0.8, VD)) if cands else '[1:a]apad=whole_dur=%.3f[au]' % VD

# ⑥ التجميع: خلفيةٌ مموّهة + الإطار المكبَّر + العنوان + الترجمة + شريط التقدّم + الخطّاف أوّلاً + بطاقة الختام آخراً
HOOK_T, END_T = 1.6, 3.2
k0 = 1 + (2 if cands else 1)
inp = ['-i', fg] + ain + ['-loop', '1', '-i', os.path.join(WORK, 'top.png'), '-f', 'concat', '-safe', '0', '-i', os.path.join(WORK, 'caps.txt'),
                          '-loop', '1', '-i', os.path.join(WORK, 'hook.png'), '-loop', '1', '-i', os.path.join(WORK, 'end.png')]
iT, iC, iH, iE = k0, k0 + 1, k0 + 2, k0 + 3
flt = ['[0:v]split[a][b]', '[a]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,boxblur=30:3,eq=brightness=-0.2[bg]' % (W, H, W, H),
       '[bg][b]overlay=0:%d:shortest=1[v0]' % FG_Y, '[v0][%d:v]overlay=0:0:shortest=1[v1]' % iT,
       '[%d:v]format=rgba[cap]' % iC, '[v1][cap]overlay=0:%d:eof_action=pass[v2]' % (FG_Y + FG_H - 200),
       "[v2]drawbox=x=0:y=0:w='iw*t/%.3f':h=12:color=0xF7C74A@1:t=fill[v3]" % VD,
       '[%d:v]format=rgba,fade=t=out:st=%.2f:d=0.25:alpha=1[hk]' % (iH, HOOK_T - 0.25),
       "[v3][hk]overlay=0:0:enable='lte(t,%.2f)'[v4]" % HOOK_T,
       '[%d:v]format=rgba,fade=t=in:st=%.2f:d=0.35:alpha=1[en]' % (iE, VD - END_T),
       "[v4][en]overlay=0:0:enable='gte(t,%.2f)',fps=30,setsar=1,format=yuv420p[v]" % (VD - END_T), amix]
out = P('reels', RID + '.mp4')
run(inp + ['-filter_complex', ';'.join(flt), '-map', '[v]', '-map', '[au]', '-t', '%.3f' % VD,
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-c:a', 'aac', '-b:a', '192k', out])
print('✅ %s | %.1f ث | %d قطعاً | %d إطار ترجمة' % (out, VD, len(segs), len(frames)))
