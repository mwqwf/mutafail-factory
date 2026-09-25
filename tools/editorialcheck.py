# -*- coding: utf-8 -*-
"""حارسُ الخطّ التحريريّ في تاريخ المسلمين — مانعٌ داخل precheck.py (أمر المالك 2026-09-25).

الاستعمال:  python3 editorialcheck.py <path/to/script.md | مجلد_الحمولة>

يمنع صيغَ الحكم الجاهزة على دول المسلمين وفتوحهم (PLAN §١٠ القاعدة ٤)، كالتي وقعت في فيلم
المرابطين: «لم تكن معاركهم فتحاً ناصعاً». الفعلُ يُسرد بلا حكم، وإن لزم تقويمٌ نُسب إلى عالمٍ
مسلمٍ قديمٍ بكتابه. ⛔ ويُستثنى ما اتّفق أهلُ السنّة على ضلاله من الفرق (الخوارج والحشّاشون
ونحوهم)، فلا يدخل في هذا الحارس أصلاً لأنّ صيغه لا تذكرهم.
⛔ لا تُحذف عبارةٌ من القائمة؛ ويحرسه tools/test_editorialcheck.py.
"""
import io
import os
import re
import sys
import unicodedata

VERDICTS = (
    "لم تكن فتحا", "لم يكن فتحا", "ليست فتحا", "ليس فتحا", "فتحا ناصعا", "غزوا لا فتحا",
    "الاحتلال العربي", "الاحتلال الاسلامي", "الغزو العربي", "الغزو الاسلامي",
    "الاستعمار العربي", "الاستعمار الاسلامي", "همجيه الفاتحين", "وحشيه الفاتحين",
    "بربريه المسلمين", "همجيه المسلمين", "وحشيه المسلمين", "جرائم الفاتحين",
    "توسع امبريالي", "الامبرياليه الاسلاميه",
)


def plain(t):
    t = "".join(c for c in unicodedata.normalize("NFKC", t) if not unicodedata.category(c).startswith("M"))
    t = re.sub("[إأآٱ]", "ا", t).replace("ة", "ه").replace("ى", "ي").replace("ـ", "")
    return re.sub(r"\s+", " ", t)


def audit_text(text):
    bad = []
    for n, line in enumerate(text.split("\n"), 1):
        if line.startswith("IMG:"):
            continue
        p = plain(line)
        for v in VERDICTS:
            if v in p:
                bad.append("سطر %d: «%s»" % (n, v))
    return bad


def main(argv):
    p = argv[1] if len(argv) > 1 else "script.md"
    if os.path.isdir(p):
        p = os.path.join(p, "script.md")
    with io.open(p, encoding="utf-8") as fh:
        bad = audit_text(fh.read())
    print("حارسُ الخطّ التحريريّ:")
    if bad:
        for b in bad:
            print("  ⛔ حكمٌ جاهزٌ على المسلمين — " + b)
        return 1
    print("  ✅ لا حكمَ جاهزاً على دول المسلمين وفتوحهم")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
