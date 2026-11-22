# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cta_gate as g


def B(i, t, **k):
    return dict({"id": i, "text": t}, **k)


def pad(n, prefix="p"):
    # 14 كلمة × 0.46 ث ≈ 6.44 ث لكل كتلة؛ 40 كتلة ≈ 258 ث
    return [B("%s%02d" % (prefix, i), " ".join(["كَلِمَةٌ"] * 14) + ".") for i in range(n)]


class CtaGateTests(unittest.TestCase):
    def test_short_film_does_not_require_cta(self):
        errs, _ = g.check_blocks(pad(10))  # ≈ 64 ث
        self.assertEqual(errs, [])

    def test_cta_in_first_four_minutes_fails(self):
        blocks = pad(5) + [B("c1", "اشْتَرِكْ وَفَعِّلِ الْجَرَسَ.")] + pad(40, "z")
        errs, _ = g.check_blocks(blocks)
        self.assertTrue(any("قبل الدقيقة الرابعة" in e and "c1" in e for e in errs), errs)

    def test_long_film_without_cta_fails(self):
        errs, _ = g.check_blocks(pad(50))  # ≈ 322 ث
        self.assertTrue(any("لا نداء اشتراك" in e for e in errs), errs)

    def test_cta_after_four_minutes_passes(self):
        # 40 كتلة ≈ 258 ث ثم النداء ثم تتمة
        blocks = pad(40) + [B("c1", "اشْتَرِكْ وَفَعِّلِ الْجَرَسَ.")] + pad(20, "z")
        start, total = g.starts_of(g.film_blocks(blocks))
        self.assertGreater(start["c1"], g.NO_ASK_BEFORE)
        self.assertGreater(total, g.NO_ASK_BEFORE)
        errs, _ = g.check_blocks(blocks)
        self.assertEqual(errs, [])

    def test_subscribe_without_bell_is_not_enough(self):
        blocks = pad(40) + [B("c1", "اشْتَرِكْ فِي الْقَنَاةِ.")] + pad(20, "z")
        errs, _ = g.check_blocks(blocks)
        self.assertTrue(any("لا نداء اشتراك" in e for e in errs), errs)

    def test_reel_only_cta_ignored(self):
        blocks = pad(50) + [B("r1", "اشْتَرِكْ وَفَعِّلِ الْجَرَسَ.", reel_only=True)]
        errs, _ = g.check_blocks(blocks)
        self.assertTrue(any("لا نداء اشتراك" in e for e in errs), errs)


if __name__ == "__main__":
    unittest.main()
