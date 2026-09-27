# -*- coding: utf-8 -*-
"""تحريك اللقطات الحيّة بـKling 2.6 Pro عبر fal.ai — للجهاز وللعدّاء معاً.
الاستعمال:  python tools/fal_animate.py <proj>
يقرأ <proj>/shots.json: اللقطة الحيّة kind == "حيّة"، واختياريّاً "audio": true لصوت Kling (مؤثّرات).
الميزانية من <proj>/publish.json → budget_usd (الافتراض 9$) — ⛔ لا يُتجاوز سقفها أبداً.
⭐ يُحفظ request_id لكل طلب فور إرساله (fal_pending.json) ويُستأنف ولا يُعاد (درس اليرموك: طلبٌ مدفوعٌ ضاع).
⛔ عمليةٌ واحدة فقط لكل مشروع (قفلٌ بملف)."""
import os, sys, io, json, time, base64, datetime
import requests
from PIL import Image

PROJ = os.path.abspath(sys.argv[1])
MODEL = 'fal-ai/kling-video/v2.6/pro/image-to-video'
PRICE = {False: 0.07, True: 0.14}   # دولار للثانية: بلا صوت / بصوت (صفحة النموذج 2026-09-26)
DUR = 5
NEG = ('women, woman, girl, female, feminine figure, text, letters, words, numbers, captions, watermark, logo, '
       'musical instruments, drums, horns, musicians, music, singing, song, melody, visible faces of warriors, '
       'crosses, emblems or symbols on banners and shields, heraldry, blood, gore, corpses, cartoon, anime, painting, '
       'blur, distortion, morphing, extra limbs, new people appearing')
KEY = os.environ.get('FAL_KEY')
if not KEY:
    try:
        import winreg
        KEY = winreg.QueryValueEx(winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment'), 'FAL_KEY')[0]
    except Exception:
        sys.exit('⛔ لا FAL_KEY')
# ⛔ درس القادسية: سرٌّ مُلصَقٌ بعلامة BOM أسقط الطلب وطبع المفتاح كاملاً في سجلٍّ عامّ ⇒ يُنظَّف، ولا يُطبع نصّ استثناءٍ قد يحويه
KEY = KEY.strip().lstrip('\ufeff').strip()
H = {'Authorization': 'Key ' + KEY}
P = lambda *a: os.path.join(PROJ, *a)
LOCK = P('.fal.lock')
if os.path.exists(LOCK) and time.time() - os.path.getmtime(LOCK) < 3 * 3600:
    sys.exit('⛔ عمليةُ تحريكٍ أخرى تعمل على هذا المشروع (%s)' % LOCK)
open(LOCK, 'w').write(str(os.getpid()))

shots = json.load(io.open(P('shots.json'), encoding='utf-8'))
meta = json.load(io.open(P('publish.json'), encoding='utf-8')) if os.path.exists(P('publish.json')) else {}
BUDGET = float(meta.get('budget_usd', 9))
os.makedirs(P('clips'), exist_ok=True)
LEDGER, PEND = P('fal_ledger.json'), P('fal_pending.json')
ledger = json.load(io.open(LEDGER, encoding='utf-8')) if os.path.exists(LEDGER) else []
pend = json.load(io.open(PEND, encoding='utf-8')) if os.path.exists(PEND) else {}
spent = lambda: sum(x['cost_usd'] for x in ledger) + sum(v.get('cost_usd', 0) for v in pend.values())
save = lambda f, d: io.open(f, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1))


def img_path(sid):
    # images/<id>.jpg أو images/<بادئة>_<id>.jpg (كما يسمّيها كوديكس في shots.json)
    for d in ('images', 'img'):
        for ext in ('jpg', 'png'):
            p = P(d, '%s.%s' % (sid, ext))
            if os.path.exists(p): return p
            q = sorted(f for f in os.listdir(P(d)) if f.endswith('_%s.%s' % (sid, ext))) if os.path.isdir(P(d)) else []
            if q: return P(d, q[0])


def data_uri(p):
    buf = io.BytesIO(); im = Image.open(p).convert('RGB'); im.thumbnail((1280, 720)); im.save(buf, 'JPEG', quality=85)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


