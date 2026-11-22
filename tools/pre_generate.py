# -*- coding: utf-8 -*-
"""بوّابات ما قبل التوليد — أمر المالك 2026-11-22.

تُشغَّل قبل TTS والبطاقات والمصغّرات: بوّابة النصّ (إملاء وتشكيل)، ثم بوّابة التشويق
(ومنها اسم السلسلة/القناة وصيغ التمريض في أول أربع دقائق، ونداء الاشتراك بعد الدقيقة الرابعة). الخروج 1 يمنع التوليد.

الاستعمال: python tools/pre_generate.py <مجلد_المشروع>
لا تُشغَّل على مشروعات الاختبار الناقصة (بلا script.md وبلا كتل d_### إنتاجية).
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import text_gate  # noqa: E402
import thrill_gate  # noqa: E402
from pathlib import Path


def is_production(proj: str) -> bool:
    if os.path.exists(os.path.join(proj, "script.md")):
        return True
    p = os.path.join(proj, "blocks.json")
    if not os.path.exists(p):
        return False
    import json
    try:
        with open(p, encoding="utf-8") as f:
            blocks = json.load(f)
    except ValueError:
        return False
    return any(re.fullmatch(r"d_\d{3}", b.get("id") or "") and len(b.get("text") or "") > 20 for b in blocks)


def run(proj: str) -> int:
    proj = os.path.abspath(proj)
    if not is_production(proj):
        return 0
    rc = text_gate.check_proj(proj, require_tashkeel=True)
    # بوّابة التشويق تحتاج blocks+publish على الأقل
    if os.path.exists(os.path.join(proj, "blocks.json")):
        errs, warns = thrill_gate.check(Path(proj), None)
        for w in warns:
            print("⚠️", w)
        for e in errs:
            print("✗", e)
        if errs:
            print("⛔ بوّابة التشويق: %d خطأ — يُصلح قبل الصوت" % len(errs))
            rc = 1
        else:
            print("✅ بوّابة التشويق: تجتاز (ومنها اسم السلسلة/القناة والتحوّط ونداء الاشتراك في أول 4 دقائق وبعدها)")
    if rc:
        print("⛔ pre_generate: لا توليد حتى تُصلح الموانع")
    else:
        print("✅ pre_generate: يجوز توليد الصوت والبطاقات والمصغّرات")
    return rc


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    return run(argv[0])


if __name__ == "__main__":
    sys.exit(main())
