# -*- coding: utf-8 -*-
"""المقارنة العمياء، الإصدار الثاني: هل يغلب نصُّنا نصوصَ الناجحين قبل أن ننفق شيئاً؟ وهل الحَكَم يميّز أصلاً؟

قال المالك 2026-10-05: «التحميس والتشويق والأكشن… كلّ مرّةٍ أشدّد عليها وفي كلّ مرّةٍ النتائج متقاربة، لا توجد قفزة واضحة».
الإصدار الأوّل كان قابلاً للخداع من بنيته. وما تغيّر بحكم المراجعة الناقدة (ops/research/mutah/00-retention-plan.md §١٠):
- **صلاحية الحَكَم أوّلاً:** مقاطع من أفلامنا هبط عندها المنحنى مقابل مقاطع ثبت عندها، من الفيلم نفسه.
  - الهبوط والثبات بتغيّر الأداء النسبيّ ليوتيوب (relativeRetentionPerformance) في النافذة، فلا يغلب أثرُ الموضع.
  - فإن لم يختر الحَكَم مقطع الثبات في ≥ 65٪ من ثمانية أزواجٍ فأكثر، فحكمه للاطلاع، ولا يُبنى عليه شيء.
- **التكافؤ:** يُنزع التشكيل والترقيم وعبارات القنوات وأسماؤها من الطرفين، ويُساوى الطول بالكلمات.
- **الحَكَم:**
  - سلسلتا نماذج منفصلتان لا تشتركان في اسم، ويُبطَل الحكم إن تطابق النموذج فيهما.
  - والحكم الذي ينقلب بتبديل الترتيب تعادل.
  - والسؤال لا يلقّن معياراً، ولا «ما الذي يجعل الخاسر يغلب».
- **ضدّ التفصيل على ذوق الحَكَم:**
  - المرجع أفلامٌ تشبهنا شكلاً، وهو نصفان: نصفٌ للتطوير يُحفظ سببُ حكمه، ونصفٌ للبوّابة تُحفظ نتيجته وحدها.
  - وثلاث محاولاتٍ على الأكثر للمسوّدة الواحدة.
  - وفحصُ تداخلٍ لفظيٍّ بين نصّنا وتفريغاتهم، بلا ما بين «»، أي بلا نصوص المصادر المقتبسة.
- **الشرط في الشيفرة:** يجتمع فيه:
  - حَكَمٌ صالح.
  - وفوز المسوّدة ≥ 70٪.
  - وفوز أفلامنا السابقة ≤ 40٪ على المنافسين أنفسهم.
  - والفرق ≥ 25 نقطة.
  - والأحكام الصالحة ≥ 90٪ من المخطّط.
  - والتداخل ≤ 3٪.

الطلب في ops/stats/judge.json:
{"المحاولة": 1, "المرجع": [ids], "السقف": [ids للاطلاع], "المعايرة": [ids أفلامنا],
 "المسوّدة": [{"id", "النوع": "opening|danger|action", "النصّ"}]}
الاستعمال: python tools/blind_judge.py <out.json> --keys K --style style.json --stats channel_stats.json
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
from openings import Gem  # noqa: E402
from voice_lab import keys_from  # noqa: E402
from style_study import norm_ts  # noqa: E402  — [12:34] ⇒ [754]: نصف التفريغات بالدقائق

HARAKAT = re.compile(r"[ً-ْٰـ]")
PUNCT = re.compile(r"[؟?!.,،؛;:«»\"'()\[\]{}…—–\-]+")
QUOTED = re.compile(r"«[^»]*»")
CHANNEL = re.compile(r"(اشترك|اشتركوا|الجرس|قناتنا|القناة|متابعينا|المتابعين|لايك|الإعجاب|السلام عليكم|أهلا بكم|مرحبا)")
LINE = re.compile(r"^\s*\[(\d+(?:\.\d+)?)\]\s*(?:\(([^)]*)\))?\s*(.+)$")
WINDOWS = {'opening': (0, 150), 'danger': (60, 240)}      # والأكشن من نافذة الأكشن الأشدّ في style.json
KIND_AR = {'opening': 'أوّل دقيقتين ونصف من الفيلم', 'danger': 'من الدقيقة الأولى إلى الرابعة',
           'action': 'مشهد قتالٍ في قلب المعركة', 'calib': 'موضعان من وسط الفيلم نفسه'}
MAX_WORDS = {'opening': 320, 'danger': 420, 'action': 220, 'calib': 160}
# سلسلتان لا تشتركان في اسم: إن نفدت حصّة نموذجٍ انتقل الحَكَم إلى التالي في سلسلته وحدها
JUDGE_CHAINS = (['gemini-3.5-flash', 'gemini-3.5-pro', 'gemini-3.5-flash-lite'],
                ['gemini-3.8-flash', 'gemini-pro-latest', 'gemini-flash-lite-latest'])
WIN_MIN, OLD_MAX, GAP_MIN, VALID_MIN = 0.70, 0.40, 0.25, 0.90
ACC_MIN, PAIRS_MIN, PAIRS_PER_FILM = 0.65, 8, 2
MAX_ROUNDS, NGRAM, OVERLAP_MAX = 3, 5, 0.03

PROMPT = """أنت مشاهدٌ عربيٌّ عاديّ يتصفّح يوتيوب. أمامك نصّان مفرّغان من كلامٍ منطوق في فيلمٍ وثائقيٍّ تاريخيّ، بلا صورة،
وكلاهما من الموضع نفسه: {where}. اقرأهما كأنّك تسمعهما.
أيّهما يجعلك تكمل المشاهدة أكثر؟ أجب بـJSON وحده: {{"winner": "A" أو "B", "why": "سطرٌ واحد بالعربية"}}

