# -*- coding: utf-8 -*-
"""فاحص الصوت: البطء الثابت يُقبل من المحاولة الثانية المتتالية، وما فوق الحدّ الليّن يبقى معيباً (درس الشوط 96 في مؤتة)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import wave

import numpy as np

TOOL = Path(__file__).resolve().parent / 'audio_checks.py'
RATE = 24000
TEXT = 'ب' * 40          # 40 حرفاً ⇒ الحدّ 0.19 + 1.2/40 = 0.22 ث/حرف، والليّن 0.33


def wav(path, seconds):
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    a = (3000 * np.sin(2 * np.pi * 200 * t)).astype(np.int16)
    a[:240] = 0                                   # لا ضجيج في البداية
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(a.tobytes())


class SlowPace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name)
        (self.p / 'audio').mkdir()
        blocks = [{'id': i, 'text': TEXT} for i in ('ok', 'slow', 'vslow')]
        (self.p / 'blocks.json').write_text(json.dumps(blocks, ensure_ascii=False), encoding='utf-8')

    def run_checks(self):
        r = subprocess.run([sys.executable, str(TOOL), str(self.p)], capture_output=True, text=True)
        bad = json.loads((self.p / 'audio_checks.json').read_text(encoding='utf-8'))
        tries = json.loads((self.p / 'audio' / '.pace_tries.json').read_text(encoding='utf-8'))
        return r, bad, tries

    def test_steady_slow_accepted_on_second_try(self):
        a = self.p / 'audio'
        wav(a / 'ok.wav', 6.0)        # 0.15 ث/حرف
        wav(a / 'slow.wav', 11.2)     # 0.28: فوق الحدّ ودون الليّن
        wav(a / 'vslow.wav', 16.0)    # 0.40: فوق الليّن
        r, bad, tries = self.run_checks()
        self.assertEqual(r.returncode, 1)
        self.assertEqual(sorted(bad), ['slow', 'vslow'])
        self.assertEqual(tries, {'slow': 1})
        self.assertFalse((a / 'slow.wav').exists())   # الأولى تُحذف لتُعاد كالعادة

        wav(a / 'slow.wav', 11.2)     # أعاد المولّد الكتلة بالبطء نفسه
        wav(a / 'vslow.wav', 16.0)
        r, bad, tries = self.run_checks()
        self.assertEqual(sorted(bad), ['vslow'])
        self.assertTrue((a / 'slow.wav').exists())
        self.assertIn('إيقاعٌ بطيء مقبول', r.stdout)
        self.assertIn('slow', r.stdout)

        wav(a / 'vslow.wav', 6.0)     # صار سليماً
        r, bad, tries = self.run_checks()
        self.assertEqual(r.returncode, 0)
        self.assertEqual(bad, {})
        self.assertNotIn('vslow', tries)

    def test_pass_resets_counter(self):
        a = self.p / 'audio'
        for i in ('ok', 'vslow'): wav(a / (i + '.wav'), 6.0)
        wav(a / 'slow.wav', 11.2)
        self.run_checks()
        wav(a / 'slow.wav', 6.0)      # الإعادة جاءت سليمة ⇒ يُصفَّر العدّاد
        r, bad, tries = self.run_checks()
        self.assertEqual(bad, {})
        self.assertEqual(tries, {})
        wav(a / 'slow.wav', 11.2)     # بطءٌ جديدٌ بعد السلامة يبدأ من الأولى فيُحذف
        r, bad, tries = self.run_checks()
        self.assertEqual(sorted(bad), ['slow'])


if __name__ == '__main__':
    unittest.main()
