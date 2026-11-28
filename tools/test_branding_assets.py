import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import envpaths
import logocheck

ROOT = Path(__file__).resolve().parents[1]
OLD_SEPT25_LOGO = "9bff87636e41d6dd8586bab885dd42adf5af4088c32b3605b15526148e57c2fe"
V2_BATTLES_ICON = "bdfe90779551aac75b04ce9dec85bc7599caf112aa4980ce9eb69bfa750b0d63"


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

    def test_production_logo_matches_v2_battles_icon(self):
        logo = ROOT / 'assets' / 'logo.png'
        icon = ROOT / 'ops' / 'branding' / '2026-11-27-v2' / 'battles' / 'battles_youtube_icon_800x800.png'
        sha = hashlib.sha256(logo.read_bytes()).hexdigest()
        self.assertEqual(sha, hashlib.sha256(icon.read_bytes()).hexdigest())
        self.assertEqual(sha, V2_BATTLES_ICON)
        self.assertNotEqual(sha, OLD_SEPT25_LOGO)

    def test_logo_identity_rejects_retired_sept25_hash(self):
        retired = {"9bff87636e41d6dd8586bab885dd42adf5af4088c32b3605b15526148e57c2fe": "أيقونة 25 سبتمبر 2026"}
        errors = logocheck.check_logo_identity(OLD_SEPT25_LOGO, V2_BATTLES_ICON, retired)
        self.assertTrue(errors)
        self.assertTrue(any("القديم" in e or "متقاعد" in e for e in errors))

    def test_logo_identity_rejects_unknown_hash(self):
        errors = logocheck.check_logo_identity("0" * 64, V2_BATTLES_ICON, {})
        self.assertTrue(errors)
        self.assertTrue(any("لا تطابق" in e for e in errors))

    def test_logo_identity_accepts_approved_hash(self):
        self.assertEqual(logocheck.check_logo_identity(V2_BATTLES_ICON, V2_BATTLES_ICON, {OLD_SEPT25_LOGO: "قديم"}), [])

    def test_logocheck_passes_on_current_v2_logo(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / 'tools' / 'logocheck.py')],
            capture_output=True, text=True, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("بصمة الشعار تطابق الهوية المعتمدة", result.stdout)


if __name__ == '__main__':
    unittest.main()
