#!/bin/bash
# بوّابات النصّ على سيناريو حطّين (بلا شبكة ولا إنفاق)
R=/workspace/mutafail-factory; S=$R/ops/research/hattin-arnat-2026-12-01/script.md; P=/workspace/hattin-work/proj
python3 /workspace/hattin-work/prep.py
cd $R/tools
echo "== cta";    python3 cta_gate.py $P
echo "== text";   python3 text_gate.py --lines /tmp/h_lines.txt | tail -4
echo "== lint";   python3 lint.py $S | tail -6
echo "== policy"; python3 policy_gate.py text $P --out /tmp/h_pol.json | tail -6
echo "== thrill"; python3 thrill_gate.py $P | tail -14
