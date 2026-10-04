# -*- coding: utf-8 -*-
"""اختبارات الانتقالات المتداخلة (tools/transitions.py): السياسة، والمواءمة مع اللقطات القصيرة، وأنّ عدد الإطارات الكلّيّ
لا يتغيّر فيبقى الصوت متزامناً، وأنّ الانتقال تداخلٌ حيّ لا إطارٌ مجمَّد."""
import importlib.util
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
HAS_CV = importlib.util.find_spec('cv2') is not None and importlib.util.find_spec('numpy') is not None
ENC = ['-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', '-r', '25', '-an']


class Plan(unittest.TestCase):
    def setUp(self):
        self.sections = [{'id': 'n1', 'title': 'افتتاحية'}, {'id': 'd1', 'title': 'تمهيد', 'phase': 'setup'},
                         {'id': 'd5', 'title': 'المعركة', 'phase': 'battle'}]

    def shot(self, sid, block, **kw):
        return {'id': sid, 'blocks': [block], 'file': sid + '.jpg', **kw}

    def test_chapter_start_fades_to_black(self):
        shots = [self.shot('A', 'n1'), self.shot('B', 'd1')]
        self.assertEqual(t.plan(shots, self.sections), [('fadeblack', 0.96)])

    def test_same_image_dissolves_and_flash_cuts(self):
        shots = [self.shot('A', 'd1'), {'id': 'B', 'blocks': ['d2'], 'file': 'A.jpg'}, self.shot('C', 'd3', flash=True)]
        self.assertEqual(t.plan(shots, self.sections), [('fade', 0.64), None])

    def test_override_old_names_become_soft(self):
        shots = [self.shot('A', 'd1'), self.shot('B', 'd2', tr=['vertopen', 0.5]), self.shot('C', 'd3', tr='nonsense'),
                 self.shot('D', 'd4', tr='cut'), self.shot('E', 'd4b', tr='hlslice')]
        self.assertEqual(t.plan(shots, self.sections), [('open_v', 0.48), None, None, ('wipe', 0.8)])

    def test_every_boundary_overlaps_outside_battle(self):
        # حكم المالك: «بدلاً منها صورٌ متداخلة» — لا قطعَ حادّاً إلا حيث الومضة هي الانتقال
        shots = [self.shot('S%d' % i, 'd1' if i == 0 else 'x%d' % i) for i in range(8)]
        tp = t.plan(shots, self.sections)
        self.assertTrue(all(x and x[0] in t.KINDS and 0.64 <= x[1] <= 0.96 for x in tp))

    def test_battle_fast_overlaps(self):
        shots = [self.shot('S%d' % i, 'd%d' % (5 + i)) for i in range(9)]
        tp = t.plan(shots, self.sections)
        self.assertTrue(all(x and x[1] <= 0.40 for x in tp))
        self.assertGreaterEqual(len({x[0] for x in tp}), 4)       # تتنوّع

    def test_fit_keeps_two_own_frames(self):
        nfr = [30, 8, 30]
        half = t.fit(nfr, [('fade', 0.96), ('fade', 0.96)])
        self.assertLessEqual(half[0] + half[1], 8 - 2)
        self.assertTrue(all(h <= t.HF for h in half))
        self.assertEqual(t.fit([40, 40], [None]), [0])


@unittest.skipUnless(HAS_FF and HAS_CV, 'ffmpeg أو numpy/cv2 غير مثبّتة')
class Assemble(unittest.TestCase):
    def seg(self, d, name, n, c):
        """مقطعٌ بمقبضين: HF إطاراً من لونٍ داكن قبل اللقطة وبعدها، وبينهما n إطاراً بلونها."""
        f = os.path.join(d, name + '.mp4')
        sp.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=%s:s=320x180:r=25' % c, '-frames:v', str(n + 2 * t.HF)]
               + ENC + [f], check=True)
        return f

    def test_total_frames_unchanged_and_blend_is_live(self):
        import numpy as np
        d = tempfile.mkdtemp()
        nfr = [50, 40, 60]
        segs = [self.seg(d, 's%d' % i, n, c) for i, (n, c) in enumerate(zip(nfr, ('red', 'green', 'blue')))]
        out = os.path.join(d, 'out.mp4')
        n = t.assemble(segs, nfr, [('fade', 0.48), ('open_v', 0.32)], out, ENC, size=(320, 180))
        self.assertEqual(n, 150)
        self.assertEqual(t.frames(out), 150)
        # منتصف الانتقال الأوّل (الإطار 50) مزيجٌ من الأحمر والأخضر لا أحدهما
        raw = sp.run(['ffmpeg', '-v', 'error', '-i', out, '-vf', 'select=eq(n\\,50)', '-frames:v', '1', '-f', 'rawvideo',
                      '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
        px = np.frombuffer(raw, np.uint8).reshape(180, 320, 3)[90, 160].astype(int)
        self.assertTrue(px[0] > 40 and px[1] > 40, px)

    def test_blend_kinds_return_frames(self):
        import numpy as np
        A = np.full((90, 160, 3), 200, np.uint8); B = np.zeros((90, 160, 3), np.uint8)
        for name in sorted(t.KINDS):
            for p in (0.1, 0.5, 0.9):
                f = t.blend(name, A, B, p)
                self.assertEqual(f.shape, A.shape, name); self.assertEqual(f.dtype, np.uint8, name)
            self.assertGreater(int(t.blend(name, A, B, 0.02).mean()), int(t.blend(name, A, B, 0.98).mean()), name)


if __name__ == '__main__':
    unittest.main()
