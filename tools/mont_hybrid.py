# -*- coding: utf-8 -*-
"""المونتاج الهجين (معمَّم من «اليرموك» 2026-09-27): صوت الكتل + لقطات Kling حيث وُجدت وkb3d للباقي
+ **طبقة مؤثّرات لكل لقطة** (assets/sfx/<فئة>_*.ogg حسب حقل sfx) + صوت Kling الطبيعي إن وُجد + رياح + شعار.
الاستعمال: python tools/mont_hybrid.py <proj> [GAP]
⛔ لا موسيقى: المؤثّرات طبيعية CC0، وصوتُ Kling لا يدخل إلا إن اجتاز sfx_gate (clips/<id>.ok)."""
import json, os, sys, glob, random, subprocess as sp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cards, envpaths, kb3d, kinetic, look, sfx_synth, transitions   # kinetic: الكتابة المتحرّكة (أمر المالك 2026-10-04)
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

# ①أ الإطارات (الإصدار الثاني — حكم المالك 2026-10-04: «صورٌ متداخلة احترافية» بدل الظهور المفاجئ):
#    بدايةُ كلّ لقطةٍ إطاراً بالتقريب التراكميّ (لا انجراف بين الصورة والصوت مهما كثرت اللقطات)، ولكلّ لقطةٍ مقبضان حيّان
#    (HF إطاراً قبلها وبعدها) يتداخل فيهما الانتقال فلا تتجمّد صورة؛ والانتقالات تُخطَّط قبل التصيير.
HF = transitions.HF; HEAD = HF / 25.0
TP = transitions.plan(shots, _secs)
SECS = transitions.sections_of(shots, _secs)
FST, _acc = [], 0.0
for _s in shots:
    FST.append(int(round(_acc * 25))); _acc += span_of(_s)
FST.append(int(round(_acc * 25)))
NF = [FST[i + 1] - FST[i] for i in range(len(shots))]
LEN = lambda n: (NF[n] + 2 * HF) / 25.0          # مدّة مقطع اللقطة بمقبضيه
ENERGY = {'battle': 1.35, 'buildup': 1.1, None: 1.15}   # شدّة الحركة المجسّمة: المعركة أقوى، والافتتاحية حماسية
energy = lambda n: ENERGY.get(SECS[n], 1.0)
ANIM = lambda s: P('anim', '%s.v%d.mp4' % (s['id'], kb3d.VERSION))   # لا تُعاد مقاطع إصدارٍ أقدم
# «النصّ خلف العنصر» (طلب المالك 2026-10-04: «أقوى وأكثر إبهاراً»): لقطةٌ مجسّمة فيها كتابةٌ كبيرة (عبارةٌ وسطى، ضربة، عنوان فصل)
# يكتب لها kb3d قناع الطبقة القريبة إطاراً بإطار، فتمرّ الكتابة خلف القريب من الصورة إن حجب منها جزءاً معتدلاً
OCC = lambda s: bool((s.get('kt') or {}).get('style') == 'center' or (s.get('slam') and not s.get('cards')) or s.get('_chapter')
                     or s.get('title'))
MATTE = lambda s: ANIM(s)[:-4] + '.matte.mp4' if OCC(s) else None
need_matte = lambda s: OCC(s) and not (os.path.exists(MATTE(s)) or os.path.exists(MATTE(s) + '.none'))

# درجات الارتطام (بحث 2026-10-04: «لا تفاوت في الشدّة» من علامات الهواية): الثقيلة ثلاثٌ في الفيلم كلّه — اسم الفيلم، وأوّل ضربةٍ
# مكتوبة، وأوّل ضربةٍ في المعركة — والبقيّة متوسّطة
_heavy = [s['id'] for s in shots if s.get('title')][:1]
_heavy += [s['id'] for s in shots if s.get('slam') and s['id'] not in _heavy][:1]
_heavy += [s['id'] for n_, s in enumerate(shots) if s.get('slam') and SECS[n_] == 'battle' and s['id'] not in _heavy][:1]
for _s in shots:
    _s['_tier'] = 'heavy' if _s['id'] in _heavy[:3] else 'medium'

