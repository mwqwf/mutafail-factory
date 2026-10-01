#!/usr/bin/env python3
"""⚡ بوّابة التشويق والحماسة — أمر المالك 2026-10-01.

حكم المالك على الأفلام كلّها بلا استثناء: «ينقصها التشويق والحماسة والأكشن الذي يجعل المشاهد
مستنفراً يريد معرفة القادم». والقاعدةُ المكتوبة تُنسى، فهذه البوّابة تقيس البنية آلياً قبل الصوت:

  ✗ خطأ يوقف: الريلزات ثلاثة (الافتتاحية + اثنان) · لكلّ ريلز سؤالٌ معلّق في ختامه · الفيلم يفتح بخطّافٍ
    قصير لا بتحيّةٍ أو مقدّمةٍ باردة · ≥ سؤالان (حلقتان مفتوحتان) في أوّل 12 كتلة · ≥ 70٪ من الفصول
    تُختم بمعلّقةٍ (سؤالٌ أو «…») · نصّ المصغّرة قصيرٌ (≤ 3 كلمات للسطر) وبلا تشكيل.
  ⚠️ تنبيه: وعدٌ صريحٌ في الافتتاحية · افتتاحيات الفصول قصيرة · عنوانٌ فيه سؤالٌ أو تعليق.

لا تقيس البوّابة الصدق — ذاك للتفنيد وسجلّ الدعاوى. والحماسة لا تُسقط التوثيق.

    python3 tools/thrill_gate.py <مجلد_المشروع> [--thumbs thumbs.json]   # خروج 0 = تجتاز · 1 = لا
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HARAKAT = re.compile(r"[ً-ْٰـ]")
GREETING = re.compile(r"^(السلام عليكم|مرحبا|أهلا|اهلا|أهلاً)")
PROMISE = re.compile(r"(سنحكي|سنروي|سنكشف|نكشف|ستعرف|ستكتشف|سنعرف|سترى|نروي لكم|نحكي لكم)")
HOOK_FIRST_MAX = 16      # كلماتُ أوّل جملة
CHAPTER_OPEN_MAX = 22    # كلماتُ أوّل كتلة في الفصل
CLIFF_MIN = 0.70         # نسبةُ الفصول المختومة بمعلّقة
OPEN_LOOPS_MIN = 2       # أسئلةٌ في أوّل 12 كتلة


def plain(t: str) -> str:
    return HARAKAT.sub("", t or "").strip()


def words(t: str) -> int:
    return len(plain(t).split())


def is_cliff(t: str) -> bool:
    t = plain(t)
    return "؟" in t or t.endswith("…") or t.endswith("...")


def load(p: Path, name: str):
    f = p / name
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def check(proj: Path, thumbs: Path | None) -> tuple[list[str], list[str]]:
    errs, warns = [], []
    blocks = load(proj, "blocks.json") or []
    by_id = {b["id"]: b for b in blocks}
    film = [b for b in blocks if not b.get("reel_only")]
    if not film:
        return [f"لا كتل فيلمٍ في {proj}/blocks.json"], warns

    # ١. الافتتاح
    first = film[0]["text"]
    if GREETING.search(plain(first)):
        errs.append(f"الفيلم يفتح بتحيّة «{plain(first)[:30]}» — الخطّافُ أوّلاً ثم التحيّة")
    elif words(first) > HOOK_FIRST_MAX:
        errs.append(f"أوّل جملة {words(first)} كلمة (> {HOOK_FIRST_MAX}): الخطّاف صدمةٌ قصيرة لا شرح")
    head = film[:12]
    loops = sum("؟" in plain(b["text"]) for b in head)
    if loops < OPEN_LOOPS_MIN:
        errs.append(f"{loops} سؤالٌ فقط في أوّل 12 كتلة (≥ {OPEN_LOOPS_MIN}): حلقاتٌ مفتوحة تُغلق متأخّرة")
    if not any(PROMISE.search(plain(b["text"])) for b in head):
        warns.append("لا وعدَ صريحاً في الافتتاح («سنحكي…» / «سنكشف…»)")

    # ٢. الفصول: كلّ فصلٍ يُختم بمعلّقة ويفتح بخطّافٍ قصير
    sections = load(proj, "sections.json") or []
    order = [b["id"] for b in film]
    starts = [s["id"] for s in sections if s.get("id") in order]
    starts_idx = sorted(order.index(s) for s in starts)
    ends = [order[i - 1] for i in starts_idx if i > 0]
    if ends:
        cl = [e for e in ends if is_cliff(by_id[e]["text"])]
        ratio = len(cl) / len(ends)
        if ratio < CLIFF_MIN:
            flat = [e for e in ends if e not in cl][:5]
            errs.append(f"{len(cl)}/{len(ends)} فصلاً يُختم بمعلّقة ({ratio:.0%} < {CLIFF_MIN:.0%}) — مثلاً: {', '.join(flat)}")
        long_open = [order[i] for i in starts_idx if words(by_id[order[i]]["text"]) > CHAPTER_OPEN_MAX]
        if long_open:
            warns.append(f"{len(long_open)} فصلاً يفتح بكتلةٍ طويلة (> {CHAPTER_OPEN_MAX} كلمة): {', '.join(long_open[:5])}")

    # ٣. الريلزات: ثلاثة، ولكلٍّ سؤالٌ معلّق
    reels = load(proj, "reels.json") or []
    if len(reels) != 3:
        errs.append(f"{len(reels)} ريلز (المطلوب 3: الافتتاحية + اثنان)")
    for r in reels:
        rb = [by_id[i]["text"] for i in r.get("blocks", []) if i in by_id]
        end = plain(rb[-1]) if rb else plain(r.get("end_q", ""))
        if "؟" not in end:
            errs.append(f"الريلز {r.get('id')} لا يُختم بسؤالٍ معلّق يقود إلى الفيلم")
        if rb and words(rb[0]) > HOOK_FIRST_MAX:
            errs.append(f"الريلز {r.get('id')} يفتح بـ{words(rb[0])} كلمة (> {HOOK_FIRST_MAX}): الصدمة في أوّل ثانيتين")

    # ٤. العنوان
    pub = load(proj, "publish.json") or {}
    title = plain(pub.get("title", ""))
    if title and not re.search(r"[؟…:]|\.\.\.", title):
        warns.append(f"العنوان بلا سؤالٍ ولا تعليق: «{title[:50]}»")

    # ٤ب. ⭐ الظهور الأوّل للراوي (أمر المالك 2026-10-01): مفاجئٌ ويختلف في كل فيلم
    shots = load(proj, "shots.json") or []
    av = [i for i, s in enumerate(shots) if s.get("avatar")]
    if av:
        first = shots[av[0]]
        ent = [s for s in shots[:av[0]] if s.get("end_image") == first["id"] and s.get("entrance")]
        if not ent:
            errs.append(f"الظهور الأوّل للراوي ({first['id']}) بلا لقطة مدخلٍ مفاجئة قبله (end_image إليه + حقل entrance)")
        else:
            reg = Path(__file__).resolve().parents[1] / "ops/state/narrator_entrances.json"
            used = json.loads(reg.read_text(encoding="utf-8")) if reg.exists() else {}
            slug = ((load(proj, "publish.json") or {}).get("slug") or "").replace("-intro", "")
            same = [k for k, v in used.items() if not k.startswith("_") and k != slug and v == ent[0]["entrance"]]
            if same:
                errs.append(f"مدخل الراوي مكرّر من فيلم {same[0]} — كل فيلمٍ بمدخلٍ جديد")
            elif slug and slug not in used:
                warns.append(f"سجّل مدخل هذا الفيلم في ops/state/narrator_entrances.json تحت «{slug}»")

    # ٥. المصغّرات
    if thumbs and thumbs.exists():
        tj = json.loads(thumbs.read_text(encoding="utf-8"))
        for t in tj.get("thumbs", []):
            lines = t.get("text") or []
            if any(HARAKAT.search(x) for x in lines):
                errs.append(f"{t.get('file')}: نصّ المصغّرة مشكول (التشكيل ينزاح في الرسم)")
            if any(len(x.split()) > 3 for x in lines) or sum(len(x.split()) for x in lines) > 6:
                errs.append(f"{t.get('file')}: نصّ المصغّرة طويل {lines} (≤ 3 كلمات للسطر و≤ 6 للكلّ)")
    return errs, warns


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("proj")
    ap.add_argument("--thumbs")
    a = ap.parse_args()
    errs, warns = check(Path(a.proj), Path(a.thumbs) if a.thumbs else None)
    for w in warns:
        print("⚠️", w)
    for e in errs:
        print("✗", e)
    print("✅ تجتاز بوّابة التشويق" if not errs else f"⛔ {len(errs)} خطأ في التشويق — يُصلَح قبل الصوت")
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
