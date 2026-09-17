"""حارس توافق أمر النبض؛ لا اتصال ولا توليد ولا نشر."""
from pathlib import Path
import unittest


class PulseContract(unittest.TestCase):
    def test_slurp_is_filtered_by_external_jq(self):
        text = (Path(__file__).resolve().parents[1] / '.github/workflows/pulse.yml').read_text(encoding='utf-8')
        start = text.index('          N=$(gh api')
        end = text.index('          echo ', start)
        command = text[start:end]
        self.assertIn('--paginate --slurp', command)
        self.assertNotIn('--jq', command)
        self.assertIn('|\n                jq -er', command)
        self.assertIn('set -euo pipefail', text[:start])
        self.assertIn('.status != "completed"', command)
        self.assertIn('(film|finish)', command)


if __name__ == '__main__':
    unittest.main()
