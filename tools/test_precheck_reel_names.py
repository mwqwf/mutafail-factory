# -*- coding: utf-8 -*-
"""اختبارٌ: `precheck.py` يمسك اسمَي ملفَّي الريلز قبل الختم لا بعد الشوط.

⛔ الكلفةُ المقيسة لعدم هذا الفحص (2026-09-21، حلقة «الثور»): شوطٌ كاملٌ — صوتٌ
   وصورٌ وتصييرٌ وفحصٌ سمعيّ — ثمّ سقط `publish` آخرَ الطريق على اسمٍ في ملفّ نشرٍ
   كان يُمكن مسكُه محلّيّاً في جزءٍ من ثانية.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRECHECK = (ROOT / "tools" / "precheck.py").read_text(encoding="utf-8")
PREFLIGHT = (ROOT / "tools" / "publish_preflight.py").read_text(encoding="utf-8")


class ReelFileNames(unittest.TestCase):
    def test_precheck_enforces_the_same_names_as_preflight(self):
        self.assertIn('["r1.mp4", "r2.mp4"]', PRECHECK)
        self.assertIn('r.get("file", "")', PRECHECK)
        # وهو الشرطُ نفسُه الذي يفرضه العدّاء — فلا يتفرّق الحارسان
        self.assertIn('["r1.mp4", "r2.mp4"]', PREFLIGHT)

    def test_live_payload_matches(self):
        import io
        import json
        payload = ROOT / "payload" / "thawr" / "publish.json"
        if not payload.exists():          # الحمولةُ الخامُ لا تُدفع إلى المستودع العام
            self.skipTest("الحمولةُ غيرُ موجودةٍ في هذه النسخة")
        data = json.load(io.open(payload, encoding="utf-8"))
        self.assertEqual(sorted(r.get("file") for r in data["reels"]), ["r1.mp4", "r2.mp4"])


if __name__ == "__main__":
    unittest.main()
