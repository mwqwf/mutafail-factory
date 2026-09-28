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
STILL = {s['id'] for s in shots if s.get('still')}
ENC = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', '25', '-an']


def dur(f):
    o = sp.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', f], capture_output=True, text=True)
    return float(o.stdout.strip())


def clip(sid):
    # مقطعُ Kling؛ وإن فشلت مطابقةُ شفاه الراوي فالخامُ المتحرّك خيرٌ من صورةٍ ثابتة
    if sid in STILL: return None                   # مقطعٌ رُفض بعد الفحص (وجهُ صحابيّ مثلاً): تبقى الصورة المعتمدة
    return (find(sid + '_av', ['clips'], ['mp4']) or find(sid, ['clips'], ['mp4'])
            or find(sid + '_raw', ['clips'], ['mp4']))


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
# لقطةٌ بلا كلام (تحوّل الراوي في الزلاقة): "hold": ثوانٍ و"blocks": [] ⇒ صمتٌ في مسار الصوت بطولها
HOLD = {}
for s in shots:
    if s.get('hold') and not s['blocks']:
        h = os.path.join(WORK, 'hold_%s.wav' % s['id'])
        sp.run([FF, '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono', '-t', '%.3f' % (float(s['hold']) * 1.05), h], check=True)
        HOLD[s['id']] = h
order, seen = [], set()
for s in shots:
    if s['id'] in HOLD: order.append(HOLD[s['id']])
    for bid in s['blocks']:
        if bid not in seen: seen.add(bid); order.append(bid)
order += [b['id'] for b in blocks if b['id'] not in seen]   # كتلةٌ بلا لقطة تبقى في الصوت كما كانت
with open(os.path.join(WORK, 'alist.txt'), 'w', encoding='utf-8') as fh:
    for x in order:
        if x in HOLD.values():
            fh.write("file '%s'\n" % x.replace('\\', '/')); continue
        a = P('audio', x + '.wav'); durs[x] = dur(a)
        fh.write("file '%s'\nfile '%s'\n" % (a.replace('\\', '/'), sil.replace('\\', '/')))
span_of = lambda s: float(s['hold']) if s['id'] in HOLD else sum(durs[b] + GAP for b in s['blocks']) / 1.05
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
    if clip(s['id']):
        continue
    span = span_of(s)
    an = find(s['id'], ['anim'], ['mp4'])
    if an and dur(an) >= span - 0.5:
        continue
    jobs.append((find(s['id'], ['images', 'img'], ['jpg', 'png']), P('anim', '%s.mp4' % s['id']), span + 0.3, n))
if jobs:
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(os.cpu_count() or 2) as ex:
        for i, f in enumerate(ex.map(_pre, jobs)):
            print('  kb3d [%d/%d] %s' % (i + 1, len(jobs), os.path.basename(f)), flush=True)

STRIP = lambda x: ''.join(ch for ch in x if not ('\u064b' <= ch <= '\u0652' or ch == '\u0670'))


def word_time(s, o):
    """زمنُ كلمةٍ داخل اللقطة تقديراً بموضعها من نصّ كتلتها (نسبة الحروف ≈ نسبة الزمن)."""
    txt = {b['id']: b['text'] for b in blocks}
    t0 = 0.0
    for bid in s['blocks']:
        plain = STRIP(txt[bid]); k = plain.find(STRIP(o['word']))
        if k >= 0:
            return (t0 + durs[bid] * k / max(1, len(plain))) / 1.05 + float(o.get('lead', -0.15))
        t0 += durs[bid] + GAP
    return float(o.get('at', 0))


def overlay(s, seg, span):
    """يركّب صور ui/ الشفافة على المقطع: تظهر بتلاشٍ سريع عند كلمتها وتبقى حتى نهاية اللقطة؛ و"shake" يهزّها ثانيةً."""
    res = seg[:-4] + '_ov.mp4'
    if os.path.exists(res) and abs(dur(res) - span) < 0.08: return res
    cmd = [FF, '-v', 'error', '-y', '-i', seg]; flt = []; last = '[0:v]'
    for i, o in enumerate(s['overlays']):
        png = P(o['png'])
        cmd += ['-loop', '1', '-t', '%.3f' % span, '-i', png]
        T = max(0.0, word_time(s, o)); x, y = int(o['x']), int(o['y'])
        flt.append('[%d:v]scale=%d:-1,format=rgba,fade=t=in:st=%.2f:d=0.25:alpha=1[o%d]' % (i + 1, int(o['w']), T, i))
        xe = ("'%d+if(between(t,%.2f,%.2f),14*sin(45*(t-%.2f)),0)'" % (x, T, T + 1.2, T)) if o.get('shake') else str(x)
        flt.append("%s[o%d]overlay=x=%s:y=%d:enable='gte(t,%.2f)'[v%d]" % (last, i, xe, y, T, i)); last = '[v%d]' % i
    sp.run(cmd + ['-filter_complex', ';'.join(flt), '-map', last, '-t', '%.3f' % span] + ENC + [res], check=True)
    return res


# ② اللقطات + جدول المؤثّرات
segs, fx = [], []   # fx: (بداية، مدة، ملف، مستوى)
t = 0.0
TL = {}             # بداية كل لقطة ومدتها في الفيلم — يقرؤها mkreel_open.py لقصّ ريلز الافتتاحية
for n, s in enumerate(shots):
    span = span_of(s)
    out = os.path.join(SEG, 's%03d.mp4' % n)
    kl = clip(s['id']); img = find(s['id'], ['images', 'img'], ['jpg', 'png'])
    an = find(s['id'], ['anim'], ['mp4'])
    if not (os.path.exists(out) and abs(dur(out) - span) < 0.08):
        if kl:
            kd = dur(kl)
            if s.get('lipsync') and kd >= span - 1.5:
                sp.run([FF, '-v', 'error', '-y', '-i', kl, '-vf', 'scale=1920:1080,fps=25,tpad=stop_mode=clone:stop_duration=%.3f' % max(0.0, span - kd + 0.1),
                        '-t', '%.3f' % span] + ENC + [out], check=True)
            elif span <= kd * 1.4:
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
    if s.get('overlays'):                          # زرّ الاشتراك والجرس لحظةَ نطق كلمتهما (الزلاقة)
        out = overlay(s, out, span)
    segs.append(out)
    # صوتُ Kling الطبيعي (إن اجتاز الفحص) وإلا مؤثّرُ المكتبة
    if kl and os.path.exists(kl[:-4] + '.ok'):
        fx.append((t, min(span, dur(kl)), kl, 0.35))
    elif s.get('sfx') and s['sfx'] != 'none':
        c = sorted(glob.glob(os.path.join(SFX, s['sfx'] + '_*.ogg')))
        if c: fx.append((t, span, random.Random(n).choice(c), float(s.get('sfx_vol', 0.22))))
    TL[s['id']] = [round(t, 3), round(span, 3)]
    t += span
    print('  [%d/%d] %s · %.1f ث · %s' % (n + 1, len(shots), s['id'], span, s.get('sfx', '-')), flush=True)

json.dump(TL, open(P('timeline.json'), 'w', encoding='utf-8'))
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
