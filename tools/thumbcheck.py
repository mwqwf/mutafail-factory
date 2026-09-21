# -*- coding: utf-8 -*-
"""حارسُ المصغّرة — تُكمِّل العنوانَ ولا تُكرّرُه، وتكون مشوّقةً لا وصفيّة.

أمرُ المالك 2026-09-21: «الصورُ المصغّرة لا يجب أن تكون مطابقةً للعنوان، بل يجب أن
تكون مكمِّلةً، ويجب أن تكون مشوّقةً جدّاً بحيث لا يستطيع المستخدمُ تجاهلَها».

⛔ وهذا حارسٌ **مانع** يعمل داخل `precheck.py` قبل الختم، لا نصيحةٌ في وثيقة.
   والقياسُ على ثلاثة أوجه:
   ① **التكرار**: تداخلُ كلماتِ المصغّرة مع كلماتِ العنوان (بلا حروفِ المعاني).
   ② **التشويق**: أثرٌ ظاهرٌ يُمسَك — سؤالٌ، أو رقمٌ، أو مفارقةٌ بكلمةٍ من قائمةٍ مقيسة.
   ③ **التمايز**: المصغّرتان (أ/ب) لا تُعيدان الزاويةَ نفسَها، وإلّا فليستا اختباراً.
⛔ والعلاجُ إعادةُ صياغةِ المصغّرة، لا تخفيفُ عتبةٍ ولا حذفُ الحارس.

الاستعمال:  python thumbcheck.py <مجلد_الحمولة>
"""
import io
import json
import os
import re
import sys

DIAC = "ًٌٍَُِّْـ"
# حروفُ المعاني وما لا يُحسب تداخلاً — تكرارُها لا يدلّ على تكرارِ المعنى
STOP = {
    "في", "من", "على", "عن", "الى", "إلى", "ما", "لا", "هل", "ثم", "او", "أو", "و",
    "هذا", "هذه", "ذلك", "التي", "الذي", "كان", "كانت", "قد", "بل", "لم", "لن",
    "كل", "بين", "بعد", "قبل", "عند", "هو", "هي", "انت", "أنت", "مع", "ان", "أن",
    "إن", "اذا", "إذا", "حتى", "كما", "لكن", "ولا", "فلا", "يا",
}
# ألفاظٌ تصنع التشويق: سؤالٌ أو رقمٌ أو مفارقةٌ أو نفيٌ لِمَا يُظَنّ
HOOKY = [
    "لماذا", "كيف", "متى", "أين", "هل", "من", "ماذا", "أيّ", "أي",
    "لم", "لا", "ليس", "ليست", "قبل", "بعد", "سرّ", "سر", "الحقيقة", "خطأ",
    "يكذّب", "يكذب", "صدمة", "انقلب", "غيّر", "غير", "أنقذ", "أسقط", "رفض",
    "اختفى", "نجا", "هزم", "وحده", "فقط", "أوّل", "اول", "آخر", "أخطر", "أغرب",
]
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
NUMBER_WORDS = [
    "واحد", "اثنان", "ثلاث", "أربع", "اربع", "خمس", "ست", "سبع", "ثمان", "تسع",
    "عشر", "عشرون", "عشرين", "ثلاثين", "أربعين", "اربعين", "خمسين", "ستين",
    "سبعين", "ثمانين", "تسعين", "مئة", "ألف", "الف", "مليون",
]


def norm(text):
    text = "".join(c for c in str(text) if c not in DIAC)
    for src, dst in (("أإآ", "ا"), ("ى", "ي"), ("ة", "ه")):
        for ch in src:
            text = text.replace(ch, dst)
    return re.sub(r"[^\w\s]", " ", text)


def words(text):
    return [w for w in norm(text).split() if len(w) > 2 and w not in STOP]


def _lines(thumb):
    return " ".join(str(thumb.get(k, "")) for k in ("l1", "l2", "title", "badge")).strip()


def audit(publish):
    """يرجع قائمةَ موانع — فارغةٌ إذا كانت المصغّراتُ مكمِّلةً ومشوّقةً ومتمايزة."""
    bad = []
    title = publish.get("film", {}).get("title", "")
    tset = set(words(title))
    thumbs = publish.get("thumbs", [])
    seen = []
    for n, thumb in enumerate(thumbs, 1):
        text = _lines(thumb)
        if not text:
            bad.append("المصغّرة %d بلا نصّ" % n)
            continue
        wset = set(words(text))

        # ① لا تُطابق العنوان
        shared = tset & wset
        if len(shared) >= 3:
            bad.append("المصغّرة %d تُكرّر العنوان (%d كلمةً مشتركة: %s) — والمطلوب أن تُكمِّله"
                       % (n, len(shared), " ".join(sorted(shared))))
        nt = norm(title)
        for key in ("l1", "l2"):
            line = norm(thumb.get(key, "")).strip()
            if line and len(line) > 8 and line in nt:
                bad.append("المصغّرة %d: سطرُها «%s» منسوخٌ من العنوان حرفيّاً"
                           % (n, str(thumb.get(key))[:40]))

        # ② تشويقٌ يُمسَك: سؤالٌ أو رقمٌ أو لفظُ مفارقة
        has_q = "؟" in text or "?" in text
        has_num = any(ch.isdigit() or ch in ARABIC_DIGITS for ch in text) or \
            any(nw in norm(text) for nw in NUMBER_WORDS)
        has_hook = any(h in norm(text).split() or norm(h) in norm(text) for h in HOOKY)
        if not (has_q or has_num or has_hook):
            bad.append("المصغّرة %d وصفيّةٌ لا مشوّقة: لا سؤالَ ولا رقمَ ولا لفظَ مفارقة" % n)

        # ③ تمايزُ المصغّرتين
        for prev_n, prev in seen:
            overlap = wset & prev
            if len(overlap) >= 3:
                bad.append("المصغّرتان %d و%d زاويةٌ واحدة (%s) — فليستا اختباراً"
                           % (prev_n, n, " ".join(sorted(overlap))))
        seen.append((n, wset))

    if len(thumbs) >= 2:
        bgs = [t.get("bg") for t in thumbs]
        if len(set(bgs)) < len(bgs):
            bad.append("المصغّرتان على الخلفيّة نفسِها — والاختبارُ يحتاج صورتين مختلفتين")
    return bad


def main(project):
    path = os.path.join(project, "publish.json")
    publish = json.load(io.open(path, encoding="utf-8"))
    problems = audit(publish)
    print("حارسُ المصغّرة: فُحصت %d مصغّرة" % len(publish.get("thumbs", [])))
    if problems:
        for p in problems:
            print("  ⛔ " + p)
        print("\nالقاعدة (أمر المالك 2026-09-21): المصغّرةُ **تُكمِّل** العنوانَ ولا تُطابقه،")
        print("وتكون مشوّقةً بحيث لا يستطيع المشاهدُ تجاهلَها. والعلاجُ إعادةُ صياغتها.")
        return 1
    print("✅ المصغّرتان مكمِّلتان ومشوّقتان ومتمايزتان")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
