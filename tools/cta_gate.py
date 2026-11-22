# -*- coding: utf-8 -*-
"""بوّابة نداء الاشتراك في وسط الفيلم — أمر المالك 2026-11-23.

كل فيلم جملةٌ منطوقة قصيرة فيها اشتراك وتفعيل الجرس، عند وقفة طبيعية بعد
الدقيقة الرابعة ونحو وسط الفيلم. وتُمنع في أول أربع دقائق (قاعدة الافتتاح باقية).

الاستعمال: python tools/cta_gate.py <مجلد_المشروع>
الخروج 1 عند المانع. إن قصر تقدير المدّة عن أربع دقائق فلا يُطلب الحضور.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HARAKAT = re.compile(r"[\u064B-\u0652ٰـ]")
SEC_PER_WORD = 0.46  # يطابق tools/thrill_gate.py


def plain(t: str) -> str:
    return HARAKAT.sub("", t or "").strip()


def words(t: str) -> int:
    return len(plain(t).split())

NO_ASK_BEFORE = 240.0
CTA_MAX_WORDS = 20
# نداء مكتمل: اشترك/اشتركوا + الجرس في الكتلة نفسها
SUB = re.compile(r"اشترك(?:وا|ي)?")
BELL = re.compile(r"الجرس|فع[ِّّ]*ل(?:وا|ي)?(?:\s+ال)?جرس")


def is_cta(text: str) -> bool:
    t = plain(text)
    return bool(SUB.search(t) and BELL.search(t))


def film_blocks(blocks: list[dict]) -> list[dict]:
    return [b for b in blocks if not b.get("reel_only")]


def starts_of(film: list[dict]) -> tuple[dict, float]:
    start, t = {}, 0.0
    for b in film:
        start[b["id"]] = t
        t += words(b.get("text") or "") * SEC_PER_WORD
    return start, t


def check_blocks(blocks: list[dict]) -> tuple[list[str], list[str]]:
    """وجود النداء بعد الدقيقة الرابعة وغيابه قبلها. الزمن تقديرٌ من الكلمات."""
    errs, warns = [], []
    film = film_blocks(blocks)
    if not film:
        return errs, warns
    start, total = starts_of(film)

    early = [b["id"] for b in film if start[b["id"]] < NO_ASK_BEFORE and is_cta(b.get("text") or "")]
    if early:
        errs.append(
            "نداء اشتراك أو جرس قبل الدقيقة الرابعة في %s (أمر المالك 2026-11-23): "
            "يُنقل إلى وقفة بعد الدقيقة الرابعة" % ", ".join(early[:5])
        )

    if total <= NO_ASK_BEFORE:
        return errs, warns

    late = [b for b in film if start[b["id"]] >= NO_ASK_BEFORE and is_cta(b.get("text") or "")]
    if not late:
        errs.append(
            "لا نداء اشتراكٍ وتفعيلِ جرس بعد الدقيقة الرابعة (أمر المالك 2026-11-23): "
            "جملة قصيرة نحو «اشترك وفعِّل الجرس» عند وقفة في وسط الفيلم"
        )
        return errs, warns

    for b in late:
        n = words(b.get("text") or "")
        if n > CTA_MAX_WORDS:
            warns.append(
                "نداء الاشتراك في %s طويل (%d كلمة، ≤ %d): يُجعل جملةً قصيرة في وقفة مستقلة"
                % (b["id"], n, CTA_MAX_WORDS)
            )

    mid = total / 2.0
    lo, hi = max(NO_ASK_BEFORE, mid * 0.70), min(total - 20.0, mid * 1.30)
    if lo >= hi:
        lo, hi = NO_ASK_BEFORE, total
    if not any(lo <= start[b["id"]] <= hi for b in late):
        t0 = start[late[0]["id"]]
        warns.append(
            "نداء الاشتراك عند ≈%.0f ث، والموضع المطلوب نحو الوسط بعد الدقيقة الرابعة (نحو %.0f ث)"
            % (t0, mid)
        )
    return errs, warns


def load_blocks(proj: str) -> list[dict]:
    p = os.path.join(proj, "blocks.json")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def check_proj(proj: str) -> tuple[list[str], list[str]]:
    return check_blocks(load_blocks(proj))


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    errs, warns = check_proj(argv[0])
    for w in warns:
        print("⚠️", w)
    for e in errs:
        print("✗", e)
    if errs:
        print("⛔ بوّابة نداء الاشتراك: %d مانع" % len(errs))
        return 1
    print("✅ بوّابة نداء الاشتراك: تجتاز (حضور بعد الدقيقة الرابعة وغياب قبلها)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
