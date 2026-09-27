# -*- coding: utf-8 -*-
"""المونتاج الهجين (معمَّم من «اليرموك» 2026-09-27): صوت الكتل + لقطات Kling حيث وُجدت وkb3d للباقي
+ **طبقة مؤثّرات لكل لقطة** (assets/sfx/<فئة>_*.ogg حسب حقل sfx) + صوت Kling الطبيعي إن وُجد + رياح + شعار.
الاستعمال: python tools/mont_hybrid.py <proj> [GAP]
⛔ لا موسيقى: المؤثّرات طبيعية CC0، وصوتُ Kling لا يدخل إلا إن اجتاز sfx_gate (clips/<id>.ok)."""
import json, os, sys, glob, random, subprocess as sp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envpaths, kb3d
from envpaths import FF, FP
from PIL import Image, ImageDraw, ImageFilter

PROJ = os.path.abspath(sys.argv[1])
GAP = float(sys.argv[2]) if len(sys.argv) > 2 else 0.30
SFX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'sfx')
P = lambda *a: os.path.join(PROJ, *a)
WORK = P('work'); SEG = os.path.join(WORK, 'seg'); os.makedirs(SEG, exist_ok=True)
blocks = [b for b in json.load(open(P('blocks.json'), encoding='utf-8')) if not b.get('reel_only')]
shots = json.load(open(P('shots.json'), encoding='utf-8'))
ENC = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', '25', '-an']


def dur(f):
    o = sp.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', f], capture_output=True, text=True)
    return float(o.stdout.strip())


def find(sid, dirs, exts):
    for d in dirs:
        for e in exts:
            for n in (sid, 'ym_' + sid):
                p = P(d, '%s.%s' % (n, e))
                if os.path.exists(p): return p


# ① الصوت — ⛔ adeclick إلزامي (درس الطقطقة)
sil = os.path.join(WORK, 'sil.wav')
sp.run([FF, '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono', '-t', str(GAP), sil], check=True)
durs = {}
with open(os.path.join(WORK, 'alist.txt'), 'w', encoding='utf-8') as fh:
    for b in blocks:
        a = P('audio', b['id'] + '.wav'); durs[b['id']] = dur(a)
        fh.write("file '%s'\nfile '%s'\n" % (a.replace('\\', '/'), sil.replace('\\', '/')))
voice = os.path.join(WORK, 'voice.wav')
sp.run([FF, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', os.path.join(WORK, 'alist.txt'),
        '-filter:a', 'atempo=1.05,adeclick,dynaudnorm', '-ar', '48000', voice], check=True)
VD = dur(voice); print('① الصوت %.2f د' % (VD / 60), flush=True)

# ①ب تصييرُ مشاهد kb3d مسبقاً بالتوازي على كلّ الأنوية (درس القادسية: تسلسلياً أخذ ساعاتٍ على عدّاء GitHub)
def _pre(job):
    kb3d.render(*job)
    return job[1]

jobs = []
os.makedirs(P('anim'), exist_ok=True)
for n, s in enumerate(shots):
    if find(s['id'], ['clips'], ['mp4']):
        continue
    span = sum(durs[b] + GAP for b in s['blocks']) / 1.05
    an = find(s['id'], ['anim'], ['mp4'])
    if an and dur(an) >= span - 0.5:
        continue
    jobs.append((find(s['id'], ['images', 'img'], ['jpg', 'png']), P('anim', '%s.mp4' % s['id']), span + 0.3, n))
if jobs:
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(os.cpu_count() or 2) as ex:
        for i, f in enumerate(ex.map(_pre, jobs)):
            print('  kb3d [%d/%d] %s' % (i + 1, len(jobs), os.path.basename(f)), flush=True)

