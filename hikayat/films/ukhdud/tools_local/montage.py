# مونتاج «أصحاب الأخدود» محليًا: صور ثابتة بحركة Ken Burns فقط، بلا موسيقى ولا مؤثرات، بصوت audio_paced.
import json,re,os,subprocess as sp,wave,sys
from PIL import Image,ImageDraw,ImageFont,ImageFilter
F='/workspace/hikayat-factory/film1/'; M=F+'montage/'; SEG=M+'seg/'; os.makedirs(SEG,exist_ok=True)
FPS=25; W,H=1920,1080; TARGET=float(os.environ.get('TARGET','690')); CARD=10.0
FONT='/usr/share/fonts/truetype/sand-box/google/Cairo/Cairo-VariableFont_slnt,wght.ttf'
voice=json.load(open(F+'voice_ready.json'))['variants']['full']
rows={}
for l in open(F+'shotlist.md'):
    if l.startswith('| d_'):
        c=[x.strip() for x in l.strip().strip('|').split('|')]; rows[c[0]]=c
def wdur(p):
    w=wave.open(p); d=w.getnframes()/w.getframerate(); w.close(); return d
A={b['id']:wdur(F+'audio_paced/'+b['id']+'.wav') for b in voice}
P={b['id']:b['pause_after_ms']/1000 for b in voice}
scale=(TARGET-CARD-sum(A.values()))/sum(P.values()); scale=max(0.25,min(1.0,scale))
G={k:round(v*scale,3) for k,v in P.items()}
# الإطارات بالعدد الصحيح لتفادي انزياح التزامن
plan=[];t=0.0;fr_acc=0
def frames_for(sec):
    global fr_acc
    end=round((t_acc[0]+sec)*FPS); n=end-fr_acc; fr_acc=end; t_acc[0]+=sec; return n
t_acc=[0.0]
MOT=['in','out','lr','rl']; mi=0
def caption_text(c):
    if not c: return ''
    if 'الانغماس' in c: return 'ابن تيمية، قاعدة في الانغماس، ص ٧٧'
    return c
for b in voice:
    i=b['id']; c=rows[i]; field=c[3]; cuts=2 if c[4]=='قطعان' else 1
    imgs=re.findall(r'I\d\d',field); cap=caption_text(c[5])
    total=A[i]+G[i]
    if i=='d_084': total+=CARD
    hint='crop' if 'قصّ' in field and 'مقصوصة' not in field else ('push' if 'دفع' in field else ('hold' if 'ثبات' in field else ''))
    right='يمين' in field
    n=max(cuts,len(imgs) if ('→' in field or '⟷' in field) else 1)
    while total/n>8.5: n+=1
    segs=[]
    for k in range(n):
        img=imgs[min(k,len(imgs)-1)] if ('→' in field or '⟷' in field) else imgs[0]
        if '⟷' in field: img=imgs[k%len(imgs)]
        if hint and k==0: mot=hint
        else: mot=MOT[mi%4]; mi+=1
        segs.append(dict(img=img,mot=mot,right=right))
    black=1.5 if i=='d_063' else 0
    each=total/n
    for k,s in enumerate(segs):
        s.update(block=i,sec=each,cap=cap,black=black if k==0 else 0,card=(i=='d_084'))
        plan.append(s)
for s in plan: s['frames']=frames_for(s['sec'])
json.dump(dict(scale=scale,gaps=G,plan=plan),open(M+'plan.json','w'),ensure_ascii=False,indent=1)
print('segments',len(plan),'gap scale %.3f'%scale,'video %.1f s'%(sum(s['frames'] for s in plan)/FPS))
