# -*- coding: utf-8 -*-
import json
import os
import tempfile
import unittest

from listen_merge import main


class ListenMergeTest(unittest.TestCase):
    def test_keeps_complete_and_fills_missing(self):
        with tempfile.TemporaryDirectory() as d:
            cur = {'a': {'ok': True, 'input_sha256': 'x'}, 'b': {'ok': None, 'why': 'nokeys'}}
            old = {'a': {'ok': False, 'input_sha256': 'old'}, 'b': {'ok': False, 'input_sha256': 'y'},
                   'c': {'ok': True, 'input_sha256': 'z'}, 'd': {'ok': None, 'why': 'nokeys'}}
            json.dump(cur, open(os.path.join(d, 'listen_results.json'), 'w'))
            json.dump(old, open(os.path.join(d, 'old.json'), 'w'))
            main(d, [os.path.join(d, 'old.json'), os.path.join(d, 'missing.json')])
            r = json.load(open(os.path.join(d, 'listen_results.json')))
            self.assertEqual(r['a']['input_sha256'], 'x')      # المكتمل لا يُستبدل
            self.assertIs(r['b']['ok'], False)                 # الناقص يُملأ
            self.assertIn('c', r)
            self.assertNotIn('d', r)                           # الناقص لا يُضاف


if __name__ == '__main__':
    unittest.main()
