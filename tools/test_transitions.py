# -*- coding: utf-8 -*-
"""اختبارات الانتقالات (tools/transitions.py): السياسة، وأنّ عدد الإطارات الكلّيّ لا يتغيّر فيبقى الصوت متزامناً."""
import os
import shutil
import subprocess as sp
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import transitions as t  # noqa: E402

HAS_FF = shutil.which('ffmpeg') is not None and shutil.which('ffprobe') is not None
ENC = ['-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', '-r', '25']


class Plan(unittest.TestCase):
    def setUp(self):
        self.sections = [{'id': 'n1', 'title': 'افتتاحية'}, {'id': 'd1', 'title': 'تمهيد', 'phase': 'setup'},
                         {'id': 'd5', 'title': 'المعركة', 'phase': 'battle'}]

    def shot(self, sid, block, **kw):
        return {'id': sid, 'blocks': [block], 'file': sid + '.jpg', **kw}

    def test_chapter_start_fades_to_black(self):
        shots = [self.shot('A', 'n1'), self.shot('B', 'd1')]
        self.assertEqual(t.plan(shots, self.sections), [('fadeblack', 0.8)])

    def test_same_image_dissolves_and_flash_cuts(self):
        shots = [self.shot('A', 'd1'), {'id': 'B', 'blocks': ['d2'], 'file': 'A.jpg'}, self.shot('C', 'd3', flash=True)]
        self.assertEqual(t.plan(shots, self.sections), [('fade', 0.48), None])

    def test_override_and_unknown_name(self):
        shots = [self.shot('A', 'd1'), self.shot('B', 'd2', tr=['vertopen', 0.5]), self.shot('C', 'd3', tr='nonsense'),
                 self.shot('D', 'd4', tr='cut')]
        self.assertEqual(t.plan(shots, self.sections), [('vertopen', 0.48), None, None])

    def test_battle_mostly_hard_cuts(self):
        shots = [self.shot('S%d' % i, 'd%d' % (5 + i)) for i in range(9)]
        tp = t.plan(shots, self.sections)
        self.assertLessEqual(sum(1 for x in tp if x), 2)
        self.assertTrue(all(x[0] in t.WHIP for x in tp if x))


@unittest.skipUnless(HAS_FF, 'ffmpeg غير مثبّت')
class FramesPreserved(unittest.TestCase):
    def test_total_frames_unchanged(self):
        d = tempfile.mkdtemp()
        segs = []
        for i, (n, c) in enumerate(((50, 'red'), (40, 'green'), (60, 'blue'))):
            f = os.path.join(d, 's%d.mp4' % i)
            sp.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=%s:s=320x180:r=25' % c, '-frames:v', str(n)] + ENC + [f],
                   check=True)
            segs.append(f)
        out = t.apply(segs, [('fade', 0.48), ('vertopen', 0.32)], d, ENC, 'v')
        self.assertEqual(sum(t.frames(x) for x in out), 150)
        self.assertEqual(len(out), 5)


if __name__ == '__main__':
    unittest.main()
