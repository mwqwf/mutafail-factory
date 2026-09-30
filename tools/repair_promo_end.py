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
source=P/'audio/p_09.wav'; taildur=dur(source)/.90+.40; enddur=6.0
vd=float(next(s['duration'] for s in probe(OLD)['streams'] if s['codec_type']=='video'))
# النسخة القديمة فيها بطاقة؛ نهاية لقطة الراوي من مدة الصوت والمشاهد لا من نهاية البطاقة.
scene_end=cut+(dur(source)+.30)/1.05
assert scene_end<vd and cut>40
factor=taildur/(scene_end-cut)
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
inputs=['-i',str(OLD),'-i',str(source),'-stream_loop','-1','-i',str(bg),'-loop','1','-i',str(OUT/'ending.png')]
filters=[
 f'[0:v]split[p][t];[p]trim=end={cut:.6f},setpts=PTS-STARTPTS,fps=30,settb=AVTB,setsar=1[pv]',
 f'[0:a]atrim=end={cut:.6f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=mono[pa]',
 f'[t]trim=start={cut:.6f}:end={scene_end:.6f},setpts={factor:.8f}*(PTS-STARTPTS),fps=30,tpad=stop_mode=clone:stop_duration=0.15,trim=duration={taildur:.6f},settb=AVTB,setsar=1[tv]',
 f'[1:a]atempo=0.90,adeclick,aresample=48000,aformat=channel_layouts=mono,apad=pad_dur=0.40,atrim=duration={taildur:.6f},asetpts=PTS-STARTPTS[ta]',
 f'[2:v]scale=-2:1920,crop=1080:1920,fps=30,trim=duration={enddur},setpts=PTS-STARTPTS,settb=AVTB,setsar=1[bg]',
 f'[bg][3:v]overlay=0:0,trim=duration={enddur},setpts=PTS-STARTPTS,format=yuv420p[ev]',
 f'anullsrc=r=48000:cl=mono,atrim=duration={enddur},asetpts=PTS-STARTPTS[ea]',
 '[pv][pa][tv][ta][ev][ea]concat=n=3:v=1:a=1[v][a]']
final=OUT/'r1.mp4'
sp.run(['ffmpeg','-v','error','-y',*inputs,'-filter_complex',';'.join(filters),'-map','[v]','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','19','-c:a','aac','-b:a','192k','-movflags','+faststart',str(final)],check=True)
expected=cut+taildur+enddur; measured=dur(final)
assert abs(measured-expected)<.20,(measured,expected)
v=next(s for s in probe(final)['streams'] if s['codec_type']=='video');assert (v['width'],v['height'])==(1080,1920)
assert measured<175
sp.run(['ffmpeg','-v','error','-y','-ss',str(cut),'-i',str(final),'-t',str(taildur),'-vn','-ar','24000','-ac','1',str(OUT/'verified_tail.wav')],check=True)
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'video_sha256':hashlib.sha256(final.read_bytes()).hexdigest(),'cut':cut,'voice_duration':dur(source),'new_spoken_segment':taildur,'ending_card':enddur,'expected_duration':expected,'actual_duration':measured}
(OUT/'repair_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('اكتملت إعادة تركيب الخاتمة وحارس المدّة')
