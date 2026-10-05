# -*- coding: utf-8 -*-
"""المقارنة العمياء — هل يغلب نصُّنا نصوصَ الناجحين قبل أن نُنفق شيئاً؟ (دراسة مؤتة §٢ و§١٠)

قال المالك 2026-10-05: «التحميس والتشويق والأكشن… كلّ مرّةٍ أشدّد عليها وفي كلّ مرّةٍ النتائج متقاربة، لا توجد قفزة واضحة».
كان الحكم على الحماسة بذوق كاتبها. هذه الأداة تجعل الحكم من خارجه:
- مقاطعُ من نصّنا: الافتتاحية، والدقائق 1–6 (موضع النزيف في منحنياتنا)، ومشاهد الأكشن.
- بجانبها مقاطعُ في الموضع نفسه من تفريغ أنجح أفلامهم (style.json من الإصدار الخاصّ، تكتبه tools/style_study.py).
- بلا أسماءٍ ولا قنوات، وبطولٍ متساوٍ بالكلمات، وبلا تشكيل في الجانبين.
- يحكم نموذجان مختلفان، ويُعاد كلُّ حكمٍ بعد تبديل الترتيب (A/B ثم B/A)، والسؤال: أيّهما يجعلك تكمل؟
- **المعايرة:** تُحكَّم بالطريقة نفسها مقاطعُ من أفلامنا المنشورة، ومنحنياتها نعرفها. فإن غلبت هي أيضاً فالحَكَم لا يميّز،
  ولا يُبنى على حكمه.
- **الشرط قبل الإنفاق:** نسبة الفوز ≥ 70٪ في كلّ نوعٍ من مقاطع المسوّدة.

الطلب في ops/stats/judge.json:
{"المسوّدة": [{"id", "النوع": "opening|danger|action", "النصّ"}],
 "المنافسون": [ids من style.json] (اختياريّ: الافتراضيّ كلّ أفلام «منافس»)، "المعايرة": [ids من أفلامنا في style.json]}
الاستعمال: python tools/blind_judge.py <out.json> --keys /tmp/keys.json --style /tmp/style.json
⛔ نصوص المنافسين محميّة: التقرير إلى الإصدار المسوّد الخاصّ وحده، ولا يُطبع منها شيءٌ في السجلّ العامّ."""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from openings import Gem, MODELS  # noqa: E402
from voice_lab import keys_from  # noqa: E402
from style_study import norm_ts  # noqa: E402  — [12:34] ⇒ [754]: نصف التفريغات بالدقائق

HARAKAT = re.compile(r"[ً-ْٰـ]")
LINE = re.compile(r"^\s*\[(\d+(?:\.\d+)?)\]\s*(?:\(([^)]*)\))?\s*(.+)$")
WINDOWS = {'opening': (0, 150), 'danger': (60, 240)}      # والأكشن من نافذة الأكشن الأشدّ في style.json
KIND_AR = {'opening': 'أوّل دقيقتين ونصف من الفيلم', 'danger': 'من الدقيقة الأولى إلى الرابعة',
           'action': 'مشهد قتالٍ في قلب المعركة'}
MAX_WORDS = {'opening': 320, 'danger': 420, 'action': 220}
WIN_MIN = 0.70
JUDGES = 2          # نموذجان مختلفان من سلسلة MODELS

PROMPT = """أنت مشاهدٌ عربيٌّ عاديّ يحبّ قصص التاريخ، يتصفّح يوتيوب. أمامك نصّان مفرّغان من فيلمين وثائقيّين مختلفين — الكلام المنطوق
وحده بلا صورة — وكلاهما من الموضع نفسه في فيلمه: {where}. اقرأهما كأنّك تسمعهما بصوت راوٍ.
أيّهما يجعلك تكمل المشاهدة أكثر؟ لا تحكم بكثرة المعلومات ولا بفصاحة اللغة، بل بالشدّ: الخطر، والحركة، والفضول، والإحساس،
وهل تريد أن تعرف ما بعده. أجب بـJSON وحده:
{{"winner": "A" أو "B", "margin": 1 أو 2 أو 3 (فرقٌ طفيف أو واضح أو كبير), "why": "سطران بالعربية",
 "a_strengths": ["…"], "b_strengths": ["…"], "fix_for_loser": "ما الذي يجعل الخاسر يغلب، محدّداً قابلاً للتطبيق"}}

النصّ A:
{a}

النصّ B:
{b}"""


def plain(t: str) -> str:
    return re.sub(r"\s+", " ", HARAKAT.sub("", t or "")).strip()


def lines(transcript: str) -> list[tuple[float, str]]:
    out = []
    for ln in norm_ts(transcript or "").splitlines():
        m = LINE.match(ln)
        if m:
            out.append((float(m.group(1)), m.group(3).strip()))
    return out


def clip(text: str, n: int) -> str:
    w = plain(text).split()
    return " ".join(w[:n])


def segments(film: dict) -> dict:
    """مقاطع فيلمٍ من style.json بأنواعها: الافتتاحية والدقائق 1–4 من التفريغ، والأكشن من نافذته الأشدّ."""
    ls = lines(film.get('transcript', ''))
    seg = {}
    for k, (a, b) in WINDOWS.items():
        t = " ".join(x for s, x in ls if a <= s < b)
        if len(t.split()) >= 40:
            seg[k] = t
    act = film.get('action') or {}
    t = act.get('narration') or ''
    if len(plain(t).split()) < 40 and act.get('from') is not None:
        t = " ".join(x for s, x in ls if act['from'] <= s < act.get('to', act['from'] + 90))
    if len(plain(t).split()) >= 40:
        seg['action'] = t
    return seg


