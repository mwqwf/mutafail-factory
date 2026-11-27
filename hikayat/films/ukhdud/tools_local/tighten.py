# ضغط الصمت الداخلي الطويل وقصّ الطرفين — معالجة غير مدمِّرة (الأصل يبقى في film1/audio)
import sys,os,wave,numpy as np,json,re
SRC,DST=sys.argv[1],sys.argv[2]; MAXGAP=float(os.environ.get('MAXGAP','0.7')); EDGE=0.15
os.makedirs(DST,exist_ok=True); tot0=tot1=0
for f in sorted(x for x in os.listdir(SRC) if x.endswith('.wav')):
    w=wave.open(os.path.join(SRC,f));r=w.getframerate();a=np.frombuffer(w.readframes(w.getnframes()),np.int16).copy()
    fr=int(r*0.02);n=len(a)//fr;e=np.array([np.sqrt(np.mean(a[i*fr:(i+1)*fr].astype(float)**2)) for i in range(n)]);sil=e<300
    sp=np.where(~sil)[0]; s0=max(sp[0]*fr-int(EDGE*r),0); s1=min((sp[-1]+1)*fr+int(EDGE*r),len(a))
    keep=np.ones(len(a),bool); keep[:s0]=False; keep[s1:]=False
    i=sp[0]
    while i<=sp[-1]:
        if sil[i]:
            j=i
            while j<=sp[-1] and sil[j]: j+=1
            L=(j-i)*0.02
            if L>MAXGAP:
                cut0=i*fr+int(MAXGAP/2*r); cut1=j*fr-int(MAXGAP/2*r); keep[cut0:cut1]=False
            i=j
        else: i+=1
    b=a[keep].astype(float)
    # تليين نقاط القصّ: كلّها داخل صمت (طاقة < 300) فلا نقرات؛ مع تلاشٍ 10 مث في الطرفين
    k=int(0.01*r); b[:k]*=np.linspace(0,1,k); b[-k:]*=np.linspace(1,0,k)
    o=wave.open(os.path.join(DST,f),'wb');o.setnchannels(1);o.setsampwidth(2);o.setframerate(r);o.writeframes(b.astype(np.int16).tobytes());o.close()
    tot0+=len(a)/r; tot1+=len(b)/r
print('قبل %.1f ث (%d:%02d) — بعد %.1f ث (%d:%02d)'%(tot0,tot0//60,tot0%60,tot1,tot1//60,tot1%60))
