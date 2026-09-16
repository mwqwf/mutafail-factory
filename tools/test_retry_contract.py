from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RetryQuotaGuardContract(unittest.TestCase):
    def test_listening_daily_quota_is_not_retried_immediately(self):
        text = (ROOT / '.github/workflows/retry.yml').read_text(encoding='utf-8')
        self.assertIn("grep -q '× nokeys'", text)
        self.assertIn('jobs?filter=latest&per_page=100', text)
        self.assertIn('steps.quota_guard.outputs.hold', text)
        self.assertIn("echo \"hold=$hold\"", text)
        self.assertIn('gh run rerun "$RUN"', text)


if __name__ == '__main__':
    unittest.main()
