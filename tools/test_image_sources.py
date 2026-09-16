import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from image_sources import import_primary


class ImageSourcesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name)
        self.write('images.json', [{'id': 'b01', 'prompt': 'documentary landscape'},
                                   {'id': 'b02', 'prompt': 'second landscape'}])
        (self.p / 'primary').mkdir()
        Image.new('RGB', (1920, 1080), '#254a65').save(self.p / 'primary/b01.png')
        self.entry = {'file': 'primary/b01.png', 'approved': True,
                      'sha256': hashlib.sha256((self.p / 'primary/b01.png').read_bytes()).hexdigest(),
                      'prompt_sha256': hashlib.sha256(b'documentary landscape').hexdigest()}

    def write(self, file, data):
        (self.p / file).write_text(json.dumps(data), encoding='utf-8')

    def manifest(self):
        self.write('image_sources.json', {'provider': 'codex-imagegen', 'primary': {'b01': self.entry}})

    def test_legacy_payload_unchanged(self):
        self.assertEqual(import_primary(self.p)['mode'], 'original-only')

    def test_primary_and_missing_fallback(self):
        self.manifest()
        report = import_primary(self.p)
        self.assertEqual(len(report['primary']), 1)
        self.assertEqual(report['fallback'][0]['id'], 'b02')
        self.assertTrue((self.p / 'primary/b01.png').exists())
        with Image.open(self.p / 'img/b01.jpg') as image:
            self.assertEqual(image.size, (1920, 1080))

    def test_unapproved_falls_back(self):
        self.entry['approved'] = False
        self.manifest()
        self.assertFalse(import_primary(self.p)['primary'])

    def test_hash_mismatch_falls_back(self):
        self.entry['sha256'] = 'changed'
        self.manifest()
        self.assertFalse(import_primary(self.p)['primary'])

    def test_old_prompt_falls_back(self):
        self.entry['prompt_sha256'] = 'changed'
        self.manifest()
        self.assertFalse(import_primary(self.p)['primary'])

    def test_path_escape_falls_back(self):
        self.entry['file'] = '../outside.png'
        self.manifest()
        self.assertFalse(import_primary(self.p)['primary'])


if __name__ == '__main__':
    unittest.main()
