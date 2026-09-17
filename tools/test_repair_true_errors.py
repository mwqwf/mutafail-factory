import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "repair_true_errors.py"


class RepairTrueErrors(unittest.TestCase):
    def test_only_current_confirmed_error_is_invalidated(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); (p / "audio").mkdir()
            blocks = [{"id": "a", "text": "أ"}, {"id": "b", "text": "ب"}]
            (p / "blocks.json").write_text(json.dumps(blocks, ensure_ascii=False), encoding="utf-8")
            for ident in ("a", "b"): (p / "audio" / (ident + ".wav")).write_bytes(ident.encode())
            fp = hashlib.sha256("أ".encode() + b"\0" + b"a").hexdigest()
            (p / "listen_results.0.json").write_text(json.dumps({"a":{"ok":False},"b":{"ok":True}}), encoding="utf-8")
            (p / "listen_reviews.0.json").write_text(json.dumps({"a":{"decision":"true_error","input_sha256":fp}}), encoding="utf-8")
            out = p / "repair.json"
            result = subprocess.run([sys.executable, str(TOOL), str(p), str(out)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((p / "audio/a.wav").exists())
            self.assertTrue((p / "audio/b.wav").exists())
            self.assertNotIn("a", json.loads((p / "listen_results.0.json").read_text()))
            self.assertEqual(json.loads(out.read_text())["ids"], ["a"])


if __name__ == "__main__": unittest.main()
