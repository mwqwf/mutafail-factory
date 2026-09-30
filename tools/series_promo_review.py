# -*- coding: utf-8 -*-
"""فحص النسخة الموجودة ونقل معاينة مشفرة إلى جلسة الإصلاح."""
import json, subprocess as sp, pathlib, shutil, tarfile, os, base64
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
R=pathlib.Path("review")
R.mkdir(exist_ok=True)
import urllib.request,re
raw=os.environ.get("GEMINI_KEYS_JSON","")
try:
    parsed=json.loads(raw)
    values=parsed if isinstance(parsed,list) else parsed.get("keys",list(parsed.values()))
except Exception: values=re.split(r'[\r\n,"\s]+',raw)
keys=list(dict.fromkeys(v.strip() for v in values if isinstance(v,str) and v.strip().startswith(("AIza","AQ."))))
sp.run(["python","tools/repair_promo_v3.py","proj","old/r1.mp4","repaired"],check=True)
sp.run(["ffmpeg","-v","error","-y","-i","repaired/r1.mp4","-vf","scale=-2:720","-c:v","libx264","-crf","24","-preset","veryfast","-c:a","aac","-b:a","96k",str(R/"series-promo-review.mp4")],check=True)
shutil.copy("repaired/repair_report.json",R/"repair_report.json")
parts=[{"text":"راجع هذا الريلز العربي كاملاً سمعياً، وخاصة الانتقال من الجمل الأولى إلى الجمل الأخيرة. لا تكتف بوجود الكلمات. فرغ آخر جملتين، وحدد أخطاء النحو أو النطق المسموعة فعلاً، وهل يوجد تلحين أو غناء غير طبيعي، وهل تتغير هوية الصوت أو سرعته أو مستوى جهارته فجأة عند الخاتمة. لا تختلق عيباً ولا تتسامح معه. أعد JSON بالحقول ending_transcript, grammar_errors (قائمة), pronunciation_errors (قائمة), unnatural_melody (منطقي), voice_identity_change (منطقي), abrupt_speed_or_level_change (منطقي), cut_off (منطقي), explanation. إليك النص المقصود للمقارنة: "+ " ".join(b["text"] for b in json.loads(pathlib.Path("proj/blocks.json").read_text()))},
{"inlineData":{"mimeType":"audio/wav","data":base64.b64encode(pathlib.Path("repaired/verified_full.wav").read_bytes()).decode()}}]
answer={"error":"لم يكتمل الفحص"}
for model in ["gemini-3.5-flash","gemini-flash-latest"]:
    for key in keys[:3]:
        body=json.dumps({"contents":[{"parts":parts}],"generationConfig":{"temperature":0,"responseMimeType":"application/json"}}).encode()
        req=urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models/"+model+":generateContent",data=body,headers={"Content-Type":"application/json","x-goog-api-key":key})
        try:
            with urllib.request.urlopen(req,timeout=120) as res: ans=json.load(res)
            answer={"model":model,"response":ans};break
        except Exception as err:
            answer.setdefault("failures",[]).append({"model":model,"type":type(err).__name__,"code":getattr(err,"code",None)})
            continue
    if "response" in answer: break
(R/"ending_asr.json").write_text(json.dumps(answer,ensure_ascii=False,indent=2))


sp.run(["gh","release","view","series-promo-v3-out"],stdout=sp.DEVNULL,stderr=sp.DEVNULL).returncode==0 or sp.run(["gh","release","create","series-promo-v3-out","--draft","--title","ريلز السلسلة — نسخة المراجعة الثالثة"],check=True)
sp.run(["gh","release","upload","series-promo-v3-out","repaired/r1.mp4","repaired/repair_report.json","review/ending_asr.json","--clobber"],check=True)
with tarfile.open("review.tgz","w:gz") as t: t.add(R,arcname="review")
config=json.loads(pathlib.Path("ops/review/series-promo.json").read_text())
pub=load_pem_public_key(config["public_key"].encode())
key=AESGCM.generate_key(bit_length=256); nonce=os.urandom(12)
data=AESGCM(key).encrypt(nonce,pathlib.Path("review.tgz").read_bytes(),b"series-promo-review")
wrapped=pub.encrypt(key,padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
dest=pathlib.Path("ops/review-output"); dest.mkdir(exist_ok=True)
encoded=base64.b64encode(data).decode()
parts=[]
for i in range(0,len(encoded),400000):
    name="part_%03d.b64"%(i//400000)
    (dest/name).write_text(encoded[i:i+400000]); parts.append(name)
(dest/"manifest.json").write_text(json.dumps({"parts":parts,"nonce":base64.b64encode(nonce).decode(),"key":base64.b64encode(wrapped).decode()}))
print("اكتمل فحص الملفات وحفظ معاينة مشفرة: %d جزءاً"%len(parts))
