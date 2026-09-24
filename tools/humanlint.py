# -*- coding: utf-8 -*-
"""حارسُ الأسلوب البشريّ — يمنع السيناريو الذي «تفوح منه رائحةُ نموذجٍ لغويّ».

أمرُ المالك 2026-09-21: «في كتابة السيناريو يجب استعمال أسلوبٍ بشريّ، والابتعاد عن
المثاليّة الزائدة وكلِّ ما يوحي بأنّ السيناريو كُتب بالذكاء الاصطناعيّ».

⛔ وهذا حارسٌ **مانع** لا مستشار: يرجع 1 فيسقط `precheck.py` قبل أيّ توليد.
   ولا يُتجاوز بتعديلِ عتبةٍ ولا بحذفِ قاعدة، وإنّما بأحد أمرين لا ثالثَ لهما:
   ① إصلاحُ النصّ حتى يمرّ،  ② أو تحكيمٌ مكتوبٌ لكلّ رايةٍ بعينها في
   `style_review.json` داخل الحمولة، بتعليلٍ لا يقلّ عن أربعين حرفاً وباسمِ محكِّم.
   والتحكيمُ الجماعيُّ («كلُّ الرايات مقبولة») مردودٌ بنصّ هذه الأداة.

الاستعمال:  python humanlint.py <مجلد_الحمولة|script.md>
"""
import io
import json
import os
import re
import statistics
import sys

DIAC = "ًٌٍَُِّْـ"
PLAIN = lambda s: "".join(c for c in s if c not in DIAC)
BLOCK = re.compile(r"^(d_\d{3}|m_\d{3}|r_\d{3})\|(\w)\|(.+)$")

# صيغٌ قالبيّةٌ يكثر منها المولِّد ويقلُّ منها الكاتب
STOCK = [
    "وهذا يدل على", "وهذا يعني ان", "والسؤال هو", "وهنا تبدا", "وهنا يظهر",
    "وهذا ما يجعل", "وفي النهاية", "وفي الختام", "بعبارة اخرى", "ولا يخفى ان",
    "ومن الجدير بالذكر", "وخلاصة القول", "ومما لا شك فيه",
]
# كليشيهاتُ الكتابة الإنشائيّة المولَّدة (أمر المالك 2026-09-24: «الكلام الإنشائيّ وما يدلّ
# على أنّه من إنشاء الذكاء الاصطناعيّ»). كلٌّ منها وحده قد يصدر عن كاتب؛ اجتماعُ اثنين
# منها في فيلمٍ واحدٍ بصمةُ نموذج.
CLICHES = [
    "منذ فجر التاريخ", "على مر العصور", "عبر العصور", "رحلة عبر الزمن", "لم يكن مجرد",
    "ليس مجرد", "ليست مجرد", "دعونا", "هيا بنا", "تخيل معي", "في هذا الفيديو",
    "في هذه الحلقة سنتعرف", "يعد من اهم", "يعتبر من اهم", "لا يخفى على احد",
    "في نهاية المطاف", "بكل تاكيد", "حجر الزاويه", "رحله مذهله", "قصه مذهله",
    "بشكل مذهل", "يبقى السؤال", "الاجابه قد تفاجئك", "ستصدمك", "لن تصدق",
]
# ما لا يُفتتح به فيلم: التحيّةُ والتعريفُ بالحلقة يؤخّران الوعدَ عن الثواني الأولى (العقد §٣)
OPENING_BANNED = ["السلام عليكم", "مرحبا", "اهلا بكم", "اهلا وسهلا", "في هذه الحلقه", "في هذا الفيديو"]
ORDINALS = ["اولا", "ثانيا", "ثالثا", "رابعا", "خامسا", "سادسا"]


def _norm(s):
    """تسويةٌ خفيفةٌ للمقارنة: بلا تشكيل، وبهمزاتٍ وياءاتٍ موحَّدة."""
    s = PLAIN(s)
    for a, b in (("أإآ", "ا"), ("ى", "ي"), ("ة", "ه")):
        for ch in a:
            s = s.replace(ch, b)
    return re.sub(r"[^\w\s]", " ", s)


