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
MODEL = 'fal-ai/kling-video/v2.6/pro/image-to-video'          # بصوت Kling (مؤثّرات)
MODEL_SILENT = 'fal-ai/kling-video/v2.5-turbo/pro/image-to-video'  # بلا صوت: السعر نفسه ويقبل cfg_scale (درس خيل القادسية)
MODEL_FLF = 'fal-ai/kling-video/v3/pro/image-to-video'       # إطار بداية + نهاية (تحوّل الراوي في الزلاقة)
PRICE = {False: 0.07, True: 0.14}   # دولار للثانية: بلا صوت / بصوت (صفحة النموذج 2026-09-26)
PRICE_FLF = 0.112                   # v3 pro بلا صوت (صفحة النموذج 2026-09-28)
DUR = 5
NEG = ('women, woman, girl, female, feminine figure, text, letters, words, numbers, captions, watermark, logo, '
       'musical instruments, drums, horns, musicians, music, singing, song, melody, visible faces of warriors, '
       'crosses, emblems or symbols on banners and shields, heraldry, blood, gore, corpses, cartoon, anime, painting, '
       'blur, distortion, morphing, extra limbs, new people appearing, '
       'human face on horse, human face on camel, anthropomorphic animal, humanoid animal face, merged rider and horse, '
       'extra legs, extra heads, deformed animals, tight clothing, clothes clinging to the body')
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
# ⭐ سقفٌ مشترك (أمر المالك 2026-10-01، بدر): budget_total_usd سقفُ الافتتاحية والفيلم معاً لا يُتجاوز بحال.
# ما أنفقه المشروع الشقيق يُقرأ من fal_ledger_*.json (ينزّلها weekly-film.yml من إصدار الشقيق)، ويُخصم من السقف؛
# فما وفّرته الافتتاحية يصير للفيلم تلقائياً، وما أنفقته يُقتطع منه. وbudget_usd يبقى سقفاً فرعياً للمشروع إن وُجد.
HARD_CAP = 45.0   # ⛔ أمر المالك 2026-10-01: لا يتجاوز فيلمٌ (افتتاحيةً وفيلماً) 45$ ولو نُسي الحقل أو كُتب أكبر منه
TOTAL = min(float(meta.get('budget_total_usd', HARD_CAP)), HARD_CAP)
OTHER = 0.0
for f in sorted(os.listdir(PROJ)):
    if f.startswith('fal_ledger_') and f.endswith('.json'):
        OTHER += sum(x.get('cost_usd', 0) for x in json.load(io.open(P(f), encoding='utf-8')))
if True:
    BUDGET = min(BUDGET if 'budget_usd' in meta else float(TOTAL), float(TOTAL) - OTHER)
    print('السقف المشترك %.2f$ · أنفق الشقيق %.2f$ ⇒ المتاح لهذا المشروع %.2f$' % (float(TOTAL), OTHER, BUDGET), flush=True)
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


def upload(path):
    """يرفع ملفاً إلى تخزين fal ويعيد رابطه. درس 2026-09-27: fal رفضت الصوت والفيديو بصيغة data: URI
    (file_download_error وVideo URL is invalid)، وقبلتها للصور فقط."""
    import subprocess as sp
    os.environ['FAL_KEY'] = KEY                    # المفتاح المنظَّف من BOM، لا نسخة البيئة الخام
    try:
        import fal_client
    except ImportError:
        sp.run([sys.executable, '-m', 'pip', 'install', '-q', 'fal-client'], check=True)
        import fal_client
    return fal_client.upload_file(path)


