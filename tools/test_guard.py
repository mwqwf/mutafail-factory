# -*- coding: utf-8 -*-
"""حارسٌ على الحارس: قوائمُ المحظورات في guard.py لا تُخفَّف، ونسختاه متطابقتان.

⛔ أمرُ المالك الثابت: لا صورَ نساءٍ ولا آلاتٍ موسيقيّة. وحين وسّعنا القائمة
(2026-09-24: الطبول والأبواق والأجراس والصنوج — وهي تظهر في ساعات الجزري المائية
وفي مشاهد الحروب — والملكات والأميرات) صار هذا الاختبارُ يمنع الرجوعَ عنها.
"""
import importlib.util
import io
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load(path):
    spec = importlib.util.spec_from_file_location("guard_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


G = load(os.path.join(HERE, "guard.py"))


def hits(label, prompt):
    return re.search(G.BANNED_IMG[label], prompt.lower(), re.I) is not None


class GuardLists(unittest.TestCase):
    def test_copies_identical(self):
        a = io.open(os.path.join(HERE, "guard.py"), encoding="utf-8").read()
        b = io.open(os.path.join(ROOT, "skill", "guard.py"), encoding="utf-8").read()
        self.assertEqual(a, b, "tools/guard.py وskill/guard.py يجب أن يتطابقا")

    def test_women_terms_blocked(self):
        for w in ("woman", "girls", "queen", "princess", "daughter", "widow", "empress"):
            self.assertTrue(hits("نساء", "a %s near the gate" % w), w)

    def test_instrument_terms_blocked(self):
        for w in ("drum", "drummers", "trumpet", "cymbals", "bell", "chimes", "gong",
                  "lute", "harp", "kettledrum", "war horn"):
            self.assertTrue(hits("آلات موسيقية", "automaton with %s" % w), w)

    def test_innocent_terms_pass(self):
        # قرنُ الثور والحصان وبرجُ الماء ليست آلات؛ ولا يُمنع ما ليس محظوراً.
        for p in ("an ox with long horns", "a horse at dawn", "a stone water tower",
                  "bronze gears of a water clock", "belly of a camel"):
            self.assertFalse(hits("آلات موسيقية", p), p)
            self.assertFalse(hits("نساء", p), p)


if __name__ == "__main__":
    unittest.main()
