#!/bin/bash
# يقصّ الشورتات الثلاثة عمودياً 1080×1920 من film.mp4 (مركز الإطار، بلا تكبير وجه)، مع ترجمة محروقة اختيارية لاحقاً
F=${1:-../proj/film.mp4}
cut(){ ffmpeg -v error -y -ss $2 -to $3 -i "$F" -vf "crop=ih*9/16:ih,scale=1080:1920,setsar=1" -c:v libx264 -crf 19 -preset veryfast -c:a aac -b:a 192k -af "afade=t=out:st=$(( $4 - 1 )):d=1" "short_$1.mp4"; }
cut 1 0:00 0:50 50
cut 2 1:59 2:49 50
cut 3 4:09 5:00 51