AV_MODEL = 'fal-ai/bytedance/omnihuman/v1.5'     # صورة + صوت ⇒ راوٍ يتكلّم بشفتيه ورأسه ويديه (0.16$/ث، ≤30 ث بدقة 1080)
AV_PRICE = 0.16


def avatar(s):
    """الراوي كصانع محتوى حقيقي (أمر المالك 2026-09-27): OmniHuman يولّد الشفاه والرأس والإيماءات من الصورة وصوت الكتلة.
    الصوت يُسرَّع 1.05 كما في mont_hybrid فيبقى التزامن. الناتج clips/<id>_av.mp4 ويُقدَّم على غيره في المونتاج."""
    import subprocess as sp
    sid = s['id']; key = sid + '_av'; out = P('clips', '%s_av.mp4' % sid)
    if os.path.exists(out): return
    if key in pend:
        q = pend[key]; print(sid, '↻ استئناف طلب الراوي', flush=True)
    else:
        mp3 = P('clips', '%s_voice.mp3' % sid)
        sp.run(['ffmpeg', '-v', 'error', '-y', '-i', P('audio', s['lipsync'] + '.wav'),
                '-filter:a', 'atempo=1.05', '-ar', '44100', '-b:a', '128k', mp3], check=True)
        o = sp.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', mp3],
                   capture_output=True, text=True)
        secs = float(o.stdout.strip()); cost = round((int(secs) + 1) * AV_PRICE, 2)
        if secs > 30: print(sid, '⛔ صوت الراوي أطول من 30 ث', flush=True); return
        if spent() + cost > BUDGET + 1e-9:
            print(sid, '⏸ الميزانية لا تكفي الراوي (%.2f$)' % cost, flush=True); return
        p = img_path(sid)
        buf = io.BytesIO(); im = Image.open(p).convert('RGB'); im.thumbnail((1920, 1080)); im.save(buf, 'JPEG', quality=90)
        body = {'image_url': 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode(),
                'audio_url': 'data:audio/mpeg;base64,' + base64.b64encode(open(mp3, 'rb').read()).decode(),
                'resolution': '1080p',
                'prompt': s.get('avatar_prompt') or s.get('move', '')}
        r = requests.post('https://queue.fal.run/' + AV_MODEL, headers=H, json=body, timeout=600)
        if r.status_code != 200: print(sid, '⛔ رُفض طلب الراوي', r.status_code, r.text[:300], flush=True); return
        q = r.json(); q['cost_usd'] = cost
        pend[key] = q; save(PEND, pend)
    t0 = time.time()
    while True:
        time.sleep(15)
        try: st = requests.get(q['status_url'], headers=H, timeout=120).json()
        except Exception: continue
        if st.get('status') == 'COMPLETED': break
        if st.get('status') not in ('IN_QUEUE', 'IN_PROGRESS'):
            print(sid, '⛔ فشل الراوي', json.dumps(st, ensure_ascii=False)[:300], flush=True); pend.pop(key, None); save(PEND, pend); return
        if time.time() - t0 > 2400: print(sid, '⏳ الراوي معلّق للاستئناف', flush=True); return
    res = requests.get(q['response_url'], headers=H, timeout=300).json()
    if not isinstance(res, dict) or 'video' not in res:
        print(sid, '⛔ ردّ الراوي بلا فيديو:', json.dumps(res, ensure_ascii=False)[:400], flush=True)
        pend.pop(key, None); save(PEND, pend); return
    with requests.get(res['video']['url'], stream=True, timeout=900) as v:
        v.raise_for_status()
        with open(out + '.part', 'wb') as f:
            for c in v.iter_content(1 << 16): f.write(c)
    os.replace(out + '.part', out)
    ledger.append({'shot': key, 'audio': False, 'cost_usd': q['cost_usd'],
                   'at': datetime.datetime.now().isoformat(timespec='seconds')})
    save(LEDGER, ledger); pend.pop(key, None); save(PEND, pend)
    print(sid, '✅ الراوي (OmniHuman) %.2f$ | المجموع %.2f$ من %.2f$' % (q['cost_usd'], spent(), BUDGET), flush=True)


