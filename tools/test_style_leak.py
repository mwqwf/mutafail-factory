# -*- coding: utf-8 -*-
"""اختبار حارس نطق التعليمات (tools/style_leak.py): الكتلة الممسوكة يُحذف توجيهها — style أو director — وصوتُها، فيُعاد بلا توجيه."""
import json
import os
import subprocess as sp
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = str(Path(__file__).resolve().parent / 'style_leak.py')


class StyleLeak(unittest.TestCase):
    def proj(self, results):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, 'audio'))
        blocks = [{'id': 'a', 'text': 'نص', 'voice': 'Algenib', 'director': '### DIRECTOR\nepic'},
                  {'id': 'b', 'text': 'نص', 'voice': 'Charon', 'style': 'Say slowly'},
                  {'id': 'c', 'text': 'نص', 'voice': 'Algenib', 'director': '### DIRECTOR\nepic'}]
        json.dump(blocks, open(os.path.join(d, 'blocks.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        json.dump(results, open(os.path.join(d, 'listen_results.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        for b in blocks:
            open(os.path.join(d, 'audio', b['id'] + '.wav'), 'wb').write(b'x')
        return d

    def run_tool(self, d):
        return sp.run([sys.executable, TOOL, d], capture_output=True, text=True).returncode

    def test_leak_drops_director_and_style(self):
        d = self.proj({'a': {'ok': False, 'why': 'نطق توجيهاً إنجليزياً', 'written': 'Read this in an epic tone'},
                       'b': {'ok': False, 'why': 'كلام إنجليزي', 'written': 'Say slowly'},
                       'c': {'ok': True}})
        self.assertEqual(self.run_tool(d), 1)
        blocks = {b['id']: b for b in json.load(open(os.path.join(d, 'blocks.json'), encoding='utf-8'))}
        self.assertNotIn('director', blocks['a'])
        self.assertNotIn('style', blocks['b'])
        self.assertIn('director', blocks['c'])                      # السليمة لا تُمسّ
        self.assertFalse(os.path.exists(os.path.join(d, 'audio', 'a.wav')))
        self.assertFalse(os.path.exists(os.path.join(d, 'audio', 'b.wav')))
        self.assertTrue(os.path.exists(os.path.join(d, 'audio', 'c.wav')))

    def test_clean_exits_zero(self):
        d = self.proj({'a': {'ok': True}, 'b': {'ok': False, 'why': 'كلمة ناقصة', 'written': 'نص'}})
        self.assertEqual(self.run_tool(d), 0)
        blocks = {b['id']: b for b in json.load(open(os.path.join(d, 'blocks.json'), encoding='utf-8'))}
        self.assertIn('director', blocks['a'])


if __name__ == '__main__':
    unittest.main()
