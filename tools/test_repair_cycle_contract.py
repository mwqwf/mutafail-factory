# -*- coding: utf-8 -*-
"""عقدُ دورة الإصلاح: تُغلق داخل الشوط، والبوّابةُ هي الحَكَم.

⛔ الكلفةُ المقيسة لجولةٍ واحدة (2026-09-21، حلقة «الثور»): خطأٌ يحكّمه التحكيمُ في
   آخر الجولة لا يُعاد صوتُه في الشوط نفسِه، فتسقط `listening-gate` بـ`stale-result`
   ويُعاد **شوطٌ كاملٌ** لأجل ثلاث كتل. تكرّر ذلك ثلاثَ دوراتٍ متتالية.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILM = (ROOT / ".github/workflows/film.yml").read_text(encoding="utf-8")
REPAIR = FILM[FILM.index("  repair:"):FILM.index("  listening-gate:")]


class RepairCycleContract(unittest.TestCase):
    def test_cycle_repeats_until_the_gate_settles(self):
        self.assertIn("for round in 1 2 3; do", REPAIR)
        self.assertIn("python tools/listen_gate.py proj", REPAIR,
                      "البوّابةُ نفسُها يجب أن تكون حَكَمَ الاستقرار داخل الإصلاح")
        self.assertIn("settled=1", REPAIR)

    def test_invalidation_runs_inside_every_round(self):
        body = REPAIR[REPAIR.index("for round in 1 2 3; do"):]
        self.assertIn("python tools/repair_true_errors.py proj repair.json", body,
                      "كلُّ جولةٍ تبدأ بإبطال ما حكّمه التحكيمُ خطأً حقيقيّاً")

    def test_unsettled_cycle_fails_closed(self):
        self.assertIn('[ "$settled" = 1 ] ||', REPAIR)
        self.assertIn("لا يُنشر", REPAIR)

    def test_generation_precedes_listening_in_the_round(self):
        body = REPAIR[REPAIR.index("for round in 1 2 3; do"):]
        gen = body.index("tools/gen25.js")
        listen = body.index("tools/listen.js")
        adjudicate = body.index("tools/adjudicate_listen.js")
        gate = body.index("tools/listen_gate.py")
        self.assertLess(gen, listen)
        self.assertLess(listen, adjudicate)
        self.assertLess(adjudicate, gate, "البوّابةُ تُقرأ بعد التحكيم لا قبله")


if __name__ == "__main__":
    unittest.main()
