# يبني proj/blocks.json من السيناريو + الأصوات (casting.json) + أرقام الدعاوى (claims.json)
import re,json,sys
S='/workspace/mutafail-factory/ops/research/hattin-arnat-2026-12-01/script.md'; P='/workspace/hattin-work/proj'
L=[l.rstrip('\n') for l in open(S,encoding='utf-8') if re.match(r'd_\d+\|',l)]
bl=[dict(zip(('id','role','text'),l.split('|',2))) for l in L]
C=json.load(open(P+'/casting.json')); K=json.load(open(P+'/claims.json'))
for b in bl:
    if b['role']=='Q':
        b['speaker']=C['blocks'][b['id']]; b['voice']=C['characters'][b['speaker']]['voice']; b['claim']=K[b['id']]
    else: b['voice']=C['narrator']['voice']
json.dump(bl,open(P+'/blocks.json','w'),ensure_ascii=False,indent=1)
open('/tmp/h_lines.txt','w').write("\n".join(b['text'] for b in bl))
w=sum(len(re.sub(r'[\u064B-\u0652ٰـ]','',b['text']).split()) for b in bl); print(len(bl),'كتلة',w,'كلمة ≈ %.0f ث'%(w*0.5627))
