# -*- coding: utf-8 -*-
"""اختبارات أزمنة الكلمات المسموعة (tools/wordtimes.py وقراءتها في kinetic) — بلا نموذج ولا شبكة."""
import hashlib
import json
import os
import shutil
import subprocess as sp
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kinetic as k  # noqa: E402
import wordtimes as wt  # noqa: E402

HAS_FF = shutil.which('ffmpeg') is not None and shutil.which('ffprobe') is not None
TEXT = 'وَلَمْ يُصَلِّ لِلَّهِ فِي عُمْرِهِ كُلِّهْ… إِلَّا رَكْعَتَيْنْ.'


class Merge(unittest.TestCase):
    def test_heard_times_win_and_gaps_shift_with_neighbours(self):
        est = [('ولم', 0.3, 0.6), ('يصل', 0.7, 1.0), ('لله', 1.1, 1.4), ('في', 1.5, 1.6)]
        heard = [('ولم', 0.1, 0.4), ('يصلداه', 0.5, 1.0), ('في', 1.3, 1.4)]
        out, ratio = wt.merge(est, heard)
        self.assertEqual([w for w, _, _ in out], ['ولم', 'يصل', 'لله', 'في'])
        self.assertAlmostEqual(out[0][1], 0.1)
        self.assertAlmostEqual(out[3][1], 1.3)
        # «يصل» و«لله» لم يُطابقا: إزاحة الجارتين (−0.2) على التقدير
        self.assertAlmostEqual(out[1][1], 0.5, places=3)
        self.assertAlmostEqual(out[2][1], 0.9, places=3)
        self.assertAlmostEqual(ratio, 0.5)

    def test_times_never_go_backwards(self):
        out, _ = wt.merge([('ا', 0.0, 0.2), ('ب', 0.3, 0.5)], [('ا', 0.4, 0.5), ('ب', 0.2, 0.3)])
        self.assertLessEqual(out[0][1], out[1][1])


@unittest.skipUnless(HAS_FF, 'ffmpeg غائب')
class KineticReadsHeard(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.wav = os.path.join(self.d, 'n_001.wav')
        sp.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'sine=f=220:d=3', '-ar', '24000', self.wav], check=True)
        k._HEARD.clear()

    def tearDown(self):
        shutil.rmtree(self.d)
        k._HEARD.clear()

    def write(self, words, sha=None):
        sha = sha or hashlib.sha256(open(self.wav, 'rb').read()).hexdigest()[:16]
        json.dump({'n_001': {'sha': sha, 'words': [[w, 0.1 * i, 0.1 * i + 0.08] for i, w in enumerate(words)]}},
                  open(os.path.join(self.d, 'wordtimes.json'), 'w', encoding='utf-8'), ensure_ascii=False)

    def words(self):
        return [w for w, p in k.tokens(TEXT) if not p]

    def test_uses_heard_times_when_fingerprint_matches(self):
        self.write(self.words())
        got = k.block_word_times(TEXT, self.wav, 3.0)
        self.assertEqual([round(s, 2) for _, s, _ in got], [round(0.1 * i, 2) for i in range(len(got))])

    def test_falls_back_when_audio_changed(self):
        self.write(self.words(), sha='0' * 16)
        got = k.block_word_times(TEXT, self.wav, 3.0)
        self.assertNotEqual([round(s, 2) for _, s, _ in got], [round(0.1 * i, 2) for i in range(len(got))])

    def test_falls_back_when_words_differ(self):
        self.write(self.words()[:-1])
        got = k.block_word_times(TEXT, self.wav, 3.0)
        self.assertEqual(len(got), len(self.words()))
        self.assertNotEqual(got[1][1], 0.1)


if __name__ == '__main__':
    unittest.main()
