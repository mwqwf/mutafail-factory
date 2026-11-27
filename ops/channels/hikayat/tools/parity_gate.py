# -*- coding: utf-8 -*-
"""⛔ بوّابة التكافؤ قبل النشر — قناة الحكايات ترث خطّ التاريخ لا خطّاً موازياً (درس «أصحاب الأخدود» 2026-11-27).

الاستعمال (من جذر المستودع):
  python3 ops/channels/hikayat/tools/parity_gate.py film    <proj> [film.mp4] [--ref-share 0.28]
  python3 ops/channels/hikayat/tools/parity_gate.py thumb   <thumb.jpg> [...]
  python3 ops/channels/hikayat/tools/parity_gate.py meta    <description.txt> [captions_ar.srt]
  python3 ops/channels/hikayat/tools/parity_gate.py logo    <film.mp4> [film|thumb]
  python3 ops/channels/hikayat/tools/parity_gate.py cleanup <proj>
  python3 ops/channels/hikayat/tools/parity_gate.py all     <proj> [film.mp4]   (film + thumbs + meta)
يخرج بـ1 عند أيّ سقوط. لا رفع ولا نشر قبل «✅ PARITY» من «all». ولا تعدّ فحص الإنسان (الإصغاء، الصور) مستغنىً عنه.

ما يفحصه «film»:
 ① المشروع من خطّ التاريخ: ملفات channel.json ▸ pipeline.required_project_files موجودة (غيابها = مونتاج محلّي موازٍ).
 ② نسبة التحريك الحقيقيّ: مجموع مدد اللقطات kind=live التي لها مقطع فعليّ clips/<id>[_av|_raw].mp4 ÷ مدّة الفيلم
    (timeline.json) ≥ motion.min_live_share و≥ --ref-share إن أُعطي. لقطة live بلا مقطع = سقوط إلا إن سُجّلت في
    live_waivers.json بسببها (وتُحسب ضدّ النسبة على كل حال).
 ③ صورة كل لقطة في كتلتها: tools/shot_image_gate.py (لا استعارة صورة لكتلة أخرى).
 ④ الصور ≥ 1280×720 و16:9.
 ⑤ المؤثّرات: sfx_cues.json موجودة و tools/sfx_cues.py lint تنجح.
 ⑥ الفيلم: 1920×1080، 25 إطاراً، الجهارة −14±1 LUFS، الذروة ≤ −1 dBFS.
 ⑦ الشعار محفور طوال الفيلم بمواصفة التاريخ (أعلى اليمين، 120/1080، هامش 46، شفافية 72٪) وهو شعار الحكايات لا التاريخ.
"""
import glob, json, os, re, subprocess as sp, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
CFG = json.load(open(os.path.join(HERE, '..', 'channel.json'), encoding='utf-8'))
FF, FP = 'ffmpeg', 'ffprobe'
ERR, WARN = [], []


def bad(m): ERR.append(m); print('✗', m, flush=True)
def warn(m): WARN.append(m); print('⚠️', m, flush=True)
def ok(m): print('✓', m, flush=True)


def probe(path):
    o = sp.run([FP, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate:format=duration',
                '-of', 'json', path], capture_output=True, text=True, check=True)
    j = json.loads(o.stdout); s = j['streams'][0]; n, d = s['r_frame_rate'].split('/')
    return int(s['width']), int(s['height']), float(n) / float(d), float(j['format']['duration'])


# ───────────── الشعار ─────────────
def badge(asset, size, opacity):
    im = Image.open(asset).convert('RGB').resize((size, size), Image.LANCZOS)
    m = Image.new('L', (size * 4, size * 4), 0); ImageDraw.Draw(m).ellipse([4, 4, size * 4 - 4, size * 4 - 4], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(3)).resize((size, size), Image.LANCZOS)
    return np.asarray(im, float), np.asarray(m, float) / 255.0 * opacity


def _box(spec, W, H):
    rw, rh = spec['ref_frame']; k = H / rh
    size = max(8, int(round(spec['size'] * k)))
    ev = lambda e, ref: eval(str(e), {}, {'W': rw, 'H': rh}) if isinstance(e, str) else e
    x = int(round(ev(spec['x'], rw) * k)); y = int(round(ev(spec['y'], rh) * k))
    return x, y, size


def logo_score(frame, spec, asset):
    """ارتباط منطقة الشعار في الإطار بالشارة المتوقَّعة (داخل الدائرة فقط)."""
    W, H = frame.size; x, y, s = _box(spec, W, H)
    crop = np.asarray(frame.crop((x, y, x + s, y + s)).convert('RGB'), float)
    exp, a = badge(asset, s, 1.0)
    msk = a > 0.5
    c = crop[msk].ravel(); e = exp[msk].ravel()
    c = c - c.mean(); e = e - e.mean()
    n = np.linalg.norm(c) * np.linalg.norm(e)
    return float(c @ e / n) if n else 0.0


