import re,sys
SPW=0.62
def retime(p):
    t=open(p).read().split('\n');T=0;starts=[];pos={}
    for i,l in enumerate(t):
        m=re.match(r'(d_\d+)\|(\w)\|(.*)',l)
        if l.startswith('## ['): starts.append([i,T])
        if m:
            pos[m.group(1)]=T
            w=len(re.findall(r'[\u0621-\u064A][\u0621-\u0652\u0670]*',m.group(3))); T+=w*SPW+(1.2 if m.group(2)=='Q' else 0.35)
    starts.append([None,T]); f=lambda s:'%d:%02d'%(s//60,s%60)
    for k in range(len(starts)-1):
        i,s=starts[k]; t[i]=re.sub(r'\d+:\d\d–\d+:\d\d',f(s)+'–'+f(starts[k+1][1]),t[i],count=1)
    open(p,'w').write('\n'.join(t)); return pos,T
for p in sys.argv[1:]:
    pos,T=retime(p)
print({k:'%d:%02d'%(v//60,v%60) for k,v in pos.items() if k in ('d_002','d_003','d_004','d_018','d_042','d_044','d_051','d_061','d_068','d_069','d_079','d_084')}, 'T=%d:%02d'%(T//60,T%60))
