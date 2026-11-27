#!/bin/bash
# ينسخ مجلّد الفيلم (بلا mp3/wav/mp4 كبيرة) إلى المستودع ويودِعه ويدفعه
set -e
S=/workspace/mutafail-today/2026-11-27; R=/workspace/mutafail-factory; D=$R/ops/research/islam-khalid-2026-11-27
cd $S && tar cf - --exclude='*.mp3' --exclude='*.wav' --exclude='*.mp4' --exclude='*.m4a' --exclude='__pycache__' --exclude='proj/audio' --exclude='proj/anim' --exclude='proj/seg' --exclude='work' . | tar xf - -C $D
cd $R && git add -f ops/research/islam-khalid-2026-11-27 && (git diff --cached --quiet || git commit -qm "$1 [skip ci]") && git pull -q --rebase && git push -q origin master && git log --oneline -1
