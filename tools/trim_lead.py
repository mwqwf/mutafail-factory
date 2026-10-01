# -*- coding: utf-8 -*-
"""قصّ بداية كتلةٍ نُطق فيها توجيه الأداء الإنجليزي، صوتاً ومقطعَ راوٍ معاً، بلا إعادة تحريك.
(الزلاقة 2026-09-28: كل جمل الراوي سبقتها جملةٌ إنجليزية نحو 3.5 ث، والمقاطع مدفوعة الثمن)
الاستعمال: python trim_lead.py <proj>
يقرأ من blocks.json الحقل lead_cut (ثوانٍ في ملف الصوت الأصلي): يقصّ audio/<id>.wav من ذلك الموضع،
ويقصّ clips/<لقطته>_av.mp4 من lead_cut/1.05 (صوت المزامنة مسرَّع 1.05). علامة <id>.cut تمنع القصّ مرتين."""
import json, os, sys, subprocess as sp

PROJ = os.path.abspath(sys.argv[1]); P = lambda *a: os.path.join(PROJ, *a)
blocks = json.load(open(P('blocks.json'), encoding='utf-8'))
shots = json.load(open(P('shots.json'), encoding='utf-8'))
clip_of = {s['lipsync']: s['id'] for s in shots if s.get('lipsync')}
for b in blocks:
    cut = b.get('lead_cut')
    if not cut: continue
    wav, mark = P('audio', b['id'] + '.wav'), P('audio', b['id'] + '.cut')
    if os.path.exists(wav) and not os.path.exists(mark):
        sp.run(['ffmpeg', '-v', 'error', '-y', '-ss', '%.3f' % cut, '-i', wav, wav + '.tmp.wav'], check=True)
        os.replace(wav + '.tmp.wav', wav); open(mark, 'w').write(str(cut))
        print(b['id'], '✂ الصوت من %.2f ث' % cut)
    sid = clip_of.get(b['id'])
    av = P('clips', '%s_av.mp4' % sid) if sid else None
    cmark = P('clips', '%s_av.cut' % sid) if sid else None
    if av and os.path.exists(av) and not os.path.exists(cmark):
        sp.run(['ffmpeg', '-v', 'error', '-y', '-ss', '%.3f' % (cut / 1.05), '-i', av, '-c:v', 'libx264', '-crf', '18',
                '-preset', 'fast', '-c:a', 'aac', av + '.tmp.mp4'], check=True)
        os.replace(av + '.tmp.mp4', av); open(cmark, 'w').write(str(cut))
        print(sid, '✂ مقطع الراوي من %.2f ث' % (cut / 1.05))
