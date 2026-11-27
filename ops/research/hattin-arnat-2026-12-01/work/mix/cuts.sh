#!/bin/bash
# cuts.sh f.mp4 — أزمنة القطع الداخلية (تغيّر المشهد > 0.3)
ffmpeg -v info -i "$1" -vf "select='gt(scene,0.3)',showinfo" -f null - 2>&1 | grep -o "pts_time:[0-9.]*" | cut -d: -f2 | tr '\n' ' '
