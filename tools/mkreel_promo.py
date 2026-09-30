# -*- coding: utf-8 -*-
"""ريلز دعائيّ للسلسلة (أمر المالك 2026-09-30: «احترافيّ بمعنى الكلمة… لا تبخل بشيء يزيد جودته»).
بخلاف mkreel_film (قطعٌ كلّ 1.7 ث مستقلٌّ عن الصوت) يتبع هذا الريلز شريطَ الفيلم نفسه لحظةً بلحظة،
فتبقى شفاه الراوي مطابقةً لكلامه، وتقع كلُّ معركةٍ على جملتها. ويُضاف فوقه:
  ① الإطار الأفقي مكبَّراً في الوسط (قصّ الوسط) على خلفيةٍ مموّهة منه
  ② خطّافٌ مكتوب في أوّل 1.6 ث · ③ بطاقةُ اسم المعركة وتاريخها أعلى الإطار طوال لقطتها (chip في shots.json)
  ④ ترجمةٌ كلمةً بكلمة (الكلمة المنطوقة ذهبية) · ⑤ ومضةٌ بيضاء خاطفة عند كلّ قطع · ⑥ شريطُ تقدّم
  ⑦ بطاقةُ ختام: الاشتراك، والسلسلة كاملة، واقتراح المعركة القادمة في التعليقات
الاستعمال: python mkreel_promo.py <proj> <reelId>
reels.json: {"id":"r1","promo":true,"title":"...","hook":"...","end_lines":["...","..."],"end_cta":"..."}
يحتاج film.mp4 وtimeline.json (mont_hybrid.py) وshots.json وblocks.json وaudio/."""
import json, os, re, sys, subprocess as sp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envpaths
from PIL import Image, ImageDraw
from envpaths import ar

PROJ, RID = os.path.abspath(sys.argv[1]), sys.argv[2]
GAP = float(sys.argv[3]) if len(sys.argv) > 3 else 0.30     # الفاصل بين الكتل كما في mont_hybrid
P = lambda *a: os.path.join(PROJ, *a)
FF, FP, FB = envpaths.FF, envpaths.FP, envpaths.font(bold=True)
W, H = 1080, 1920
FG_H, FG_Y = 1350, 330
GOLD, WHITE, RED = (247, 199, 74, 255), (255, 255, 255, 255), (200, 32, 34, 240)
R = {r['id']: r for r in json.load(open(P('reels.json'), encoding='utf-8'))}[RID]
TL = json.load(open(P('timeline.json'), encoding='utf-8'))
SHOTS = json.load(open(P('shots.json'), encoding='utf-8'))
TXT = {b['id']: b['text'] for b in json.load(open(P('blocks.json'), encoding='utf-8'))}
WORK = P('reelwork', RID); os.makedirs(WORK, exist_ok=True); os.makedirs(P('reels'), exist_ok=True)
dur = lambda f: float(sp.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', f],
                             capture_output=True, text=True).stdout.strip())
run = lambda cmd: sp.run([FF, '-v', 'error', '-y'] + cmd, check=True)
FILM = P('film.mp4'); VD = dur(FILM)
assert VD <= 170, '⛔ الريلز الدعائي أطول من 170 ث (%.1f)' % VD


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


# ① توقيت كلّ كتلة من الخطّ الزمني: بداية لقطتها + ما قبلها من كتلها (بمدّة صوتها المسرَّع 1.05 وفاصلها)
times = []
for s in SHOTS:
    if s['id'] not in TL or not s.get('blocks'): continue
    t = TL[s['id']][0]
    for b in s['blocks']:
        d_ = dur(P('audio', b + '.wav')) / 1.05
        times.append((b, t, d_)); t += d_ + GAP / 1.05

# ② الطبقة العلوية: العنوان والشعار
top = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(top)
for sz in (62, 56, 50, 46):
    ft = envpaths.arfont(sz, path=FB); tl = lines(d, R['title'], ft, W - 90)
    if len(tl) <= 3: break
y = 100
for i, ln in enumerate(tl):
    centered(d, y, ln, ft, GOLD if i else WHITE); y += int(sz * 1.3)
