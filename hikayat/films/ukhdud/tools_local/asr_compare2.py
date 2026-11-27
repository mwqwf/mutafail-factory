import json,re,sys,difflib,os
spec=json.load(open(sys.argv[1])); D=sys.argv[2]
T={b['id']:b['text'] for b in spec['blocks']}
def norm(t):
    t=re.sub(r'[\u064B-\u0652\u0670\u0640]','',t)
    t=re.sub('[أإآٱ]','ا',t).replace('ى','ي').replace('ة','ه').replace('ؤ','و').replace('ئ','ي')
    t=re.sub(r'[^\u0621-\u064A\s]',' ',t)
    return t.split()
res={}
for f in sorted(os.listdir(D)):
    if not f.endswith('.txt'): continue
    i=f[:-4]; h=open(os.path.join(D,f)).read().strip()
    A,B=norm(T[i]),norm(h); sm=difflib.SequenceMatcher(a=A,b=B,autojunk=False)
    latin=bool(re.search(r'[A-Za-z]',h)) or len(B)==0
    diffs=[(op,' '.join(A[a1:a2]),' '.join(B[b1:b2])) for op,a1,a2,b1,b2 in sm.get_opcodes() if op!='equal']
    res[i]={'ratio':round(sm.ratio(),2),'garbled':latin,'diffs':diffs,'asr':h}
    tag='هذيان' if latin or sm.ratio()<0.6 else ('تطابق' if not diffs else 'فروق')
    print(i,tag,res[i]['ratio'],' | '.join(f'{op}:«{x}»→«{y}»' for op,x,y in diffs)[:300])
json.dump(res,open(sys.argv[3],'w'),ensure_ascii=False,indent=1)