def read_blocks(path):
    """كتلُ الفيلم وحدَها — كتلُ الريلز `r_` لها منطقُ نداءٍ مختلف."""
    out = []
    for raw in io.open(path, encoding="utf-8"):
        m = BLOCK.match(raw.rstrip("\n").strip())
        if m and not m.group(1).startswith("r_"):
            out.append((m.group(1), m.group(3).strip()))
    return out


def audit(blocks):
    """يرجع قائمةَ رايات: (المعرّف، العنوان، القياس)."""
    flags = []
    if len(blocks) < 20:
        return flags
    texts = [t for _, t in blocks]
    plains = [PLAIN(t) for t in texts]
    lens = [len(p) for p in plains]
    n = len(blocks)

    # ① رتابةُ الطول: الكاتبُ البشريُّ يتنفّس، فيقصّر ويطيل
    mean = statistics.fmean(lens)
    cv = statistics.pstdev(lens) / mean if mean else 0.0
    if cv < 0.22:
        flags.append(("uniform_length", "رتابةُ طولِ الكتل — إيقاعٌ آليٌّ لا نفَسَ فيه",
                      "معامل الاختلاف %.3f والحدّ 0.220" % cv))

    # ② غيابُ الجملة القصيرة الحادّة
    short = sum(1 for L in lens if L < 45) / n
    if short < 0.08:
        flags.append(("no_short_beats", "لا جُمَلَ قصيرةً حادّة — كلُّ الكتل بطولٍ واحد",
                      "نسبةُ ما دون ٤٥ حرفاً %.1f%% والحدّ 8.0%%" % (short * 100)))

    # ③ إفراطُ الاستهلال بالواو
    waw = sum(1 for p in plains if p.lstrip().startswith("و")) / n
    if waw > 0.55:
        flags.append(("waw_opening", "أكثرُ الكتل تبدأ بالواو — وصلٌ آليٌّ متكرّر",
                      "%.1f%% والحدّ 55.0%%" % (waw * 100)))

    # ④ استهلالٌ ثلاثيٌّ مكرّر
    heads = {}
    for p in plains:
        k = " ".join(_norm(p).split()[:3])
        if k:
            heads[k] = heads.get(k, 0) + 1
    worst = max(heads.items(), key=lambda kv: kv[1]) if heads else ("", 0)
    if worst[1] > 6:
        flags.append(("repeated_opening", "استهلالٌ واحدٌ يتكرّر كثيراً",
                      "«%s» تكرّر %d مرّة والحدّ ٦" % (worst[0], worst[1])))

    # ⑤ الصيغُ القالبيّة
    joined = _norm(" ".join(texts))
    hits = [(s, joined.count(_norm(s))) for s in STOCK]
    hits = [(s, c) for s, c in hits if c >= 3]
    if hits:
        flags.append(("stock_phrases", "صيغٌ قالبيّةٌ مكرّرة",
                      " · ".join("«%s» ×%d" % (s, c) for s, c in hits)))

    # ⑥ التعدادُ المدرسيّ (أوّلاً… ثانياً… ثالثاً…) داخل السرد
    ords_used = sum(1 for o in ORDINALS if re.search(r"(?<!\w)" + o + r"(?!\w)", joined))
    if ords_used >= 4:
        flags.append(("schoolbook_list", "تعدادٌ مدرسيٌّ مرقَّمٌ في السرد المنطوق",
                      "استُعمل %d من صيغ العدّ والحدّ ٣" % ords_used))

    # ⑦ لا سؤالَ حقيقيّاً في الفيلم كلِّه
    q = sum(1 for p in plains if p.rstrip().endswith("؟")) / n
    if q < 0.02:
        flags.append(("no_questions", "سردٌ بلا أسئلةٍ حقيقيّة — تقريرٌ لا حكاية",
                      "%.1f%% والحدّ 2.0%%" % (q * 100)))

    # ⑧ جملةٌ كاملةٌ مكرّرةٌ حرفيّاً (خلا اللازمة المقصودة)
    seen = {}
    for p in plains:
        k = _norm(p).strip()
        if len(k) > 30:
            seen[k] = seen.get(k, 0) + 1
    dup = [k for k, v in seen.items() if v > 1]
    if dup:
        flags.append(("duplicate_block", "كتلتان بنصٍّ واحد",
                      "%d موضعاً" % len(dup)))

    # ⑨ كليشيهاتُ الإنشاء المولَّد
    ch = [(c, joined.count(_norm(c))) for c in CLICHES]
    ch = [(c, k) for c, k in ch if k]
    if sum(k for _, k in ch) >= 2:
        flags.append(("ai_cliches", "كليشيهاتٌ إنشائيّةٌ تفضح النصَّ المولَّد",
                      " · ".join("«%s» ×%d" % (c, k) for c, k in ch)))

    # ⑩ الهوك: أوّلُ كتلةٍ جملةٌ مكتملةٌ قصيرةٌ تضع المفارقة، لا تحيّةٌ ولا تعريفٌ بالحلقة
    first3 = _norm(" ".join(texts[:3]))
    greet = [g for g in OPENING_BANNED if _norm(g) in first3]
    if greet or lens[0] > 140:
        flags.append(("weak_hook", "افتتاحٌ رخو — تحيّةٌ أو تعريفٌ أو جملةٌ أولى طويلة",
                      ("«%s» في أوّل ثلاث كتل" % greet[0]) if greet
                      else "الكتلةُ الأولى %d حرفاً والحدّ ١٤٠" % lens[0]))

    # ⑪ طلبُ الاشتراك قبل تقديم القيمة (العقد §٣: لا طلبَ اشتراكٍ قبل نهاية الدقيقة الأولى)
    early = _norm(" ".join(texts[:12]))
    if "اشترك" in early or "الاشتراك" in early:
        flags.append(("early_cta", "طلبُ اشتراكٍ في أوّل الفيلم قبل أن يأخذ المشاهدُ شيئاً",
                      "في أوّل اثنتي عشرة كتلة"))
    return flags


