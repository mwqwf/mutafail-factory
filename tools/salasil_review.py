"""مراجعة آلية محدودة للفيلم الموجود؛ لا توليد ولا نشر ولا طباعة نصوص خاصة."""
import argparse, base64, contextlib, hashlib, io, json, math, os, re, subprocess, sys, tempfile, time, urllib.error, urllib.request
from pathlib import Path

MAX_CALLS = 120
MAX_OUTPUT = 4096

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()

def write(p, d):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(p.suffix + '.tmp'); t.write_text(json.dumps(d, ensure_ascii=False, indent=1)); t.replace(p)

class ReviewError(RuntimeError): pass

class Client:
    def __init__(self, keys):
        if not keys: raise ReviewError('missing_gemini_key')
        self.key = keys[0]  # لا تدوير مفاتيح أو مشاريع بعد نفاد الحصة.
        self.model = 'gemini-3.5-flash'
        self.calls = 0; self.usage = []; self.last = 0

    def generate(self, body):
        body = dict(body); cfg = dict(body.get('generationConfig') or {})
        cfg['maxOutputTokens'] = MAX_OUTPUT
        body['generationConfig'] = cfg
        data = json.dumps(body).encode()
        if len(data) > 18000000: raise ReviewError('inline_request_too_large')
        for attempt in range(3):
            if self.calls >= MAX_CALLS: raise ReviewError('review_call_cap')
            time.sleep(max(0, 4 - (time.time() - self.last)))
            self.calls += 1; self.last = time.time()
            req = urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models/'+self.model+':generateContent', data=data,
                headers={'content-type':'application/json','x-goog-api-key':self.key})
            try:
                with urllib.request.urlopen(req, timeout=180) as r: j = json.load(r)
            except urllib.error.HTTPError as e:
                raw = e.read().decode('utf-8','replace')
                # لا نطبع الاستجابة أو الرابط؛ قد تتضمن معلومات خاصة.
                if e.code == 429:
                    if re.search('PerDay|per.day|daily', raw, re.I): raise ReviewError('gemini_daily_quota')
                    if attempt < 2: time.sleep(65); continue
                if e.code in (500,502,503,504) and attempt < 2: time.sleep(10); continue
                raise ReviewError('gemini_http_'+str(e.code))
            except (TimeoutError, OSError):
                raise ReviewError('gemini_uncertain_request_no_automatic_retry')
            self.usage.append(j.get('usageMetadata') or {})
            cs=j.get('candidates') or []
            if len(cs)!=1 or cs[0].get('finishReason') != 'STOP': raise ReviewError('gemini_incomplete_response')
            txt=''.join(p.get('text','') for p in cs[0].get('content',{}).get('parts',[]) if not p.get('thought'))
            try: return json.loads(re.search(r'\{.*\}',txt,re.S).group(0))
            except (ValueError, AttributeError): raise ReviewError('gemini_invalid_json')
        raise ReviewError('gemini_retry_limit')

    def ask(self, parts):
        return self.generate({'contents':[{'parts':parts}], 'generationConfig':{'temperature':0,'responseMimeType':'application/json'}})

def inline(p, mime): return {'inlineData':{'mimeType':mime,'data':base64.b64encode(Path(p).read_bytes()).decode()}}

def check_rows(result, field, ids):
    rows=result.get(field)
    if not isinstance(rows,list) or len(rows)!=len(ids): raise ReviewError('missing_review_rows')
    if {r.get('id') for r in rows} != set(ids): raise ReviewError('wrong_review_ids')
    return rows

