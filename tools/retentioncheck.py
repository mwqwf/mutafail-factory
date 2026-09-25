# -*- coding: utf-8 -*-
"""حارسُ الاحتفاظ بالمشاهد — مانعٌ داخل precheck.py (أمر المالك 2026-09-25).

الاستعمال:  python3 retentioncheck.py <path/to/script.md | مجلد_الحمولة>

يفحص آليّاً ما يُقاس من أساليب الشدّ المجرّبة (PLAN §٩ب)، ولا يغني عن خريطة الاحتفاظ
المكتوبة في ops/research/<slug>/04-retention.md:
① افتتاحٌ بارد: في أوّل أربع كتلٍ سؤالٌ أو رقم — لا تعريفٌ ولا خلفيّة.
② خطّافٌ متجدّد: كلُّ ٢٥ كتلةً متتاليةً فيها سؤالٌ واحدٌ على الأقلّ (≈ ثلاث دقائق).
③ لا تلخيصَ ولا إحالةَ إلى الوراء ولا حديثَ عن الفيديو نفسه.
④ الجسر: في آخر ثماني كتلٍ سؤالٌ يفتح الحلقة التالية.
⛔ لا تُرفع النافذة ولا تُحذف عبارةٌ ممنوعة؛ ويحرسه tools/test_retentioncheck.py.
"""
import io
import os
import re
import sys
import unicodedata

WINDOW = 25
OPEN_BLOCKS = 4
BRIDGE_BLOCKS = 8
RECAP = ("كما ذكرنا", "كما قلنا", "كما رأينا سابقا", "وخلاصه القول", "في هذا الفيديو",
         "في هذه الحلقه", "في هذا المقطع", "قبل ان نبدا")
DIGITS = re.compile(r"[0-9٠-٩]")
NUMWORDS = ("ثلاث", "اربع", "خمس", "ست", "سبع", "ثماني", "تسع", "عشر", "مئه", "مائه", "الف",
            "مليون", "مليار", "قرن", "قرون")


def plain(t):
    t = "".join(c for c in unicodedata.normalize("NFKC", t) if not unicodedata.category(c).startswith("M"))
    return re.sub("[إأآ]", "ا", t).replace("ة", "ه").replace("ى", "ي")


def film_blocks(path):
    out = []
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^(d_\d+)\|[^|]*\|(.*)$", line.rstrip("\n"))
            if m:
                out.append((m.group(1), m.group(2)))
    return out


def audit(blocks):
    bad = []
    if not blocks:
        return ["لا كتلَ فيلمٍ في السيناريو"]
    head = " ".join(t for _, t in blocks[:OPEN_BLOCKS])
    hp = plain(head)
    if "؟" not in head and not DIGITS.search(head) and not any(
            re.search(r"(^|\s)(و|ب|ل)?%s" % w, hp) for w in NUMWORDS):
        bad.append("① الافتتاح: لا سؤالَ ولا رقمَ في أوّل %d كتل" % OPEN_BLOCKS)
    for i in range(0, max(1, len(blocks) - WINDOW + 1)):
        win = blocks[i:i + WINDOW]
        if len(win) == WINDOW and not any("؟" in t for _, t in win):
            bad.append("② فراغٌ بلا سؤال: %s ← %s (%d كتلة)" % (win[0][0], win[-1][0], WINDOW))
            break
    for bid, t in blocks:
        p = plain(t)
        for r in RECAP:
            if r in p:
                bad.append("③ %s: «%s»" % (bid, r))
    if not any("؟" in t for _, t in blocks[-BRIDGE_BLOCKS:]):
        bad.append("④ الجسر: لا سؤالَ في آخر %d كتل" % BRIDGE_BLOCKS)
    return bad


def main(argv):
    p = argv[1] if len(argv) > 1 else "script.md"
    if os.path.isdir(p):
        p = os.path.join(p, "script.md")
    bad = audit(film_blocks(p))
    print("حارسُ الاحتفاظ بالمشاهد:")
    if bad:
        for b in bad:
            print("  ⛔ " + b)
        return 1
    print("  ✅ افتتاحٌ وخطّافٌ كلَّ %d كتلة وجسرٌ، بلا تلخيص" % WINDOW)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