def run(s):
    sid = s['id']; out = P('clips', '%s.mp4' % sid)
    if s.get('avatar'): return avatar(s)           # الراوي: نموذجُ الأفاتار يغني عن Kling ومطابقة الشفاه
    if os.path.exists(out): return
    if s.get('lipsync'):                           # الراوي: تحريكٌ خام ثم مطابقةُ الشفاه لصوت كتلته
        out = P('clips', '%s_raw.mp4' % sid)
        if os.path.exists(out): return lipsync(s, out)
    audio = bool(s.get('audio'))
    dur = int(s.get('duration', DUR))
    cost = round(dur * PRICE[audio], 2)
    if sid in pend:
        q = pend[sid]; print(sid, '↻ استئناف طلبٍ مدفوع', flush=True)
    else:
        if spent() + cost > BUDGET + 1e-9:
            print(sid, '⏸ الميزانية (%.2f$ من %.2f$) — تُحرَّك بـkb3d' % (spent(), BUDGET), flush=True); return
        p = img_path(sid)
        if not p: print(sid, '⛔ الصورة غائبة', flush=True); return
        prompt = ('Cinematic documentary shot, realistic motion and physics. ' + s['move'] +
                  '. Keep the composition, people and faces exactly as in the image; nobody new enters the frame. No text.' +
                  (' Natural ambient sound effects only (' + s.get('sfx', 'battle') + '), absolutely no music, no singing, no drums.' if audio else ''))
        body = {'prompt': prompt, 'start_image_url': data_uri(p), 'duration': str(dur),
                'negative_prompt': NEG, 'generate_audio': audio, 'cfg_scale': 0.5}
        r = None
        for t in range(4):
            try:
                r = requests.post('https://queue.fal.run/' + MODEL, headers=H, json=body, timeout=600); break
            except requests.exceptions.ConnectionError:
                print(sid, 'إعادة الإرسال', t + 1, flush=True); time.sleep(20)
        if r is None: return
        if r.status_code != 200: print(sid, '⛔ رُفض', r.status_code, r.text[:200], flush=True); return
        q = r.json(); q['cost_usd'] = cost; q['audio'] = audio
        pend[sid] = q; save(PEND, pend)            # ⛔ يُحفظ فوراً: الطلب مدفوع
    t0 = time.time()
    while True:
        time.sleep(15)
        try: st = requests.get(q['status_url'], headers=H, timeout=120).json()
        except Exception: continue
        if st.get('status') == 'COMPLETED': break
        if st.get('status') not in ('IN_QUEUE', 'IN_PROGRESS'): print(sid, '⛔ فشل', st, flush=True); return
        if time.time() - t0 > 1800: print(sid, '⏳ تجاوز المهلة — يبقى معلّقاً للاستئناف', flush=True); return
    res = requests.get(q['response_url'], headers=H, timeout=300).json()
    tmp = out + '.part'
    with requests.get(res['video']['url'], stream=True, timeout=900) as v:
        v.raise_for_status()
        with open(tmp, 'wb') as f:
            for c in v.iter_content(1 << 16): f.write(c)
    os.replace(tmp, out)
    ledger.append({'shot': sid, 'audio': q.get('audio', False), 'cost_usd': q['cost_usd'],
                   'at': datetime.datetime.now().isoformat(timespec='seconds')})
    save(LEDGER, ledger); pend.pop(sid, None); save(PEND, pend)
    print(sid, '✅', '%.2f$' % q['cost_usd'], '| المجموع %.2f$ من %.2f$' % (spent(), BUDGET), flush=True)
    if s.get('lipsync'):
        lipsync(s, out)


LS_MODEL = 'fal-ai/kling-video/lipsync/audio-to-video'
LS_COST = 0.30                                     # تقديرٌ محافظ (الصفحة لا تذكر السعر)


