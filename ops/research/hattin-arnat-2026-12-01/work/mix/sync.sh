#!/bin/bash
# يودِع خطط حطّين وسكربتاته وملفاتها النصّية (بلا وسائط) على فرع hattin/production
W=/workspace/hattin-work; R=/workspace/mutafail-factory; D=$R/ops/research/hattin-arnat-2026-12-01/work
mkdir -p $D; cd $W && find . \( -path ./voice -o -path ./review -o -path ./proj/segs -o -path ./proj/anim -o -path ./proj/clips -o -path ./proj/images -o -path ./proj/rejected -o -path ./proj/audio -o -path ./proj/audio_full \) -prune -o -type f \( -name '*.py' -o -name '*.sh' -o -name '*.json' -o -name '*.txt' -o -name '*.md' -o -name '*.srt' \) -size -2M -print | while read f; do mkdir -p $D/$(dirname $f); cp $f $D/$f; done
cd $R && git add ops/research/hattin-arnat-2026-12-01/work && git commit -qm "${1:-حطّين: حفظ تقدّم الإنتاج} [skip ci]" && git push -q origin hattin/production 2>&1 | tail -2; git log --oneline -1
