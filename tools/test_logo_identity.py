"""إطار مشفر فعلياً: يُقبل الشعار الحالي ويُرفض شعار آخر أو مخرج مفقود."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from PIL import Image
from logo_identity import expected_frame
import envpaths


class LogoIdentityTests(unittest.TestCase):
    def test_encoded_current_and_wrong_logo(self):
        self.check_layout('film', (1920, 1080))

    def test_encoded_reel_logo(self):
        self.check_layout('reel', (1080, 1920))

    def check_layout(self, layout, dimensions):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = Image.new('RGB', dimensions, '#456078')
            base.save(root / 'base.png')
            expected_frame(base, envpaths.logo(), layout).save(root / 'correct.png')
            wrong = Image.new('RGB', (800, 800), '#f818ee')
            wrong.save(root / 'wrong-logo.png')
            expected_frame(base, root / 'wrong-logo.png', layout).save(root / 'wrong.png')
            for name in ('base', 'correct', 'wrong'):
                subprocess.run([envpaths.FF, '-v', 'error', '-y', '-loop', '1', '-i',
                                str(root / (name + '.png')), '-t', '4', '-r', '5',
                                '-c:v', 'libx264', '-threads', '2', '-pix_fmt', 'yuv420p',
                                str(root / (name + '.mp4'))], check=True)
            Image.new('RGBA', dimensions, (0, 0, 0, 0)).save(root / 'overlay.png')
            tool = Path(__file__).with_name('logocheck.py')
            for name, expected in (('correct', 0), ('wrong', 1), ('missing', 1)):
                run = subprocess.run([sys.executable, str(tool), str(root / (name + '.mp4')),
                                      str(root / 'base.mp4'), layout] +
                                     ([str(root / 'overlay.png')] if layout == 'reel' else []),
                                     capture_output=True, text=True)
                self.assertEqual(run.returncode, expected, run.stdout + run.stderr)

