# -*- coding: utf-8 -*-
"""المونتاج الهجين (معمَّم من «اليرموك» 2026-09-27): صوت الكتل + لقطات Kling حيث وُجدت وkb3d للباقي
+ **طبقة مؤثّرات لكل لقطة** (assets/sfx/<فئة>_*.ogg حسب حقل sfx) + صوت Kling الطبيعي إن وُجد + رياح + شعار.
الاستعمال: python tools/mont_hybrid.py <proj> [GAP]
⛔ لا موسيقى: المؤثّرات طبيعية CC0، وصوتُ Kling لا يدخل إلا إن اجتاز sfx_gate (clips/<id>.ok)."""
import json, os, sys, glob, random, subprocess as sp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cards, envpaths, kb3d, kinetic, transitions   # kinetic: الكتابة المتحرّكة بأسلوب العروض التقديمية (أمر المالك 2026-10-04)
from sfx_verdict import ok as sfx_ok   # صوت Kling يدخل بحكمٍ مطابقٍ لبصمة المقطع الحاليّ (MF-07)
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
SHOT = {s['id']: s for s in shots}
# عنوانُ كلّ فصلٍ (عدا الافتتاحية) يُكتب أعلى أوّل لقطةٍ فيه — kinetic.chapter_els
_secs = json.load(open(P('sections.json'), encoding='utf-8')) if os.path.exists(P('sections.json')) else []
_first = {x['id']: x['title'] for x in _secs[1:]}
for _s in shots:
    if _s.get('blocks') and _s['blocks'][0] in _first and not _s.get('_chapter'):
        _s['_chapter'] = _first.pop(_s['blocks'][0])
ENC = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', '25', '-an']


def dur(f):
    o = sp.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', f], capture_output=True, text=True)
    return float(o.stdout.strip())


def clip(sid):
    # مقطعُ Kling؛ وإن فشلت مطابقةُ شفاه الراوي فالخامُ المتحرّك خيرٌ من صورةٍ ثابتة
    if sid in STILL: return None                   # مقطعٌ رُفض بعد الفحص (وجهُ صحابيّ مثلاً): تبقى الصورة المعتمدة
    if SHOT.get(sid, {}).get('clip'):             # الأرك 2026-10-04: مقطعُ لقطةٍ أخرى يُعاد في الافتتاحية بلا كلفة
        r = kinetic.reuse_clip(PROJ, SHOT[sid])
        if r: return r
    return (find(sid + '_av', ['clips'], ['mp4']) or find(sid, ['clips'], ['mp4'])
            or find(sid + '_raw', ['clips'], ['mp4']))


def image_of(s):
    # الصورة باسم file إن اختلف عن معرّف اللقطة (لقطتان تتشاركان صورة — ملاذكرد 2026-10-03: 35 لقطة سقطت هنا)
    return (find(s['id'], ['images', 'img'], ['jpg', 'png'])
            or find(s.get('file', '').rsplit('.', 1)[0], ['images', 'img'], ['jpg', 'png']))


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
# سلسلة معالجة الصوت: الافتراضية، أو ما اختاره مختبر الأصوات للفيلم (publish.json: voice_filter — الأرك 2026-10-04)
VF = 'atempo=1.05,adeclick,dynaudnorm'
try:
    VF = json.load(open(P('publish.json'), encoding='utf-8')).get('voice_filter') or VF
except (OSError, ValueError):
    pass
assert VF.startswith('atempo=1.05,adeclick'), 'سلسلة الصوت يجب أن تبدأ بـatempo=1.05,adeclick (التوقيت ودرس الطقطقة)'
sp.run([FF, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', os.path.join(WORK, 'alist.txt'),
        '-filter:a', VF, '-ar', '48000', voice], check=True)
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
    jobs.append((image_of(s), P('anim', '%s.mp4' % s['id']), span + 0.3, n))
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


