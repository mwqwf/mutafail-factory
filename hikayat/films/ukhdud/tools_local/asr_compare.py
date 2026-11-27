import json,re,sys,difflib
spec=json.load(open(sys.argv[1]));asr=json.load(open(sys.argv[2]))
def norm(t):
    t=re.sub(r'[\u064B-\u0652\u0670\u0640]','',t)
    t=re.sub('[أإآٱ]','ا',t).replace('ى','ي').replace('ة','ه').replace('ؤ','و').replace('ئ','ي')
    t=re.sub(r'[^\u0621-\u064A\s]',' ',t)
    return t.split()
bad=0
for b in spec['blocks']:
    h=asr.get(b['id']);
    if h is None: print(b['id'],'لا تفريغ');continue
    A,B=norm(b['text']),norm(h)
    sm=difflib.SequenceMatcher(a=A,b=B,autojunk=False)
    diffs=[(op,' '.join(A[i1:i2]),' '.join(B[j1:j2])) for op,i1,i2,j1,j2 in sm.get_opcodes() if op!='equal']
    if diffs:
        bad+=1; print(b['id'],'%.2f'%sm.ratio(),' | '.join(f'{op}:«{x}»→«{y}»' for op,x,y in diffs))
print('كتل فيها فروق:',bad)
