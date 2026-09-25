# -*- coding: utf-8 -*-
"""حارسٌ على حارس الاحتفاظ: لا يُخفَّف ولا يُفصل عن precheck."""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import retentioncheck as R  # noqa: E402


def blocks(texts):
    return [("d_%03d" % (i + 1), t) for i, t in enumerate(texts)]


GOOD = ["كم عمرُ أقدم ورقة؟"] + ["جملةٌ عادية."] * 20 + ["لكن لماذا؟"] + ["جملةٌ عادية."] * 20 + ["فما التالي؟"]


class Retention(unittest.TestCase):
    def test_good_passes(self):
        self.assertEqual(R.audit(blocks(GOOD)), [])

    def test_number_word_opening_passes(self):
        t = ["قبل نحو ثمانية قرون كان رجل."] + GOOD[1:]
        self.assertEqual(R.audit(blocks(t)), [])

    def test_flat_opening_blocked(self):
        t = ["كان الورق مادةً."] * 4 + GOOD[4:]
        self.assertTrue(any("①" in b for b in R.audit(blocks(t))))

    def test_long_gap_blocked(self):
        t = ["سؤال؟"] + ["جملة."] * 30 + ["سؤال؟"]
        self.assertTrue(any("②" in b for b in R.audit(blocks(t))))

    def test_recap_blocked(self):
        t = GOOD[:5] + ["وكما ذكرنا من قبل."] + GOOD[5:]
        self.assertTrue(any("③" in b for b in R.audit(blocks(t))))

    def test_no_bridge_blocked(self):
        t = GOOD + ["انتهى."] * 8
        self.assertTrue(any("④" in b for b in R.audit(blocks(t))))

    def test_thresholds_not_relaxed(self):
        self.assertLessEqual(R.WINDOW, 25)
        self.assertLessEqual(R.OPEN_BLOCKS, 4)
        self.assertLessEqual(R.BRIDGE_BLOCKS, 8)

    def test_wired_into_precheck(self):
        src = io.open(os.path.join(HERE, "precheck.py"), encoding="utf-8").read()
        self.assertIn('"retentioncheck.py"', src)


if __name__ == "__main__":
    unittest.main()
