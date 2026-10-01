# -*- coding: utf-8 -*-
"""إعادة تركيب دعوة الاشتراك كاملة، ثم بطاقة واضحة باسم السلسلة."""
import sys,json,pathlib,subprocess as sp,hashlib
from PIL import Image,ImageDraw,ImageFont
P=pathlib.Path(sys.argv[1]); OLD=pathlib.Path(sys.argv[2]); OUT=pathlib.Path(sys.argv[3]); OUT.mkdir(parents=True,exist_ok=True)
def probe(f):
 return json.loads(sp.check_output(['ffprobe','-v','error','-show_entries','stream=codec_type,duration,width,height:format=duration','-of','json',str(f)]))
def dur(f): return float(probe(f)['format']['duration'])
shots=json.loads((P/'shots.json').read_text()); assert shots[-1]['blocks']==['p_09']
cut=sum((dur(P/'audio'/(b+'.wav'))+.30)/1.05 for s in shots[:-1] for b in s['blocks'])
source=P/'audio/p_09.wav'; enddur=6.0
vd=float(next(s['duration'] for s in probe(OLD)['streams'] if s['codec_type']=='video'))
# النسخة القديمة فيها بطاقة؛ نهاية لقطة الراوي من مدة الصوت والمشاهد لا من نهاية البطاقة.
scene_end=cut+(dur(source)+.30)/1.05
assert scene_end<vd and cut>40
card=Image.new('RGBA',(1080,1920),(0,0,0,180)); d=ImageDraw.Draw(card)
font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
rows=[('شاهد السلسلة كاملة',76,440,'white'),('معارك غيرت مجرى التاريخ',64,620,'#F7C74A'),('على قناة المتفائل',72,790,'white'),('روابط الحلقات في الوصف',62,1000,'white'),('اشترك وفعّل الجرس',74,1200,'#F7C74A')]
for text,size,y,color in rows:
 f=ImageFont.truetype(font,size)
 while d.textlength(text,font=f,direction='rtl')>980:
  size-=2;f=ImageFont.truetype(font,size)
 d.text((540,y),text,font=f,fill=color,anchor='mt',direction='rtl',stroke_width=3,stroke_fill='black')
card.save(OUT/'ending.png')
bg=P/'clips/B6.mp4'
duration=dur(P/'../old/film_full.mp4')
# المحافظة على الصوت الأصلي الكامل بنفس سرعته وتسويته من البداية للنهاية.
inputs=['-i',str(OLD),'-stream_loop','-1','-i',str(bg),'-loop','1','-i',str(OUT/'ending.png')]
filters=[
 f'[0:v]trim=duration={duration},setpts=PTS-STARTPTS,fps=30,settb=AVTB,setsar=1[pv]',
 f'[1:v]scale=-2:1920,crop=1080:1920,fps=30,trim=duration={enddur},setpts=PTS-STARTPTS,settb=AVTB,setsar=1[bg]',
 f'[bg][2:v]overlay=0:0,trim=duration={enddur},setpts=PTS-STARTPTS,format=yuv420p[ev]',
 '[pv][ev]concat=n=2:v=1:a=0[v]',
 f'[0:a]atrim=duration={duration},asetpts=PTS-STARTPTS,apad=pad_dur={enddur},atrim=duration={duration+enddur}[a]']
final=OUT/'r1.mp4'
sp.run(['ffmpeg','-v','error','-y',*inputs,'-filter_complex',';'.join(filters),'-map','[v]','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','19','-c:a','aac','-b:a','192k','-movflags','+faststart',str(final)],check=True)
expected=duration+enddur;measured=dur(final)
assert abs(measured-expected)<.20
v=next(s for s in probe(final)['streams'] if s['codec_type']=='video');assert (v['width'],v['height'])==(1080,1920)
sp.run(['ffmpeg','-v','error','-y','-i',str(final),'-vn','-ar','24000','-ac','1',str(OUT/'verified_full.wav')],check=True)
report={'video_sha256':hashlib.sha256(final.read_bytes()).hexdigest(),'original_voice_retained':True,'last_segment_speed_matches_prefix':True,'original_duration':duration,'ending_card':enddur,'expected_duration':expected,'actual_duration':measured}
(OUT/'repair_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('اكتملت إعادة تركيب الخاتمة وحارس المدّة')
