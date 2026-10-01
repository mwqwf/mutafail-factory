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
pathlib.Path("repaired").mkdir(exist_ok=True)
sp.run(["gh","release","download","series-promo-v3-out","-D","repaired"],check=True)
sp.run(["ffmpeg","-v","error","-y","-i","repaired/r1.mp4","-vn","-ar","24000","-ac","1","repaired/verified_full.wav"],check=True)
sp.run(["ffmpeg","-v","error","-y","-i","repaired/r1.mp4","-vf","scale=-2:720","-c:v","libx264","-crf","24","-preset","veryfast","-c:a","aac","-b:a","96k",str(R/"series-promo-review.mp4")],check=True)
shutil.copy("repaired/repair_report.json",R/"repair_report.json")
sp.run(["ffmpeg","-v","error","-y","-ss","5.885714","-i","repaired/r1.mp4","-t","4.019048","-vn","-ar","24000","-ac","1","review/word_context.wav"],check=True)
parts=[{"text":"تحكيم سمعي محدد: الفحص الأول لصوت هذا المشروع أجاز مقطع «وَادٍ ابْتَلَعَ جَيْشَ الرُّومِ… فِي الْيَرْمُوكْ»، لكن فحص لاحق ادعى سقوط التنوين في «وادٍ». استمع للمصدر ثم المقطع المصيّر. هل يوجد وقف بعد «واد» يجعل سقوط التنوين جائزاً، أم وصل صحيح بنون التنوين قبل همزة الوصل، أم سقوط حقيقي؟ لا تعتمد تقرير أي فاحص. اكتب ما سمعت من الأصوات، وهل الراية صحيحة أو خاطئة أو غير محسومة ولماذا. أعد JSON: source_heard, render_heard, pause_after_wadi, tanween_audible, verdict (confirmed_error / false_positive / uncertain), rationale."},
{"text":"المصدر"},{"inlineData":{"mimeType":"audio/wav","data":base64.b64encode(pathlib.Path("proj/audio/p_02.wav").read_bytes()).decode()}},
{"text":"المقطع النهائي"},{"inlineData":{"mimeType":"audio/wav","data":base64.b64encode(pathlib.Path("review/word_context.wav").read_bytes()).decode()}}]
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
(R/"adjudication.json").write_text(json.dumps(answer,ensure_ascii=False,indent=2))


sp.run(["gh","release","view","series-promo-v3-out"],stdout=sp.DEVNULL,stderr=sp.DEVNULL).returncode==0 or sp.run(["gh","release","create","series-promo-v3-out","--draft","--title","ريلز السلسلة — نسخة المراجعة الثالثة"],check=True)
sp.run(["gh","release","upload","series-promo-v3-out","repaired/r1.mp4","repaired/repair_report.json","review/adjudication.json","--clobber"],check=True)
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
