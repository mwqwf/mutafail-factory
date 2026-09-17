from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ListenModelProbeContract(unittest.TestCase):
    def test_probe_is_one_clip_private_and_non_mutating(self):
        text = (ROOT / '.github/workflows/listen-model-probe.yml').read_text(encoding='utf-8')
        self.assertIn('--batch 1 --model gemini-2.5-flash', text)
        self.assertIn('>/tmp/probe.log 2>&1', text)
        self.assertIn('listen-model-probe', text)
        self.assertNotIn('git push', text)
        self.assertNotIn('publish_youtube.py', text)


if __name__ == '__main__': unittest.main()
