# -*- coding: utf-8 -*-
"""فحص النسخة الموجودة ونقل معاينة مشفرة إلى جلسة الإصلاح."""
import json, subprocess as sp, pathlib, shutil, tarfile, os, base64
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
P=pathlib.Path("proj"); R=pathlib.Path("review")
def probe(p):
    return json.loads(sp.check_output(["ffprobe","-v","error","-show_entries","stream=codec_type,duration,width,height:format=duration","-of","json",str(p)]))
report={}
for p in list(P.glob("*.json")):
    shutil.copy(p,R/p.name)
for p in list((P/"audio").glob("*.wav"))+list(pathlib.Path("old").glob("*.mp4"))+list((P/"clips").glob("*.mp4")):
    report[str(p)]=probe(p)
(R/"durations.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
for name in ("r1","film_full"):
    sp.run(["ffmpeg","-v","error","-y","-i","old/"+name+".mp4","-vf","scale=-2:480","-c:v","libx264","-crf","32","-preset","veryfast","-c:a","aac","-b:a","64k",str(R/(name+".mp4"))],check=True)
shots=json.loads((P/"shots.json").read_text())
for bid in shots[-1]["blocks"]:
    shutil.copy(P/"audio"/(bid+".wav"),R/(bid+".wav"))
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
