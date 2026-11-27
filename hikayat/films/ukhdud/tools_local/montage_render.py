import json,os,subprocess as sp,sys
from concurrent.futures import ThreadPoolExecutor
from PIL import Image,ImageDraw,ImageFont,ImageFilter
F='/workspace/hikayat-factory/film1/'; M=F+'montage/'; SEG=M+'seg/'; os.makedirs(SEG,exist_ok=True)
FONT='/usr/share/fonts/truetype/sand-box/google/Cairo/Cairo-VariableFont_slnt,wght.ttf'
W,H,FPS=1920,1080,25
plan=json.load(open(M+'plan.json'))['plan']
def font(sz,wt=600):
    f=ImageFont.truetype(FONT,sz,layout_engine=ImageFont.Layout.RAQM)
    try: f.set_variation_by_axes([wt,0])
    except Exception: pass
    return f
def caption_png(text,path):
    im=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(im); f=font(34,600)
    bb=d.textbbox((0,0),text,font=f,direction='rtl',language='ar'); tw=bb[2]-bb[0]; th=bb[3]-bb[1]
    x=W-80-tw; y=H-70-th
    pad=14; d.rounded_rectangle((x-pad,y-pad+bb[1],x+tw+pad,y+th+pad+bb[1]),radius=10,fill=(0,0,0,120))
    d.text((x-bb[0],y),text,font=f,fill=(240,232,215,235),direction='rtl',language='ar')
    im.save(path)
CARD_LINES=[('المصادر',70,800),
 ('صحيح مسلم، كتاب الزهد والرقائق',48,700),('باب قصة أصحاب الأخدود والساحر والراهب والغلام، الحديث ٣٠٠٥',42,600),
 ('تفسير ابن كثير، سورة البروج',48,700),('ابن تيمية، قاعدة في الانغماس، ص ٧٧',48,700),
 ('الصور مولَّدة بالذكاء الاصطناعي للتوضيح، ولا تمثّل أشخاصًا حقيقيين',34,500)]
def card_bg(path):
    im=Image.open(F+'images/I45.jpg').convert('RGB').resize((W,H),Image.LANCZOS).filter(ImageFilter.GaussianBlur(14))
    ov=Image.new('RGBA',(W,H),(0,0,0,150)); im=Image.alpha_composite(im.convert('RGBA'),ov); d=ImageDraw.Draw(im)
    y=200
    for t,sz,wt in CARD_LINES:
        f=font(sz,wt); bb=d.textbbox((0,0),t,font=f,direction='rtl',language='ar'); tw=bb[2]-bb[0]
        d.text(((W-tw)//2-bb[0],y),t,font=f,fill=(245,238,220,255),direction='rtl',language='ar')
        y+= sz+ (70 if sz>=70 else 40)
    im.convert('RGB').save(path,quality=95)
caps={}
for s in plan:
    if s['cap'] and s['cap'] not in caps:
        p=M+'cap_%d.png'%len(caps); caption_png(s['cap'],p); caps[s['cap']]=p
card_bg(M+'card.jpg')
def zexpr(mot,N,right):
    c="x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    if mot=='in': return f"z='1+0.12*on/{N}':"+c
    if mot=='out': return f"z='1.12-0.12*on/{N}':"+c
    if mot=='push': return f"z='1+0.20*on/{N}':"+c
    if mot=='hold': return f"z='1+0.03*on/{N}':"+c
    if mot=='crop':
        xr="x='iw-iw/zoom':y='ih/2-(ih/zoom/2)'" if right else c
        return f"z='1.30+0.06*on/{N}':"+xr
    if mot=='lr': return f"z='1.15':x='(iw-iw/zoom)*on/{N}':y='ih/2-(ih/zoom/2)'"
    if mot=='rl': return f"z='1.15':x='(iw-iw/zoom)*(1-on/{N})':y='ih/2-(ih/zoom/2)'"
def render(k):
    s=plan[k]; out=SEG+'%03d.mp4'%k
    if os.path.exists(out) and os.path.getsize(out)>1000: return
    N=s['frames']
    src=M+'card.jpg' if s['card'] else F+'images/'+s['img']+'.jpg'
    mot='hold' if s['card'] else s['mot']
    vf=f"[0:v]scale=3840:2160:flags=lanczos,zoompan={zexpr(mot,N,s.get('right'))}:d={N}:s={W}x{H}:fps={FPS},setsar=1"
    if s['black']: vf+=f",drawbox=enable='lt(t,{s['black']})':c=black:t=fill"
    inputs=['-i',src]
    if s['cap'] and not s['card']:
        inputs+=['-i',caps[s['cap']]]; vf+="[v];[v][1:v]overlay=0:0"
    vf+="[o]"
    sp.run(['ffmpeg','-v','error','-y']+inputs+['-filter_complex',vf,'-map','[o]','-frames:v',str(N),'-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-r',str(FPS),out+'.tmp.mp4'],check=True)
    os.replace(out+'.tmp.mp4',out)
idx=list(range(len(plan)))
if len(sys.argv)>1: idx=[int(x) for x in sys.argv[1:]]
with ThreadPoolExecutor(int(os.environ.get('JOBS','3'))) as ex: list(ex.map(render,idx))
print('done',len(idx))