# ①ب تصييرُ مشاهد kb3d مسبقاً بالتوازي على كلّ الأنوية (درس القادسية: تسلسلياً أخذ ساعاتٍ على عدّاء GitHub)
def _pre(job):
    kb3d.render(*job)
    return job[1]

jobs = []
os.makedirs(P('anim'), exist_ok=True)
for n, s in enumerate(shots):
    if clip(s['id']):
        continue
    an = ANIM(s)
    if os.path.exists(an) and dur(an) >= LEN(n) - 0.02 and not need_matte(s):
        continue
    jobs.append((image_of(s), an, LEN(n) + 0.04, n, None, energy(n), MATTE(s)))
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


def overlay(s, seg, span, L):
    """يركّب صور ui/ الشفافة على المقطع: تظهر بتلاشٍ سريع عند كلمتها وتبقى حتى نهاية اللقطة؛ و"shake" يهزّها ثانيةً.
    المقطع بمقبضيه (مدّته L، وبداية اللقطة فيه عند HEAD)."""
    res = seg[:-4] + '_ov.mp4'
    if os.path.exists(res) and abs(dur(res) - L) < 0.03: return res
    cmd = [FF, '-v', 'error', '-y', '-i', seg]; flt = []; last = '[0:v]'
    for i, o in enumerate(s['overlays']):
        png = P(o['png'])
        cmd += ['-loop', '1', '-t', '%.3f' % L, '-i', png]
        T = max(0.0, word_time(s, o)) + HEAD; x, y = int(o['x']), int(o['y'])
        flt.append('[%d:v]scale=%d:-1,format=rgba,fade=t=in:st=%.2f:d=0.25:alpha=1[o%d]' % (i + 1, int(o['w']), T, i))
        xe = ("'%d+if(between(t,%.2f,%.2f),14*sin(45*(t-%.2f)),0)'" % (x, T, T + 1.2, T)) if o.get('shake') else str(x)
        flt.append("%s[o%d]overlay=x=%s:y=%d:enable='gte(t,%.2f)'[v%d]" % (last, i, xe, y, T, i)); last = '[v%d]' % i
    sp.run(cmd + ['-filter_complex', ';'.join(flt), '-map', last, '-frames:v', str(int(round(L * 25)))] + ENC + [res], check=True)
    return res


