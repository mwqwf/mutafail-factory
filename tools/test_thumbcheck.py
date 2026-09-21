# -*- coding: utf-8 -*-
"""اختبارُ حارسِ المصغّرة — يُختبر نصّاً قبل أن يُعتمد (شرطُ الدستور).

أمرُ المالك 2026-09-21: المصغّرةُ تُكمِّل العنوانَ ولا تُطابقه، وتكون مشوّقةً جدّاً
بحيث لا يستطيع المستخدمُ تجاهلَها.
"""
import unittest
from pathlib import Path

import thumbcheck

ROOT = Path(__file__).resolve().parents[1]
TITLE = "رجالٌ بدأوا بعد الأربعين: ما الذي يملكه ابنُ الأربعين ولا يملكه ابنُ العشرين؟"


def pub(thumbs, title=TITLE):
    return {"film": {"title": title}, "thumbs": thumbs}


class ThumbGuard(unittest.TestCase):
    def test_mirroring_the_title_is_refused(self):
        problems = thumbcheck.audit(pub([
            {"bg": "b01", "l1": "رجالٌ بدأوا بعد الأربعين", "l2": "ما الذي يملكه ابنُ الأربعين؟"},
            {"bg": "b02", "l1": "٤٥ لا ٢٠", "l2": "عمرُ من يبني أنجحَ الشركات"},
        ]))
        self.assertTrue(any("تُكرّر العنوان" in p or "منسوخ" in p for p in problems), problems)

    def test_descriptive_thumb_without_intrigue_is_refused(self):
        problems = thumbcheck.audit(pub([
            {"bg": "b01", "l1": "حديثٌ عن العمرِ والعملِ", "l2": "مراجعةٌ هادئةٌ للسيرةِ والتاريخ"},
            {"bg": "b02", "l1": "٤٥ لا ٢٠", "l2": "عمرُ من يبني أنجحَ الشركات"},
        ]))
        self.assertTrue(any("وصفيّة" in p for p in problems), problems)

    def test_two_thumbs_with_one_angle_are_refused(self):
        problems = thumbcheck.audit(pub([
            {"bg": "b01", "l1": "قاطعُ طريقٍ صارَ إماماً", "l2": "ماذا سمعَ يومَها؟"},
            {"bg": "b02", "l1": "قاطعُ طريقٍ صارَ إماماً", "l2": "ماذا سمعَ يومَها حقّاً؟"},
        ]))
        self.assertTrue(any("زاويةٌ واحدة" in p for p in problems), problems)

    def test_same_background_twice_is_refused(self):
        problems = thumbcheck.audit(pub([
            {"bg": "b01", "l1": "كانَ يقطعُ الطريقَ", "l2": "فصاروا يقصدونَه؟"},
            {"bg": "b01", "l1": "٤٥ لا ٢٠", "l2": "عمرُ من يبني أنجحَ الشركات"},
        ]))
        self.assertTrue(any("الخلفيّة نفسِها" in p for p in problems), problems)

    def test_complementary_and_hooky_thumbs_pass(self):
        problems = thumbcheck.audit(pub([
            {"bg": "b10", "l1": "كانَ يقطعُ الطريقَ على النّاس", "l2": "فصاروا يقطعونَه إليه",
             "badge": "ماذا سمعَ؟"},
            {"bg": "b22", "l1": "٤٥ لا ٢٠", "l2": "هذا عمرُ من يبني أنجحَ الشركات",
             "badge": "رقمٌ يكذّب الصورة"},
        ]))
        self.assertEqual(problems, [])

    def test_precheck_calls_the_guard(self):
        text = (ROOT / "tools" / "precheck.py").read_text(encoding="utf-8")
        self.assertIn("import thumbcheck", text)
        self.assertIn("thumbcheck.audit(pub)", text)


if __name__ == "__main__":
    unittest.main()
