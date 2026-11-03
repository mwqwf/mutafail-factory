#!/usr/bin/env python3
"""تجربة Chatterbox (أمر المالك 2026-11-03): هل يقرأ الفصحى قراءةً تصلح مرشّحاً في مختبر الأصوات؟
يولّد جملاً من فيلمٍ منشور بصوت مرجعٍ هو راوينا نفسه (Gemini، صوتٌ اصطناعيّ لا شخصٌ حقيقيّ)، بالتشكيل وبدونه،
ويضع بجانب كلّ جملةٍ أصلها من Gemini، ثمّ يرتّب كلّ زوجٍ عشوائياً (أ/ب) ومفتاحه في ملفٍّ منفصل للحكم الأعمى.
مجّانيّ على عدّاد GitHub القياسيّ، ولا يمسّ الإنتاج.
    python tools/exp/chatterbox_ar.py <مجلد المشروع> <مجلد الناتج> <معرّفات الكتل مفصولة بفواصل>
"""
import json, os, random, re, shutil, subprocess as sp, sys, time
import torch, torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

TASHKEEL = re.compile('[ؐ-ًؚ-ٰٟۖ-ۭ]')

def main(proj, out, ids):
    os.makedirs(out, exist_ok=True)
    blocks = {b['id']: b for b in json.load(open(os.path.join(proj, 'blocks.json'), encoding='utf-8'))}
    # المرجع: أوّل ثلاث كتلٍ للراوي (N) موصولةً، نحو 10 ث
    narr = [b['id'] for b in blocks.values() if b.get('role') == 'N' and not b.get('reel_only')][:4]
    lst = os.path.join(out, 'ref.txt')
    open(lst, 'w').write(''.join("file '%s'\n" % os.path.abspath(os.path.join(proj, 'audio', i + '.wav')) for i in narr))
    ref = os.path.join(out, 'ref.wav')
    sp.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-ac', '1', '-ar', '24000', ref], check=True)
    model = ChatterboxMultilingualTTS.from_pretrained(device='cpu', t3_model='v3')
    key, rnd, log = {}, random.Random(20261103), []
    for i in ids:
        text = blocks[i]['text']
        for tag, t in (('tashkeel', text), ('bare', TASHKEEL.sub('', text))):
            t0 = time.time()
            torch.manual_seed(7)
            w = model.generate(t, language_id='ar', audio_prompt_path=ref, exaggeration=0.5, cfg_weight=0.5)
            f = os.path.join(out, 'cb_%s_%s.wav' % (i, tag))
            ta.save(f, w, model.sr)
            log.append({'id': i, 'variant': tag, 'sec': round(time.time() - t0, 1)})
            print(i, tag, log[-1]['sec'], flush=True)
        # الزوج الأعمى: Gemini الأصل مقابل Chatterbox بالتشكيل، بالجهارة نفسها
        pair = [('gemini', os.path.join(proj, 'audio', i + '.wav')), ('chatterbox', os.path.join(out, 'cb_%s_tashkeel.wav' % i))]
        rnd.shuffle(pair)
        key[i] = {'أ': pair[0][0], 'ب': pair[1][0], 'text': text}
        for lab, (_, src) in zip(('A', 'B'), pair):
            sp.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-af', 'loudnorm=I=-16:TP=-1.5', '-ac', '1', '-ar', '44100', '-b:a', '128k',
                    os.path.join(out, 'pair_%s_%s.mp3' % (i, lab))], check=True)
    json.dump(key, open(os.path.join(out, 'blind_key.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(log, open(os.path.join(out, 'gen_log.json'), 'w'), indent=1)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3].split(','))
