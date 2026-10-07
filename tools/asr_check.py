# -*- coding: utf-8 -*-
"""تحكيم رايات الإصغاء بتفريغٍ مستقلّ محلّيّ (faster-whisper large-v3) — بلا أيّ نداءٍ لجيميناي ولا حصّة.

درس مؤتة 2026-10-06: رفع الإصغاء 18 رايةً، أغلبها وقفٌ صحيح أو مخرجاتٌ مضطربة من نموذج الإصغاء نفسه،
وفيها ما يقلب المعنى إن صحّ (n_027 «ولم يُقتَلْ لِرسولِ الله ﷺ»). فالحكم من الصوت نفسه لا من قول الإصغاء:

  python3 tools/asr_check.py transcribe audio/n_003.wav audio/n_027.wav
      تفريغٌ حرٌّ كلمةً كلمة (بلا نصٍّ مسبق).
  python3 tools/asr_check.py score audio/n_027.wav "ولم يقتل لرسول الله" "ولم يقتل رسول الله"
      احتمال كلّ قراءةٍ بالإملاء القسريّ (محاذاة النموذج): مجموع اللوغ للقراءة كلّها، ومتوسّط كلّ كلمة.
      الفارق الكبير حاسم (n_003: «كالموج» −0.04 و«كالموت» −12.8)، والصغير غير حاسم فيُعاد التوليد أو يُسمّى للمالك.

القراءات بلا تشكيل، كما يكتب النموذج. والنموذج (نحو 3 غ.ب) يُنزَّل مرّةً إلى ذاكرة huggingface.
"""
import sys


def model():
    from faster_whisper import WhisperModel
    return WhisperModel('large-v3', device='cpu', compute_type='int8', cpu_threads=4)


def transcribe(paths):
    m = model()
    for f in paths:
        segs, _ = m.transcribe(f, language='ar', beam_size=5, word_timestamps=True, vad_filter=False,
                               condition_on_previous_text=False, temperature=0.0)
        print(f, '⇐', ' '.join(w.word.strip() for s in segs for w in (s.words or [])), flush=True)


def score(path, cands):
    import numpy as np
    from faster_whisper.audio import decode_audio
    from faster_whisper.tokenizer import Tokenizer
    m = model()
    tok = Tokenizer(m.hf_tokenizer, True, task='transcribe', language='ar')
    feats = m.feature_extractor(decode_audio(path, sampling_rate=16000))
    nfr = feats.shape[-1]
    if nfr < 3000:
        feats = np.pad(feats, ((0, 0), (0, 3000 - nfr)))
    enc = m.encode(feats[:, :3000])
    print('==', path)
    for c in cands:
        ids = tok.encode(' ' + c)
        p = np.array(m.model.align(enc, tok.sot_sequence, [ids], min(nfr, 3000) // 2)[0].text_token_probs[:len(ids)])
        words, wt = tok.split_to_word_tokens(ids + [tok.eot])
        k, ws = 0, []
        for w, t in zip(words, wt):
            if t and w.strip():
                ws.append('%s:%.2f' % (w.strip(), float(np.mean(p[k:k + len(t)]))))
            k += len(t)
        print('  مجموع اللوغ %.2f | %s' % (float(np.sum(np.log(p + 1e-9))), c))
        print('    ', ' '.join(ws), flush=True)


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'transcribe':
        transcribe(sys.argv[2:])
    elif len(sys.argv) >= 5 and sys.argv[1] == 'score':
        score(sys.argv[2], sys.argv[3:])
    else:
        sys.exit(__doc__)
