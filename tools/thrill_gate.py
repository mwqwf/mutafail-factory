#!/usr/bin/env python3
"""⚡ بوّابة التشويق والحماسة — أمر المالك 2026-10-01.

حكم المالك على الأفلام كلّها بلا استثناء: «ينقصها التشويق والحماسة والأكشن الذي يجعل المشاهد
مستنفراً يريد معرفة القادم». والقاعدةُ المكتوبة تُنسى، فهذه البوّابة تقيس البنية آلياً قبل الصوت:

  ✗ خطأ يوقف: الريلزات ثلاثة (الافتتاحية + اثنان) · لكلّ ريلز سؤالٌ معلّق في ختامه · الفيلم يفتح بخطّافٍ
    قصير لا بتحيّةٍ أو مقدّمةٍ باردة · ≥ سؤالان (حلقتان مفتوحتان) في أوّل 12 كتلة · ≥ 70٪ من الفصول
    تُختم بمعلّقةٍ (سؤالٌ أو «…») · نصّ المصغّرة قصيرٌ (≤ 3 كلمات للسطر) وبلا تشكيل.
  ⚠️ تنبيه: وعدٌ صريحٌ في الافتتاحية · افتتاحيات الفصول قصيرة · عنوانٌ فيه سؤالٌ أو تعليق.

⭐ الإيقاع والتركيز (أمر المالك 2026-10-03: «الفيديوهات طويلة ومع ذلك لا تركّز على المعركة نفسها،
   ولا أكشن ولا حماسة»). القياس على بدر: الالتحامُ 6٪ من الكلام، وأوّل سيفٍ بعد 44٪ منه، وكلُّ صورةٍ
   تبقى على الشاشة نحو 22 ثانية — وكانت تجتاز البوّابة القديمة. فصارت تقيس البنيةَ لا علاماتِ الترقيم وحدها:
  ✗ فيلم المعركة (`genre: battle` في publish.json): كلُّ فصلٍ له `phase` (setup/buildup/battle/aftermath)،
    والمعركة ≥ 45٪ من كلام المتن، والتمهيد ≤ 15٪، وما بعد المعركة مع الخاتمة ≤ 15٪، وأوّلُ كتلة قتالٍ قبل 35٪.
  ✗ إيقاع الصورة: متوسّط اللقطة ≤ 6 ث وأطولُها ≤ 10 ث (تقديراً من عدد الكلمات؛ مقطعُ الراوي مستثنى).
  ✗ الافتتاحية (الفصل الأوّل) ≤ 60 ث تقديراً، وكلام الراوي فيها ≤ 45 كلمة: الخطّاف ثم القصّة.
  ✗ لا ذكرَ للمصادر في الفيلم (المصادر في الوصف) · كلفةُ التحريك المخطّط ≤ 90٪ من budget_total_usd.
  ✗ لا تفضيلَ مطلقاً بلا «من» في العنوان ونصّ المصغّرات وعناوين الريلزات (أعظم/أكبر/الوحيد/لم يسبق) — تنبيهٌ في المتن.

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
PROMISE = re.compile(r"(سنحكي|سنروي|سنكشف|نكشف|ستعرف|ستكتشف|سنعرف|سترى|سترون|نروي لكم|نحكي لكم)")
SMIRK = ("smirk", "half-smile", "half smile", "knowing", "sly", "wink", "playful", "mischiev")   # درس ملاذكرد: تعابير تُقرأ استهزاءً
HOOK_FIRST_MAX = 16      # كلماتُ أوّل جملة
CHAPTER_OPEN_MAX = 22    # كلماتُ أوّل كتلة في الفصل
CLIFF_MIN = 0.70         # نسبةُ الفصول المختومة بمعلّقة
OPEN_LOOPS_MIN = 2       # أسئلةٌ في أوّل 12 كتلة
SEC_PER_WORD = 0.46      # تقديرُ زمن الكلمة المشكولة بصوت القناة (≈ 130 كلمة/د) — قبل وجود الصوت
SHOT_MEAN_MAX = 6.0      # متوسّط بقاء اللقطة على الشاشة (ث)
SHOT_MAX = 10.0          # أطولُ لقطة (ث)
INTRO_MAX = 60.0         # الفصل الأوّل كلّه (ث): بدر كانت نحو 80 ث، عشرون منها خطّاف والباقي مراسم
INTRO_NARRATOR_MAX = 45  # كلماتُ الراوي الظاهر في الافتتاحية
BATTLE_MIN, SETUP_MAX, AFTER_MAX, FIRST_CLASH_MAX = 0.45, 0.15, 0.15, 0.35
PHASES = ("setup", "buildup", "battle", "aftermath")
SUPERLATIVE = re.compile(r"(?<!من )(?<!الله )\b(أعظم|أكبر|الوحيد|لم يسبق)")   # «الله أكبر» تكبيرٌ لا تفضيل
SUBSCRIBE = re.compile(r"(اشتركوا|اشترك|الجرس)")
# ⭐ أمر المالك 2026-10-03: «لا داعي لذكر المصادر في الفيلم… يكفي الإشارة بأنّ المصادر في الوصف، لأنّ هذا يطيل جداً ويشتّت الانتباه»
CITATION = re.compile(r"(رواه|رَوَاهُ|أخرجه|حسّنه|حسنه|صحّحه|صححه|بإسناد|في صحيحه|في مسنده|في سننه|في تاريخه|في كتابه|الطبعة|"
                      r"المصادر الأولى|مصادرها|صحيح البخاري|صحيح مسلم|ابن هشام|الواقدي|ابن الأثير|ابن كثير|الطبري|الهيثمي)")
PRICE_LIVE, PRICE_AUDIO, PRICE_AVATAR = 0.07, 0.14, 0.16   # $/ث (tools/fal_animate.py)
BUDGET_SHARE = 0.90      # المخطّط ≤ 90٪ من السقف (هامشُ إعادات)، والفيلم كلّه حيّ إلا ما وُسم kb3d صراحةً


def plain(t: str) -> str:
    return HARAKAT.sub("", t or "").strip()


def words(t: str) -> int:
    return len(plain(t).split())


def is_cliff(t: str) -> bool:
    t = plain(t)
    return "؟" in t or t.endswith("…") or t.endswith("...")


def absolute(t: str) -> list[str]:
    """تفضيلٌ مطلقٌ غيرُ مقيّد: «أعظم معركة» لا «من أعظم المعارك»."""
    return [m.group(1) for m in SUPERLATIVE.finditer(plain(t))]


def pacing(proj: Path, blocks: list[dict], film: list[dict], sections: list[dict], pub: dict) -> tuple[list[str], list[str]]:
    """الإيقاع والتركيز على المعركة — تقديرٌ من النصّ قبل الصوت."""
    errs, warns = [], []
    by_id = {b["id"]: b for b in blocks}
    order = [b["id"] for b in film]
    sec = lambda ids: sum(words(by_id[i]["text"]) for i in ids if i in by_id) * SEC_PER_WORD

    # ١. إيقاع الصورة: كلُّ لقطةٍ تُقاس بكلام كتلها (أو مدّتها الثابتة)
    shots = load(proj, "shots.json") or []
    spans = []
    for s in shots:
        if s.get("avatar") or s.get("lipsync"):
            continue
        ids = [i for i in s.get("blocks", []) if i in by_id and not by_id[i].get("reel_only")]
        span = sec(ids) if ids else float(s.get("hold") or 0)
        if span:
            spans.append((span, s["id"]))
    if spans:
        mean = sum(x for x, _ in spans) / len(spans)
        if mean > SHOT_MEAN_MAX:
            errs.append(f"اللقطة تبقى {mean:.1f} ث في المتوسّط (> {SHOT_MEAN_MAX:.0f}): صورةٌ ثابتةٌ طويلة تقتل الأكشن — "
                        f"لقطةٌ لكلّ جملة، ويجوز أن تتشارك لقطتان صورةً واحدة بحركتين (حقل file)")
        long_ = sorted(((x, i) for x, i in spans if x > SHOT_MAX), reverse=True)
        if long_:
            errs.append(f"{len(long_)} لقطة أطول من {SHOT_MAX:.0f} ث، أطولُها " +
                        ", ".join(f"{i} ({x:.0f} ث)" for x, i in long_[:5]))

    # ٢. الافتتاحية: الفصل الأوّل كلّه، وكلام الراوي الظاهر فيه
    starts = sorted(order.index(x["id"]) for x in sections if x.get("id") in order)
    if len(starts) > 1:
        intro = order[starts[0]:starts[1]]
        cut = next((k for k, t in enumerate(shots) if order[starts[1]] in t.get("blocks", [])), 0)
        holds = sum(float(t.get("hold") or 0) for t in shots[:cut] if not t.get("blocks"))
        total = sec(intro) + holds
        if total > INTRO_MAX:
            errs.append(f"الافتتاحية نحو {total:.0f} ث (> {INTRO_MAX:.0f}): ما بعد الخطّاف من مراسمٍ يُسرَّب منه المشاهد")
        av = {i for s in shots if s.get("avatar") or s.get("lipsync") for i in s.get("blocks", [])}
        nw = sum(words(by_id[i]["text"]) for i in intro if i in av)
        if nw > INTRO_NARRATOR_MAX:
            errs.append(f"كلام الراوي في الافتتاحية {nw} كلمة (> {INTRO_NARRATOR_MAX}): ظهورٌ خاطف ثم القصّة")
        if any(SUBSCRIBE.search(plain(by_id[i]["text"])) for i in intro if i in by_id):
            warns.append("نداء الاشتراك في الافتتاحية: يُقترح نقله بعد أوّل وفاءٍ بوعد (قرار المالك)")

    # ٣. فيلم المعركة: التركيز على المعركة نفسها
    battle_film = pub.get("genre") == "battle" or any(x.get("phase") for x in sections)
    if battle_film and len(starts) > 1:
        body = order[starts[1]:]
        sec_of = {}
        bounds = starts[1:] + [len(order)]
        for x in sections:
            if x.get("id") in order and order.index(x["id"]) >= starts[1]:
                a = order.index(x["id"])
                b = min(k for k in bounds if k > a)
                sec_of[x["id"]] = (x.get("phase"), order[a:b])
        missing = [k for k, (ph, _) in sec_of.items() if ph not in PHASES]
        if missing:
            errs.append(f"{len(missing)} فصلاً بلا phase صالح ({'/'.join(PHASES)}): {', '.join(missing[:5])}")
        else:
            tot = sum(words(by_id[i]["text"]) for i in body) or 1
            share = {p: sum(words(by_id[i]["text"]) for ph, ids in sec_of.values() if ph == p for i in ids) / tot for p in PHASES}
            if share["battle"] < BATTLE_MIN:
                errs.append(f"المعركة {share['battle']:.0%} من المتن (≥ {BATTLE_MIN:.0%}): الفيلم يدور حولها لا فيها")
            if share["setup"] > SETUP_MAX:
                errs.append(f"التمهيد {share['setup']:.0%} من المتن (≤ {SETUP_MAX:.0%}): السياق يُروى داخل المعركة لا قبلها")
            if share["aftermath"] > AFTER_MAX:
                errs.append(f"ما بعد المعركة والخاتمة {share['aftermath']:.0%} (≤ {AFTER_MAX:.0%})")
            first = next((n for n, i in enumerate(body) for ph, ids in sec_of.values() if ph == "battle" and i in ids), None)
            pos = sum(words(by_id[i]["text"]) for i in body[:first]) / tot if first is not None else 1
            if pos > FIRST_CLASH_MAX:
                errs.append(f"أوّل كتلة قتالٍ بعد {pos:.0%} من المتن (≤ {FIRST_CLASH_MAX:.0%})")
    elif pub.get("genre") == "battle":
        errs.append("فيلم معركة بلا فصول (sections.json)")

    # ٤. الصدق: لا تفضيلَ مطلق في الواجهة
    title = (pub.get("film") or {}).get("title") or pub.get("title") or ""
    faces = [("العنوان", title)] + [(f"الريلز {r.get('id')}", r.get("title", "")) for r in (load(proj, "reels.json") or [])]
    for where, t in faces:
        bad = absolute(t)
        if bad:
            errs.append(f"{where}: تفضيلٌ مطلق «{bad[0]}» بلا «من» — «من أعظم…» أو مصدرٌ صريح")
    cited = [b["id"] for b in film if CITATION.search(plain(b["text"]))]
    if cited:
        errs.append(f"ذكرُ مصدرٍ في {len(cited)} كتلة ({', '.join(cited[:6])}): المصادر في الوصف وحده (أمر المالك 2026-10-03)")

    # ٥. الميزانية تكفي تحريك الفيلم (أمر المالك 2026-10-03: «المدّة لو قلّلت لتضمن أنّ الميزانية تكفيها 100٪ أو أغلبها»)
    cap = pub.get("budget_total_usd")
    if cap and shots:
        est, still = 0.0, 0.0
        for s in shots:
            ids = [i for i in s.get("blocks", []) if i in by_id and not by_id[i].get("reel_only")]
            span = sec(ids) if ids else float(s.get("hold") or 0)
            if s.get("avatar") or s.get("lipsync"):
                est += span * PRICE_AVATAR
            elif s.get("kind") == "حيّة":
                est += span * (PRICE_AUDIO if s.get("audio") else PRICE_LIVE)
            else:
                still += span
        total = est + still * PRICE_LIVE
        if est > cap * BUDGET_SHARE:
            cut = (est - cap * BUDGET_SHARE) / PRICE_LIVE
            errs.append(f"التحريك المخطّط ≈ {est:.0f}$ يتجاوز {BUDGET_SHARE:.0%} من السقف {cap}$: قصّر الفيلم نحو {cut:.0f} ث")
        elif still and total > cap * BUDGET_SHARE:
            warns.append(f"{still:.0f} ث بلا تحريك حيّ؛ تحريكها كلّها ≈ {total:.0f}$ (> {BUDGET_SHARE:.0%} من {cap}$) — قصّرها أو اقبلها kb3d")

    flagged = [b["id"] for b in film if absolute(b["text"])]
    if flagged:
        warns.append(f"تفضيلٌ مطلق في {len(flagged)} كتلة ({', '.join(flagged[:5])}): يُسند أو يُقيَّد")
    return errs, warns


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

    # ٣ب. ⛔ تعابير الراوي (درس ملاذكرد 2026-10-03): نصف الابتسامة الماكرة تُقرأ استهزاءً لا تشويقاً
    for s in load(proj, "shots.json") or []:
        ap = (s.get("avatar_prompt") or "").lower()
        bad = [w for w in SMIRK if w in ap]
        if bad:
            errs.append(f"لقطة الراوي {s.get('id')} تطلب {', '.join(bad)} — التعبير يطابق معنى الجملة (ops/LESSONS_MANZIKERT_2026-10-03.md §١)")

    # ٤. العنوان
    pub = load(proj, "publish.json") or {}
    title = plain((pub.get("film") or {}).get("title") or pub.get("title", ""))
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
            if any(absolute(x) for x in lines):
                errs.append(f"{t.get('file')}: تفضيلٌ مطلق في نصّ المصغّرة {lines} — المحروق لا يُصحَّح بعد النشر")
            tw = set(plain(title).split())
            if lines and tw and sum(w in tw for x in lines for w in x.split()) >= max(2, len(" ".join(lines).split()) - 1):
                warns.append(f"{t.get('file')}: نصّ المصغّرة يكرّر العنوان — المصغّرة تكمله ولا تعيده")

    e2, w2 = pacing(proj, blocks, film, sections, pub)
    return errs + e2, warns + w2


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
