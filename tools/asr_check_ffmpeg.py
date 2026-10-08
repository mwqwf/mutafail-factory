# -*- coding: utf-8 -*-
"""غلاف لـtools/asr_check.py يفكّ الصوت بـffmpeg بدل av.

لماذا: في بيئة الجلسة السحابيّة (بايثون 3.13) إصدار av الجديد لا يوافق faster-whisper فيسقط الفكّ بالخطأ
  TypeError: open() got an unexpected keyword argument 'metadata_errors'
والحلّ هنا ترقيع decode_audio دون المساس بالأداة الأصليّة. يلزم: pip install faster-whisper، وffmpeg في المسار.

الاستعمال كما في asr_check.py تماماً:
  python3 tools/asr_check_ffmpeg.py transcribe audio/n_001.wav ...
  python3 tools/asr_check_ffmpeg.py score audio/n_111.wav "ثابت ..." "فابت ..."
"""
import os
import runpy
import subprocess
import sys

import numpy as np
import faster_whisper.audio as AU
import faster_whisper.transcribe as T


def decode(f, sampling_rate=16000, split_stereo=False):
    out = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-f', 'f32le', '-ac', '1', '-ar', str(sampling_rate), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32)


T.decode_audio = decode
AU.decode_audio = decode
sys.argv = ['asr_check.py'] + sys.argv[1:]
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'asr_check.py'), run_name='__main__')