def listen(src, client, reports):
    import listen_gate
    blocks=json.loads((src/'blocks.json').read_text())
    if not isinstance(blocks,list) or not blocks or len({b.get('id') for b in blocks})!=len(blocks): raise ReviewError('invalid_audio_block_inventory')
    resfile=src/'listen_results.json'; revfile=src/'listen_reviews.json'
    results=json.loads(resfile.read_text()) if resfile.exists() else {}
    reviews=json.loads(revfile.read_text()) if revfile.exists() else {}
    # Duplicate shard records cannot silently override one another.
    if list(src.glob('listen_results.*.json')) or list(src.glob('listen_reviews.*.json')): raise ReviewError('duplicate_audio_result_shards')
    todo=[]; digests={}
    for b in blocks:
        bid=b['id']; p=src/'audio'/(bid+'.wav')
        if Path(bid).name != bid or not p.is_file(): raise ReviewError('missing_or_invalid_audio')
        audio=p.read_bytes()
        if audio[44:48] == b'RIFF': raise ReviewError('double_wav_header')
        d=hashlib.sha256(b['text'].encode()+b'\0'+audio).hexdigest();digests[bid]=d
        old=results.get(bid,{})
        if old.get('input_sha256')!=d or not isinstance(old.get('ok'),bool): todo.append(b)
    prompt='''أنت مدقق عربي للصوت الفعلي. قارن كل مقطع بالنص المشكول حرفا وحركة. افحص حذف أو تبديل الكلمات والحروف والحركات في الوصل وأي كلام زائد أو توجيه أداء منطوق. الوقف العربي المشروع ليس خطأ، ولا اختلاف النبر. استمع لكل المقاطع كاملة وأعد JSON: {"results":[{"id":"...","ok":true|false,"heard":"تفريغ المسموع حرفيا","written":"النص المقارن","why":"السبب"}]}. لا تجز مقطعا لم تسمعه.'''
    for n in range(0,len(todo),4):
        group=todo[n:n+4];parts=[{'text':prompt}]
        for b in group:parts += [{'text':'المعرف: '+b['id']+'\nالنص: '+b['text']},inline(src/'audio'/(b['id']+'.wav'),'audio/wav')]
        r=client.ask(parts)
        for row in check_rows(r,'results',[b['id'] for b in group]):
            if not isinstance(row.get('ok'),bool) or not row.get('heard') or not row.get('written'): raise ReviewError('invalid_audio_verdict')
            results[row['id']]={**row,'input_sha256':digests[row['id']]}
        write(resfile,results)
        print('فحص الصوت:',min(n+4,len(todo)),'/',len(todo),flush=True)
    flags=[b for b in blocks if results.get(b['id'],{}).get('ok') is False]
    for b in flags:
        bid=b['id']; old=reviews.get(bid,{})
        if old.get('input_sha256')==digests[bid] and old.get('decision')=='false_positive' and old.get('review_kind')=='automated_independent': continue
        prompt2='''أنت حكم ثان في نداء مستقل. استمع إلى الصوت نفسه وقارن النص والراية. إن كان المنطوق سليما أو فرق الوقف مشروعا فاحكم false_positive. إن وجدت حرفا أو كلمة محذوفة/مبدلة أو خطأ حركة في الوصل أو كلاما زائدا فاحكم true_error. لا تجامل الفاحص الأول. أعد JSON {"id":"...","decision":"false_positive|true_error","reason":"تعليل محدد","heard":"المسموع","written":"المكتوب"}.'''
        r=client.ask([{'text':prompt2+'\nالمعرف: '+bid+'\nالنص: '+b['text']+'\nالراية: '+json.dumps(results[bid],ensure_ascii=False)},inline(src/'audio'/(bid+'.wav'),'audio/wav')])
        if r.get('id')!=bid or r.get('decision') not in ('false_positive','true_error') or not all(r.get(x) for x in ('reason','heard','written')): raise ReviewError('invalid_audio_adjudication')
        reviews[bid]={**r,'input_sha256':digests[bid], 'review_kind':'automated_independent','reviewer':'automated-independent-review:'+client.model,'primary_model':client.model,'review_model':client.model,'independence':'separate_call_same_model'}
        write(revfile,reviews)
    errors=listen_gate.audit(src)
    write(reports/'audio.json',{'blocks':len(blocks),'newly_checked':len(todo),'flags':len(flags),'errors':errors})
    if errors: raise ReviewError('audio_gate_failed_'+str(len(errors)))
    print('اجتاز فحص الصوت:',len(blocks),'مقطعا',flush=True)

