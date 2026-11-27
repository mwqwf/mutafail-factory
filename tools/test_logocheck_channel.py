# -*- coding: utf-8 -*-
"""logocheck يرفض شعار القناة الخطأ ويقبل شعار القناة الصحيحة."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envpaths  # noqa: E402
import logocheck as lc  # noqa: E402


def badge(asset, size=120, opacity=0.72):
    im = Image.open(asset).convert('RGBA').resize((size, size), Image.LANCZOS)
    m = Image.new('L', (480, 480), 0)
    ImageDraw.Draw(m).ellipse([4, 4, 476, 476], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(3)).resize((size, size), Image.LANCZOS)
    o = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    o.paste(im, (0, 0), m)
    o.putalpha(o.split()[3].point(lambda v: int(v * opacity)))
    return o


def frame_with(logo, size=(1920, 1080), bg=(30, 40, 50)):
    im = Image.new('RGB', size, bg)
    b = badge(logo)
    x, y = size[0] - 46 - 120, 46
    im.paste(b, (x, y), b)
    return im


def _mp4_from(im, path):
    png = path + '.png'
    im.save(png)
    subprocess.run(
        ['ffmpeg', '-v', 'error', '-y', '-loop', '1', '-i', png, '-t', '4', '-r', '25',
         '-c:v', 'libx264', '-pix_fmt', 'yuv420p', path], check=True)


HIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'logo.png')
HK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                  'ops/branding/2026-11-27-v2/hikayat/hikayat_youtube_icon_800x800.png')


class Identity(unittest.TestCase):
    def test_history_logo_matches_and_hikayat_is_rejected(self):
        self.assertTrue(os.path.exists(HIST) and os.path.exists(HK))
        ok = frame_with(HIST)
        bad = frame_with(HK)
        box = lc.layout_box('film', 1920, 1080)
        s_ok = lc.logo_score(ok, box, HIST)
        s_wrong_on_ok = lc.logo_score(ok, box, HK)
        s_bad = lc.logo_score(bad, box, HIST)
        s_hk_on_bad = lc.logo_score(bad, box, HK)
        self.assertGreaterEqual(s_ok, 0.55)
        self.assertGreater(s_ok, s_wrong_on_ok + 0.05)
        self.assertGreaterEqual(s_hk_on_bad, 0.55)
        self.assertGreater(s_hk_on_bad, s_bad + 0.05)
        errs = lc.check_identity(ok, 'film', HIST, {'hikayat': HK})
        self.assertEqual(errs, [])
        errs = lc.check_identity(bad, 'film', HIST, {'hikayat': HK})
        self.assertTrue(any('خاطئ' in e or 'hikayat' in e or 'قناة' in e for e in errs), errs)

    def test_cli_rejects_wrong_channel_logo(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'out.mp4')
            base = os.path.join(d, 'base.mp4')
            _mp4_from(Image.new('RGB', (1920, 1080), (30, 40, 50)), base)
            _mp4_from(frame_with(HK), out)
            os.environ.pop('MUTAFAIL_CHANNEL', None)
            r = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'logocheck.py'),
                                out, base, 'film'], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertTrue('خاطئ' in r.stdout + r.stderr or 'شعار' in r.stdout + r.stderr, r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main()
