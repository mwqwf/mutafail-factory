#!/usr/bin/env python3
"""تجربة التوقيت (أمر المالك 2026-11-03: «ابدأ تجربتي التوقيت وChatterbox»).
تقارن زمن ظهور كلّ كلمةٍ كما يقدّره tools/kinetic.py (الصمت + عدد الحروف) بزمنها كما يسمعه faster-whisper
(word_timestamps) على صوت الكتلة النظيف نفسه. لا توليد ولا إنفاق، ولا تغيير في المحرّك.
    python tools/exp/timing.py <مجلد المشروع: blocks.json وaudio/> <ملفّ الناتج.json>
"""
import difflib, json, os, re, statistics, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import kinetic  # noqa: E402

TASHKEEL = re.compile('[ؐ-ًؚ-ٰٟۖ-ۭـ]')
def norm(w):
    w = TASHKEEL.sub('', w)
    w = re.sub('[^ء-ي]', '', w)
    w = re.sub('[أإآٱ]', 'ا', w).replace('ة', 'ه').replace('ى', 'ي')
    return w

def main(proj, out):
    from faster_whisper import WhisperModel
    m = WhisperModel(os.environ.get('ASR_MODEL', 'large-v3'), device='cpu', compute_type='int8', cpu_threads=4)
    blocks = [b for b in json.load(open(os.path.join(proj, 'blocks.json'), encoding='utf-8')) if not b.get('reel_only')]
    res, t0 = [], time.time()
    for b in blocks:
        wav = os.path.join(proj, 'audio', b['id'] + '.wav')
        if not os.path.exists(wav):
            continue
        dur = kinetic._dur(wav) if hasattr(kinetic, '_dur') else 0.0
        est = kinetic.block_word_times(b['text'], wav, dur)
        segs, _ = m.transcribe(wav, language='ar', beam_size=5, word_timestamps=True, vad_filter=False,
                               initial_prompt=TASHKEEL.sub('', b['text']))
        asr = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
        a, c = [norm(w) for w, _, _ in est], [norm(w) for w, _, _ in asr]
        sm = difflib.SequenceMatcher(None, a, c, autojunk=False)
        pairs = []
        for i, j, n in sm.get_matching_blocks():
            for k in range(n):
                e, r = est[i + k], asr[j + k]
                pairs.append({'w': e[0], 'est': round(e[1], 3), 'asr': round(r[1], 3), 'd': round(e[1] - r[1], 3)})
        res.append({'id': b['id'], 'dur': round(dur, 2), 'words': len(est), 'matched': len(pairs), 'pairs': pairs})
        print(b['id'], len(est), len(pairs), flush=True)
    d = [abs(p['d']) for r in res for p in r['pairs']]
    summ = {'blocks': len(res), 'words': sum(r['words'] for r in res), 'matched': len(d),
            'median_abs_s': round(statistics.median(d), 3) if d else None,
            'p90_abs_s': round(sorted(d)[int(len(d) * .9)], 3) if d else None,
            'share_gt_0.15': round(sum(x > .15 for x in d) / len(d), 3) if d else None,
            'share_gt_0.25': round(sum(x > .25 for x in d) / len(d), 3) if d else None,
            'share_gt_0.40': round(sum(x > .40 for x in d) / len(d), 3) if d else None,
            'seconds': round(time.time() - t0)}
    worst = sorted(((abs(p['d']), r['id'], p['w'], p['est'], p['asr']) for r in res for p in r['pairs']), reverse=True)[:25]
    json.dump({'summary': summ, 'worst': worst, 'blocks': res}, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(summ, ensure_ascii=False))

if __name__ == '__main__':
    main(*sys.argv[1:3])
