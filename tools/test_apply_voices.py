# -*- coding: utf-8 -*-
"""تطبيق أصوات المختبر على الكتل (tools/apply_voices.py): صوتٌ وملاحظاتٌ لكلّ دور، وأسلوب المدينة للراوي نفسه،
وصوت الاقتباس غيرُ صوت الراوي، ولا كتابةَ بلا حكمٍ فعليّ، والحارس قبل التوليد (درس «medina» في مؤتة 2026-10-06)."""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apply_voices as av  # noqa: E402

NARR = {'slug': 'm', 'styles': {'epic': 'EPIC', 'urgent': 'URGENT', 'reverent': 'REVERENT'}, 'pos_styles': {'medina': 'reverent'},
        'roles': {'narrator': {'winner': {'voice': 'Charon', 'style': 'epic', 'director': 'EPIC', 'order': ['Charon·epic'],
                                          'chain': 'M1', 'filter': 'F1'}}}}
VOICES = {'slug': 'm-voices', 'styles': {'quote': 'QUOTE', 'recitation': 'RECITE'},
          'roles': {'quote': {'winner': {'voice': 'Charon', 'style': 'quote', 'director': 'QUOTE',
                                         'order': ['Charon·quote', 'Iapetus·quote']}},
                    'poetry': {'winner': {'voice': 'Enceladus', 'style': 'recitation', 'director': 'RECITE',
                                          'order': ['Enceladus·recitation']}}}}
BLOCKS = [{'id': 'n_001', 'role': 'N', 'voice': 'Algenib', 'text': 'أ'},
          {'id': 'n_002', 'role': 'N', 'pos': 'medina', 'voice': 'Algenib', 'text': 'ب'},
          {'id': 'n_003', 'role': 'Q', 'voice': 'Enceladus', 'text': 'ج'},
          {'id': 'n_004', 'role': 'P', 'voice': 'Charon', 'text': 'د… ه', 'style': 'old'}]


class ApplyTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.write('blocks.json', BLOCKS)
        self.write('publish.json', {'slug': 'm'})

    def write(self, name, obj):
        p = os.path.join(self.d, name)
        io.open(p, 'w', encoding='utf-8').write(json.dumps(obj, ensure_ascii=False))
        return p

    def read(self, name):
        return json.load(io.open(os.path.join(self.d, name), encoding='utf-8'))

    def run_main(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = av.main(list(args))
        return rc, buf.getvalue()

    def test_roles_positions_distinct_quote_voice_and_filter(self):
        rc, out = self.run_main(self.d, self.write('n.json', NARR), self.write('v.json', VOICES))
        self.assertEqual(rc, 0, out)
        b = {x['id']: x for x in self.read('blocks.json')}
        self.assertEqual((b['n_001']['voice'], b['n_001']['director']), ('Charon', 'EPIC'))
        self.assertEqual((b['n_002']['voice'], b['n_002']['director']), ('Charon', 'REVERENT'))   # المدينة: الصوت نفسه موقّراً
        self.assertEqual((b['n_003']['voice'], b['n_003']['director']), ('Iapetus', 'QUOTE'))    # لا يكون صوتَ الراوي
        self.assertEqual((b['n_004']['voice'], b['n_004']['director']), ('Enceladus', 'RECITE'))
        self.assertNotIn('style', b['n_004'])                                                     # لا «style» خام مع director
        self.assertEqual(self.read('publish.json')['voice_filter'], 'F1')
        self.assertEqual(self.run_main('--check', self.d)[0], 0)

    def test_unjudged_role_writes_nothing(self):
        bad = json.loads(json.dumps(VOICES))
        bad['roles']['poetry'] = {'finalists': ['Enceladus·recitation'], 'error': 'تعذّر الحكم الأخير: لا حكم'}
        rc, out = self.run_main(self.d, self.write('n.json', NARR), self.write('v.json', bad))
        self.assertEqual(rc, 1)
        self.assertIn('poetry', out)
        self.assertIn('تعذّر الحكم الأخير', out)
        self.assertEqual(self.read('blocks.json'), BLOCKS)
        self.assertNotIn('voice_filter', self.read('publish.json'))
        rc, out = self.run_main(self.d, self.write('n.json', NARR))                               # دورا الاقتباس والشعر بلا نتيجة
        self.assertEqual(rc, 1)
        self.assertIn('لا نتيجة', out)

    def test_old_single_narrator_result_and_unjudged_chain(self):
        old = {'slug': 'm', 'styles': NARR['styles'], 'pos_styles': {'medina': 'reverent'},
               'winner': dict(NARR['roles']['narrator']['winner'], chain=None, filter=None), 'final': {'order': ['Charon·epic']}}
        self.write('blocks.json', BLOCKS[:2])
        rc, out = self.run_main(self.d, self.write('n.json', old))
        self.assertEqual(rc, 0, out)
        self.assertNotIn('voice_filter', self.read('publish.json'))                               # يبقى الافتراض
        self.assertIn('الافتراضية', out)

    def test_position_without_style_refuses(self):
        n = json.loads(json.dumps(NARR))
        n['pos_styles'] = {}
        rc, out = self.run_main(self.d, self.write('n.json', n), self.write('v.json', VOICES))
        self.assertEqual(rc, 1)
        self.assertIn('medina', out)

    def test_check_blocks_generation_until_voices_applied(self):
        rc, out = self.run_main('--check', self.d)
        self.assertEqual(rc, 1)
        self.assertIn('n_001: بلا director', out)
        self.write('blocks.json', [{'id': 'x', 'voice': 'Algenib', 'text': 'أ', 'director': 'D'}])          # فيلمٌ قديم بلا أدوار
        self.assertEqual(self.run_main('--check', self.d)[0], 0)
        self.write('blocks.json', [{'id': 'x', 'role': 'N', 'voice': 'A', 'text': 'أ', 'director': 'D', 'style': 'medina'}])
        rc, out = self.run_main('--check', self.d)
        self.assertEqual(rc, 1)
        self.assertIn('style خام «medina»', out)


if __name__ == '__main__':
    unittest.main()
