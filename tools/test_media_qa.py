import os
import shutil
import subprocess as sp
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import media_qa  # noqa: E402


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg غير متاح')
class MediaQaTest(unittest.TestCase):
    """درس مؤتة 2026-10-07: فحصٌ بـ-v error لم يرَ تجمّد آخر الريلزات — فهنا مقطعٌ مصنوعٌ بتجمّدٍ معروف يجب أن يُكشف."""

    def make(self, d, freeze):
        f = os.path.join(d, 'v_%d.mp4' % freeze)
        vf = 'tpad=stop_mode=clone:stop_duration=3' if freeze else 'null'
        sp.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=s=320x240:r=25:d=%d' % (3 if freeze else 6),
                '-f', 'lavfi', '-i', 'sine=f=440:d=6', '-vf', vf, '-t', '6', '-c:v', 'libx264', '-preset', 'ultrafast',
                '-pix_fmt', 'yuv420p', '-c:a', 'aac', f], check=True)
        return f

    def test_freeze_at_the_end_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            errs, info = media_qa.check(self.make(d, True))
            self.assertTrue(any('تجمّد' in e for e in errs), errs)
            self.assertTrue(info['تجمّد'] and info['تجمّد'][0][1] >= 2.0)

    def test_moving_video_has_no_freeze(self):
        with tempfile.TemporaryDirectory() as d:
            errs, info = media_qa.check(self.make(d, False))
            self.assertFalse(any('تجمّد' in e for e in errs), errs)
            self.assertEqual(info['تجمّد'], [])


if __name__ == '__main__':
    unittest.main()
