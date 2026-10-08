# -*- coding: utf-8 -*-
"""مسحٌ مستقلّ لكلّ كتل الصوت: تفريغ بـWhisper large-v3 ومقارنةٌ بنصّ script.md، ثمّ قائمة الكتل الأضعف تطابقاً.

الاستعمال:
  python3 tools/asr_sweep.py <مجلّد_wav> <script.md> <خرج.json> [beam]
  (يُحفظ بعد كلّ كتلة ويستأنف من الخرج إن وُجد؛ beam=1 افتراضيّاً للمسح السريع، والمشتبه يُحسم بـasr_check_ffmpeg.py score)

⛔ الخرج يحوي نصّ الفيلم المسموع غير المنشور: لا يُودَع في المستودع العامّ؛ مكانه المستودع الخاصّ.
ملاحظة: النسبة المنخفضة وحدها ليست خللاً: الإملاء (همزة/تاء مربوطة/ياء) والوقوف على الهاء وتحويل الأرقام تخفّضها
وتفريغ Whisper لا يسمع حركة آخر الكلمة؛ فالحكم بالإملاء القسريّ score على القراءتين.
"""
import difflib
import glob
import json
import os
import re
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
from faster_whisper import WhisperModel  # noqa: E402


def norm(s):
    s = re.sub(r'[ً-ٰٟـ]', '', s)
    s = re.sub(r'[^ء-ي0-9 ]', ' ', s)
    for a, b in (('أ', 'ا'), ('إ', 'ا'), ('آ', 'ا'), ('ى', 'ي'), ('ة', 'ه'), ('ؤ', 'و'), ('ئ', 'ي')):
        s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s).strip()


def main(audio_dir, script, outp, beam=1):
    m = WhisperModel('large-v3', device='cpu', compute_type='int8', cpu_threads=4)
    txt = {}
    for line in open(script, encoding='utf-8'):
        p = line.rstrip('\n').split('|')
        if len(p) >= 3 and re.match(r'^[a-z]_\d', p[0]):
            txt[p[0]] = p[-1]
    res = json.load(open(outp, encoding='utf-8')) if os.path.exists(outp) else {}
    for f in sorted(glob.glob(audio_dir + '/*.wav')):
        k = os.path.basename(f)[:-4]
        if k in res:
            continue
        segs, _ = m.transcribe(f, language='ar', beam_size=beam, vad_filter=False,
                               condition_on_previous_text=False, temperature=0.0)
        heard = norm(' '.join(s.text for s in segs))
        want = norm(txt.get(k, ''))
        res[k] = {'ratio': round(difflib.SequenceMatcher(None, want.split(), heard.split()).ratio(), 3),
                  'heard': heard, 'want': want}
        json.dump(res, open(outp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(k, res[k]['ratio'], flush=True)
    low = sorted(((v['ratio'], k) for k, v in res.items() if v['ratio'] < 0.9))
    print('الكتل الأضعف تطابقاً (< 0.9):', [k for _, k in low])


if __name__ == '__main__':
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 1)
