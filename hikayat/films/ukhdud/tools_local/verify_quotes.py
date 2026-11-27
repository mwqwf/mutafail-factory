"""يقارن كل نصّ بين «» وكل كتلة Q بهيكل حروف الشاملة (مسلم ٣٠٠٥) أو نصّ ابن تيمية. خروج 1 عند أي اختلاف."""
import re,sys
def skel(s):
    s=re.sub(r'[\u064B-\u0652\u0670\u0640]','',s)
    s=re.sub(r'[أإآٱ]','ا',s); s=s.replace('ى','ي').replace('ة','ه').replace('ئ','ي').replace('ؤ','و').replace('ء','')
    return ' '.join(re.sub(r'[^\u0621-\u064A ]',' ',s).split())
base='/workspace/hikayat-factory/'
ref=skel(open(base+'sources/muslim3005_shamela.txt').read().split('### page 7444')[0])
extra=[skel("وأما الغلام فإنه أمر بقتل نفسه لما علم أن ذلك يوجب ظهور الإيمان في الناس")]  # https://shamela.ws/book/11288/60
bad=cnt=0
for l in open(sys.argv[1] if len(sys.argv)>1 else base+'film1/script.md'):
    m=re.match(r'(d_\d+)\|(\w)\|(.*)',l.strip())
    if not m: continue
    bid,role,txt=m.groups()
    segs=[re.sub(r'[«»]','',txt)] if role=='Q' else re.findall(r'«([^»]*)»',txt)
    for s in segs:
        for part in s.split('…'):
            k=skel(part)
            if not k: continue
            cnt+=1
            if k not in ref and not any(k in e for e in extra):
                bad+=1; print('MISMATCH',bid,part.strip())
print(f'quoted segments: {cnt} · mismatches: {bad}')
sys.exit(1 if bad else 0)