def check_logo(path, kind='film', every=20.0):
    spec = CFG['logo'][kind]
    hk = os.path.join(REPO, CFG['logo']['asset']); hist = os.path.join(REPO, CFG['logo']['history_asset'])
    frames = []
    if kind == 'film':
        dur = probe(path)[3]; t = 2.0
        while t < dur - 1:
            o = sp.run([FF, '-v', 'error', '-ss', '%.2f' % t, '-i', path, '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'],
                       capture_output=True)
            if o.stdout:
                import io; frames.append((t, Image.open(io.BytesIO(o.stdout)).convert('RGB')))
            t += every
    else:
        frames = [(0, Image.open(path).convert('RGB'))]
    good = 0; wrong = 0
    for t, f in frames:
        sh, sx = logo_score(f, spec, hk), (logo_score(f, spec, hist) if os.path.exists(hist) else -1)
        if sh >= 0.55 and sh > sx + 0.05: good += 1
        elif sx >= 0.55 and sx > sh: wrong += 1
    n = len(frames) or 1
    tag = '%s %s: شعار الحكايات في %d/%d إطاراً' % (kind, os.path.basename(path), good, n)
    if wrong:
        bad('%s — وشعار قناة التاريخ في %d إطاراً (شعار خاطئ)' % (tag, wrong))
    elif good / n < (0.9 if kind == 'film' else 1.0):
        bad(tag + ' — الشعار غائب أو في غير موضع التاريخ (%s)' % spec['corner'])
    else:
        ok(tag + ' (%s)' % spec['corner'])


# ───────────── المشروع والفيلم ─────────────
def clip_of(proj, sid):
    for n in (sid + '_av', sid, sid + '_raw'):
        p = os.path.join(proj, 'clips', n + '.mp4')
        if os.path.isfile(p) and os.path.getsize(p) > 10000:
            return p


def check_film(proj, film=None, ref_share=None):
    P = lambda *a: os.path.join(proj, *a)
    miss = [f for f in CFG['pipeline']['required_project_files'] if not os.path.exists(P(f))]
    if miss:
        bad('المشروع ليس من خطّ التاريخ (ينقصه: %s) — هذا هو خطأ «الأخدود»: مونتاج محلّي موازٍ' % ', '.join(miss))
        return
    ok('ملفات المشروع من خطّ التاريخ موجودة')
    shots = json.load(open(P('shots.json'), encoding='utf-8'))
    tl = json.load(open(P('timeline.json'), encoding='utf-8'))
    waive = json.load(open(P('live_waivers.json'), encoding='utf-8')) if os.path.exists(P('live_waivers.json')) else {}
    total = sum(v[1] for v in tl.values()) or 1
    live = kb = 0.0; missing = []
    base = {s['id']: s for s in shots}
    for sid, (st, d) in tl.items():
        s = base.get(sid) or base.get(sid.split('_')[0]) or {}
        root = re.sub(r'_\d+$', '', s.get('id', sid))
        if s.get('kind') == 'live' and clip_of(proj, root) and not s.get('still'):
            live += d
        else:
            kb += d
            if s.get('kind') == 'live' and root not in waive and root not in missing:
                missing.append(root)
    share = live / total
    need = max(CFG['motion']['min_live_share'], ref_share or 0)
    print('   التحريك الحقيقيّ: %.1f%% من %.0f ث (حركة كاميرا/ثابت: %.1f%%) — المطلوب ≥ %.0f%%' % (100 * share, total, 100 * kb / total, 100 * need))
    if missing:
        bad('لقطات live بلا مقطع حيّ (بديل kb3d صامت ممنوع): %s' % ' '.join(missing[:30]))
    if share < need:
        bad('نسبة التحريك الحقيقيّ %.1f%% < %.0f%% (أمر المالك: أغلب الفيلم متحرّك، لا كاميرا فقط)' % (100 * share, 100 * need))
    else:
        ok('نسبة التحريك الحقيقيّ %.1f%%' % (100 * share))
    # الصور
    small = []
    imgs = glob.glob(P('images', '*.jpg')) + glob.glob(P('images', '*.png'))
    if not imgs:
        bad('لا صور في proj/images — لا يُفحص فيلم بلا مصادره (ولا تُحذف قبل مراجعة المالك)')
    for f in imgs:
        w, h = Image.open(f).size
        if w < 1280 or h < 720 or abs(w / h - 16 / 9) > 0.02: small.append('%s %dx%d' % (os.path.basename(f), w, h))
    bad('صور دون 1280×720 أو ليست 16:9: %s' % ', '.join(small[:10])) if small else (imgs and ok('أبعاد الصور %d صورة' % len(imgs)))
    # المؤثّرات
    r = sp.run([sys.executable, os.path.join(REPO, 'tools', 'sfx_cues.py'), 'lint', proj], capture_output=True, text=True)
    bad('sfx_cues lint: ' + (r.stdout + r.stderr).strip()[-300:]) if r.returncode else ok('sfx_cues lint')
    film = film or P('film.mp4')
    if not os.path.exists(film):
        bad('لا فيلم مصيَّر: %s' % film); return
    r = sp.run([sys.executable, os.path.join(REPO, 'tools', 'shot_image_gate.py'), proj, film], capture_output=True, text=True)
    bad('shot_image_gate: ' + (r.stdout + r.stderr).strip()[-300:]) if r.returncode else ok('صورة كل لقطة في كتلتها')
    check_video(film)
    check_logo(film, 'film')


