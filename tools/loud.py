# -*- coding: utf-8 -*-
"""🔊 تسوية الجهارة على مرّتين إلى معيار يوتيوب: −14 LUFS، والذروة الحقيقية −1، والمدى 11.
المرّة الأولى تقيس، والثانية تطبّق القياس خطّياً (linear=true) فلا يتبدّل إيقاع الكلام ولا يُضغط.
وإن تعذّر القياس (صمتٌ تامّ يُقاس ‎-inf) طُبّقت التسوية الديناميكية بمرّةٍ واحدة.
وهي التسوية نفسها في mont_hybrid وmkreel_film، ومكانها هنا لأدوات الريلز التي لا تمرّ بالمونتاج:
درس مؤتة 2026-10-07 — ريلزاتٌ بلا تسويةٍ خرجت بين −16.5 و−26 LUFS، ويوتيوب يخفض الأعلى ولا يرفع الأخفض.
    python3 tools/loud.py <مدخل> <مخرج.wav>
"""
import json
import subprocess as sp
import sys

LN = 'loudnorm=I=-14:TP=-1.0:LRA=11'


def norm(src, dst, ff='ffmpeg', out_args=('-ar', '48000', '-c:a', 'pcm_s16le')):
    o = sp.run([ff, '-hide_banner', '-nostats', '-i', src, '-af', LN + ':print_format=json', '-f', 'null', '-'],
               capture_output=True, text=True).stderr
    ln = LN
    try:
        m = json.loads(o[o.rindex('{'):o.rindex('}') + 1])
        if float(m['input_i']) > -70:
            ln += (':measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true'
                   % (m['input_i'], m['input_tp'], m['input_lra'], m['input_thresh'], m['target_offset']))
    except (ValueError, KeyError):
        pass
    sp.run([ff, '-v', 'error', '-y', '-i', src, '-af', ln + ',aresample=48000'] + list(out_args) + [dst], check=True)
    return dst


if __name__ == '__main__':
    norm(sys.argv[1], sys.argv[2])