# ② اللقطات + جدول المؤثّرات
segs, fx = [], []   # fx: (بداية، مدة، ملف، مستوى)
t = 0.0
for n, s in enumerate(shots):
    span = sum(durs[b] + GAP for b in s['blocks']) / 1.05
    out = os.path.join(SEG, 's%03d.mp4' % n)
    kl = find(s['id'], ['clips'], ['mp4']); img = find(s['id'], ['images', 'img'], ['jpg', 'png'])
    an = find(s['id'], ['anim'], ['mp4'])
    if not (os.path.exists(out) and abs(dur(out) - span) < 0.08):
        if kl:
            kd = dur(kl)
            if span <= kd * 1.4:
                sp.run([FF, '-v', 'error', '-y', '-i', kl, '-vf', 'setpts=%.4f*PTS,scale=1920:1080,fps=25' % max(1.0, span / kd),
                        '-t', '%.3f' % span] + ENC + [out], check=True)
            else:
                a, b2 = out[:-4] + '_a.mp4', out[:-4] + '_b.mp4'
                sp.run([FF, '-v', 'error', '-y', '-i', kl, '-vf', 'setpts=1.4*PTS,scale=1920:1080,fps=25', '-t', '%.3f' % (kd * 1.4)] + ENC + [a], check=True)
                kb3d.render(img, b2, span - kd * 1.4, n)
                lst = out[:-4] + '.txt'
                open(lst, 'w', encoding='utf-8').write("file '%s'\nfile '%s'\n" % (a.replace('\\', '/'), b2.replace('\\', '/')))
                sp.run([FF, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-vf', 'fps=25'] + ENC + [out], check=True)
        else:
            if not (an and dur(an) >= span - 0.5):
                an = P('anim', '%s.mp4' % s['id']); os.makedirs(P('anim'), exist_ok=True); kb3d.render(img, an, span + 0.3, n)
            pad = max(0.0, span - dur(an) + 0.1)
            sp.run([FF, '-v', 'error', '-y', '-i', an, '-vf', 'tpad=stop_mode=clone:stop_duration=%.3f,fps=25' % pad,
                    '-t', '%.3f' % span] + ENC + [out], check=True)
    segs.append(out)
    # صوتُ Kling الطبيعي (إن اجتاز الفحص) وإلا مؤثّرُ المكتبة
    if kl and os.path.exists(kl[:-4] + '.ok'):
        fx.append((t, min(span, dur(kl)), kl, 0.35))
    elif s.get('sfx') and s['sfx'] != 'none':
        c = sorted(glob.glob(os.path.join(SFX, s['sfx'] + '_*.ogg')))
        if c: fx.append((t, span, random.Random(n).choice(c), 0.22))
    t += span
    print('  [%d/%d] %s · %.1f ث · %s' % (n + 1, len(shots), s['id'], span, s.get('sfx', '-')), flush=True)

vlist = os.path.join(WORK, 'vlist.txt')
open(vlist, 'w', encoding='utf-8').write(''.join("file '%s'\n" % x.replace('\\', '/') for x in segs))
silent = os.path.join(WORK, 'video_silent.mp4')
sp.run([FF, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', vlist, '-c', 'copy', silent], check=True)

# ③ المزج: الصوت + الرياح + المؤثّرات (−18dB تقريباً تحت الكلام)
inp = [FF, '-v', 'error', '-y', '-i', voice, '-f', 'lavfi', '-t', str(VD), '-i', 'anoisesrc=c=pink:r=48000']
flt = ['[1:a]lowpass=520,highpass=60,volume=0.10[w]']; mix = ['[0:a]', '[w]']
for i, (st, d, f, vol) in enumerate(fx):
    inp += ['-stream_loop', '-1', '-i', f]
    k = i + 2
    flt.append('[%d:a]atrim=0:%.3f,afade=t=in:d=0.4,afade=t=out:st=%.3f:d=0.6,volume=%.2f,adelay=%d|%d,aresample=48000,aformat=channel_layouts=mono[f%d]'
               % (k, d, max(0, d - 0.6), vol, int(st * 1000), int(st * 1000), i))
    mix.append('[f%d]' % i)
flt.append('%samix=inputs=%d:duration=first:normalize=0[a]' % (''.join(mix), len(mix)))
mixed = os.path.join(WORK, 'audio_final.m4a')
sp.run(inp + ['-filter_complex', ';'.join(flt), '-map', '[a]', '-c:a', 'aac', '-b:a', '192k', mixed], check=True)

# ④ الدمج والشعار (⛔ لا فيلم بلا شعار)
lg = os.path.join(WORK, 'logo_round.png')
im = Image.open(envpaths.logo(required=True)).convert('RGBA').resize((120, 120), Image.LANCZOS)
m = Image.new('L', (480, 480), 0); ImageDraw.Draw(m).ellipse([4, 4, 476, 476], fill=255)
m = m.filter(ImageFilter.GaussianBlur(3)).resize((120, 120), Image.LANCZOS)
o = Image.new('RGBA', (120, 120), (0, 0, 0, 0)); o.paste(im, (0, 0), m)
o.putalpha(o.split()[3].point(lambda v: int(v * 0.72))); o.save(lg)
final = P('film.mp4')
sp.run([FF, '-v', 'error', '-y', '-i', silent, '-i', mixed, '-i', lg, '-filter_complex', '[0:v][2:v]overlay=W-w-46:46:format=auto[v]',
        '-map', '[v]', '-map', '1:a', '-c:v', 'libx264', '-preset', 'medium', '-crf', '24', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', final], check=True)
print('✅ %s | %.2f د | مؤثّرات: %d' % (final, dur(final) / 60, len(fx)), flush=True)