def check_video(film):
    W, H, fps, dur = probe(film); v = CFG['video']
    if (W, H) != (v['width'], v['height']) or abs(fps - v['fps']) > 0.01:
        bad('الفيلم %dx%d@%.2f والمطلوب %dx%d@%d' % (W, H, fps, v['width'], v['height'], v['fps']))
    else:
        ok('الأبعاد %dx%d@%g' % (W, H, fps))
    o = sp.run([FF, '-nostats', '-i', film, '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    I = re.findall(r'I:\s+(-?[\d.]+) LUFS', o); pk = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', o)
    a = CFG['audio']
    if not I:
        bad('تعذّر قياس الجهارة')
    else:
        i = float(I[-1]); p = float(pk[-1]) if pk else 0
        if abs(i - a['lufs']) > a['lufs_tol'] or p > a['true_peak_max']:
            bad('الجهارة %.1f LUFS والذروة %.1f dBFS (المطلوب %.0f±%.0f وذروة ≤ %.0f)' % (i, p, a['lufs'], a['lufs_tol'], a['true_peak_max']))
        else:
            ok('الجهارة %.1f LUFS، الذروة %.1f' % (i, p))
    o = sp.run([FF, '-nostats', '-i', film, '-vn', '-af', 'silencedetect=n=-50dB:d=0.3', '-f', 'null', '-'], capture_output=True, text=True).stderr
    per_min = o.count('silence_start') / (dur / 60)
    # مرجع مقيس: فيلم التاريخ «إسلام خالد» ≈ 12/د (صمت مقصود فوق الكتل المفتاحية)، «الأخدود» ≈ 24/د (لا فرش ولا مؤثّرات)
    (warn if per_min > 16 else ok)('فجوات صمت تامّ: %.1f/د (التاريخ ≈ 12/د)' % per_min)


def check_meta(desc_path, captions=None):
    t = open(desc_path, encoding='utf-8').read()
    for rx in CFG['publish']['description_must_match']:
        (ok if re.search(rx, t) else bad)('الوصف يحوي: %s' % rx)
    if captions is not None:
        okc = os.path.exists(captions) and os.path.getsize(captions) > 500
        (ok if okc else bad)('ملف ترجمة عربي للرفع: %s' % captions)


def check_cleanup(proj):
    P = lambda *a: os.path.join(proj, *a)
    if not os.path.exists(P('OWNER_REVIEW.ok')):
        bad('لا حذف: المالك لم يراجع الفيلم بعد (proj/OWNER_REVIEW.ok غائب). درس «الأخدود»: حُذفت الصور قبل أن يُرى الخلل.')
    man = P('ARCHIVE_SHA256.txt')
    if not os.path.exists(man):
        bad('لا حذف: لا بيان sha256 لأرشيف الصور والمقاطع (ARCHIVE_SHA256.txt) يثبت حفظها على GitHub')
    else:
        listed = {l.split()[-1] for l in open(man, encoding='utf-8') if l.strip()}
        media = [os.path.relpath(f, proj) for d in ('images', 'clips') for f in glob.glob(P(d, '*')) if os.path.isfile(f)]
        unl = [m for m in media if m not in listed]
        bad('ملفات غير مؤرشفة: %s' % ', '.join(unl[:10])) if unl else ok('كل الصور والمقاطع في بيان الأرشيف')


def main(a):
    if len(a) < 2:
        print(__doc__); return 2
    cmd = a[0]
    ref = None
    if '--ref-share' in a:
        i = a.index('--ref-share'); ref = float(a[i + 1]); a = a[:i] + a[i + 2:]
    if cmd == 'film': check_film(a[1], a[2] if len(a) > 2 else None, ref)
    elif cmd == 'thumb': [check_logo(p, 'thumb') for p in a[1:]]
    elif cmd == 'logo': check_logo(a[1], a[2] if len(a) > 2 else 'film')
    elif cmd == 'meta': check_meta(a[1], a[2] if len(a) > 2 else None)
    elif cmd == 'cleanup': check_cleanup(a[1])
    elif cmd == 'all':
        proj = a[1]; check_film(proj, a[2] if len(a) > 2 else None, ref)
        th = sorted(glob.glob(os.path.join(proj, 'thumb-*.jpg')) + glob.glob(os.path.join(proj, 'publish', 'thumb*.jpg')))
        if len(th) < CFG['publish']['thumbnails']: bad('مصغّرات أقلّ من %d' % CFG['publish']['thumbnails'])
        for p in th: check_logo(p, 'thumb')
        d = os.path.join(proj, 'publish', 'description.txt')
        check_meta(d, os.path.join(proj, 'publish', 'captions_ar.srt')) if os.path.exists(d) else bad('لا وصف: publish/description.txt')
    else:
        print(__doc__); return 2
    print('%s PARITY (%d سقوط، %d تنبيه)' % ('✅' if not ERR else '⛔', len(ERR), len(WARN)))
    return 1 if ERR else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