AV_RES = {}   # دقّةٌ بديلة لكل لقطة بعد خطأ الخدمة
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
        # الجملُ القصيرة (مثل «ما جاء بكم؟») تُمدّ بصمتٍ إلى 3 ث على الأقل كي يقبلها النموذج؛ والمونتاج يقصّ اللقطة على طول كتلتها
        sp.run(['ffmpeg', '-v', 'error', '-y', '-i', P('audio', s['lipsync'] + '.wav'),
                '-filter:a', 'atempo=1.05,apad=whole_dur=3', '-ar', '44100', '-b:a', '128k', mp3], check=True)
        o = sp.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', mp3],
                   capture_output=True, text=True)
        secs = float(o.stdout.strip()); cost = round((int(secs) + 1) * AV_PRICE, 2)
        if secs > 30: print(sid, '⛔ صوت الراوي أطول من 30 ث', flush=True); return
        if spent() + cost > BUDGET + 1e-9:
            print(sid, '⏸ الميزانية لا تكفي الراوي (%.2f$)' % cost, flush=True); return
        p = img_path(sid)
        jpg = P('clips', '%s_img.jpg' % sid)
        im = Image.open(p).convert('RGB'); im.thumbnail((1920, 1080)); im.save(jpg, 'JPEG', quality=90)
        body = {'image_url': upload(jpg), 'audio_url': upload(mp3),
                'resolution': AV_RES.get(sid, '1080p'),
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
        pend.pop(key, None); save(PEND, pend)
        # ⭐ بدر N04: «Downstream service unavailable» أربع مرّات للقطةٍ واحدة بعينها ⇒ محاولةٌ ثانية بدقّة 720p مرّةً واحدة
        if 'downstream' in json.dumps(res) and not s.get('_retry720'):
            s['_retry720'] = True; AV_RES[sid] = '720p'; print(sid, '↻ محاولة بدقّة 720p', flush=True); return avatar(s)
        return
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
    redo = s.get('redo')                           # إعادةُ تحريكِ مقطعٍ مرفوضٍ بعد الفحص، مرّةً لكل وسم
    mark = P('clips', '%s.redo_%s' % (sid, redo)) if redo else None
    if s.get('avatar'):                            # الراوي: نموذجُ الأفاتار يغني عن Kling ومطابقة الشفاه
        av = P('clips', '%s_av.mp4' % sid)         # وredo يسري عليه أيضاً (الزلاقة: أُعيد صوت N09 فلم يُعَد تحريكه)
        if mark and os.path.exists(av) and not os.path.exists(mark):
            os.remove(av); open(mark, 'w').close(); print(sid, '♻ يُعاد تحريك الراوي (%s)' % redo, flush=True)
        return avatar(s)
    if mark and os.path.exists(out) and not os.path.exists(mark):
        os.remove(out); print(sid, '♻ يُعاد تحريكه (%s)' % redo, flush=True)
    if os.path.exists(out): return
    if s.get('lipsync'):                           # الراوي: تحريكٌ خام ثم مطابقةُ الشفاه لصوت كتلته
        out = P('clips', '%s_raw.mp4' % sid)
        if os.path.exists(out): return lipsync(s, out)
    audio = bool(s.get('audio'))
    dur = int(s.get('duration', DUR))
    flf = img_path(s['end_image']) if s.get('end_image') else None
    cost = round(dur * (PRICE_FLF if flf else PRICE[audio]), 2)
    if sid in pend:
        q = pend[sid]; print(sid, '↻ استئناف طلبٍ مدفوع', flush=True)
    else:
        # فحصُ السقف والإرسالُ وحفظُ الطلب ذرّيٌّ بين الخيوط: لا يتجاوز مجموعُ الطلبات المتوازية الميزانية
        with SUBMIT:
            if spent() + cost > BUDGET + 1e-9:
                print(sid, '⏸ الميزانية (%.2f$ من %.2f$) — تُحرَّك بـkb3d' % (spent(), BUDGET), flush=True); return
            p = img_path(sid)
            # ⭐ «start_from»: يبدأ المقطع من آخر إطارٍ حقيقيٍّ لمقطع الراوي السابق لا من صورةٍ ثابتة
            #    (حكم المالك على عين جالوت: الانتقال بتجميد الراوي طريقةٌ بدائية). الراوي يُحرَّك قبل غيره فمقطعه موجود.
            if s.get('start_from'):
                src = P('clips', '%s_av.mp4' % s['start_from'])
                if not os.path.exists(src): src = P('clips', '%s.mp4' % s['start_from'])
                if os.path.exists(src):
                    import subprocess as sp
                    last = P('clips', '%s_start.jpg' % sid)
                    sp.run(['ffmpeg', '-v', 'error', '-y', '-sseof', '-0.12', '-i', src, '-frames:v', '1', '-q:v', '2', last], check=True)
                    p = last
                else:
                    print(sid, '⚠ لا مقطع لـ%s — يبدأ من صورته' % s['start_from'], flush=True)
            if not p: print(sid, '⛔ الصورة غائبة', flush=True); return
            prompt = ('Cinematic documentary shot, realistic motion and physics. ' + s['move'] +
                      '. Keep the composition, people and faces exactly as in the image; nobody new enters the frame. No text.' +
                      (' Natural ambient sound effects only (' + s.get('sfx', 'battle') + '), absolutely no music, no singing, no drums.' if audio else ''))
            if flf:      # التحوّل: Kling v3 يرسم ما بين الصورتين، فيبقى الوجه ثابتاً في الطرفين
                model = MODEL_FLF
                body = {'prompt': s['move'] + '. The man keeps exactly the same face and identity from the first frame to the last. No text.',
                        'start_image_url': data_uri(p), 'end_image_url': data_uri(flf), 'duration': str(dur),
                        'generate_audio': False, 'cfg_scale': 0.65,
                        'negative_prompt': NEG + ', face change, identity change, morphing face, different person, distorted face, extra fingers'}
            elif audio:
                model = MODEL
                body = {'prompt': prompt, 'start_image_url': data_uri(p), 'duration': str(dur),
                        'negative_prompt': NEG, 'generate_audio': True}
            else:
                model = MODEL_SILENT
                body = {'prompt': prompt, 'image_url': data_uri(p), 'duration': str(dur),
                        'negative_prompt': NEG, 'cfg_scale': float(s.get('cfg', 0.65))}
            r = None
            for t in range(4):
                try:
                    r = requests.post('https://queue.fal.run/' + model, headers=H, json=body, timeout=600); break
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
    if mark: open(mark, 'w').close()
    with SUBMIT:
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
        body = {'video_url': upload(vid), 'audio_url': upload(mp3)}
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


import threading
SUBMIT = threading.Lock()
try:
    # الأولوية: ذات الصوت (البطولية) ثم الحيّة الصامتة، بترتيب الفيلم
    live = [s for s in shots if s.get('kind') == 'حيّة']
    def safe(s):
        try: run(s)
        except Exception as e:   # نصّ الاستثناء بعد حجب المفتاح: «الرصيد نفد» مثلاً لا يُعرف بغيره
            msg = str(e)
            for part in [KEY or ''] + (KEY or '').split(':'):
                if len(part) > 6: msg = msg.replace(part, '***')
            msg = msg[:240]
            print(s['id'], '⛔ خطأ', type(e).__name__, getattr(e, 'status_code', ''), msg, flush=True)
    order = sorted(live, key=lambda s: (not s.get('avatar'), not s.get('lipsync'), not s.get('audio'), s['id']))
    # الراوي ومطابقة الشفاه بالتتابع؛ ولقطات Kling الأخرى متوازية (أمر المالك 2026-09-28: «ضاعف السرعة»)
    for s in [x for x in order if x.get('avatar') or x.get('lipsync')]: safe(s)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(int(os.environ.get('FAL_PAR', '6'))) as ex:
        list(ex.map(safe, [x for x in order if not (x.get('avatar') or x.get('lipsync'))]))
finally:
    os.remove(LOCK)
print('انتهى التحريك: %d مقطعاً · %.2f$' % (len(ledger), spent()))