def captions(s, seg, span):
    """"title": {"text","sub","word"|"at"} ⇒ اسمٌ كبير بخطٍّ عربيّ يظهر بتلاشٍ عند كلمته.
    "counter": {"from":2026,"to":1260,"start":0.4,"secs":4.5,"suffix":"م","then":"٦٥٨ هـ"} ⇒ عدّادُ سنين تنازليّ متسارعٌ ثم متباطئ.
    نصٌّ مركَّبٌ على المقطع فقط — لا يُرسم به محتوى صورة."""
    res = seg[:-4] + '_cap.mp4'
    if os.path.exists(res) and abs(dur(res) - span) < 0.08: return res
    fb = envpaths.font(bold=True)
    cmd = [FF, '-v', 'error', '-y', '-i', seg]; flt = []; last = '[0:v]'; k = 0

    def card(lines, name):
        W, H = 1920, 1080
        im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        y = H * 0.36
        for txt, size, col in lines:
            f = envpaths.arfont(size, path=fb); t = envpaths.ar(txt); tw = d.textlength(t, font=f)
            for r in (10, 7, 4):
                sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(sh).text(((W - tw) / 2, y), t, font=f, fill=(0, 0, 0, 90))
                im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(r)))
            d = ImageDraw.Draw(im); d.text(((W - tw) / 2, y), t, font=f, fill=col)
            y += size * 1.35
        p = os.path.join(WORK, name); im.save(p); return p

    ti = s.get('title')
    # ⛔ أمر المالك 2026-10-04: العنوان بطاقةٌ من كوديكس (tools/cards.py) — لا يُرسم هنا، والغائبة يُتخطّى عنصرها
    spec = next((c for c in cards.shot_cards(s, {}) if c['role'] == 'title'), None) if ti else None
    tim = kinetic.card(PROJ, spec['key']) if spec else None
    if ti and tim is not None:
        T = max(0.0, word_time(s, ti)) if ti.get('word') else float(ti.get('at', 0.3))
        tim = kinetic.fit(tim, 1500, 420)
        full = Image.new('RGBA', (1920, 1080), (0, 0, 0, 0)); full.alpha_composite(tim, ((1920 - tim.width) // 2, int(1080 * 0.36)))
        tp = os.path.join(WORK, 'title_%s.png' % s['id']); full.save(tp)
        cmd += ['-loop', '1', '-t', '%.3f' % span, '-i', tp]; k += 1
        flt.append('[%d:v]format=rgba,fade=t=in:st=%.2f:d=0.6:alpha=1[t%d]' % (k, T, k))
        flt.append("%s[t%d]overlay=0:0:enable='gte(t,%.2f)'[v%d]" % (last, k, T, k)); last = '[v%d]' % k
    c = s.get('counter')
    if c:
        # إطاراتٌ بـPIL (drawtext لا يصل الحروف العربية وقد لا يوجد): أرقامٌ عربيةٌ مشرقية بمنحنى تباطؤ 1-(1-x)^3
        a, b = int(c['from']), int(c['to']); st = float(c.get('start', 0.4)); L = float(c.get('secs', 4.5))
        fdir = os.path.join(WORK, 'cnt_%s' % s['id']); os.makedirs(fdir, exist_ok=True)
        f = envpaths.arfont(150, path=fb); fs = envpaths.arfont(80, path=fb)
        IND = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
        n = int(round((span - st) * 25)) + 1
        for i in range(n):
            x = min(1.0, (i / 25.0) / L); yr = int(round(a - (a - b) * (1 - (1 - x) ** 3)))
            im = Image.new('RGBA', (1920, 340), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            t1 = envpaths.ar(str(yr).translate(IND) + ' ' + c.get('suffix', 'م'))
            rows = [(t1, f, (244, 214, 140, 255), 20)]
            if c.get('then') and x >= 1.0: rows.append((envpaths.ar(c['then']), fs, (255, 255, 255, 240), 205))
            for t, ff, col, y in rows:
                tw = d.textlength(t, font=ff)
                for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4), (3, 3)):
                    d.text(((1920 - tw) / 2 + dx, y + dy), t, font=ff, fill=(0, 0, 0, 170))
                d.text(((1920 - tw) / 2, y), t, font=ff, fill=col)
            im.save(os.path.join(fdir, '%04d.png' % i))
        k += 1
        cmd += ['-framerate', '25', '-i', os.path.join(fdir, '%04d.png')]
        flt.append('[%d:v]format=rgba,setpts=PTS+%.3f/TB,fade=t=in:st=%.2f:d=0.3:alpha=1[c%d]' % (k, st, st, k))
        flt.append("%s[c%d]overlay=0:H*0.34:eof_action=repeat:enable='gte(t,%.2f)'[w%d]" % (last, k, st, k)); last = '[w%d]' % k
    if not flt:
        return seg                                   # بطاقةٌ غائبة ولا عدّاد: المقطع كما هو
    sp.run(cmd + ['-filter_complex', ';'.join(flt), '-map', last, '-t', '%.3f' % span] + ENC + [res], check=True)
    return res


# ② اللقطات + جدول المؤثّرات
segs, fx = [], []   # fx: (بداية، مدة، ملف، مستوى)
clean = []          # المقاطع قبل الكتابة المتحرّكة والبطاقات — تُصنع منها الريلزات العمودية فلا يُقصّ نصٌّ محروق
# ⭐ أمر المالك 2026-10-03 («لا أكشن»): كان المقطعُ الحيّ يُبطَّأ ×1.4 ليملأ كلاماً أطول، فتصير الخيلُ والسيوف حركةً بطيئةً
#    مائعة. ⇒ لا إبطاء فوق ×1.15، وما زاد يكمله kb3d — والعلاجُ الحقّ لقطاتٌ أقصر (thrill_gate: ≤ 6 ث متوسّطاً).
SLOW_MAX = 1.15
t = 0.0
TL = {}             # بداية كل لقطة ومدتها في الفيلم — يقرؤها mkreel_open.py لقصّ ريلز الافتتاحية
for n, s in enumerate(shots):
    span = span_of(s)
    out = os.path.join(SEG, 's%03d.mp4' % n)
    kl = clip(s['id']); img = image_of(s)
    an = find(s['id'], ['anim'], ['mp4'])
    if not (os.path.exists(out) and abs(dur(out) - span) < 0.08):
        if kl:
            kd = dur(kl)
            if s.get('lipsync') and kd >= span - 1.5:
                # ⛔ درس عين جالوت (حكم المالك 2026-09-29): مدُّ الإطار الأخير (tpad clone) جمّد الراوي ويده قبل القطع — «طريقة بدائية».
                #    ⇒ النقص يُملأ بإبطاء آخر ثانيةٍ من المقطع نفسه (الكلام انتهى فيها)، فتبقى الحركة حيّةً حتى القطع.
                short = span - kd
                if short > 0.04:
                    tail = min(1.0, kd)
                    k = (tail + short + 0.05) / tail
                    sp.run([FF, '-v', 'error', '-y', '-i', kl, '-filter_complex',
                            '[0:v]scale=1920:1080,fps=25,split[a][b];[a]trim=0:%.3f,setpts=PTS-STARTPTS[h];'
                            '[b]trim=%.3f,setpts=%.4f*(PTS-STARTPTS),fps=25[t];[h][t]concat=n=2:v=1[v]' % (kd - tail, kd - tail, k),
                            '-map', '[v]', '-t', '%.3f' % span] + ENC + [out], check=True)
                else:
                    sp.run([FF, '-v', 'error', '-y', '-i', kl, '-vf', 'scale=1920:1080,fps=25',
                            '-t', '%.3f' % span] + ENC + [out], check=True)
            elif span <= kd * SLOW_MAX:
                # لقطة التحوّل (FLF) تُضغط إن طالت فلا يُقصّ آخرها — نهايتها هي صورة اللقطة التالية (ظهور الراوي في حطّين)
                k = span / kd if s.get('end_image') else max(1.0, span / kd)
                sp.run([FF, '-v', 'error', '-y', '-i', kl, '-vf', 'setpts=%.4f*PTS,scale=1920:1080,fps=25' % k,
                        '-t', '%.3f' % span] + ENC + [out], check=True)
            else:
                a, b2 = out[:-4] + '_a.mp4', out[:-4] + '_b.mp4'
                sp.run([FF, '-v', 'error', '-y', '-i', kl, '-vf', 'setpts=%.2f*PTS,scale=1920:1080,fps=25' % SLOW_MAX, '-t', '%.3f' % (kd * SLOW_MAX)] + ENC + [a], check=True)
                kb3d.render(img, b2, span - kd * SLOW_MAX, n)
                lst = out[:-4] + '.txt'
                open(lst, 'w', encoding='utf-8').write("file '%s'\nfile '%s'\n" % (a.replace('\\', '/'), b2.replace('\\', '/')))
                sp.run([FF, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-vf', 'fps=25'] + ENC + [out], check=True)
        else:
            if not (an and dur(an) >= span - 0.5):
                an = P('anim', '%s.mp4' % s['id']); os.makedirs(P('anim'), exist_ok=True); kb3d.render(img, an, span + 0.3, n)
            pad = max(0.0, span - dur(an) + 0.1)
            sp.run([FF, '-v', 'error', '-y', '-i', an, '-vf', 'tpad=stop_mode=clone:stop_duration=%.3f,fps=25' % pad,
                    '-t', '%.3f' % span] + ENC + [out], check=True)
    clean.append(out)
    if s.get('overlays'):                          # زرّ الاشتراك والجرس لحظةَ نطق كلمتهما (الزلاقة)
        out = overlay(s, out, span)
    if s.get('title') or s.get('counter'):         # بطاقةُ الاسم لحظةَ كشفه وعدّادُ السنين في العودة إلى الماضي (عين جالوت)
        out = captions(s, out, span)
    if kinetic.has_fx(s):                          # الكتابة المتحرّكة والضربات والبطاقات (الأرك)
        out = kinetic.apply(PROJ, s, out, span, {b['id']: b['text'] for b in blocks}, durs, GAP, WORK, ENC)
    segs.append(out)
    # صوتُ Kling الطبيعي (إن اجتاز الفحص) وإلا مؤثّرُ المكتبة
    if kl and sfx_ok(kl):
        fx.append((t, min(span, dur(kl)), kl, 0.35))
    elif s.get('sfx') and s['sfx'] != 'none':
        c = sorted(glob.glob(os.path.join(SFX, s['sfx'] + '_*.ogg')))
        if c: fx.append((t, span, random.Random(n).choice(c), float(s.get('sfx_vol', 0.22))))
    TL[s['id']] = [round(t, 3), round(span, 3)]
    t += span
    print('  [%d/%d] %s · %.1f ث · %s' % (n + 1, len(shots), s['id'], span, s.get('sfx', '-')), flush=True)

json.dump(TL, open(P('timeline.json'), 'w', encoding='utf-8'))
# ②ب الانتقالات بحسب الموقف (أمر المالك 2026-10-04: «تلاشي الصور وظهور الجديدة، وانقسام صورة ثم ظهور الجديدة مكانها…»)
#    متمركزةٌ على نقاط القطع بلا تغيير عدد الإطارات، فتبقى timeline.json والصوت متزامنين؛ والنسخة النظيفة بالانتقالات نفسها
TP = transitions.plan(shots, _secs)
print('②ب الانتقالات: %d من %d حدّاً' % (sum(1 for x in TP if x), len(TP)), flush=True)
segs = transitions.apply(segs, TP, WORK, ENC, 'v')
clean = transitions.apply(clean, TP, WORK, ENC, 'c')
vlist = os.path.join(WORK, 'vlist.txt')
open(vlist, 'w', encoding='utf-8').write(''.join("file '%s'\n" % x.replace('\\', '/') for x in segs))
silent = os.path.join(WORK, 'video_silent.mp4')
clist = os.path.join(WORK, 'clist.txt')
open(clist, 'w', encoding='utf-8').write(''.join("file '%s'\n" % x.replace('\\', '/') for x in clean))
sp.run([FF, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', clist, '-c', 'copy', os.path.join(WORK, 'video_clean.mp4')], check=True)
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