النصّ A:
{a}

النصّ B:
{b}"""


def plain(t: str) -> str:
    """بلا تشكيلٍ ولا ترقيم: نصّنا المكتوب وتفريغهم الآليّ على هيئةٍ واحدة."""
    return re.sub(r"\s+", " ", PUNCT.sub(" ", HARAKAT.sub("", t or ""))).strip()


def lines(transcript: str) -> list[tuple[float, str]]:
    out = []
    for ln in norm_ts(transcript or "").splitlines():
        m = LINE.match(ln)
        if m and not CHANNEL.search(m.group(3)):
            out.append((float(m.group(1)), m.group(3).strip()))
    return out


def scrub(text: str, names: list[str]) -> str:
    for n in names:
        if n:
            text = text.replace(n, " ")
    return plain(text)


def clip(text: str, n: int) -> str:
    return " ".join(plain(text).split()[:n])


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


def channel_names(style: dict) -> list[str]:
    """أسماء القنوات من الوسم («المواطن سعيد: غزوة مؤتة» ⇒ «المواطن سعيد») لتُنزع من النصوص."""
    return sorted({f.get('الوسم', '').split(':')[0].strip() for f in style.get('الأفلام') or [] if ':' in f.get('الوسم', '')},
                  key=len, reverse=True)


# ———— صلاحية الحَكَم: الهبوط والثبات على منحنياتنا ————
def calib_pairs(film: dict, curve: list, length: float) -> list[tuple[str, str, float, float]]:
    """أزواج (ثبات، هبوط) من الفيلم نفسه.
    - النافذة دقيقةٌ أو أكثر (نقطتان من المنحنى على الأقلّ).
    - الهبوط والثبات بتغيّر الأداء النسبيّ ليوتيوب فيها، فلا يحكم الموضع: الهبوط في الدقيقة الأولى طبيعيٌّ في كلّ فيلم.
    - النوافذ بين الثانية 60 و85٪ من الطول، ولا تتداخل."""
    ls = lines(film.get('transcript', ''))
    pts = [(p[0] * length, p[2]) for p in curve if isinstance(p, (list, tuple)) and len(p) >= 3 and p[2] is not None]
    if len(ls) < 20 or len(pts) < 20 or not length:
        return []
    win = max(60.0, 2.5 * length / 100.0)
    rel = lambda t: min(pts, key=lambda q: abs(q[0] - t))[1]
    cands = []
    t = 60.0
    while t + win <= 0.85 * length:
        txt = " ".join(x for s, x in ls if t <= s < t + win)
        if len(txt.split()) >= 60:
            cands.append((rel(t + win) - rel(t), t, txt))
        t += win / 2
    cands.sort()
    used, drops, holds = [], [], []

    def free(t0):
        return all(abs(t0 - u) >= win for u in used)
    for d, t0, txt in cands:                       # الأشدّ هبوطاً أوّلاً
        if d < 0 and free(t0) and len(drops) < PAIRS_PER_FILM:
            drops.append((t0, txt)); used.append(t0)
    for d, t0, txt in reversed(cands):             # والأثبت
        if d > 0 and free(t0) and len(holds) < PAIRS_PER_FILM:
            holds.append((t0, txt)); used.append(t0)
    return [(h[1], dr[1], h[0], dr[0]) for h, dr in zip(holds, drops)]


# ———— الحكم ————
def body(a: str, b: str, kind: str) -> bytes:
    cfg = {'temperature': 0.2, 'responseMimeType': 'application/json'}
    txt = PROMPT.format(where=KIND_AR[kind], a=a, b=b)
    return json.dumps({'contents': [{'parts': [{'text': txt}]}], 'generationConfig': cfg}).encode('utf-8')


def unit(g, x: str, y: str, kind: str, tag: str, chain: list[str]) -> dict:
    """حَكَمٌ واحد بالترتيبين. score لـx: 1 إن اختاره فيهما، و0 إن اختار y فيهما، و0.5 إن انقلب بالترتيب."""
    picks, models, why = [], [], []
    for x_first in (True, False):
        a, b = (x, y) if x_first else (y, x)
        r = g.call(lambda light, a=a, b=b: body(a, b, kind), tag, budget_s=180, models=chain)
        if 'error' in r:
            return {'error': str(r['error'])[:160]}
        w = str(r.get('winner', '')).strip().upper()[:1]
        if w not in ('A', 'B'):
            return {'error': 'حكمٌ بلا فائز'}
        picks.append((w == 'A') == x_first)
        models.append(r.get('_model'))
        why.append(r.get('why'))
    score = 1.0 if all(picks) else 0.0 if not any(picks) else 0.5
    return {'score': score, 'flip': score == 0.5, 'models': models, 'why': why}


def duel(g, x: str, y: str, kind: str, tag: str, keep_why: bool = True) -> list[dict]:
    """الحَكَمان على زوجٍ واحد. ويُبطَلان إن تطابق نموذجاهما (نفدت حصّةٌ فالتقت السلسلتان على اسمٍ واحد)."""
    n = min(len(plain(x).split()), len(plain(y).split()), MAX_WORDS[kind])
    x_, y_ = clip(x, n), clip(y, n)
    res = [unit(g, x_, y_, kind, '%s#%d' % (tag, i), chain) for i, chain in enumerate(JUDGE_CHAINS)]
    ok = [r for r in res if 'error' not in r]
    if len(ok) == 2 and set(ok[0]['models']) & set(ok[1]['models']):
        res = [{'error': 'الحَكَمان نموذجٌ واحد'} for _ in res]
    if not keep_why:
        for r in res:
            r.pop('why', None)
    return res


def rate(rows: list[dict]) -> float | None:
    ok = [r for r in rows if 'error' not in r]
    return round(sum(r['score'] for r in ok) / len(ok), 2) if ok else None


def valid_share(rows: list[dict]) -> float:
    return round(sum('error' not in r for r in rows) / len(rows), 2) if rows else 0.0


def grams(t: str) -> set:
    w = plain(QUOTED.sub(" ", t or "")).split()
    return {" ".join(w[i:i + NGRAM]) for i in range(len(w) - NGRAM + 1)}


def overlap(draft: str, texts: list[str]) -> float:
    """نسبة خماسيّات المسوّدة الموجودة في تفريغاتهم (بلا ما بين «»): ألّا نقلّد لفظاً محميّاً."""
    mine = grams(draft)
    if not mine:
        return 0.0
    theirs = set().union(*[grams(t) for t in texts]) if texts else set()
    return round(len(mine & theirs) / len(mine), 3)


def run(req: dict, style: dict, stats: dict | None, g, workers: int = 6) -> dict:
    films = {f['id']: f for f in style.get('الأفلام') or [] if 'error' not in f}
    names = channel_names(style)
    ref = [i for i in (req.get('المرجع') or [i for i, f in films.items() if f.get('الجهة') == 'منافس']) if i in films]
    ref = sorted(ref)
    dev, hold = ref[0::2], ref[1::2]
    ceiling = [i for i in req.get('السقف') or [] if i in films]
    seg = {i: {k: scrub(v, names) for k, v in segments(films[i]).items()} for i in set(ref) | set(ceiling)}
    jobs = []                                           # (المجموعة، المعرّف، النوع، نصّنا، المقابل، احفظ السبب؟)
    # ١. صلاحية الحَكَم
    curves = ((stats or {}).get('الحقيقة') or {}).get('منحنى_البقاء_الطبيعي') or {}
    lengths = {v['id']: v.get('الطول_ث') for v in ((stats or {}).get('الحقيقة') or {}).get('لكل_فيديو') or []}
    for oid in req.get('المعايرة') or []:
        if oid in films and isinstance(curves.get(oid), list):
            for k, (h, d, th, td) in enumerate(calib_pairs(films[oid], curves[oid], lengths.get(oid) or 0)):
                jobs.append(('الصلاحية', '%s@%d/%d' % (oid, th, td), 'calib', scrub(h, names), scrub(d, names), True))
    # ٢. أفلامنا السابقة على نصف البوّابة: خطّ الأساس
    for oid in req.get('المعايرة') or []:
        for kind, text in segments(films.get(oid, {})).items():
            for cid in hold:
                if kind in seg.get(cid, {}):
                    jobs.append(('أفلامنا', oid + '/' + kind, kind, scrub(text, names), seg[cid][kind], False))
    # ٣. المسوّدة: نصف التطوير بأسبابه، ونصف البوّابة بنتيجته وحدها، والسقف للاطلاع
    for d in req.get('المسوّدة') or []:
        k = d['النوع']
        for grp, ids, why in (('المسوّدة_تطوير', dev, True), ('المسوّدة_بوّابة', hold, False), ('المسوّدة_سقف', ceiling, False)):
            for cid in ids:
                if k in seg.get(cid, {}):
                    jobs.append((grp, d['id'] + '/' + k, k, d['النصّ'], seg[cid][k], why))
    rows = {}
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(duel, g, x, y, k, '%s:%s' % (grp, sid), why): (grp, sid) for grp, sid, k, x, y, why in jobs}
        for fu in cf.as_completed(futs):
            grp, sid = futs[fu]
            rows.setdefault(grp, {}).setdefault(sid, []).extend(fu.result())
    flat = lambda grp, pref=None: [r for sid, v in rows.get(grp, {}).items() if pref is None or sid.startswith(pref) for r in v]
    pairs = len(rows.get('الصلاحية', {}))
    acc, acc_valid = rate(flat('الصلاحية')), valid_share(flat('الصلاحية'))
    judge_ok = bool(pairs >= PAIRS_MIN and acc is not None and acc >= ACC_MIN and acc_valid >= VALID_MIN)
    old = rate(flat('أفلامنا'))
    summary = {'الصلاحية': {'أزواج': pairs, 'دقّة_اختيار_الثبات': acc, 'الصالح': acc_valid, 'صالح': judge_ok},
               'أفلامنا': {'نسبة_الفوز': old, 'الصالح': valid_share(flat('أفلامنا'))}, 'المسوّدة': {}}
    gate = {}
    comp_texts = [films[i].get('transcript', '') for i in ref + ceiling]
    for d in req.get('المسوّدة') or []:
        sid = d['id'] + '/' + d['النوع']
        h, dv, cl = flat('المسوّدة_بوّابة', sid), flat('المسوّدة_تطوير', sid), flat('المسوّدة_سقف', sid)
        win = rate(h)
        ov = overlap(d['النصّ'], comp_texts)
        why_not = []
        if not judge_ok:
            why_not.append('الحَكَم لم يجتز صلاحيته: الحكم للاطلاع')
        if (req.get('المحاولة') or 1) > MAX_ROUNDS:
            why_not.append('تجاوزت المحاولات %d: يُكتب المشهد من جديد لا يُرقَّع على ذوق الحَكَم' % MAX_ROUNDS)
        if win is None or win < WIN_MIN:
            why_not.append('الفوز %s < %s' % (win, WIN_MIN))
        if old is None or old > OLD_MAX:
            why_not.append('أفلامنا السابقة تفوز %s > %s: الحَكَم لا يفرّق' % (old, OLD_MAX))
        if win is not None and old is not None and win - old < GAP_MIN:
            why_not.append('الفرق عن أفلامنا %.2f < %s' % (win - old, GAP_MIN))
        if valid_share(h) < VALID_MIN:
            why_not.append('الأحكام الصالحة %s < %s' % (valid_share(h), VALID_MIN))
        if ov > OVERLAP_MAX:
            why_not.append('تداخلٌ لفظيٌّ %.1f٪ مع تفريغاتهم' % (ov * 100))
        summary['المسوّدة'][sid] = {'الفوز_بوّابة': win, 'الفوز_تطوير': rate(dv), 'الفوز_سقف': rate(cl),
                                    'الصالح': valid_share(h), 'التداخل': ov, 'أسباب_الرفض': why_not}
        gate[sid] = not why_not
    return {'تاريخ': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
            'الشروط': {'فوز': WIN_MIN, 'أفلامنا': OLD_MAX, 'فرق': GAP_MIN, 'صالح': VALID_MIN, 'صلاحية': ACC_MIN,
                       'أزواج': PAIRS_MIN, 'محاولات': MAX_ROUNDS, 'تداخل': OVERLAP_MAX},
            'المرجع': {'تطوير': dev, 'بوّابة': hold, 'سقف': ceiling},
            'الخلاصة': summary, 'تجتاز': gate,
            # نصف البوّابة بلا أسبابٍ محفوظة (keep_why=False)، فلا يُكتب على مقاسه
            'التفصيل': rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--keys', required=True)
    ap.add_argument('--style', required=True, help='style.json من الإصدار الخاصّ')
    ap.add_argument('--stats', help='channel_stats.json: منحنيات أفلامنا لصلاحية الحَكَم')
    ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args()
    keys = keys_from(a.keys)
    if not keys:
        print('⛔ لا مفاتيح جيميناي'); return 1
    req = json.load(io.open(os.path.join('ops', 'stats', 'judge.json'), encoding='utf-8'))
    style = json.load(io.open(a.style, encoding='utf-8'))
    stats = json.load(io.open(a.stats, encoding='utf-8')) if a.stats and os.path.exists(a.stats) else None
    rep = run(req, style, stats, Gem(keys), a.workers)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(rep, io.open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    s = rep['الخلاصة']                                  # نسبٌ وحدها في السجلّ العامّ، لا نصوص
    print('صلاحية الحَكَم:', s['الصلاحية'])
    print('أفلامنا السابقة:', s['أفلامنا'])
    for sid, v in s['المسوّدة'].items():
        print('المسوّدة', sid, {k: v[k] for k in ('الفوز_بوّابة', 'الفوز_تطوير', 'الفوز_سقف', 'الصالح', 'التداخل')},
              '⛔ ' + ' | '.join(v['أسباب_الرفض']) if v['أسباب_الرفض'] else '✅')
    print('تجتاز:', rep['تجتاز'])
    return 0 if s['الصلاحية']['أزواج'] or s['المسوّدة'] else 1


if __name__ == '__main__':
    sys.exit(main())
