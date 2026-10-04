# -*- coding: utf-8 -*-
"""اختبارات العيّنة القصيرة (tools/sample_cut.py) وبحث خريطة العمق (tools/kb3d.depth_of)."""
import json
import os
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sample_cut  # noqa: E402


def wav(f, seconds, rate=24000):
    with wave.open(f, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b'\x00\x00' * int(seconds * rate))


class SampleCut(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); p = self.d
        for sub in ('audio', 'images', 'cards', 'img'):
            os.makedirs(os.path.join(p, sub))
        blocks = [{'id': i, 'text': 'نص'} for i in ('n_01', 'n_02', 'n_03', 'n_04', 'd_001')] + [{'id': 'r_001', 'text': 'ر', 'reel_only': True}]
        shots = [{'id': 'A', 'blocks': ['n_01']}, {'id': 'B', 'blocks': ['n_02', 'n_03']}, {'id': 'C', 'blocks': ['n_04']},
                 {'id': 'D', 'blocks': ['d_001']}]
        sections = [{'id': 'n_01', 'title': 'افتتاحية'}, {'id': 'd_001', 'title': 'تمهيد', 'phase': 'setup'}]
        for name, obj in (('blocks.json', blocks), ('shots.json', shots), ('sections.json', sections),
                          ('publish.json', {'voice_filter': 'atempo=1.05,adeclick'})):
            json.dump(obj, open(os.path.join(p, name), 'w', encoding='utf-8'), ensure_ascii=False)
        for b, s in (('n_01', 4.2), ('n_02', 3.0), ('n_03', 2.1), ('d_001', 5.0)):   # n_04 صوتها ناقص
            wav(os.path.join(p, 'audio', b + '.wav'), s)

    def test_stops_at_first_missing_audio(self):
        out = os.path.join(self.d, 'sample')
        self.assertEqual(sample_cut.cut(self.d, out), ['A', 'B'])
        self.assertEqual([b['id'] for b in json.load(open(os.path.join(out, 'blocks.json'), encoding='utf-8'))], ['n_01', 'n_02', 'n_03'])
        self.assertEqual([x['id'] for x in json.load(open(os.path.join(out, 'sections.json'), encoding='utf-8'))], ['n_01'])
        self.assertTrue(os.path.islink(os.path.join(out, 'audio')))
        self.assertEqual(json.load(open(os.path.join(out, 'reels.json'), encoding='utf-8')), [])

    def test_max_seconds(self):
        self.assertEqual(sample_cut.cut(self.d, os.path.join(self.d, 's2'), max_s=5.0), ['A'])


class DepthPath(unittest.TestCase):
    def test_depth_found_in_sibling_img(self):
        import kb3d
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, 'images')); os.makedirs(os.path.join(d, 'img'))
        src = os.path.join(d, 'images', 'K19.jpg'); open(src, 'wb').close()
        self.assertEqual(kb3d.depth_of(src), os.path.join(d, 'images', 'K19_depth.png'))   # لا عمق ⇒ المسار الأصلي (تدرّج)
        open(os.path.join(d, 'img', 'K19_depth.png'), 'wb').close()
        self.assertEqual(kb3d.depth_of(src), os.path.join(d, 'img', 'K19_depth.png'))
        open(os.path.join(d, 'images', 'K19_depth.png'), 'wb').close()
        self.assertEqual(kb3d.depth_of(src), os.path.join(d, 'images', 'K19_depth.png'))   # بجانب الصورة أوّلاً


if __name__ == '__main__':
    unittest.main()