def _arbitration(root):
    """تحكيمٌ مكتوبٌ لكلّ رايةٍ باسمها — لا إعفاءَ جماعيّ."""
    f = os.path.join(root, "style_review.json")
    if not os.path.exists(f):
        return {}
    try:
        data = json.loads(io.open(f, encoding="utf-8").read())
    except ValueError:
        return {}
    out = {}
    for rule, entry in (data.get("rules") or {}).items():
        if not isinstance(entry, dict):
            continue
        reason = entry.get("reason")
        who = entry.get("reviewer")
        if isinstance(reason, str) and len(reason.strip()) >= 40 and isinstance(who, str) and who.strip():
            out[rule] = reason.strip()
    return out


def main(target):
    root = target if os.path.isdir(target) else os.path.dirname(os.path.abspath(target))
    script = os.path.join(root, "script.md") if os.path.isdir(target) else target
    blocks = read_blocks(script)
    flags = audit(blocks)
    waived = _arbitration(root)
    print("حارسُ الأسلوب البشريّ: فُحصت %d كتلةَ فيلم" % len(blocks))
    live = [f for f in flags if f[0] not in waived]
    for rule, title, measure in flags:
        mark = "⚖" if rule in waived else "⛔"
        print("  %s %s · %s · %s" % (mark, rule, title, measure))
        if rule in waived:
            print("     تحكيمٌ مكتوب: %s" % waived[rule])
    if live:
        print("\n⛔ %d رايةُ أسلوبٍ غيرُ محكَّمة — لا توليدَ قبل إصلاحِ النصّ." % len(live))
        print("القاعدة (أمر المالك 2026-09-21): أسلوبٌ بشريٌّ، ولا مثاليّةَ زائدةً توحي")
        print("بأنّ السيناريو كُتب بالذكاء الاصطناعيّ. العلاجُ تنويعُ الإيقاع والتركيب،")
        print("لا تخفيفُ العتبة ولا تعطيلُ هذا الحارس.")
        return 1
    print("✅ الأسلوبُ بشريُّ الإيقاع بحسب المقاييس الإحدى عشرة")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "script.md"))
