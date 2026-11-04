#!/usr/bin/env python3
"""أزمنة الكلمات المسموعة للكتابة المتحرّكة (أمر المالك 2026-11-04: «طبّق توقيت الكلمات المسموعة»).

لماذا؟ تجربة 2026-11-03 على صوت جرجة (759 كلمة، tools/exp/timing.py): تقديرُ kinetic.block_word_times من الصمت وعدد
الحروف يُظهر الكلمة **بعد** نطقها بوسيط 0.20 ث، و36٪ من الكلمات تتأخّر أكثر من ربع ثانية، وبعضها أكثر من ثانية.
هنا يُسمع صوت كلّ كتلةٍ بـfaster-whisper (word_timestamps، بنصّ الكتلة تلميحاً) ويُحفظ زمن كلّ كلمةٍ معروضة في
audio/wordtimes.json، فيُحمل مع حالة الشوط (⑤ يحفظ audio/ كلّه)، وتقرؤه kinetic.block_word_times إن طابقت بصمةُ الصوت.

- لكلّ كتلةٍ بصمةُ ملفّها: الكتلة المعاد توليدها تُعاد، والباقي لا يُسمع مرّتين.
- الكلمة التي لم يطابقها السمع تأخذ زمن التقدير مزاحاً بإزاحة جارتيها المسموعتين.
- إن طابق السمعُ أقلّ من 60٪ من كلمات الكتلة فلا يُحفظ لها شيء، وتبقى على التقدير (لا شيء أسوأ مما كان).
- بلا نداءٍ مدفوع ولا حصّة: النموذج محلّيّ على العدّاء، ونحو 27 د لفيلمٍ من 109 كتل بـlarge-v3.

    python tools/wordtimes.py <مجلد المشروع> [--model large-v3]
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kinetic  # noqa: E402

TASHKEEL = re.compile('[ؐ-ًؚ-ٰٟۖ-ۭـ]')
MIN_MATCH = 0.6


def norm(w: str) -> str:
    w = TASHKEEL.sub('', w)
    w = re.sub('[^ء-ي]', '', w)
    return re.sub('[أإآٱ]', 'ا', w).replace('ة', 'ه').replace('ى', 'ي')


def sha(f: str) -> str:
    return hashlib.sha256(open(f, 'rb').read()).hexdigest()[:16]


def merge(est: list, heard: list) -> tuple[list, float]:
    """كلمات التقدير المعروضة بأزمنة السمع حيث طابقت، والباقي بإزاحة الجارتين."""
    a, c = [norm(w) for w, _, _ in est], [norm(w) for w, _, _ in heard]
    sm = difflib.SequenceMatcher(None, a, c, autojunk=False)
    hit = {}
    for i, j, n in sm.get_matching_blocks():
        for k in range(n):
            hit[i + k] = heard[j + k]
    if not est:
        return [], 0.0
    out = []
    for i, (w, s, e) in enumerate(est):
        if i in hit:
            out.append([w, round(hit[i][1], 3), round(max(hit[i][2], hit[i][1] + 0.05), 3)])
            continue
        prev = next((hit[k][1] - est[k][1] for k in range(i - 1, -1, -1) if k in hit), None)
        nxt = next((hit[k][1] - est[k][1] for k in range(i + 1, len(est)) if k in hit), None)
        offs = [x for x in (prev, nxt) if x is not None]
        d = sum(offs) / len(offs) if offs else 0.0
        out.append([w, round(max(0.0, s + d), 3), round(max(0.05, e + d), 3)])
    # أزمنةٌ لا ترجع إلى الوراء
    for i in range(1, len(out)):
        if out[i][1] < out[i - 1][1]:
            out[i][1] = out[i - 1][1]
    return out, len(hit) / len(est)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('proj')
    ap.add_argument('--model', default=os.environ.get('WORDTIMES_MODEL', 'large-v3'))
    a = ap.parse_args(argv)
    blocks = json.load(open(os.path.join(a.proj, 'blocks.json'), encoding='utf-8'))
    adir = os.path.join(a.proj, 'audio')
    dst = os.path.join(adir, 'wordtimes.json')
    old = json.load(open(dst, encoding='utf-8')) if os.path.exists(dst) else {}
    todo = []
    for b in blocks:
        f = os.path.join(adir, b['id'] + '.wav')
        if os.path.exists(f) and (old.get(b['id']) or {}).get('sha') != sha(f):
            todo.append((b, f))
    print('أزمنة الكلمات: %d كتلة تُسمع، و%d محفوظة' % (len(todo), len(old)), flush=True)
    if not todo:
        return 0
    from faster_whisper import WhisperModel
    m = WhisperModel(a.model, device='cpu', compute_type='int8', cpu_threads=os.cpu_count() or 4)
    t0, kept, skipped = time.time(), 0, []
    for b, f in todo:
        est = kinetic.block_word_times(b['text'], f, kinetic._dur(f), heard=False)
        segs, _ = m.transcribe(f, language='ar', beam_size=5, word_timestamps=True, vad_filter=False,
                               initial_prompt=TASHKEEL.sub('', b['text']))
        heard = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
        words, ratio = merge(est, heard)
        if ratio < MIN_MATCH:
            old.pop(b['id'], None); skipped.append(b['id']); continue
        old[b['id']] = {'sha': sha(f), 'match': round(ratio, 2), 'words': words}
        kept += 1
        # يُحفظ بعد كلّ كتلة: انقطاع الشوط لا يضيّع ما سُمع
        json.dump(old, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(old, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
    print('أزمنة الكلمات: حُفظت %d كتلة في %d ث%s' % (kept, time.time() - t0,
          ('، وبقيت على التقدير %s (سمعٌ ضعيف)' % ' '.join(skipped)) if skipped else ''), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
