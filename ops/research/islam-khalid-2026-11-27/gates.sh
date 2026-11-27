cd /workspace/mutafail-today/2026-11-27 && python3 build_script.py | tail -1
python3 - <<'P'
import re,json,os
L=[l.rstrip('\n') for l in open('script.md',encoding='utf-8') if re.match(r'd_\d+\|',l)]
bl=[dict(zip(('id','role','text'),l.split('|',2))) for l in L]
os.makedirs('/tmp/proj',exist_ok=True); json.dump(bl,open('/tmp/proj/blocks.json','w'),ensure_ascii=False)
open('/tmp/lines.txt','w').write("\n".join(b['text'] for b in bl))
P
cd /workspace/mutafail-factory/tools && python3 cta_gate.py /tmp/proj; python3 text_gate.py --lines /tmp/lines.txt; python3 lint.py /workspace/mutafail-today/2026-11-27/script.md | tail -15
