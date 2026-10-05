# -*- coding: utf-8 -*-
"""المقارنة العمياء (tools/blind_judge.py) بلا شبكة: استخراج المقاطع من التفريغ ونافذة الأكشن، وتساوي الطول بلا تشكيل،
وتبديل الترتيب لكلّ حَكَم، وحساب نسبة الفوز والشرط — والحَكَم مستبدَل."""
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blind_judge as bj  # noqa: E402


def transcript(n_lines, step=5, word='كلمة'):
    return "\n".join('[%d] (راوٍ) %s' % (i * step, " ".join([word] * 12)) for i in range(n_lines))


FILM = {'id': 'c1', 'الجهة': 'منافس', 'transcript': transcript(80),
        'action': {'from': 200, 'to': 290, 'narration': " ".join(['ضربة'] * 60)}}
MINE = {'id': 'o1', 'الجهة': 'نحن', 'transcript': transcript(80, word='معلومة')}


class SegTest(unittest.TestCase):
    def test_segments_by_window_and_action(self):
        s = bj.segments(FILM)
        self.assertEqual(set(s), {'opening', 'danger', 'action'})
        self.assertEqual(len(s['opening'].split()), 30 * 12)          # الأسطر من 0 إلى 145
        self.assertTrue(s['action'].startswith('ضربة'))
        self.assertNotIn('action', bj.segments(MINE))                  # لا نافذة أكشن ولا أسطر فيها

    def test_clip_strips_harakat_and_equalises(self):
        self.assertEqual(bj.clip('سَيْفٌ  مَكْسُورٌ فِي الْيَدِ', 2), 'سيف مكسور')


class RunTest(unittest.TestCase):
    def test_swapped_orders_win_rate_and_gate(self):
        seen = []

        def fake_call(self, mk, tag, budget_s=420, parse=None, cap_s=240, models=None):
            txt = json.loads(mk(False))['contents'][0]['parts'][0]['text']
            a = txt.split('النصّ A:')[1].split('النصّ B:')[0]
            seen.append((models[0], 'سيف' in a))
            # الحَكَم يفضّل نصّ المسوّدة (فيه «سيف») في الافتتاحية، ونصّ المنافس في الأكشن
            ours_is_a = 'سيف' in a
            if 'مشهد قتال' in txt:
                return {'winner': 'B' if ours_is_a else 'A', 'margin': 2, '_model': models[0]}
            return {'winner': 'A' if ours_is_a else 'B', 'margin': 3, '_model': models[0]}

        req = {'المسوّدة': [{'id': 'm', 'النوع': 'opening', 'النصّ': " ".join(['سيف'] * 100)},
                            {'id': 'm2', 'النوع': 'action', 'النصّ': " ".join(['سيف'] * 100)}],
               'المعايرة': ['o1']}
        style = {'الأفلام': [FILM, MINE]}
        with mock.patch.object(bj.Gem, 'call', fake_call):
            rep = bj.run(req, style, bj.Gem(['k']), workers=2)
        self.assertEqual(rep['الخلاصة']['المسوّدة']['m']['opening']['نسبة_الفوز'], 1.0)
        self.assertEqual(rep['الخلاصة']['المسوّدة']['m2']['action']['نسبة_الفوز'], 0.0)
        self.assertEqual(rep['الخلاصة']['المسوّدة']['m']['opening']['الأحكام'], 4)   # حَكَمان × ترتيبان
        self.assertEqual(rep['تجتاز'], {'m': True, 'm2': False})
        self.assertIn('o1', rep['الخلاصة']['المعايرة'])
        self.assertEqual({m for m, _ in seen}, {bj.MODELS[0], bj.MODELS[1]})            # نموذجان مختلفان
        self.assertEqual({o for _, o in seen}, {True, False})                            # والترتيبان كلاهما


if __name__ == '__main__':
    unittest.main()