def clips(src, client, reports):
    paths=sorted((src/'clips').glob('*.mp4'))
    if len(paths)!=46: raise ReviewError('expected_46_animation_clips_got_'+str(len(paths)))
    report={}
    for i,p in enumerate(paths):
        duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(p)],stderr=subprocess.PIPE))
        if duration<=0: raise ReviewError('bad_clip_duration')
        prompt='''راجع عشرة إطارات مرتبة من مقطع وثائقي تاريخي، ولا تعتمد على وصفه وحده. افحص التشوهات الجسيمة، الأطراف الزائدة، تبدل الشخصية واللباس، ظهور وجه مسلم يجب أن يبقى من الخلف، امرأة، آلة موسيقية، دم أو جريح أو صريع، أذى حيوان، كتابة مولدة مشوهة. وجود وجه قائد فارسي غير مسلم مثل هرمز جائز. لا تعتبر القتال غير الدموي وحده خللا. إذا لم تستطع تحديد وجه المسلم من السياق فلا تجزه تخمينا. أعد JSON {"checked_frames":10,"pass":true|false,"issues":[{"frame":1,"reason":"..."}],"summary":"..."}. أي عيب واضح أو التباس جوهري يمنع الاجتياز.'''
        parts=[{'text':prompt+'\nمعرف المقطع: '+p.stem}]
        with tempfile.TemporaryDirectory() as tmp:
            for k in range(10):
                t=(max(0,duration-.08))*k/9
                out=Path(tmp)/(str(k)+'.jpg')
                subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',str(p),'-frames:v','1','-vf','scale=640:-2',str(out)],check=True,capture_output=True)
                parts += [{'text':'الإطار '+str(k+1)+' عند '+str(round(t,3))+' ث'},inline(out,'image/jpeg')]
            r=client.ask(parts)
        if r.get('checked_frames')!=10 or not isinstance(r.get('pass'),bool) or not isinstance(r.get('issues'),list): raise ReviewError('invalid_clip_verdict')
        report[p.name]={'sha256':sha(p),**r};write(reports/'clips.json',report)
        print('فحص التحريك:',i+1,'/ 46', 'سليم' if r['pass'] else 'راية',flush=True)
    if any(not r['pass'] or r['issues'] for r in report.values()): raise ReviewError('clip_visual_gate_failed')

def technical(pub,reports):
    import media_qa
    data={};failed=False
    for p in [pub/'film.mp4']+sorted((pub/'reels').glob('r*.mp4')):
        probe=media_qa.probe(str(p))
        if not all(any(s.get('codec_type')==kind for s in probe['streams']) for kind in ('audio','video')):raise ReviewError('missing_final_stream')
        if not math.isfinite(float(probe['format']['duration'])) or float(probe['format']['duration'])<=0:raise ReviewError('invalid_final_duration')
        original_run=media_qa.sp.run
        def checked_run(*args,**kwargs):
            kwargs['check']=True
            return original_run(*args,**kwargs)
        try:
            media_qa.sp.run=checked_run
            errors,info=media_qa.check(str(p),reel=p.parent.name=='reels')
        finally:
            media_qa.sp.run=original_run
        if info.get('LUFS') is None or not math.isfinite(float(info['LUFS'])) or info.get('ذروة') is None or not math.isfinite(float(info['ذروة'])):raise ReviewError('audio_measurement_missing')
        data[str(p.relative_to(pub))]={'errors':errors,'info':info};failed |= bool(errors)
        print('فحص تقني',str(p.relative_to(pub)),json.dumps({'errors':errors,'info':info},ensure_ascii=False),flush=True)
    write(reports/'technical.json',data)
    if failed: raise ReviewError('technical_media_gate_failed')
    print('اجتاز الفحص التقني: أربعة فيديوهات',flush=True)

