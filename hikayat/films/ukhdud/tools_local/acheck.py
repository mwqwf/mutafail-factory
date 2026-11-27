import json,re,sys,wave,os,numpy as np
D=sys.argv[1]; blocks=json.load(open(sys.argv[2]))
blocks=blocks['blocks'] if isinstance(blocks,dict) else blocks
W=lambda t:len(re.findall(r'[\u0621-\u064A][\u0621-\u0652\u0670]*',t))
rows=[];tot=0
for b in blocks:
    f=os.path.join(D,b['id']+'.wav')
    if not os.path.exists(f): rows.append((b['id'],'MISSING'));continue
    raw=open(f,'rb').read(); dup=raw[44:48]==b'RIFF'
    w=wave.open(f);r=w.getframerate();a=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(float)
    d=len(a)/r; tot+=d
    fr=int(r*0.02); n=len(a)//fr; e=np.array([np.sqrt(np.mean(a[i*fr:(i+1)*fr]**2)) for i in range(n)])
    sil=e<300
    lead=np.argmax(~sil)*0.02 if (~sil).any() else d; trail=np.argmax(~sil[::-1])*0.02 if (~sil).any() else d
    # longest internal silence
    run=mx=0
    for s in sil[int(lead/0.02):n-int(trail/0.02)]:
        run=run+1 if s else 0; mx=max(mx,run)
    speech=(~sil).sum()*0.02
    clip=int((np.abs(a)>=32700).sum()); peak=np.abs(a).max()
    rows.append((b['id'],b.get('role'),round(d,2),W(b['text']),round(d/max(W(b['text']),1),2),round(speech,2),round(lead,2),round(trail,2),round(mx*0.02,2),clip,int(peak),'DUPHDR' if dup else ''))
print('id role dur words s/word speech lead trail maxgap clip peak')
for x in rows: print(*x)
print('TOTAL %.1f s = %d:%02d'%(tot,tot//60,tot%60))
