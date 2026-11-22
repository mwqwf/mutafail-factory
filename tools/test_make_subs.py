# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import tempfile
from pathlib import Path

import make_subs as s


class MakeSubsTests(unittest.TestCase):
    def test_vtt_and_srt_from_blocks(self):
        d = Path(tempfile.mkdtemp())
        blocks = [
            {"id": "d_001", "text": "سُيُوفٌ فِي اللَّيْلِ."},
            {"id": "d_002", "text": "فَمَنْ صَاحِبُ الرَّايَةِ؟"},
            {"id": "r_001", "text": "اشترك.", "reel_only": True},
        ]
        (d / "blocks.json").write_text(json.dumps(blocks, ensure_ascii=False), encoding="utf-8")
        vtt, srt = s.generate(str(d))
        vt, st = Path(vtt).read_text(encoding="utf-8"), Path(srt).read_text(encoding="utf-8")
        self.assertTrue(vt.startswith("WEBVTT"))
        self.assertIn("Language: ar", vt)
        self.assertIn("سُيُوفٌ فِي اللَّيْلِ.", vt)
        self.assertIn("فَمَنْ صَاحِبُ الرَّايَةِ؟", vt)
        self.assertNotIn("اشترك.", vt)
        self.assertIn("00:00:00,000 -->", st)
        self.assertIn("سُيُوفٌ فِي اللَّيْلِ.", st)
        # ترتيب الإشارات
        self.assertLess(vt.index("سُيُوفٌ"), vt.index("الرَّايَةِ"))

    def test_empty_project_fails(self):
        d = Path(tempfile.mkdtemp())
        with self.assertRaises(ValueError):
            s.generate(str(d))


if __name__ == "__main__":
    unittest.main()
