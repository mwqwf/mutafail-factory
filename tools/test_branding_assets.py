import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import envpaths

ROOT = Path(__file__).resolve().parents[1]


class BrandingAssetsTests(unittest.TestCase):
    def test_repository_logo_wins_over_legacy_device_copy(self):
        with patch('envpaths.os.path.exists', return_value=True):
            self.assertEqual(Path(envpaths.logo()), ROOT / 'assets' / 'logo.png')

    def test_missing_requested_video_fails_the_visual_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / 'tools' / 'logocheck.py'), str(Path(directory) / 'missing.mp4')],
                capture_output=True, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
            self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
