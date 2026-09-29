# -*- coding: utf-8 -*-
"""ريلز الافتتاحية: يقصّ بداية الفيلم نفسه عمودياً ويقطعه عند لحظةٍ مشوّقة ثم يكتب «تابع الفيديو كاملاً في القناة».
(أمر المالك 2026-09-28: «الافتتاحية نفسها يجب أن تنشر كريلز ثالث ويقطع في مكان مشوق جدا»)
الاستعمال: python mkreel_open.py <projectDir> <reelId>
يقرأ من reels.json: {"id":"r3","from_film":"TR1","cut_into":3.5,"title":"..."}
  from_film = اللقطة التي يقع فيها القطع، cut_into = الثواني بعد بدايتها (منتصف التحوّل مثلاً).
يحتاج film.mp4 وtimeline.json من mont_hybrid.py.
"""
import json, os, sys, subprocess as sp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envpaths
from PIL import Image, ImageDraw
from envpaths import ar

PROJ, RID = os.path.abspath(sys.argv[1]), sys.argv[2]
FF, FB = envpaths.FF, envpaths.font(bold=True)
W, H, TAIL = 1080, 1920, 3.5
R = {r['id']: r for r in json.load(open(os.path.join(PROJ, 'reels.json'), encoding='utf-8'))}[RID]
TL = json.load(open(os.path.join(PROJ, 'timeline.json'), encoding='utf-8'))
CUT = TL[R['from_film']][0] + float(R.get('cut_into', 3.0))
# الشورت حتى 3 دقائق: الافتتاحية كاملةً ريلزاً (أمر المالك 2026-09-29) — تُقصّ عند 176 ث إن طالت بدل إسقاط الشوط
if CUT > 176: print('⚠ الافتتاحية %.1f ث أطول من حدّ الشورت ⇒ تُقصّ عند 176 ث' % CUT); CUT = 176.0
WORK = os.path.join(PROJ, 'reelwork', RID); os.makedirs(WORK, exist_ok=True)
OUTD = os.path.join(PROJ, 'reels'); os.makedirs(OUTD, exist_ok=True)


def band(d, y, text, size, fill, bg=None):
    f = envpaths.arfont(size, path=FB); t = ar(text); tw = d.textlength(t, font=f)
    if bg:
        d.rounded_rectangle([(W - tw) / 2 - 60, y - 24, (W + tw) / 2 + 60, y + size + 40], radius=40, fill=bg)
    for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
        d.text(((W - tw) / 2 + dx, y + dy), t, font=f, fill=(0, 0, 0, 255))
    d.text(((W - tw) / 2, y), t, font=f, fill=fill)


# العنوان فوق الإطار الأفقي طوال الريلز
top = Image.new('RGBA', (W, H), (0, 0, 0, 0))
dt = ImageDraw.Draw(top); ft_ = envpaths.arfont(70, path=FB); ls_, cur = [], ''
for w_ in R['title'].split():    # العنوان الطويل يُلفّ سطرين (خرج سطرٌ واحد عن عرض الشاشة في ريلز الزلاقة)
    c_ = (cur + ' ' + w_).strip()
    if dt.textlength(ar(c_), font=ft_) > W - 120 and cur: ls_.append(cur); cur = w_
    else: cur = c_
for i_, ln_ in enumerate(ls_ + [cur]):
    band(dt, 230 + i_ * 100, ln_, 70, (247, 199, 74, 255))
topp = os.path.join(WORK, 'top.png'); top.save(topp)
# بطاقة القطع: إطارٌ مجمَّد معتم ونداء المتابعة
end = Image.new('RGBA', (W, H), (0, 0, 0, 150))
d = ImageDraw.Draw(end)
band(d, 760, R.get('end_q', 'ماذا سيحدث بعد ذلك؟'), 76, (255, 255, 255, 255))
band(d, 900, R.get('end_cta', 'تابع الفيديو كاملاً في القناة'), 62, (255, 255, 255, 255), bg=(200, 32, 34, 245))
endp = os.path.join(WORK, 'end.png'); end.save(endp)

film = os.path.join(PROJ, 'film.mp4')
out = os.path.join(OUTD, RID + '.mp4')
# خلفيةٌ مموّهة من الفيلم نفسه تملأ العمودي، والإطار الأفقي كاملاً في الوسط (لا تُقصّ إيماءات الراوي)،
# ثم يُجمَّد آخر إطار TAIL ثانية تحت البطاقة، والصوت يخفت عند القطع
flt = ('[0:v]trim=0:%.3f,setpts=PTS-STARTPTS,split[a][b];'
       '[a]scale=-2:%d,crop=%d:%d,boxblur=30:3,eq=brightness=-0.12[bg];'
       '[b]scale=%d:-2[fg];[bg][fg]overlay=0:(H-h)/2[v0];[v0][1:v]overlay=0:0:shortest=1,tpad=stop_mode=clone:stop_duration=%.2f[v1];'
       '[2:v]format=rgba,fade=t=in:st=%.3f:d=0.3:alpha=1[e];[v1][e]overlay=0:0,fps=30,setsar=1,format=yuv420p[v];'
       '[0:a]atrim=0:%.3f,asetpts=PTS-STARTPTS,afade=t=out:st=%.3f:d=0.6,apad=pad_dur=%.2f[au]'
       % (CUT, H, W, H, W, TAIL, CUT, CUT, CUT - 0.6, TAIL))
sp.run([FF, '-v', 'error', '-y', '-i', film, '-loop', '1', '-i', topp, '-loop', '1', '-i', endp, '-filter_complex', flt,
        '-map', '[v]', '-map', '[au]', '-t', '%.3f' % (CUT + TAIL), '-c:v', 'libx264', '-preset', 'veryfast',
        '-crf', '21', '-c:a', 'aac', '-b:a', '192k', out], check=True)
print('✅ %s | القطع عند %.1f ث + بطاقة %.1f ث' % (out, CUT, TAIL))
