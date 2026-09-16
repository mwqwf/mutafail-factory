import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from listen_gate import audit


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name)
        (self.p / 'audio').mkdir()
        (self.p / 'audio/a.wav').write_bytes(b'fixture')
        self.write('blocks.json', [{'id': 'a', 'text': 'test'}])
        self.digest = hashlib.sha256(b'test\0fixture').hexdigest()

    def write(self, file, data):
        (self.p / file).write_text(json.dumps(data), encoding='utf-8')

    def test_missing_report(self):
        self.assertTrue(audit(self.p))

    def test_success(self):
        self.write('listen_results.0.json', {'a': {'ok': True, 'input_sha256': self.digest}})
        self.assertEqual(audit(self.p), [])

    def test_flag_or_skipped_or_string(self):
        for status in [False, None, 'true', 1]:
            self.write('listen_results.0.json', {'a': {'ok': status, 'input_sha256': self.digest}})
            self.assertTrue(audit(self.p))

    def test_changed_audio(self):
        self.write('listen_results.0.json', {'a': {'ok': True, 'input_sha256': self.digest}})
        (self.p / 'audio/a.wav').write_bytes(b'changed')
        self.assertIn('a: stale-result', audit(self.p))

    def test_changed_text(self):
        self.write('listen_results.0.json', {'a': {'ok': True, 'input_sha256': self.digest}})
        self.write('blocks.json', [{'id': 'a', 'text': 'changed'}])
        self.assertIn('a: stale-result', audit(self.p))

    def test_duplicate_report(self):
        for part in [0, 1]:
            self.write(f'listen_results.{part}.json', {'a': {'ok': True}})
        with self.assertRaises(ValueError):
            audit(self.p)

    def test_empty_blocks(self):
        self.write('blocks.json', [])
        self.assertTrue(audit(self.p))

    def test_review_false_positive_only(self):
        review = {'a': {'decision': 'false_positive', 'input_sha256': self.digest,
                        'reason': 'reviewed pronunciation against text', 'reviewer': 'review-session'}}
        self.write('listen_reviews.json', review)
        self.write('listen_results.0.json', {'a': {'ok': False, 'input_sha256': self.digest}})
        self.assertEqual(audit(self.p), [])
        self.write('listen_results.0.json', {'a': {'ok': None, 'input_sha256': self.digest}})
        self.assertTrue(audit(self.p))

    def test_old_review_cannot_approve_changed_input(self):
        self.write('listen_results.0.json', {'a': {'ok': False, 'input_sha256': self.digest}})
        self.write('listen_reviews.json', {'a': {'decision': 'false_positive', 'input_sha256': 'old',
                                                'reason': 'reviewed', 'reviewer': 'review-session'}})
        self.assertTrue(audit(self.p))


if __name__ == '__main__':
    unittest.main()
