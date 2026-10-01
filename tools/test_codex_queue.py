import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "codex_queue.py"


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True)


class CodexQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.prompts = self.tmp / "prompts.json"
        self.prompts.write_text(json.dumps({"F001": "a", "F002": "b", "F003": "c"}), encoding="utf-8")

    def test_write_status_and_shards_cover_every_missing_image_once(self):
        self.assertEqual(run("write", self.tmp, "film", self.prompts).returncode, 0)
        job = json.loads((self.tmp / "film" / "codex_job.json").read_text(encoding="utf-8"))
        self.assertEqual([i["file"] for i in job["items"]], ["images/F001.jpg", "images/F002.jpg", "images/F003.jpg"])
        self.assertEqual(job["items"][0]["size"], [1920, 1080])
        self.assertEqual(run("status", self.tmp, "film").returncode, 3)
        parts = [run("shard", self.tmp, "film", k, 2).stdout.split() for k in (1, 2)]
        self.assertEqual(sorted(parts[0] + parts[1]), ["images/F001.jpg", "images/F002.jpg", "images/F003.jpg"])
        (self.tmp / "film" / "images").mkdir()
        for f in ("F001", "F002", "F003"):
            (self.tmp / "film" / "images" / f"{f}.jpg").write_bytes(b"x")
        self.assertEqual(run("status", self.tmp, "film").returncode, 0)

    def test_list_form_keeps_custom_sizes_and_rejects_duplicates(self):
        self.prompts.write_text(json.dumps([{"file": "thumbs/x-A.png", "prompt": "t", "size": [1280, 720]}]), encoding="utf-8")
        self.assertEqual(run("write", self.tmp, "film", self.prompts).returncode, 0)
        job = json.loads((self.tmp / "film" / "codex_job.json").read_text(encoding="utf-8"))
        self.assertEqual(job["items"][0]["size"], [1280, 720])
        self.prompts.write_text(json.dumps([{"file": "a.jpg", "prompt": "1"}, {"file": "a.jpg", "prompt": "2"}]), encoding="utf-8")
        self.assertNotEqual(run("write", self.tmp, "film", self.prompts).returncode, 0)


if __name__ == "__main__":
    unittest.main()
