# -*- coding: utf-8 -*-
"""استئناف تشريح الافتتاحيات (tools/openings.py --resume): يبقى ما نجح، ويُعاد ما فشل وما لم يُحلَّل، ويزيد عدّاد
المحاولات، ويُترك ما بلغ MAX_TRIES — بلا شبكة: نداء جيميناي مستبدَل."""
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import openings  # noqa: E402


class ResumeTest(unittest.TestCase):
    def run_main(self, films, prev, answers):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, 'ops', 'stats'))
        json.dump({'الأفلام': films}, io.open(os.path.join(d, 'ops', 'stats', 'openings.json'), 'w', encoding='utf-8'))
        json.dump({'الأفلام': prev}, io.open(os.path.join(d, 'prev.json'), 'w', encoding='utf-8'))
        io.open(os.path.join(d, 'keys.json'), 'w').write('["AIzaTEST"]')
        called = []

        def fake(self, vid, budget_s=420):
            called.append(vid)
            return answers[vid]
        cwd = os.getcwd()
        os.chdir(d)
        try:
            with mock.patch.object(openings.Gem, 'video', fake), \
                 mock.patch.object(sys, 'argv', ['x', 'out.json', '--keys', 'keys.json', '--resume', 'prev.json']):
                code = openings.main()
            rep = json.load(io.open('out.json', encoding='utf-8'))
        finally:
            os.chdir(cwd)
        return code, called, {f['id']: f for f in rep['الأفلام']}, rep

    def test_keeps_success_retries_failures_and_new(self):
        films = [{'id': i, 'الجهة': 'منافس', 'الوسم': i} for i in ('ok', 'bad', 'new', 'dead')]
        prev = [{'id': 'ok', 'hook': {'score': 8}}, {'id': 'bad', 'error': '429', '_tries': 1},
                {'id': 'dead', 'error': '400', '_tries': openings.MAX_TRIES}]
        code, called, got, rep = self.run_main(films, prev, {'bad': {'hook': {'score': 7}}, 'new': {'error': '503'}})
        self.assertEqual(code, 0)
        self.assertEqual(sorted(called), ['bad', 'new'])           # لا يُعاد الناجح ولا ما بلغ الحدّ
        self.assertEqual(got['ok']['hook']['score'], 8)
        self.assertEqual(got['bad']['hook']['score'], 7)
        self.assertEqual(got['new']['_tries'], 1)
        self.assertNotIn('dead', got)                             # يبقى خارج التقرير حتى يتغيّر الطلب
        self.assertEqual((rep['نجح'], rep['المطلوب']), (2, 4))


if __name__ == '__main__':
    unittest.main()
