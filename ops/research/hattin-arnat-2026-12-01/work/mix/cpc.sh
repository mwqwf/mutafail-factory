#!/bin/bash
# cpc.sh ID HASH [ID HASH...] — ينسخ مقطع GenerateVideo إلى proj/clips/ID.mp4 بلا صوت، ويصنع صورة مراجعة (3 إطارات)
A=/cursor/stores/user/grok-bot/agents/5b415a5d-20ea-49f0-ae04-c93664069335/assets; cd /workspace/hattin-work
while [ $# -ge 2 ]; do id=$1; h=$2; shift 2
 ffmpeg -v error -y -i $( [[ $h == /* ]] && echo $h || echo $A/$h.mp4 ) -an -c:v copy proj/clips/$id.mp4
 echo "$id $h" >> proj/clips_src.txt
 d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 proj/clips/$id.mp4)
 ffmpeg -v error -y -i proj/clips/$id.mp4 -vf "fps=5/$d,scale=320:-1,tile=5x1" -frames:v 1 review/$id.jpg
 echo "$id $d"; done
