# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime
from zoneinfo import ZoneInfo

import meta_gate as g

ALG = ZoneInfo("Africa/Algiers")


def pub(**kw):
    base = {
        "film": {
            "title": "«لفّوا رأسي بثوب!» قالها قائد الروم أمام جيش خالد بن الوليد",
            "description": (
                "قصة خالد بن الوليد في معركة أجنادين.\n"
                "قائد الروم يطلب أن يُلفّ رأسه بثوب.\n\n"
                "{CHAPTERS}\n\n"
                "المصادر: الواقدي وابن عساكر.\n"
            ),
        },
        "publishAt": "2026-11-26T16:30:00Z",  # 17:30 الجزائر
        "reels": [
            {"file": "r1.mp4", "publishAt": "2026-11-27T16:30:00Z"},
            {"file": "r2.mp4", "publishAt": "2026-11-27T18:00:00Z"},
        ],
    }
    # shallow merge for tests
    for k, v in kw.items():
        if k == "film" and isinstance(v, dict):
            base["film"] = {**base["film"], **v}
        else:
            base[k] = v
    return base


class MetaGateTests(unittest.TestCase):
    def test_good_payload_passes(self):
        errs, _ = g.check_pub(pub())
        self.assertEqual(errs, [])

    def test_title_without_search_term_fails(self):
        errs, _ = g.check_pub(pub(film={"title": "لفّوا رأسي بثوب! قالها القائد أمام الجيش"}))
        self.assertTrue(any("العنوان بلا لفظ" in e for e in errs), errs)

    def test_description_head_without_search_fails(self):
        errs, _ = g.check_pub(pub(film={"description": "ليلة باردة في المعسكر.\nرجل ينظر إلى الأفق.\n\n{CHAPTERS}\n\nالمصادر: الطبري.\n"}))
        self.assertTrue(any("السطران الأوّلان" in e for e in errs), errs)

    def test_missing_sources_fails(self):
        errs, _ = g.check_pub(pub(film={"description": "قصة خالد بن الوليد في أجنادين.\nمعركة فاصلة.\n\n{CHAPTERS}\n"}))
        self.assertTrue(any("بلا قائمة مصادر" in e for e in errs), errs)

    def test_publish_slot_outside_fails(self):
        # 16:00 الجزائر = 15:00Z
        errs, _ = g.check_pub(pub(publishAt="2026-11-26T15:00:00Z"))
        self.assertTrue(any("خارج الفترة الافتراضية" in e for e in errs), errs)

    def test_slot_at_2100_passes(self):
        # 21:00 الجزائر = 20:00Z
        errs, _ = g.check_pub(pub(publishAt="2026-11-26T20:00:00Z", reels=[
            {"file": "r1.mp4", "publishAt": "2026-11-27T16:30:00Z"},
        ]))
        self.assertEqual(errs, [])

    def test_shorts_same_day_fail(self):
        errs, _ = g.check_pub(pub(reels=[{"file": "r1.mp4", "publishAt": "2026-11-26T18:00:00Z"}]))
        self.assertTrue(any("اليوم التالي" in e for e in errs), errs)

    def test_parse_z_to_algiers(self):
        dt = g.parse_when("2026-11-26T16:30:00Z")
        self.assertEqual(dt.tzinfo, ALG)
        self.assertEqual(dt.hour, 17)
        self.assertEqual(dt.minute, 30)
        self.assertTrue(g.in_slot(dt))


if __name__ == "__main__":
    unittest.main()
