# -*- coding: utf-8 -*-
"""اختيار الأصوات لكلّ سيناريو (أمر المالك 2026-11-27): لا صوت امرأة، ولكلّ شخصية صوتٌ مستقلّ بسبب، وثبات السلسلة،
والوكيل يختار الأصوات بنفسه (لا إجازة عيّنات من المالك)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import casting  # noqa: E402

BLOCKS = [{'id': 'd1', 'role': 'N', 'text': 'أ'}, {'id': 'd2', 'role': 'Q', 'text': 'ب'}, {'id': 'd3', 'role': 'Q', 'text': 'ج'}]


def cast():
    return {'series': 's', 'narrator': {'voice': 'Algenib', 'style': 'epic', 'reason': 'راوٍ ملحميّ لقصّة معركة'},
            'characters': {'khalid': {'voice': 'Algieba', 'reason': 'صوت قائد شابّ حازم'},
                           'amr': {'voice': 'Charon', 'reason': 'صوت أعمق وأسنّ لداهية العرب'}},
            'blocks': {'d2': 'khalid', 'd3': 'amr'}, 'samples': {'status': 'approved'}}


class Casting(unittest.TestCase):
    def test_good_passes_and_applies(self):
        self.assertEqual(casting.check(cast(), BLOCKS, {'s': {'narrator': {'voice': 'Algenib'}}}, True), [])
        b = casting.apply(cast(), [dict(x) for x in BLOCKS])
        self.assertEqual([x['voice'] for x in b], ['Algenib', 'Algieba', 'Charon'])

    def test_female_voice_rejected(self):
        c = cast(); c['characters']['amr']['voice'] = 'Kore'
        self.assertTrue(any('امرأة' in e for e in casting.check(c, BLOCKS)))

    def test_shared_or_narrator_voice_and_missing_reason_rejected(self):
        c = cast(); c['characters']['amr']['voice'] = 'Algieba'; c['characters']['khalid']['reason'] = ''
        errs = ' '.join(casting.check(c, BLOCKS))
        self.assertIn('متعدّدة', errs); self.assertIn('بلا سبب', errs)
        c = cast(); c['characters']['amr']['voice'] = 'Algenib'
        self.assertTrue(any('الراوي نفسه' in e for e in casting.check(c, BLOCKS)))

    def test_unassigned_quote_and_series_drift_rejected(self):
        c = cast(); del c['blocks']['d3']
        self.assertTrue(any('بلا شخصية' in e for e in casting.check(c, BLOCKS)))
        errs = casting.check(cast(), BLOCKS, {'s': {'characters': {'khalid': {'voice': 'Iapetus'}}}})
        self.assertTrue(any('السلسلة' in e for e in errs))

    def test_render_does_not_need_owner_sample_approval(self):
        c = cast(); c['samples']['status'] = 'pending'
        self.assertEqual(casting.check(c, BLOCKS, render=True), [])

    def test_render_needs_reasons(self):
        c = cast(); c['characters']['amr']['reason'] = ''
        self.assertTrue(any('سبب' in e for e in casting.check(c, BLOCKS, render=True)))

if __name__ == '__main__':
    unittest.main()