def lipsync(s, raw, retry=True):
    """يطابق شفاه الراوي لصوت كتلته. الصوت يُسرَّع 1.05 كما في mont_hybrid فيبقى التزامن."""
    import subprocess as sp
    sid = s['id']; key = sid + '_ls'; out = P('clips', '%s.mp4' % sid)
    if os.path.exists(out): return
    resumed = key in pend
    if resumed:
        q = pend[key]
    else:
        if spent() + LS_COST > BUDGET + 1e-9:
            print(sid, '⏸ الميزانية لا تكفي مطابقة الشفاه', flush=True); return
        mp3 = P('clips', '%s_voice.mp3' % sid)
        sp.run(['ffmpeg', '-v', 'error', '-y', '-i', P('audio', s['lipsync'] + '.wav'),
                '-filter:a', 'atempo=1.05', '-ar', '44100', '-b:a', '128k', mp3], check=True)
        # درس 2026-09-27: الخامُ 10 ث بدقة 1080 رُفض أربع مرّات؛ نقصّه إلى 9.5 ث (الحدّ 2–10) ونخفّفه إلى 720 ليصغر الحمل
        vid = P('clips', '%s_ls_in.mp4' % sid)
        sp.run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-t', '9.5', '-vf', 'scale=-2:720,fps=25', '-an',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p', vid], check=True)
        body = {'video_url': 'data:video/mp4;base64,' + base64.b64encode(open(vid, 'rb').read()).decode(),
                'audio_url': 'data:audio/mpeg;base64,' + base64.b64encode(open(mp3, 'rb').read()).decode()}
        r = requests.post('https://queue.fal.run/' + LS_MODEL, headers=H, json=body, timeout=600)
        if r.status_code != 200: print(sid, '⛔ رُفضت مطابقة الشفاه', r.status_code, r.text[:200], flush=True); return
        q = r.json(); q['cost_usd'] = LS_COST
        pend[key] = q; save(PEND, pend)
    t0 = time.time()
    while True:
        time.sleep(15)
        try: st = requests.get(q['status_url'], headers=H, timeout=120).json()
        except Exception: continue
        if st.get('status') == 'COMPLETED': break
        if st.get('status') not in ('IN_QUEUE', 'IN_PROGRESS'):
            print(sid, '⛔ فشلت مطابقة الشفاه', st, flush=True); pend.pop(key, None); save(PEND, pend)
            if resumed and retry: return lipsync(s, raw, False)
            return
        if time.time() - t0 > 1800: print(sid, '⏳ مطابقة الشفاه معلّقة للاستئناف', flush=True); return
    res = requests.get(q['response_url'], headers=H, timeout=300).json()
    if not isinstance(res, dict) or 'video' not in res:
        # ردُّ خطأٍ من fal (لا يحوي المفتاح): نطبعه ونُسقط الطلب ليُعاد في الشوط التالي؛ والمونتاج يستعمل الخام
        print(sid, '⛔ ردّ مطابقة الشفاه بلا فيديو:', json.dumps(res, ensure_ascii=False)[:400], flush=True)
        pend.pop(key, None); save(PEND, pend)
        if resumed and retry: return lipsync(s, raw, False)   # طلبٌ قديمٌ فاشل: نعيد الإرسال مرّةً بالمدخل المصحَّح
        return
    with requests.get(res['video']['url'], stream=True, timeout=900) as v:
        v.raise_for_status()
        with open(out + '.part', 'wb') as f:
            for c in v.iter_content(1 << 16): f.write(c)
    os.replace(out + '.part', out)
    ledger.append({'shot': key, 'audio': False, 'cost_usd': q['cost_usd'],
                   'at': datetime.datetime.now().isoformat(timespec='seconds')})
    save(LEDGER, ledger); pend.pop(key, None); save(PEND, pend)
    print(sid, '✅ مطابقة الشفاه | المجموع %.2f$ من %.2f$' % (spent(), BUDGET), flush=True)


try:
    # الأولوية: ذات الصوت (البطولية) ثم الحيّة الصامتة، بترتيب الفيلم
    live = [s for s in shots if s.get('kind') == 'حيّة']
    for s in sorted(live, key=lambda s: (not s.get('avatar'), not s.get('lipsync'), not s.get('audio'), s['id'])):
        try: run(s)
        except Exception as e: print(s['id'], '⛔ خطأ', type(e).__name__, flush=True)  # لا نصّ الاستثناء: قد يحوي المفتاح
finally:
    os.remove(LOCK)
print('انتهى التحريك: %d مقطعاً · %.2f$' % (len(ledger), spent()))
