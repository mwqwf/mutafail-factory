import sys,json,os,subprocess,numpy as np
from faster_whisper import WhisperModel
m=WhisperModel(os.environ.get('ASR_MODEL','large-v3-turbo'),device='cpu',compute_type='int8',cpu_threads=int(os.environ.get('ASR_T','3')))
out={}
for f in sys.argv[1:]:
    a=np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i',f,'-ar','16000','-ac','1','-f','s16le','-'],capture_output=True,check=True).stdout,np.int16).astype(np.float32)/32768
    segs,_=m.transcribe(a,language='ar',beam_size=5,temperature=0.0,condition_on_previous_text=False,without_timestamps=True,initial_prompt='قال رسول الله صلى الله عليه وسلم')
    t=' '.join(s.text.strip() for s in segs); out[os.path.basename(f)[:-4]]=t; print(os.path.basename(f),'⇐',t,flush=True)
json.dump(out,open(os.environ.get('ASR_OUT','/tmp/asr.json'),'w'),ensure_ascii=False,indent=1)