def final_audio(pub,client,reports):
    results={}
    for p in [pub/'film.mp4']+sorted((pub/'reels').glob('r*.mp4')):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'audio.mp3'
            subprocess.run(['ffmpeg','-v','error','-y','-i',str(p),'-vn','-ac','1','-ar','22050','-b:a','48k',str(out)],check=True,capture_output=True)
            prompt='''استمع إلى كامل صوت هذا الفيديو النهائي. افحص الموسيقى أو الآلات (ممنوعة تماما)، الطقطقة والقطع المفاجئ والكلام الأجنبي غير المقصود أو توجيه الأداء المنطوق وانقطاع نهاية الكلام أو التكرار التقني. صوت الرياح ومؤثرات المعركة غير الموسيقية مسموحة. أعد JSON {"complete":true|false,"pass":true|false,"issues":[{"time_s":0,"reason":"..."}]}. لا تزعم سماع ما تعذر سماعه.'''
            r=client.ask([{'text':prompt},inline(out,'audio/mpeg')])
        results[str(p.relative_to(pub))]=r;write(reports/'final_audio.json',results)
        if r.get('complete') is not True or r.get('pass') is not True or r.get('issues')!=[]: raise ReviewError('final_audio_gate_failed')
    print('اجتاز الإصغاء النهائي: أربعة فيديوهات',flush=True)

def existing_gates(src,pub,client,reports,keys):
    import openings, opening_gate, policy_gate
    class Adapter:
        def __init__(self, ignored):pass
        def call(self,mk,tag,budget_s=420,**kw):
            try:return client.generate(json.loads(mk(False)))
            except ReviewError as e:return {'error':str(e)}
        def video(self,vid,budget_s=420):
            return self.call(lambda light:openings.body(vid,light),vid,budget_s)
    openings.Gem=Adapter
    with (reports/'gate_details.log').open('w') as f, contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
        if policy_gate.main(['text',str(src),'--out',str(reports/'policy_text_source.json')]):raise ReviewError('policy_text_source_failed')
        if policy_gate.main(['text',str(pub),'--out',str(reports/'policy_text_final.json')]):raise ReviewError('policy_text_final_failed')
        if policy_gate.main(['media',str(pub),'--keys',keys,'--strict','--out',str(reports/'policy_media.json')]):raise ReviewError('policy_media_failed')
        if opening_gate.main([str(pub),'--keys',keys,'--out',str(reports/'opening.json')]):raise ReviewError('opening_gate_failed')
    print('اجتازت بوابات النص والسياسات والافتتاحية',flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--pub',required=True);ap.add_argument('--keys',required=True);ap.add_argument('--reports',required=True);a=ap.parse_args()
    src,pub,reports=Path(a.source),Path(a.pub),Path(a.reports);reports.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(Path.cwd()/'tools'))
    from voice_lab import keys_from
    client=Client(keys_from(a.keys))
    report={'slug':'salasil','status':'failed','review_kind':'automated','files':{},'checks':{}}
    try:
        meta=json.loads((pub/'publish.json').read_text());assert meta.get('slug')=='salasil'
        files=[pub/'film.mp4']+sorted((pub/'reels').glob('r*.mp4'))
        if len(files)!=4:raise ReviewError('expected_four_final_videos')
        report['files']={str(p.relative_to(pub)):sha(p) for p in files};report['thumbnail_sha256']=sha(pub/'thumb-a.jpg')
        technical(pub,reports);report['checks']['technical']=True
        listen(src,client,reports);report['checks']['audio']=True
        clips(src,client,reports);report['checks']['clips']=True
        final_audio(pub,client,reports);report['checks']['final_audio']=True
        existing_gates(src,pub,client,reports,a.keys);report['checks'].update(policy=True,opening=True)
        report['status']='passed'
    except Exception as e:
        report['error']=str(e) if isinstance(e,ReviewError) else type(e).__name__
        print('توقفت المراجعة:',report['error'],flush=True)
    finally:
        report['api_calls']=client.calls;report['usage']=client.usage;write(reports/'review.json',report)
    print('نتيجة المراجعة:',report['status'],'· نداءات:',client.calls,flush=True)
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':sys.exit(main())
