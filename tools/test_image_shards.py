# -*- coding: utf-8 -*-
"""اختبارُ قسمةِ الصور على العدّائين — أسرعُ بلا أن يسقط شيء.

⛔ الخطرُ الذي يحرسه: قسمةٌ تُسقط صورةً فيُركَّب فيلمٌ ناقصُ لقطة، أو قسمةٌ تُكرّرها
   فتُنفق دقائقُ مرّتين. ولذلك يُشترط أن تكون القسمةُ **تجزئةً تامّةً**: كلُّ صورةٍ
   في سهمٍ واحدٍ لا غير، ومجموعُ الأسهم هو القائمةُ كلُّها بترتيبها.
"""
import unittest
from pathlib import Path

import imgdl3

ROOT = Path(__file__).resolve().parents[1]
FILM = (ROOT / ".github/workflows/film.yml").read_text(encoding="utf-8")


class ShardPartition(unittest.TestCase):
    def test_partition_is_exact_for_many_sizes(self):
        for total in (1, 5, 6, 7, 75, 83, 200):
            items = [{"id": "b%03d" % i} for i in range(total)]
            for shards in (1, 2, 3, 6, 8):
                seen = []
                for shard in range(shards):
                    seen += imgdl3.slice_for(items, shard, shards)
                self.assertEqual(sorted(x["id"] for x in seen),
                                 sorted(x["id"] for x in items),
                                 "قسمةٌ ناقصةٌ أو مكرّرة: %d صورة على %d أسهم" % (total, shards))
                self.assertEqual(len(seen), total)

    def test_shards_are_balanced(self):
        items = [{"id": "b%03d" % i} for i in range(75)]
        sizes = [len(imgdl3.slice_for(items, s, 6)) for s in range(6)]
        self.assertLessEqual(max(sizes) - min(sizes), 1, "أسهمٌ غيرُ متوازنة: %s" % sizes)

    def test_bad_shard_arguments_fail_closed(self):
        with self.assertRaises(SystemExit):
            imgdl3._shard_args(["--shard", "6", "--shards", "6"])
        with self.assertRaises(SystemExit):
            imgdl3._shard_args(["--shard", "0", "--shards", "0"])

    def test_default_is_the_whole_list(self):
        self.assertEqual(imgdl3._shard_args([]), (0, 1))


class FilmWorkflowUsesShards(unittest.TestCase):
    def test_images_job_runs_six_shards(self):
        self.assertIn("matrix: { shard: [0, 1, 2, 3, 4, 5] }", FILM)
        self.assertIn("python tools/imgdl3.py proj --shard ${{ matrix.shard }} --shards 6", FILM)

    def test_each_shard_uploads_its_own_artifact(self):
        self.assertIn("name: 'img-${{ matrix.shard }}'", FILM)

    def test_consumers_read_every_shard(self):
        # ⛔ `name: img` وحدَه بعد القسمة يعني فيلماً بصورِ سهمٍ واحد
        self.assertNotIn("name: img,", FILM)
        self.assertNotIn("          name: img\n", FILM)
        self.assertGreaterEqual(FILM.count("pattern: 'img*'"), 4)

    def test_no_in_runner_parallelism_is_introduced(self):
        """مذهبُ «طابورٌ واحدٌ لكلّ عنوان» باقٍ: التسريعُ بعدّائين لا بخيوط."""
        src = (ROOT / "tools" / "imgdl3.py").read_text(encoding="utf-8")
        for banned in ("ThreadPool", "multiprocessing", "concurrent.futures", "asyncio"):
            self.assertNotIn(banned, src)


if __name__ == "__main__":
    unittest.main()