def captions(s, seg, span, L):
    """"title": {"text","sub","word"|"at"} ⇒ اسمٌ كبير بخطٍّ عربيّ يظهر بتلاشٍ عند كلمته.
    "counter": {"from":2026,"to":1260,"start":0.4,"secs":4.5,"suffix":"م","then":"٦٥٨ هـ"} ⇒ عدّادُ سنين تنازليّ متسارعٌ ثم متباطئ.
    نصٌّ مركَّبٌ على المقطع فقط — لا يُرسم به محتوى صورة."""
    res = seg[:-4] + '_cap.mp4'
    if os.path.exists(res) and abs(dur(res) - L) < 0.03: return res
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

    ti = s.get('title') if not kinetic.has_fx(s) else None   # العنوان صار ضربةً في kinetic (title_els)؛ هنا العدّاد وحده
    # ⛔ أمر المالك 2026-10-04: العنوان بطاقةٌ من كوديكس (tools/cards.py) — لا يُرسم هنا، والغائبة يُتخطّى عنصرها
    spec = next((c for c in cards.shot_cards(s, {}) if c['role'] == 'title'), None) if ti else None
    tim = kinetic.card(PROJ, spec['key']) if spec else None
    if ti and tim is not None:
        T = (max(0.0, word_time(s, ti)) if ti.get('word') else float(ti.get('at', 0.3))) + HEAD
        tim = kinetic.fit(tim, 1500, 420)
        full = Image.new('RGBA', (1920, 1080), (0, 0, 0, 0)); full.alpha_composite(tim, ((1920 - tim.width) // 2, int(1080 * 0.36)))
        tp = os.path.join(WORK, 'title_%s.png' % s['id']); full.save(tp)
        cmd += ['-loop', '1', '-t', '%.3f' % L, '-i', tp]; k += 1
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
        flt.append('[%d:v]format=rgba,setpts=PTS+%.3f/TB,fade=t=in:st=%.2f:d=0.3:alpha=1[c%d]' % (k, st + HEAD, st + HEAD, k))
        flt.append("%s[c%d]overlay=0:H*0.34:eof_action=repeat:enable='gte(t,%.2f)'[w%d]" % (last, k, st + HEAD, k)); last = '[w%d]' % k
    if not flt:
        return seg                                   # بطاقةٌ غائبة ولا عدّاد: المقطع كما هو
    sp.run(cmd + ['-filter_complex', ';'.join(flt), '-map', last, '-frames:v', str(int(round(L * 25)))] + ENC + [res], check=True)
    return res


# ② اللقطات + جدول المؤثّرات — كلّ مقطعٍ بمقبضيه: NF[n] + 2×HF إطاراً، وبداية اللقطة فيه عند HEAD
segs, fx = [], []   # fx: (بداية، مدة، ملف، مستوى)
clean = []          # المقاطع قبل الكتابة المتحرّكة والبطاقات — تُصنع منها الريلزات العمودية فلا يُقصّ نصٌّ محروق
# ⭐ أمر المالك 2026-10-03 («لا أكشن»): كان المقطعُ الحيّ يُبطَّأ ×1.4 ليملأ كلاماً أطول، فتصير الخيلُ والسيوف حركةً بطيئةً
#    مائعة. ⇒ لا إبطاء فوق ×1.15، وما زاد يكمله kb3d — والعلاجُ الحقّ لقطاتٌ أقصر (thrill_gate: ≤ 6 ث متوسّطاً).
SLOW_MAX = 1.15
TL = {}             # بداية كل لقطة ومدتها في الفيلم — يقرؤها mkreel_open.py لقصّ ريلز الافتتاحية
TEXTS = {b['id']: b['text'] for b in blocks}
for n, s in enumerate(shots):
    span = NF[n] / 25.0                            # مدّة اللقطة مؤطَّرةً (تختلف عن span_of بأقلّ من نصف إطار)
    L, NT = LEN(n), NF[n] + 2 * HF
    t = FST[n] / 25.0
    out = os.path.join(SEG, 's%03d_v%d.mp4' % (n, kb3d.VERSION))   # بإصدار المجسّم: تغيّره يعيد بناء المقطع
    kl = clip(s['id']); img = image_of(s)
    if not (os.path.exists(out) and abs(dur(out) - L) < 0.03):
        if kl:
            kd = dur(kl)
            if s.get('lipsync') or s.get('end_image'):
                # الشفاه والتحوّل مربوطان ببداية اللقطة ونهايتها: يُصنع الجسم بطول اللقطة ثم يُمدّ المقبضان بالإطار الطرفيّ
                # (الانتقال عند هذين قطعٌ حادّ في plan فلا يظهر المقبض المجمَّد)
                core = out[:-4] + '_core.mp4'
                if s.get('end_image'):
                    sp.run([FF, '-v', 'error', '-y', '-i', kl, '-vf', 'setpts=%.4f*PTS,scale=1920:1080,fps=25' % (span / kd),
                            '-t', '%.3f' % span] + ENC + [core], check=True)
                elif kd >= span - 1.5 and span - kd > 0.04:
                    # ⛔ درس عين جالوت (حكم المالك 2026-09-29): مدُّ الإطار الأخير جمّد الراوي ويده قبل القطع — «طريقة بدائية».
                    #    ⇒ النقص يُملأ بإبطاء آخر ثانيةٍ من المقطع نفسه (الكلام انتهى فيها)، فتبقى الحركة حيّةً حتى القطع.
                    short = span - kd
                    tail = min(1.0, kd)
                    k = (tail + short + 0.05) / tail
                    sp.run([FF, '-v', 'error', '-y', '-i', kl, '-filter_complex',
                            '[0:v]scale=1920:1080,fps=25,split[a][b];[a]trim=0:%.3f,setpts=PTS-STARTPTS[h];'
                            '[b]trim=%.3f,setpts=%.4f*(PTS-STARTPTS),fps=25[t];[h][t]concat=n=2:v=1[v]' % (kd - tail, kd - tail, k),
                            '-map', '[v]', '-t', '%.3f' % span] + ENC + [core], check=True)
                else:
                    sp.run([FF, '-v', 'error', '-y', '-i', kl, '-vf', 'scale=1920:1080,fps=25',
                            '-t', '%.3f' % span] + ENC + [core], check=True)
                sp.run([FF, '-v', 'error', '-y', '-i', core, '-vf', 'tpad=start_mode=clone:start=%d:stop_mode=clone:stop=%d' % (HF, HF + 4),
                        '-frames:v', str(NT)] + ENC + [out], check=True)
            elif L <= kd * SLOW_MAX:
                # المقطع الحيّ يبدأ من أوّل المقبض: محتواه يتقدّم نصف ثانيةٍ عن الكلام بلا ضرر، والتداخل حيٌّ من الجهتين
                sp.run([FF, '-v', 'error', '-y', '-i', kl, '-vf', 'setpts=%.4f*PTS,scale=1920:1080,fps=25,tpad=stop_mode=clone:stop=4'
                        % max(1.0, L / kd), '-frames:v', str(NT)] + ENC + [out], check=True)
            else:
                a, b2 = out[:-4] + '_a.mp4', out[:-4] + '_b.mp4'
                sp.run([FF, '-v', 'error', '-y', '-i', kl, '-vf', 'setpts=%.2f*PTS,scale=1920:1080,fps=25' % SLOW_MAX, '-t', '%.3f' % (kd * SLOW_MAX)] + ENC + [a], check=True)
                kb3d.render(img, b2, L - kd * SLOW_MAX + 0.12, n, None, energy(n))
                lst = out[:-4] + '.txt'
                open(lst, 'w', encoding='utf-8').write("file '%s'\nfile '%s'\n" % (a.replace('\\', '/'), b2.replace('\\', '/')))
                sp.run([FF, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-vf', 'fps=25,tpad=stop_mode=clone:stop=4',
                        '-frames:v', str(NT)] + ENC + [out], check=True)
        else:
            an = ANIM(s)
            if not (os.path.exists(an) and dur(an) >= L - 0.02) or need_matte(s):
                kb3d.render(img, an, L + 0.04, n, None, energy(n), MATTE(s))
            sp.run([FF, '-v', 'error', '-y', '-i', an, '-vf', 'tpad=stop_mode=clone:stop=4,fps=25',
                    '-frames:v', str(NT)] + ENC + [out], check=True)
    clean.append(out)
    if s.get('overlays'):                          # زرّ الاشتراك والجرس لحظةَ نطق كلمتهما (الزلاقة)
        out = overlay(s, out, span, L)
    if s.get('title') or s.get('counter'):         # بطاقةُ الاسم لحظةَ كشفه وعدّادُ السنين في العودة إلى الماضي (عين جالوت)
        out = captions(s, out, span, L)
    if kinetic.has_fx(s):                          # الكتابة المتحرّكة كلمةً كلمة والضربات والبطاقات (الأرك)
        mt = MATTE(s) if not kl else None                # القناع للّقطة المجسّمة وحدها (المقطع الحيّ بلا عمقٍ إطاراً بإطار)
        out = kinetic.apply(PROJ, s, out, span, TEXTS, durs, GAP, WORK, ENC, HEAD, L, mt if mt and os.path.exists(mt) else None)
    segs.append(out)
    # صوتُ Kling الطبيعي (إن اجتاز الفحص) وإلا مؤثّرُ المكتبة
    if kl and sfx_ok(kl):
        fx.append((t, min(span, dur(kl)), kl, 0.35))
    elif s.get('sfx') and s['sfx'] != 'none':
        c = sorted(glob.glob(os.path.join(SFX, s['sfx'] + '_*.ogg')))
        if c: fx.append((t, span, random.Random(n).choice(c), float(s.get('sfx_vol', 0.22))))
    TL[s['id']] = [round(t, 3), round(span, 3)]
    print('  [%d/%d] %s · %.1f ث · %s' % (n + 1, len(shots), s['id'], span, s.get('sfx', '-')), flush=True)

json.dump(TL, open(P('timeline.json'), 'w', encoding='utf-8'))
# ②ب الانتقالات المتداخلة بحسب الموقف (أمر المالك 2026-10-04: «صورٌ متداخلة احترافية» — tools/transitions.py)
#    مُجمِّعٌ واحد يقرأ المقاطع بمقابضها ويكتب الفيلم الصامت: عدد الإطارات = مجموع إطارات اللقطات، فالصوت متزامن
print('②ب الانتقالات: %d من %d حدّاً' % (sum(1 for x in TP if x), len(TP)), flush=True)
silent = os.path.join(WORK, 'video_silent.mp4')
# التدريج السينمائيّ بحسب الفصل (tools/look.py) على كلّ إطار — والنسخة النظيفة للريلزات بالتدريج نفسه
_lk = {}
LOOKS = [_lk.setdefault(sec, look.Look(sec)) for sec in SECS]
nv = transitions.assemble(segs, NF, TP, silent, ENC, looks=LOOKS)
nc = transitions.assemble(clean, NF, TP, os.path.join(WORK, 'video_clean.mp4'), ENC, looks=LOOKS)
assert nv == nc == sum(NF), 'عدد إطارات الفيلم لا يساوي مجموع اللقطات (%d، %d، %d)' % (nv, nc, sum(NF))

# ③ المزج: الصوت + الرياح + المؤثّرات (−18dB تقريباً تحت الكلام)
# MONT_MUTE_VOICE=1: عيّنةٌ قبل اكتمال الصوت (أمر المالك 2026-10-04: «عيّنةٌ احترافية… ولو بلا صوت أو جزءٌ منها بلا صوت»):
#   الكلام صمتٌ بطوله وتبقى الرياح والمؤثّرات؛ والتوقيت كلّه من الأصوات المؤقّتة فالكتابة تُكشف بإيقاع الكلام
if os.environ.get('MONT_MUTE_VOICE') == '1':
    voice = os.path.join(WORK, 'voice_muted.wav')
    sp.run([FF, '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=mono', '-t', '%.3f' % VD, voice], check=True)
    print('③ الكلام مكتومٌ في المزج (MONT_MUTE_VOICE)', flush=True)
# ③أ ارتطامٌ وحفيف (tools/sfx_synth.py — ضجيجٌ مرشَّح بلا نغمة): حفيفٌ قبل كلّ ضربةٍ مكتوبة وارتطامٌ لحظة هبوطها (الثقيلة أعلى)،
#     وارتطامٌ خفيف للختم، وحفيفٌ تقع ذروته على القطع في الانتقالات الخاطفة، وحفيفٌ عميقٌ طويل عند التعتيم بين الفصول
SB = sfx_synth.bank(WORK)
hits, heavy_t = [], []
for n, s in enumerate(shots):
    ev = kinetic.EVENTS.get(s['id']) or {}
    t0 = FST[n] / 25.0
    for x in ev.get('slam', []):
        ts, tier = (x, 'medium') if isinstance(x, (int, float)) else x
        hv = tier == 'heavy'
        hits += [(t0 + ts - 0.30, 'whoosh_fast', 0.34 if hv else 0.24),
                 (t0 + ts + kinetic.IMPACT_AT - 0.02, 'thud', 0.85 if hv else 0.5)]
        if hv:
            heavy_t.append(t0 + ts + kinetic.IMPACT_AT)
    for ts in ev.get('stamp', []):
        hits.append((t0 + ts - 0.02, 'thud_soft', 0.32))
for i, p_ in enumerate(TP):
    if not p_:
        continue
    cut = FST[i + 1] / 25.0
    if p_[0] in ('whip', 'whipr', 'push', 'zoom', 'flash'):
        hits.append((cut - 0.32, 'whoosh_fast', 0.24))          # ذروة الحفيف (62% من 0.55 ث) على القطع
    elif p_[0] == 'fadeblack':
        hits.append((cut - 0.70, 'whoosh_slow', 0.28))
HITS = sfx_synth.mix(hits, VD, SB, os.path.join(WORK, 'hits.wav'))
print('③أ الارتطام والحفيف: %d مؤثّراً (منها %d ثقيلة)' % (len(hits), len(heavy_t)), flush=True)
# ③ب المزج (بحث 2026-10-04 في تصميم صوت الوثائقيات): جوّ اللقطة يسبقها بنصف ثانية (قطع J)، والرياح والجوّ تنخفض تحت الكلام
#     بضاغطٍ يقوده الكلام نفسه وترتفع بين الجمل، وتصمت قبيل الارتطام الثقيل فيدوّي، ثم تسوية الجهارة إلى −14 LUFS (معيار يوتيوب)
inp = [FF, '-v', 'error', '-y', '-i', voice, '-f', 'lavfi', '-t', str(VD), '-i', 'anoisesrc=c=pink:r=48000', '-i', HITS]
flt = ['[0:a]aresample=48000,aformat=channel_layouts=mono,asplit=2[v][vsc]',
       '[1:a]lowpass=520,highpass=60,volume=0.10[w]', '[2:a]aresample=48000,aformat=channel_layouts=mono[h]']
amb = ['[w]']
for i, (st, d, f, vol) in enumerate(fx):
    inp += ['-stream_loop', '-1', '-i', f]
    k = i + 3
    st2 = max(0.0, st - 0.5); d2 = d + (st - st2)
    flt.append('[%d:a]atrim=0:%.3f,afade=t=in:d=0.5,afade=t=out:st=%.3f:d=0.6,volume=%.2f,adelay=%d|%d,aresample=48000,aformat=channel_layouts=mono[f%d]'
               % (k, d2, max(0, d2 - 0.6), vol, int(st2 * 1000), int(st2 * 1000), i))
    amb.append('[f%d]' % i)
flt.append('%samix=inputs=%d:duration=first:normalize=0[amb]' % (''.join(amb), len(amb)))
dip = '+'.join('between(t,%.3f,%.3f)' % (ht - 0.28, ht) for ht in heavy_t)
flt.append('[amb][vsc]sidechaincompress=threshold=0.025:ratio=5:attack=50:release=450:makeup=1[ambd]')
flt.append("[ambd]volume='max(0.3,1-0.7*(%s))':eval=frame[amb2]" % (dip or '0'))
flt.append('[v][amb2][h]amix=inputs=3:duration=first:normalize=0[a]')
raw = os.path.join(WORK, 'audio_mix.wav')
sp.run(inp + ['-filter_complex', ';'.join(flt), '-map', '[a]', '-c:a', 'pcm_s16le', '-ar', '48000', raw], check=True)
mixed = os.path.join(WORK, 'audio_final.m4a')
LN = 'loudnorm=I=-14:TP=-1.0:LRA=11'
if os.environ.get('MONT_MUTE_VOICE') == '1':                   # بلا كلام: لا تُرفع الرياح إلى جهارة الكلام
    sp.run([FF, '-v', 'error', '-y', '-i', raw, '-c:a', 'aac', '-b:a', '192k', mixed], check=True)
else:
    o = sp.run([FF, '-hide_banner', '-nostats', '-i', raw, '-af', LN + ':print_format=json', '-f', 'null', '-'],
               capture_output=True, text=True).stderr
    try:
        mj = json.loads(o[o.rindex('{'):o.rindex('}') + 1])
        LN2 = LN + (':measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true'
                    % (mj['input_i'], mj['input_tp'], mj['input_lra'], mj['input_thresh'], mj['target_offset']))
    except (ValueError, KeyError):
        LN2 = LN
    sp.run([FF, '-v', 'error', '-y', '-i', raw, '-af', LN2 + ',aresample=48000', '-c:a', 'aac', '-b:a', '192k', mixed], check=True)

# ④ الدمج والشعار (⛔ لا فيلم بلا شعار)
lg = os.path.join(WORK, 'logo_round.png')
im = Image.open(envpaths.logo(required=True)).convert('RGBA').resize((120, 120), Image.LANCZOS)
m = Image.new('L', (480, 480), 0); ImageDraw.Draw(m).ellipse([4, 4, 476, 476], fill=255)
m = m.filter(ImageFilter.GaussianBlur(3)).resize((120, 120), Image.LANCZOS)
o = Image.new('RGBA', (120, 120), (0, 0, 0, 0)); o.paste(im, (0, 0), m)
o.putalpha(o.split()[3].point(lambda v: int(v * 0.72))); o.save(lg)
final = P('film.mp4')
sp.run([FF, '-v', 'error', '-y', '-i', silent, '-i', mixed, '-i', lg, '-filter_complex', '[0:v][2:v]overlay=W-w-46:46:format=auto[v]',
        '-map', '[v]', '-map', '1:a', '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-tune', 'film', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', final], check=True)
print('✅ %s | %.2f د | مؤثّرات: %d' % (final, dur(final) / 60, len(fx)), flush=True)
