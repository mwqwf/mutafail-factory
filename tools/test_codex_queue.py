import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageFile

import codex_queue

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "codex_queue.py"


def png(path, w=1920, h=1080):
    """صورةٌ حقيقية قابلة لفكّ البكسلات؛ الترويسة وحدها لا تكفي."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (w, h), (38, 75, 112)).save(path, format="PNG")


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True)


class CodexQueueTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp = Path(directory.name)
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
        self.assertEqual(run("status", self.tmp, "film").returncode, 3, "ملفٌّ ليس صورةً لا يُعدّ منجزاً")
        for f in ("F001", "F002"):
            png(self.tmp / "film" / "images" / f"{f}.jpg")
        png(self.tmp / "film" / "images" / "F003.jpg", 1024, 576)
        r = run("status", self.tmp, "film")
        self.assertEqual(r.returncode, 3, "المقاس المغاير ناقص")
        self.assertIn("F003", r.stdout)
        png(self.tmp / "film" / "images" / "F003.jpg")
        self.assertEqual(run("status", self.tmp, "film").returncode, 0)

    def test_shards_are_stable_when_parts_start_at_different_times(self):
        self.prompts.write_text(json.dumps({k: k for k in ("A", "B", "C", "D")}), encoding="utf-8")
        run("write", self.tmp, "film", self.prompts)
        first = run("shard", self.tmp, "film", 1, 2).stdout.split()
        png(self.tmp / "film" / "images" / "A.jpg")            # الجزء الأوّل أنجز A قبل أن يبدأ الثاني
        second = run("shard", self.tmp, "film", 2, 2).stdout.split()
        self.assertEqual(first, ["images/A.jpg", "images/C.jpg"])
        self.assertEqual(second, ["images/B.jpg", "images/D.jpg"], "لا يأخذ C من نصيب غيره ولا يُسقط D")

    def test_paths_outside_the_film_folder_are_rejected(self):
        self.prompts.write_text(json.dumps([{"file": "../other/x.jpg", "prompt": "p"}]), encoding="utf-8")
        self.assertNotEqual(run("write", self.tmp, "film", self.prompts).returncode, 0)

    def test_list_form_keeps_custom_sizes_and_rejects_duplicates(self):
        self.prompts.write_text(json.dumps([{"file": "thumbs/x-A.png", "prompt": "t", "size": [1280, 720]}]), encoding="utf-8")
        self.assertEqual(run("write", self.tmp, "film", self.prompts).returncode, 0)
        job = json.loads((self.tmp / "film" / "codex_job.json").read_text(encoding="utf-8"))
        self.assertEqual(job["items"][0]["size"], [1280, 720])
        self.prompts.write_text(json.dumps([{"file": "a.jpg", "prompt": "1"}, {"file": "a.jpg", "prompt": "2"}]), encoding="utf-8")
        self.assertNotEqual(run("write", self.tmp, "film", self.prompts).returncode, 0)

    def test_header_only_png_is_missing_in_status_and_its_original_shard(self):
        run("write", self.tmp, "film", self.prompts)
        images = self.tmp / "film" / "images"
        for name in ("F001", "F002", "F003"):
            png(images / f"{name}.jpg")
        (images / "F002.jpg").write_bytes(
            b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
            + struct.pack(">II", 1920, 1080) + b"\x08\x02\x00\x00\x00")
        result = run("status", self.tmp, "film")
        self.assertEqual(result.returncode, 3)
        self.assertIn("2/3", result.stdout)
        self.assertIn("F002.jpg", result.stdout)
        self.assertEqual(run("shard", self.tmp, "film", 1, 2).stdout.split(), [])
        self.assertEqual(run("shard", self.tmp, "film", 2, 2).stdout.split(), ["images/F002.jpg"])

    def test_real_jpeg_and_png_are_complete(self):
        for image_format in ("JPEG", "PNG"):
            with self.subTest(image_format=image_format):
                file = self.tmp / image_format
                Image.new("RGB", (1280, 720), "navy").save(file, format=image_format)
                self.assertTrue(codex_queue.done(self.tmp, {"file": file.name, "size": [1280, 720]}))

    def test_truncated_jpeg_with_readable_dimensions_is_not_complete(self):
        file = self.tmp / "broken.jpg"
        Image.new("RGB", (320, 180), "navy").save(file)
        file.write_bytes(file.read_bytes()[:-20])
        with Image.open(file) as image:
            self.assertEqual(image.size, (320, 180))
            with self.assertRaises(OSError):
                image.load()
        self.assertFalse(codex_queue.done(self.tmp, {"file": file.name, "size": [320, 180]}))

    def test_truncated_png_is_not_complete(self):
        file = self.tmp / "broken.png"
        png(file, 320, 180)
        file.write_bytes(file.read_bytes()[:50])
        self.assertIsNone(codex_queue.dims(file))

    def test_png_with_bad_chunk_checksum_is_not_complete(self):
        file = self.tmp / "bad-checksum.png"
        png(file, 320, 180)
        data = bytearray(file.read_bytes())
        data[-13] ^= 1  # آخر بايت من بصمة مقطع IDAT، قبل مقطع IEND.
        file.write_bytes(data)
        self.assertIsNone(codex_queue.dims(file))

    def test_non_images_empty_files_and_directories_are_missing(self):
        for name, content in (("empty.png", b""), ("text.jpg", b"not an image")):
            (self.tmp / name).write_bytes(content)
            self.assertIsNone(codex_queue.dims(self.tmp / name))
        self.assertIsNone(codex_queue.dims(self.tmp / "absent.png"))
        self.assertIsNone(codex_queue.dims(self.tmp))

    def test_other_image_formats_are_not_accepted_as_queue_images(self):
        file = self.tmp / "renamed.jpg"
        Image.new("RGB", (32, 32)).save(file, format="GIF")
        self.assertIsNone(codex_queue.dims(file))

    def test_large_image_guard_is_preserved(self):
        file = self.tmp / "large.png"
        png(file, 32, 32)
        for limit in (600, 100):
            with self.subTest(limit=limit), patch.object(Image, "MAX_IMAGE_PIXELS", limit):
                self.assertIsNone(codex_queue.dims(file))

    def test_truncated_image_setting_is_temporarily_disabled_and_restored(self):
        file = self.tmp / "broken.jpg"
        Image.new("RGB", (320, 180)).save(file)
        file.write_bytes(file.read_bytes()[:-20])
        with patch.object(ImageFile, "LOAD_TRUNCATED_IMAGES", True):
            self.assertIsNone(codex_queue.dims(file))
            self.assertTrue(ImageFile.LOAD_TRUNCATED_IMAGES)


if __name__ == "__main__":
    unittest.main()

