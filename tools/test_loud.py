import os
import re
import shutil
import subprocess as sp
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import loud  # noqa: E402


def lufs(f):
    err = sp.run(['ffmpeg', '-hide_banner', '-nostats', '-i', f, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                 capture_output=True, text=True).stderr
    s = err[err.rfind('Summary:'):]
    return float(re.search(r'I:\s*(-?[0-9.]+) LUFS', s).group(1)), float(re.search(r'Peak:\s*(-?[0-9.]+) dBFS', s).group(1))


@unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg غير متاح')
class LoudTest(unittest.TestCase):
    """درس مؤتة 2026-10-07: ريلزاتٌ بلا تسويةٍ خرجت بين −16.5 و−26 LUFS — فأيُّ مدخلٍ يخرج عند −14 ± 1 وذروته دون −1."""

    def make(self, d, name, vol):
        f = os.path.join(d, name + '.wav')
        sp.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anoisesrc=c=pink:r=24000:d=8',
                '-af', "volume='%s*(0.55+0.45*sin(2*PI*3*t))':eval=frame" % vol, '-ac', '1', f], check=True)
        return f

    def test_quiet_and_loud_inputs_reach_minus_14(self):
        with tempfile.TemporaryDirectory() as d:
            for name, vol in (('quiet', 0.02), ('loud', 0.9)):
                out = loud.norm(self.make(d, name, vol), os.path.join(d, name + '_n.wav'))
                i, tp = lufs(out)
                self.assertAlmostEqual(i, -14.0, delta=1.0, msg='%s: %.1f LUFS' % (name, i))
                self.assertLessEqual(tp, -0.5, '%s: ذروة %.1f' % (name, tp))

    def test_silence_does_not_crash(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, 's.wav')
            sp.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono', '-t', '2', src], check=True)
            self.assertTrue(os.path.getsize(loud.norm(src, os.path.join(d, 's_n.wav'))) > 0)


if __name__ == '__main__':
    unittest.main()
