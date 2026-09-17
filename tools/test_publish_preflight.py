import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "publish_preflight.py"


class PublishPreflight(unittest.TestCase):
    def project(self, public_now=True, reel_files=("r1.mp4", "r2.mp4")):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / "reels").mkdir()
        (root / "meta.json").write_text(json.dumps({"slug": "amal-2"}), encoding="utf-8")
        publish = {"publicNow": public_now, "playlistId": "PL-test",
                   "reels": [{"file": name, "description": "{FILM_URL}"}
                             for name in reel_files]}
        (root / "publish.json").write_text(json.dumps(publish), encoding="utf-8")
        for name in ("film.mp4", "thumb-a.jpg", "الفصول.txt"):
            (root / name).write_bytes(b"x")
        for name in reel_files:
            (root / "reels" / name).write_bytes(b"x")
        return tmp, root

    def run_tool(self, root):
        return subprocess.run([sys.executable, str(TOOL), str(root)], cwd=ROOT,
                              capture_output=True, text=True)

    def test_accepts_exact_public_bundle(self):
        tmp, root = self.project(); self.addCleanup(tmp.cleanup)
        result = self.run_tool(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_non_public_film(self):
        tmp, root = self.project(public_now=False); self.addCleanup(tmp.cleanup)
        self.assertNotEqual(self.run_tool(root).returncode, 0)

    def test_rejects_wrong_reel_set(self):
        tmp, root = self.project(reel_files=("r1.mp4", "r3.mp4")); self.addCleanup(tmp.cleanup)
        self.assertNotEqual(self.run_tool(root).returncode, 0)


if __name__ == "__main__": unittest.main()
