# -*- coding: utf-8 -*-
"""حارسٌ على المقاييس الثلاثة الجديدة في humanlint (أمر المالك 2026-09-24):
الكليشيهاتُ الإنشائيّة · الهوكُ الرخو · طلبُ الاشتراك المبكر. ولا تُحذف ولا تُخفَّف."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import humanlint as H  # noqa: E402

BASE = [("d_%03d" % i, t) for i, t in enumerate([
    "سَقَطَتِ الْقَلْعَةُ فِي لَيْلَةٍ وَاحِدَةٍ.",
    "لَكِنَّ الْحِصَارَ بَدَأَ قَبْلَهَا بِعَشْرِ سِنِينَ كَامِلَةٍ، حِينَ جَفَّ النَّهْرُ الَّذِي يَسْقِيهَا مِنَ الشَّرْقِ.",
    "فَمَنْ قَطَعَ الْمَاءَ؟",
] + ["كَتَبَ الْمُؤَرِّخُ رَقْمَ %d فِي هَامِشِ الْمَخْطُوطِ، وَهُوَ رَقْمٌ لَا يَظْهَرُ فِي النُّسَخِ الْمَطْبُوعَةِ." % i
     if i % 3 else "لِمَاذَا؟" for i in range(40)], 1)]


def rules(blocks):
    return {f[0] for f in H.audit(blocks)}


class NewHumanRules(unittest.TestCase):
    def test_clean_opening_has_no_new_flags(self):
        self.assertFalse({"ai_cliches", "weak_hook", "early_cta"} & rules(BASE))

    def test_cliches_flagged(self):
        b = list(BASE)
        b[10] = (b[10][0], "مُنْذُ فَجْرِ التَّارِيخِ وَالْإِنْسَانُ يَسْأَلُ.")
        b[20] = (b[20][0], "لَمْ يَكُنْ مُجَرَّدَ حَجَرٍ.")
        self.assertIn("ai_cliches", rules(b))

    def test_greeting_opening_flagged(self):
        b = [("d_001", "السَّلَامُ عَلَيْكُمْ، فِي هَذِهِ الْحَلَقَةِ نَتَحَدَّثُ عَنِ الْقَلْعَةِ.")] + BASE[1:]
        self.assertIn("weak_hook", rules(b))

    def test_early_subscribe_flagged(self):
        b = list(BASE)
        b[4] = (b[4][0], "اشْتَرِكْ فِي الْقَنَاةِ قَبْلَ أَنْ نَبْدَأَ.")
        self.assertIn("early_cta", rules(b))


if __name__ == "__main__":
    unittest.main()
