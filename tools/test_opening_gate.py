# -*- coding: utf-8 -*-
"""بوّابة الافتتاحية قبل النشر (tools/opening_gate.py) بلا شبكة ولا ffmpeg: نسبة القصّة، وموانع الدقيقة الرابعة،
والتحيّة في الافتتاح البارد، والتعذّر الذي لا يُحسب نجاحاً، والحمولة بلا فيلم، والاستئناف."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import opening_gate as og  # noqa: E402

NO = {'present': False}
GOOD = {'segments': [{'from': 0, 'to': 25, 'role': 'hook'}, {'from': 25, 'to': 45, 'role': 'greeting'},
                     {'from': 45, 'to': 150, 'role': 'story_scene'}, {'from': 150, 'to': 240, 'role': 'story_scene'}],
        'first_scene_s': 0, 'greeting': {'present': True, 's': 33}, 'channel_intro': NO, 'method_or_sources': NO,
        'engagement_ask': NO, 'open_question': {'text': 'فكيف يخرج؟', 's': 42}, 'cuts_30': 13, 'numbers_30': 1,
        'names_30': 1, 'voice': {'kind': 'synthetic', 'varies': True}, 'hook': {'score': 8}}


class VerdictTest(unittest.TestCase):
    def test_prompt_is_same_standard_with_longer_window(self):
        self.assertIn('أوّلُ ٢٤٠ ثانيةً', og.PROMPT)
        self.assertNotIn('١٥٠', og.PROMPT)
        self.assertEqual(og.PROMPT.count('first_scene_s'), og.openings.PROMPT.count('first_scene_s'))

    def test_good_opening_passes(self):
        errs, warns, facts = og.verdict(GOOD)
        self.assertEqual(errs, [])
        self.assertEqual(warns, [])
        self.assertAlmostEqual(facts['نسبة_القصّة'], round(130 / 150, 3))

    def test_story_share_counts_overlaps_once_and_clips_window(self):
        a = {'segments': [{'from': 0, 'to': 40, 'role': 'hook'}, {'from': 20, 'to': 60, 'role': 'story_scene'},
                          {'from': 140, 'to': 200, 'role': 'story_scene'}]}
        self.assertAlmostEqual(og.story_share(a), round(70 / 150, 3))

    def test_owner_rules_block_publishing(self):
        bad = dict(GOOD, segments=[{'from': 0, 'to': 10, 'role': 'hook'}, {'from': 10, 'to': 150, 'role': 'context'}],
                   greeting={'present': True, 's': 1}, method_or_sources={'present': True, 's': 100},
                   engagement_ask={'present': True, 's': 200}, channel_intro={'present': True, 's': 3})
        errs, _, _ = og.verdict(bad)
        text = '\n'.join(errs)
        for word in ('القصّة', 'منهجٌ', 'طلبُ اشتراك', 'تعريفٌ بالقناة', 'تحيّةٌ عند الثانية 1'):
            self.assertIn(word, text)
        late = dict(GOOD, engagement_ask={'present': True, 's': 260})                # بعد الدقيقة الرابعة: جائز
        self.assertEqual(og.verdict(late)[0], [])

    def test_soft_signals_are_warnings(self):
        soft = dict(GOOD, cuts_30=6, numbers_30=3, first_scene_s=50, open_question={}, voice={'varies': False},
                    hook={'score': 5})
        errs, warns, _ = og.verdict(soft)
        self.assertEqual(errs, [])
        self.assertEqual(len(warns), 6)


class MainTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.keys = os.path.join(self.d, 'k.json')
        json.dump(['AIza-test'], open(self.keys, 'w'))   # مفتاحٌ بصيغة جيميناي (keys_from يتركه غيرها)
        self.out = os.path.join(self.d, 'r.json')

    def run_main(self, call_result, env=None):
        with mock.patch.object(og, 'clip_proxy', lambda p, end=og.END_S: p), \
             mock.patch.object(og.openings.Gem, 'call', lambda self_, mk, tag, budget_s=420, **k: call_result), \
             mock.patch.dict(os.environ, env or {}, clear=False):
            return og.main([self.d, '--keys', self.keys, '--out', self.out])

    def test_no_film_skips_and_resume_skips(self):
        self.assertEqual(self.run_main({'error': 'x'}), 0)                             # ريلزاتٌ وحدها
        open(os.path.join(self.d, 'film.mp4'), 'wb').write(b'0')
        self.assertEqual(self.run_main({'error': 'x'}, {'FILM_VIDEO_ID': 'abc'}), 0)   # مرفوعٌ سلفاً

    def test_resume_from_master_state_by_slug(self):
        json.dump({'slug': 'mutah'}, open(os.path.join(self.d, 'publish.json'), 'w'))
        st = os.path.join(self.d, 'last.json')
        json.dump({'slug': 'mutah', 'film': {'id': 'vid1'}}, open(st, 'w'))
        with mock.patch.dict(os.environ, {'FILM_VIDEO_ID': ''}):
            self.assertEqual(og.already_up(self.d, st), 'vid1')
            json.dump({'slug': 'alarcos', 'film': {'id': 'vid0'}}, open(st, 'w'))
            self.assertEqual(og.already_up(self.d, st), '')                          # فيلمٌ آخر: البوّابة تعمل

    def test_failure_is_not_success_and_verdict_exit_codes(self):
        open(os.path.join(self.d, 'film.mp4'), 'wb').write(b'0')
        with mock.patch.dict(os.environ, {'FILM_VIDEO_ID': ''}):
            self.assertEqual(self.run_main({'error': '429 Resource has been exhausted'}), 2)
            self.assertEqual(self.run_main(GOOD), 0)
            rep = json.load(open(self.out, encoding='utf-8'))
            self.assertEqual(rep['موانع'], [])
            self.assertEqual(self.run_main(dict(GOOD, engagement_ask={'present': True, 's': 30})), 1)


if __name__ == '__main__':
    unittest.main()
