# -*- coding: utf-8 -*-
"""تقرير الإصغاء لا يعدّ نتيجةً قديمة ولا كتلةً بلا صوت مفحوصةً (درس الشوط 87 في الأرك)."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from listen_report import report


class ListenReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name)
        (self.p / 'audio').mkdir()
        blocks = [{'id': i, 'text': 'نص ' + i} for i in ('ok', 'flag', 'stale', 'none', 'gone')]
        (self.p / 'blocks.json').write_text(json.dumps(blocks, ensure_ascii=False), encoding='utf-8')
        for i in ('ok', 'flag', 'stale', 'none'):
            (self.p / 'audio' / (i + '.wav')).write_bytes(b'wav-' + i.encode())
        d = lambda i: hashlib.sha256(('نص ' + i).encode('utf-8') + b'\0' + b'wav-' + i.encode()).hexdigest()
        res = {'ok': {'ok': True, 'input_sha256': d('ok')},
               'flag': {'ok': False, 'why': 'سقوط كلمة', 'input_sha256': d('flag')},
               'stale': {'ok': True, 'input_sha256': 'صوتٌ-سابق'},
               'gone': {'ok': True, 'input_sha256': 'x'},
               'old_block': {'ok': True, 'input_sha256': 'y'}}          # كتلةٌ لم تعد في blocks.json لا تُحسب
        (self.p / 'listen_results.json').write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')

    def test_only_current_audio_counts(self):
        r = report(str(self.p))
        self.assertEqual(sorted(r['flags']), ['flag'])
        self.assertEqual(sorted(r['unchecked']), ['gone', 'none', 'stale'])
        self.assertEqual(r['why_unchecked']['stale'], 'نتيجةٌ قديمة لصوتٍ سابق')
        self.assertEqual(r['why_unchecked']['gone'], 'لا ملفّ صوت')
        self.assertEqual(r['why_unchecked']['none'], 'بلا نتيجة')

    def test_no_results_file_means_all_unchecked(self):
        (self.p / 'listen_results.json').unlink()
        r = report(str(self.p))
        self.assertEqual(r['flags'], {})
        self.assertEqual(len(r['unchecked']), 5)


if __name__ == '__main__':
    unittest.main()
