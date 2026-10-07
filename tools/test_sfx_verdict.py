import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sfx_verdict as v  # noqa: E402


class SfxVerdictTests(unittest.TestCase):
    def setUp(self):
        self.clip = os.path.join(tempfile.mkdtemp(), "F001.mp4")
        Path(self.clip).write_bytes(b"first clip")

    def test_verdict_is_bound_to_clip_hash(self):
        v.write(self.clip, "CLEAN", True)
        self.assertTrue(v.ok(self.clip) and v.judged(self.clip))
        Path(self.clip).write_bytes(b"re-animated clip under the same id")
        self.assertFalse(v.ok(self.clip), "مقطعٌ أعيد تحريكه لا يرث حكم سابقه")
        self.assertFalse(v.judged(self.clip))

    def test_legacy_plain_ok_file_is_not_trusted(self):
        Path(self.clip[:-4] + ".ok").write_text("CLEAN", encoding="utf-8")
        self.assertFalse(v.ok(self.clip))
        self.assertFalse(v.judged(self.clip))

    def test_reject_replaces_ok(self):
        v.write(self.clip, "CLEAN", True)
        v.write(self.clip, "MUSIC", False)
        self.assertFalse(os.path.exists(self.clip[:-4] + ".ok"))
        self.assertFalse(v.ok(self.clip))
        self.assertTrue(v.judged(self.clip))


if __name__ == "__main__":
    unittest.main()
