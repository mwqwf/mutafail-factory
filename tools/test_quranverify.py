# -*- coding: utf-8 -*-
"""حارسٌ على حارس النصّ القرآنيّ: يمسك التحريفَ ولا يُخفَّف."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quranverify as Q  # noqa: E402

M = Q.load_mushaf()


def run(text):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text)
    try:
        return Q.audit_files([f.name], M)[0]
    finally:
        os.unlink(f.name)


class QuranGuard(unittest.TestCase):
    def test_mushaf_complete(self):
        for seqs in M:
            self.assertEqual(len(seqs), 114)

    def test_exact_verse_passes(self):
        self.assertEqual(run("d_001|C|قَالَ تَعَالَى: ﴿وَالْخَيْلَ وَالْبِغَالَ وَالْحَمِيرَ لِتَرْكَبُوهَا وَزِينَةً﴾\n"), [])

    def test_consecutive_verses_pass(self):
        self.assertEqual(run("d_001|C|﴿فَإِنَّ مَعَ الْعُسْرِ يُسْرًا إِنَّ مَعَ الْعُسْرِ يُسْرًا﴾\n"), [])

    def test_changed_word_blocked(self):
        self.assertTrue(run("d_001|C|﴿فَإِنَّ مَعَ الْعُسْرِ فَرَجًا﴾\n"))

    def test_missing_word_blocked(self):
        self.assertTrue(run("d_001|C|﴿وَالْخَيْلَ وَالْحَمِيرَ لِتَرْكَبُوهَا﴾\n"))

    def test_reordered_blocked(self):
        self.assertTrue(run("d_001|C|﴿يُسْرًا الْعُسْرِ مَعَ فَإِنَّ﴾\n"))

    def test_unmarked_quran_blocked(self):
        self.assertTrue(run("d_001|C|وَالْخَيْلَ وَالْبِغَالَ وَالْحَمِيرَ لِتَرْكَبُوهَا وَزِينَةً وَيَخْلُقُ مَا لَا تَعْلَمُونَ\n"))

    def test_quran_in_image_blocked(self):
        self.assertTrue(run("IMG:b01|a horse ﴿وَالْخَيْلَ﴾ No text, no letters, no captions, no watermark.\n"))

    def test_plain_prose_passes(self):
        self.assertEqual(run("d_002|C|كَانَ الْحِصَانُ فِي السُّهُوبِ قَبْلَ أَنْ يَعْرِفَهُ الْإِنْسَانُ بِزَمَنٍ طَوِيلٍ.\n"), [])


if __name__ == "__main__":
    unittest.main()