def body(a: str, b: str, kind: str) -> bytes:
    cfg = {'temperature': 0.2, 'responseMimeType': 'application/json'}
    txt = PROMPT.format(where=KIND_AR[kind], a=a, b=b)
    return json.dumps({'contents': [{'parts': [{'text': txt}]}], 'generationConfig': cfg}).encode('utf-8')


def duel(g, ours: str, theirs: str, kind: str, tag: str, judges: list[list[str]]) -> list[dict]:
    """حكمان لكلّ نموذج: نصّنا A ثم B. ويُسجَّل لكلٍّ هل فاز نصّنا وبأيّ فرق."""
    n = min(len(plain(ours).split()), len(plain(theirs).split()), MAX_WORDS[kind])
    a_, b_ = clip(ours, n), clip(theirs, n)
    res = []
    for models in judges:
        for ours_first in (True, False):
            a, b = (a_, b_) if ours_first else (b_, a_)
            r = g.call(lambda light, a=a, b=b: body(a, b, kind), tag, budget_s=180, models=models)
            if 'error' in r:
                res.append({'error': r['error'][:160], 'ours_first': ours_first}); continue
            win = str(r.get('winner', '')).strip().upper()[:1]
            res.append({'model': r.get('_model'), 'ours_first': ours_first, 'win': (win == 'A') == ours_first,
                        'margin': r.get('margin'), 'why': r.get('why'), 'fix_for_loser': r.get('fix_for_loser'),
                        'ours_strengths': r.get('a_strengths' if ours_first else 'b_strengths'),
                        'their_strengths': r.get('b_strengths' if ours_first else 'a_strengths')})
    return res


def rate(rows: list[dict]) -> float | None:
    ok = [r for r in rows if 'error' not in r]
    return round(sum(r['win'] for r in ok) / len(ok), 2) if ok else None


def run(req: dict, style: dict, g, workers: int = 6) -> dict:
    films = {f['id']: f for f in style.get('الأفلام') or [] if 'error' not in f}
    comp_ids = req.get('المنافسون') or [i for i, f in films.items() if f.get('الجهة') == 'منافس']
    comp = {i: segments(films[i]) for i in comp_ids if i in films}
    # الحَكَمان: أوّل نموذجين مختلفين يصلحان من السلسلة (كلٌّ بسلسلته البديلة إن نفدت حصّته)
    judges = [MODELS[k:] + MODELS[:k] for k in range(JUDGES)]
    jobs = []
    for d in req.get('المسوّدة') or []:
        for cid, seg in comp.items():
            if d['النوع'] in seg:
                jobs.append(('المسوّدة', d['id'], d['النوع'], d['النصّ'], cid, seg[d['النوع']]))
    for oid in req.get('المعايرة') or []:
        mine = segments(films.get(oid, {}))
        for kind, text in mine.items():
            for cid, seg in list(comp.items())[:4]:
                if kind in seg:
                    jobs.append(('المعايرة', oid, kind, text, cid, seg[kind]))
    out = {'المسوّدة': {}, 'المعايرة': {}}
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(duel, g, o, t, k, '%s:%s/%s' % (sid, k, cid), judges): (grp, sid, k, cid)
                for grp, sid, k, o, cid, t in jobs}
        for fu in cf.as_completed(futs):
            grp, sid, k, cid = futs[fu]
            out[grp].setdefault(sid, {}).setdefault(k, {})[cid] = fu.result()
    summary = {}
    for grp, items in out.items():
        for sid, kinds in items.items():
            for k, by in kinds.items():
                rows = [r for v in by.values() for r in v]
                summary.setdefault(grp, {}).setdefault(sid, {})[k] = {
                    'نسبة_الفوز': rate(rows), 'الأحكام': sum('error' not in r for r in rows),
                    'أخطاء': sum('error' in r for r in rows)}
    gate = {sid: all((v['نسبة_الفوز'] or 0) >= WIN_MIN for v in kinds.values())
            for sid, kinds in summary.get('المسوّدة', {}).items()}
    return {'تاريخ': dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'), 'الشرط': WIN_MIN, 'الخلاصة': summary,
            'تجتاز': gate, 'التفصيل': out}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--keys', required=True)
    ap.add_argument('--style', required=True, help='style.json من الإصدار الخاصّ')
    ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args()
    keys = keys_from(a.keys)
    if not keys:
        print('⛔ لا مفاتيح جيميناي'); return 1
    req = json.load(io.open(os.path.join('ops', 'stats', 'judge.json'), encoding='utf-8'))
    style = json.load(io.open(a.style, encoding='utf-8'))
    rep = run(req, style, Gem(keys), a.workers)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(rep, io.open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for grp, items in rep['الخلاصة'].items():                 # نسبٌ وحدها في السجلّ العامّ، لا نصوص
        for sid, kinds in items.items():
            print(grp, sid, ' · '.join('%s=%s (%d حكماً)' % (k, v['نسبة_الفوز'], v['الأحكام']) for k, v in kinds.items()))
    print('تجتاز:', rep['تجتاز'])
    return 0 if rep['الخلاصة'] else 1


if __name__ == '__main__':
    sys.exit(main())
