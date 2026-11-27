#!/bin/bash
# قطعٌ بصريّ داخل الكتلة d_004 (لا يقبل المونتاج قطعاً داخل الكتلة): مقطع S04 = 1.72 ث من تحريك reveal ثم 1.88 ث لقطة مقرّبة
# على آثار الحوافر (الفرسان من الخلف، لا وجوه). يرفع لقطات أوّل 30 ث الفعلية إلى 12.
cd "$(dirname "$0")/../proj"
ffmpeg -v error -y -i anim/S04.v4.reveal.out.mp4 -t 1.72 -vf "scale=1920:1080,fps=25,setsar=1" -an -c:v libx264 -crf 16 -pix_fmt yuv420p /tmp/s04a.mp4
ffmpeg -v error -y -i images/S04.jpg -vf "scale=3840:2160,zoompan=z='1.6+0.003*on':x='iw*0.47-iw/zoom/2':y='ih*0.62-ih/zoom/2':d=47:s=1920x1080:fps=25,setsar=1" -frames:v 47 -c:v libx264 -crf 16 -pix_fmt yuv420p /tmp/s04b.mp4
printf "file /tmp/s04a.mp4\nfile /tmp/s04b.mp4\n" > /tmp/s04.txt
ffmpeg -v error -y -f concat -safe 0 -i /tmp/s04.txt -c copy clips/S04.mp4