lg = Image.open(envpaths.logo()).convert('RGBA').resize((110, 110))
m = Image.new('L', (110, 110), 0); ImageDraw.Draw(m).ellipse([2, 2, 108, 108], fill=255); top.paste(lg, ((W - 110) // 2, H - 150), m)
top.save(os.path.join(WORK, 'top.png'))

# ③ بطاقات أسماء المعارك: صورةٌ لكلّ لقطةٍ لها chip، تظهر طوال لقطتها أعلى الإطار
chips = []
for s in SHOTS:
    c = s.get('chip')
    if not c or s['id'] not in TL: continue
    im = Image.new('RGBA', (W, 260), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
    centered(dd, 30, c['text'], envpaths.arfont(88, path=FB), WHITE, 6, band=RED)
    if c.get('sub'): centered(dd, 170, c['sub'], envpaths.arfont(52, path=FB), GOLD, 5)
    f = os.path.join(WORK, 'chip_%s.png' % s['id']); im.save(f)
    st, span = TL[s['id']]; chips.append((f, st, span))

# ④ الخطّاف وبطاقة الختام
hook = Image.new('RGBA', (W, H), (0, 0, 0, 90)); d = ImageDraw.Draw(hook)
fh_ = envpaths.arfont(96, path=FB); hl = lines(d, R.get('hook') or R['title'], fh_, W - 140)[:3]; y = (H - len(hl) * 150) / 2
for ln in hl:
    centered(d, y, ln, fh_, WHITE, 6, band=RED); y += 150
hook.save(os.path.join(WORK, 'hook.png'))
END_T = float(R.get('end_secs', 5.0))
end = Image.new('RGBA', (W, H), (0, 0, 0, 165)); d = ImageDraw.Draw(end)
y = 560
for i, ln in enumerate(R.get('end_lines', [])):
    f = envpaths.arfont(70 if i == 0 else 60, path=FB)
    for sub in lines(d, ln, f, W - 120)[:2]:
        centered(d, y, sub, f, GOLD if i == 0 else WHITE, 5); y += int(f.size * 1.35)
    y += 30
centered(d, y + 40, R.get('end_cta', 'اشترك وفعّل الجرس'), envpaths.arfont(66, path=FB), WHITE, 4, band=RED)
end.save(os.path.join(WORK, 'end.png'))

# ⑤ الترجمة كلمةً بكلمة
DIAC = re.compile('[ً-ْٰ]')
fc = envpaths.arfont(74, path=FB); frames = []
blank = os.path.join(WORK, 'cap_blank.png'); Image.new('RGBA', (W, 300), (0, 0, 0, 0)).save(blank)
tcur = 0.0
for b, st, d_ in times:
    if st > tcur: frames.append((blank, st - tcur)); tcur = st
    words = DIAC.sub('', TXT[b]).replace('…', ' ').replace('!', ' ! ').split()
    words = [w for w in words if w != '!'] or words
    chunks = [words[i:i + 3] for i in range(0, len(words), 3)]
    total = sum(len(w) + 1 for w in words)
    for ci, ch in enumerate(chunks):
        for wi, w in enumerate(ch):
            wd = d_ * (len(w) + 1) / total
            im = Image.new('RGBA', (W, 300), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
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

# ⑥ التجميع
HOOK_T = 1.6
cuts = sorted({round(v[0], 3) for v in TL.values() if 0.2 < v[0] < VD - 0.2})
inp = ['-i', FILM, '-loop', '1', '-i', os.path.join(WORK, 'top.png'), '-f', 'concat', '-safe', '0', '-i', os.path.join(WORK, 'caps.txt'),
       '-loop', '1', '-i', os.path.join(WORK, 'hook.png'), '-loop', '1', '-i', os.path.join(WORK, 'end.png')]
for f, _, _ in chips: inp += ['-loop', '1', '-i', f]
flt = ['[0:v]split[a][b]',
       '[a]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,boxblur=30:3,eq=brightness=-0.22[bg]' % (W, H, W, H),
       "[b]scale=-2:%d,crop=%d:%d:(iw-%d)/2:0[fg]" % (FG_H, W, FG_H, W),
       '[bg][fg]overlay=0:%d:shortest=1[v0]' % FG_Y]
cur = 'v0'
for i, (f, st, span) in enumerate(chips):
    flt.append("[%d:v]format=rgba[c%d]" % (5 + i, i))
    flt.append("[%s][c%d]overlay=0:%d:enable='between(t,%.3f,%.3f)'[k%d]" % (cur, i, FG_Y + 30, st + 0.15, st + span - 0.1, i)); cur = 'k%d' % i
flash = '+'.join("between(t,%.3f,%.3f)" % (c, c + 0.07) for c in cuts) or '0'
flt += ["[%s]drawbox=x=0:y=%d:w=%d:h=%d:color=white@0.55:t=fill:enable='%s'[f0]" % (cur, FG_Y, W, FG_H, flash),
        '[f0][1:v]overlay=0:0:shortest=1[v1]',
        '[2:v]format=rgba[cap]', '[v1][cap]overlay=0:%d:eof_action=pass[v2]' % (FG_Y + FG_H - 220),
        "[v2]drawbox=x=0:y=0:w='iw*t/%.3f':h=12:color=0xF7C74A@1:t=fill[v3]" % VD,
        '[3:v]format=rgba,fade=t=out:st=%.2f:d=0.25:alpha=1[hk]' % (HOOK_T - 0.25),
        "[v3][hk]overlay=0:0:enable='lte(t,%.2f)'[v4]" % HOOK_T,
        '[4:v]format=rgba,fade=t=in:st=%.2f:d=0.35:alpha=1[en]' % (VD - END_T),
        "[v4][en]overlay=0:0:enable='gte(t,%.2f)',fps=30,setsar=1,format=yuv420p[v]" % (VD - END_T)]
out = P('reels', RID + '.mp4')
run(inp + ['-filter_complex', ';'.join(flt), '-map', '[v]', '-map', '0:a', '-t', '%.3f' % VD,
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-c:a', 'aac', '-b:a', '192k', out])
o_ = sp.run([FP, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', out],
            capture_output=True, text=True).stdout.strip()
assert o_ == '%d,%d' % (W, H), '⛔ الريلز ليس عموديّاً %s' % o_
print('✅ %s | %.1f ث | %d قطعاً | %d بطاقة معركة | %d إطار ترجمة' % (out, VD, len(cuts), len(chips), len(frames)))
