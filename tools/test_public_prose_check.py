import json
from pathlib import Path
import tempfile
import unittest
from public_prose_check import audit

class PublicProseTests(unittest.TestCase):
    def test_scans_metadata_and_narration(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            (p / 'script.md').write_text('d_001|d|سقط القلم على الأرض.\n')
            data = {'film': {'title': 'دعونا نغوص في الورق'}, 'reels': [], 'thumbs': []}
            (p / 'publish.json').write_text(json.dumps(data))
            self.assertTrue(audit(p))
            data['film']['title'] = 'كيف صار الورق في كل بيت؟'
            (p / 'publish.json').write_text(json.dumps(data))
            self.assertEqual(audit(p), [])
            (p / 'script.md').write_text('d_001|d|رِحْلَةٌ مُذْهِلَةٌ\n')
            self.assertTrue(audit(p))
