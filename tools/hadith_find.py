# -*- coding: utf-8 -*-
"""بحثٌ محلّيٌّ في نصوص الحديث (assets/hadith/) بلا شبكة — فلا طلبَ إذنٍ ولا جلب.

الاستعمال:  python3 tools/hadith_find.py "العسل شفاء" [--book bukhari] [--max 10]
يُطبِّع النصَّ كما يُطبِّع حارسُ القرآن (بلا تشكيلٍ ولا فرقٍ في رسم الهمزة)، ويطبع
الكتابَ ورقمَ الحديث ودرجاته (حين تحملها النسخة) وأوّلَ النصّ.
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from quranverify import words  # noqa: E402

HDIR = os.path.join(os.path.dirname(HERE), "assets", "hadith")
BOOKS = ("bukhari", "muslim", "abudawud", "tirmidhi", "nasai", "ibnmajah", "malik")


def search(query, books=BOOKS, limit=10):
    q = words(query)
    out = []
    for b in books:
        with io.open(os.path.join(HDIR, "ara-%s.json" % b), encoding="utf-8") as fh:
            d = json.load(fh)
        for h in d["hadiths"]:
            w = words(h["text"])
            if all(any(x in y for y in w) for x in q):
                out.append((b, h))
                if len(out) >= limit:
                    return out
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--book", choices=BOOKS)
    ap.add_argument("--max", type=int, default=10)
    a = ap.parse_args()
    res = search(a.query, (a.book,) if a.book else BOOKS, a.max)
    for b, h in res:
        g = "، ".join("%s: %s" % (x["name"], x["grade"]) for x in h.get("grades", []))
        print("── %s ‏%s%s" % (b, h["hadithnumber"], ("  [" + g + "]") if g else ""))
        print(h["text"].strip()[:600])
    print("\n%d نتيجة" % len(res))


if __name__ == "__main__":
    main()
