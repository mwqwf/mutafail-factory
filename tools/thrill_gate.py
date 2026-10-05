#!/usr/bin/env python3
"""⚡ بوّابة التشويق والحماسة — أمر المالك 2026-10-01.

حكم المالك على الأفلام كلّها بلا استثناء: «ينقصها التشويق والحماسة والأكشن الذي يجعل المشاهد
مستنفراً يريد معرفة القادم». والقاعدةُ المكتوبة تُنسى، فهذه البوّابة تقيس البنية آلياً قبل الصوت:

  ✗ خطأ يوقف: الريلزات ثلاثة (الافتتاحية + اثنان) · لكلّ ريلز سؤالٌ معلّق في ختامه · الفيلم يفتح بخطّافٍ
    قصير لا بتحيّةٍ أو مقدّمةٍ باردة · سؤالٌ مركزيّ بعد الافتتاح البارد وقبل الدقيقة · ≥ 70٪ من الفصول
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

⭐⭐ حكم المالك 2026-10-05 بعد «بحث الاحتفاظ بالمشاهد» (ops/research/mutah/00-retention-plan.md §١٠) — موانع لا تنبيهات:
  ✗ لا منهج ولا مصادر ولا طلب اشتراكٍ أو تعليقٍ قبل الدقيقة الرابعة · لا سؤال ولا تحيّة قبل الثانية 25 (الافتتاح البارد)
  ✗ رقمٌ واحد على الأكثر ولا تاريخ في أوّل 30 ث · 12 لقطةً فأكثر تبدأ في أوّل 30 ث
  ✗ إعادة شدٍّ كلّ ≤ 45 ث في الدقائق 1–6 (موضع النزيف في منحنياتنا) · خطّاف الحلقة التالية في آخر دقيقةٍ من فيلمٍ في سلسلة
  ✗ الكلمات المأثورة (كتلةٌ فيها speaker) لا تُقبل بلا رقم دعواها في السجلّ (claim).

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
OPEN_LOOPS_MIN = 1       # سؤالٌ مركزيّ بعد الافتتاح البارد وقبل الدقيقة (حكم المالك 2026-10-05؛ كان سؤالين في أوّل 12 كتلة)
SEC_PER_WORD = 0.46      # تقديرُ زمن الكلمة المشكولة بصوت القناة (≈ 130 كلمة/د) — قبل وجود الصوت
SHOT_MEAN_MAX = 6.0      # متوسّط بقاء اللقطة على الشاشة (ث)
SHOT_MAX = 10.0          # أطولُ لقطة (ث)
INTRO_MAX = 60.0         # الفصل الأوّل كلّه (ث): بدر كانت نحو 80 ث، عشرون منها خطّاف والباقي مراسم
INTRO_NARRATOR_MAX = 45  # كلماتُ الراوي الظاهر في الافتتاحية
BATTLE_MIN, SETUP_MAX, AFTER_MAX, FIRST_CLASH_MAX = 0.45, 0.15, 0.15, 0.35
PHASES = ("setup", "buildup", "battle", "aftermath")
# «الله أكبر» تكبيرٌ لا تفضيل. و«أخطر/أقوى» من مراجعة مؤتة («أخطر من ادّعى النبوّة»)؛ و«أشدّ» تُترك: أكثرها نسبيٌّ («أشدّ ساعات القتال»)
SUPERLATIVE = re.compile(r"(?<!من )(?<!الله )\b(أعظم|أكبر|الوحيد|لم يسبق|أخطر|أقوى)")
SUBSCRIBE = re.compile(r"(اشتركوا|اشترك|الجرس)")
# ⭐ أمر المالك 2026-10-03: «لا داعي لذكر المصادر في الفيلم… يكفي الإشارة بأنّ المصادر في الوصف، لأنّ هذا يطيل جداً ويشتّت الانتباه»
CITATION = re.compile(r"(رواه|رَوَاهُ|أخرجه|حسّنه|حسنه|صحّحه|صححه|بإسناد|في صحيحه|في مسنده|في سننه|في تاريخه|في كتابه|الطبعة|"
                      r"المصادر الأولى|مصادرها|صحيح البخاري|صحيح مسلم|ابن هشام|الواقدي|ابن الأثير|ابن كثير|الطبري|الهيثمي|"
                      # مراجعة مؤتة: كانت تفلت «يروي ابن إسحاق» و«مؤرّخهم»
                      r"ابن إسحاق|ابن اسحاق|ابن سعد|البيهقي|موسى بن عقبة|ابن حجر|الذهبي|ابن عساكر|البلاذري|مؤرّخ|مؤرخ|ثيوفانيس)")
PRICE_LIVE, PRICE_AUDIO, PRICE_AVATAR, PRICE_FLF = 0.07, 0.14, 0.16, 0.112   # $/ث (tools/fal_animate.py)
CLIP_SEC = 5              # مدّة مقطع Kling المدفوع (DUR في tools/fal_animate.py)
BUDGET_SHARE = 0.90      # المخطّط ≤ 90٪ من السقف (هامشُ إعادات)، والفيلم كلّه حيّ إلا ما وُسم kb3d صراحةً
# ⭐⭐ حكم المالك 2026-10-05 بعد «بحث الاحتفاظ بالمشاهد» (ops/research/mutah/00-retention-plan.md §١ و§١٠): موانع لا تنبيهات
NO_ASK_BEFORE = 240.0    # لا منهج ولا مصادر ولا طلب اشتراكٍ أو تعليقٍ قبل الدقيقة الرابعة
COLD_MIN = 25.0          # الافتتاح البارد مشهدٌ متّصل: لا سؤال ولا تحيّة قبل هذه الثانية
OPEN_CUTS_MIN = 12       # لقطاتٌ تبدأ في أوّل 30 ث (لقطةٌ كلّ ثانيتين تقريباً)
OPEN_NUMBERS_MAX = 1     # رقمٌ واحد في أوّل 30 ث على الأكثر (الخطّاف نفسه) ولا تاريخ
DANGER = (60.0, 360.0)   # الدقائق 1–6: موضع النزيف في منحنياتنا
REHOOK_GAP_MAX = 45.0    # أطول فجوةٍ بين إعادتَي شدٍّ في الدقائق 1–6
NEXT_TAIL = 60.0         # خطّاف الحلقة التالية في آخر دقيقة من فيلمٍ في سلسلة
# دراسة الأسلوب 2026-10-05: وعد الكشف والتصحيح في الافتتاحية («سنكشف لكم حقائق كنتم تحسبونها مسلّمات») في 5 من أفلامنا
# الثمانية، في موضع نزيفنا، ولا شيء منه في أفلامهم السبعة ⇒ مانعٌ في أوّل ثلاث دقائق (الوعد بالقصّة لا بالتصحيح)
DEBUNK_PROMISE = re.compile(r"(تحسبون|تحسبونها|تحسبها|مسلّمات|مسلمات|لم تقع أصلا|لم يقلها|لم يقله|خرافات|خرافة|أسطورة|أساطير|"
                            r"أكاذيب|كذبة|نصحّح|نصحح|تصحيح)")
DEBUNK_WINDOW = 180.0
# سجلّ الحلقات المفتوحة (مراجعة مؤتة §١٥): إن حملت الكتل opens/closes قيست إعادة الشدّ بها لا بعلامات الترقيم
LOOPS_MIN, LOOPS_FROM = 2, 45.0
ASK = re.compile(r"(اشتركوا|اشترك |الجرس|اكتب في التعليقات|اكتبوا|علّقوا|في التعليقات|المنهج|منهجنا|مصادرنا|"
                 r"المصادر في الوصف|نوثّق|نوثق|سنحكيها|نترككم)")
NUMBER = re.compile(r"[0-9٠-٩]+|\b[وفبل]?(واحد|اثنان|اثنين|ثلاث|ثلاثة|أربع|أربعة|خمس|خمسة|ست|ستة|سبع|سبعة|ثمان|ثمانية|تسع|تسعة|عشر|عشرة|"
                    r"عشرون|عشرين|ثلاثون|ثلاثين|أربعون|أربعين|خمسون|خمسين|مئة|مائة|مئتي|مئتا|ألف|آلاف|ألفا|ألفي|مليون)\b")
DATE = re.compile(r"[0-9٠-٩]+\s*(هـ|م\b)|\b(سنة|عام)\s+([0-9٠-٩]|ثمان|سبع|ست|خمس|أربع|ثلاث|اثنت|إحدى|عشر)|للهجرة|للميلاد")
REHOOK = re.compile(r"(؟|…|\.\.\.|لكنّ|لكن |غير أنّ|إلا أنّ|فجأة|لم يكن يعلم|لم يكونوا يعلمون|وهنا|ثم حدث|ولم يبق)")
NEXT = re.compile(r"(الحلقة القادمة|الحلقة التالية|الحلقة المقبلة|في الحلقة|الحلقة الثانية|الحلقة الثالثة)")


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
                # ⭐ الأرك 2026-10-04: Kling يحاسب مقطعاً كاملاً (duration، 5 ث افتراضاً) لكلّ لقطةٍ حيّة مهما قصرت جملتها —
                #    كان التقدير بطول الكلام يُخفي نحو نصف الكلفة في الجمل القصيرة. والتحوّل (end_image) بسعر v3.
                clip = float(s.get("duration") or CLIP_SEC)
                est += clip * (PRICE_FLF if s.get("end_image") else PRICE_AUDIO if s.get("audio") else PRICE_LIVE)
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


def owner_1005(blocks: list[dict], film: list[dict], shots: list[dict], pub: dict) -> tuple[list[str], list[str]]:
    """قواعد المالك 2026-10-05 موانع: الافتتاح البارد، والطلب بعد الدقيقة الرابعة، وأوّل 30 ث، والدقائق 1–6، وخطّاف الحلقة
    التالية، وكلمات الصحابة بأرقام دعاواها. الزمن تقديرٌ من الكلمات قبل الصوت (SEC_PER_WORD) كبقيّة البوّابة."""
    errs, warns = [], []
    by_id = {b["id"]: b for b in blocks}
    t, start = 0.0, {}
    for b in film:
        start[b["id"]] = t
        t += words(b["text"]) * SEC_PER_WORD
    total = t
    early = lambda lim: [b for b in film if start[b["id"]] < lim]

    asks = [b["id"] for b in early(NO_ASK_BEFORE) if ASK.search(plain(b["text"]))]
    if asks:
        errs.append(f"منهجٌ أو طلبٌ قبل الدقيقة الرابعة في {', '.join(asks[:5])} (حكم المالك 2026-10-05): بعد أوّل وفاءٍ بوعد")
    cold = early(COLD_MIN)
    broke = [b["id"] for b in cold if "؟" in plain(b["text"]) or GREETING.search(plain(b["text"]))]
    if broke:
        errs.append(f"الافتتاح البارد يُقطع قبل الثانية {COLD_MIN:.0f} بسؤالٍ أو تحيّة ({', '.join(broke[:4])}): مشهدٌ متّصلٌ واحد أوّلاً")
    first30 = " ".join(plain(b["text"]) for b in early(30.0))
    nums = NUMBER.findall(first30)
    if len(nums) > OPEN_NUMBERS_MAX:
        errs.append(f"{len(nums)} أرقام في أوّل 30 ث (≤ {OPEN_NUMBERS_MAX}): رقمٌ واحد هو الخطّاف، والباقي بعد أن يهتمّ المشاهد")
    if DATE.search(first30):
        errs.append("تاريخٌ في أوّل 30 ث: التاريخ الهجريّ والميلاديّ بعد أن يهتمّ المشاهد")
    warns.append("راجع أسماء الأعلام في أوّل 30 ث بالعين: اسم البطل وحده (لا تكشفه الآلة)")

    if shots:
        sec = lambda s: (sum(words(by_id[i]["text"]) for i in s.get("blocks", []) if i in by_id and not by_id[i].get("reel_only"))
                         * SEC_PER_WORD) or float(s.get("hold") or 0)
        t, cuts = 0.0, 0
        for s in shots:
            if t < 30.0:
                cuts += 1
            t += sec(s)
        if cuts < OPEN_CUTS_MIN:
            errs.append(f"{cuts} لقطةً في أوّل 30 ث (≥ {OPEN_CUTS_MIN}): لقطةٌ كلّ ثانيتين — جملٌ أقصر أو لقطاتٌ صامتة (hold) للأكشن")

    promised = [b["id"] for b in early(DEBUNK_WINDOW) if DEBUNK_PROMISE.search(plain(b["text"]))]
    if promised:
        errs.append(f"وعدُ كشفٍ أو تصحيحٍ في أوّل ثلاث دقائق ({', '.join(promised[:4])}): الوعد بالقصّة لا بالتصحيح "
                    "(دراسة الأسلوب: في موضع نزيفنا، ولا شيء منه عند الناجحين)")

    looped = any(x.get("opens") or x.get("closes") for x in film)
    if looped:
        opened, closed = {}, {}
        for x in film:
            for k in x.get("opens") or []:
                opened.setdefault(k, start[x["id"]])
            for k in x.get("closes") or []:
                closed.setdefault(k, start[x["id"]])
        orphan = sorted(set(closed) - set(opened))
        if orphan:
            errs.append(f"حلقاتٌ تُغلق ولم تُفتح: {', '.join(orphan[:5])}")
        live = lambda t: sum(1 for k, s0 in opened.items() if s0 <= t and closed.get(k, 1e9) > t)
        thin = [f"{start[x['id']]:.0f}" for x in film
                if LOOPS_FROM <= start[x["id"]] < total - NEXT_TAIL and live(start[x["id"]]) < LOOPS_MIN]
        if thin:
            errs.append(f"أقلّ من {LOOPS_MIN} حلقاتٍ مفتوحة عند {', '.join(thin[:6])} ث: سؤالٌ أو وعدٌ قائم يُفتح قبل أن يُغلق آخر")
    a, b = DANGER
    zone = [x for x in film if a <= start[x["id"]] < min(b, total)]
    if zone:
        hooked = (lambda x: bool(x.get("opens"))) if looped else (lambda x: bool(REHOOK.search(plain(x["text"]))))
        marks = [a] + [start[x["id"]] for x in zone if hooked(x)] + [min(b, total)]
        gap = max(q - p for p, q in zip(marks, marks[1:]))
        if gap > REHOOK_GAP_MAX:
            errs.append(f"فجوةٌ {gap:.0f} ث بلا إعادة شدٍّ في الدقائق 1–6 (≤ {REHOOK_GAP_MAX:.0f}): موضع النزيف في منحنياتنا")

    if pub.get("series"):
        tail = [x for x in film if start[x["id"]] >= total - NEXT_TAIL]
        if not any(NEXT.search(plain(x["text"])) for x in tail):
            errs.append("فيلمٌ في سلسلة بلا خطّافٍ للحلقة التالية في دقيقته الأخيرة")

    quoted = [x["id"] for x in film if x.get("speaker") and not x.get("claim")]
    if quoted:
        errs.append(f"كلماتٌ مأثورة بلا رقم دعوى في السجلّ ({', '.join(quoted[:5])}): النصّ حرفيّاً من مصدره وحده (حكم المالك 2026-10-05)")
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
    # ⭐ حكم المالك 2026-10-05: الافتتاح البارد مشهدٌ متّصل بلا سؤال، ثم السؤال المركزيّ قبل الدقيقة. والأسئلة المتراكمة
    #    («فأين… ولماذا… وكيف…») تشويقٌ طويل وافق مواضع المغادرة في منحنياتنا ⇒ سؤالٌ مركزيّ واحد يكفي، وأكثر من ثلاثة تنبيه.
    t, head = 0.0, []
    for b in film:
        if t >= 60.0:
            break
        if t >= COLD_MIN:
            head.append(b)
        t += words(b["text"]) * SEC_PER_WORD
    loops = sum("؟" in plain(b["text"]) for b in head)
    if loops < OPEN_LOOPS_MIN:
        errs.append(f"لا سؤالَ مركزيّاً بين الثانية {COLD_MIN:.0f} و60: حلقةٌ مفتوحة بعد الافتتاح البارد")
    elif loops > 3:
        warns.append(f"{loops} أسئلة متتابعة في الدقيقة الأولى: سلسلة أسئلةٍ تشويقٌ طويل — سؤالٌ مركزيّ واحد ثم القصّة")
    if not any(PROMISE.search(plain(b["text"])) for b in film[:12]):
        warns.append("لا وعدَ صريحاً في الافتتاح بالقصّة («سترى كيف…»)، ولا يكون وعداً بكشفٍ أو تصحيح")

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

    # ٣. الريلزات: ثلاثة، ولكلٍّ سؤالٌ معلّق — إلا ما أمر به المالك لفيلمٍ بعينه (publish.json: reels_required؛
    #    الأرك 2026-10-04: «الريلزات يكفي اثنان فقط لهذا الفيلم فاخترهما بعناية»)
    reels = load(proj, "reels.json") or []
    need = int((load(proj, "publish.json") or {}).get("reels_required", 3))
    if len(reels) != need:
        errs.append(f"{len(reels)} ريلز (المطلوب {need}" + (": الافتتاحية + اثنان)" if need == 3 else " بأمر المالك)"))
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
    e3, w3 = owner_1005(blocks, film, load(proj, "shots.json") or [], pub)
    return errs + e2 + e3, warns + w2 + w3


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
