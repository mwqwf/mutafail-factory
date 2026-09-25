# -*- coding: utf-8 -*-
"""حارسٌ على حارس الخطّ التحريريّ."""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import editorialcheck as E  # noqa: E402


class Editorial(unittest.TestCase):
    def test_almoravid_verdict_blocked(self):
        self.assertTrue(E.audit_text("d_001|C|لَمْ تَكُنْ كُلُّ مَعَارِكِهِمْ فَتْحاً نَاصِعاً.\n"))

    def test_occupation_framing_blocked(self):
        self.assertTrue(E.audit_text("d_002|C|بَعْدَ الِاحْتِلَالِ الْعَرَبِيِّ لِلْأَنْدَلُسِ\n"))

    def test_narration_passes(self):
        self.assertEqual(E.audit_text("d_003|C|عَبَرَ يُوسُفُ بْنُ تَاشُفِينَ الْبَحْرَ سَنَةَ ٤٧٩هـ.\n"), [])

    def test_list_not_shrunk(self):
        self.assertGreaterEqual(len(E.VERDICTS), 20)

    def test_wired_into_precheck(self):
        src = io.open(os.path.join(HERE, "precheck.py"), encoding="utf-8").read()
        self.assertIn('"editorialcheck.py"', src)


if __name__ == "__main__":
    unittest.main()
