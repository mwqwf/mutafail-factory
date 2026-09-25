import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from logo_receipt import digest
import envpaths

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
        for name, layout in [("film.mp4", "film"), ("reels/r1.mp4", "reel"), ("reels/r2.mp4", "reel")]:
            if not (root / name).exists():
                continue
            (root / (name + ".logo.json")).write_text(json.dumps({
                "passed": True, "layout": layout, "video_sha256": digest(root / name),
                "logo_sha256": digest(envpaths.logo())}))
        return tmp, root

    def run_tool(self, root):
        return subprocess.run([sys.executable, str(TOOL), str(root), "amal-2"], cwd=ROOT,
                              capture_output=True, text=True)

    def test_accepts_exact_public_bundle(self):
        tmp, root = self.project(); self.addCleanup(tmp.cleanup)
        result = self.run_tool(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_missing_logo_receipt(self):
        tmp, root = self.project(); self.addCleanup(tmp.cleanup)
        (root / "film.mp4.logo.json").unlink()
        self.assertNotEqual(self.run_tool(root).returncode, 0)

    def test_rejects_changed_video(self):
        tmp, root = self.project(); self.addCleanup(tmp.cleanup)
        (root / "film.mp4").write_bytes(b"changed")
        self.assertNotEqual(self.run_tool(root).returncode, 0)

    def test_rejects_old_logo(self):
        tmp, root = self.project(); self.addCleanup(tmp.cleanup)
        receipt = root / "reels/r2.mp4.logo.json"
        data = json.loads(receipt.read_text()); data["logo_sha256"] = "old"
        receipt.write_text(json.dumps(data))
        self.assertNotEqual(self.run_tool(root).returncode, 0)

    def test_rejects_non_public_film(self):
        tmp, root = self.project(public_now=False); self.addCleanup(tmp.cleanup)
        self.assertNotEqual(self.run_tool(root).returncode, 0)

    def test_rejects_wrong_reel_set(self):
        tmp, root = self.project(reel_files=("r1.mp4", "r3.mp4")); self.addCleanup(tmp.cleanup)
        self.assertNotEqual(self.run_tool(root).returncode, 0)


if __name__ == "__main__": unittest.main()
