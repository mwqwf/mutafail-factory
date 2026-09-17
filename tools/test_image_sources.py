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
        self.write('meta.json', {'slug': 'amal-2'})
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

    def strict(self):
        self.write('meta.json', {'slug': 'amal-3'})

    def strict_manifest(self):
        self.write('image_sources.json',
                   {'provider': 'openai-chatgpt-imagegen', 'primary': {'b01': self.entry}})

    def exception(self):
        proof = {
            'tool': 'image_gen.imagegen',
            'runStatus': 'failed-terminal',
            'attemptCount': 1,
            'outputCount': 0,
            'attemptedAt': '2026-09-17T06:40:00Z',
            'promptSha256': 'a' * 64,
            'errorClass': 'ToolUnavailable',
        }
        evidence = json.dumps(proof, sort_keys=True).encode()
        (self.p / 'imagegen-evidence.json').write_bytes(evidence)
        self.write('image_fallback_exception.json', {
            'provider': 'openai-chatgpt-imagegen',
            'status': 'unavailable-after-authorized-attempts',
            'authorizedAlternativesExhausted': True,
            'checkedAt': '2026-09-17T06:40:00Z',
            'reason': 'The embedded cloud image tool returned a terminal availability error.',
            'evidenceFile': 'imagegen-evidence.json',
            'evidenceSha256': hashlib.sha256(evidence).hexdigest(),
        })

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

    def test_amal3_missing_manifest_fails_closed(self):
        self.strict()
        with self.assertRaises(RuntimeError):
            import_primary(self.p)

    def test_missing_meta_fails_closed(self):
        (self.p / 'meta.json').unlink()
        with self.assertRaises(RuntimeError):
            import_primary(self.p)

    def test_amal3_missing_image_fails_closed(self):
        self.strict()
        self.strict_manifest()
        with self.assertRaises(RuntimeError):
            import_primary(self.p)

    def test_amal3_documented_exception_unlocks_only_fallback(self):
        self.strict()
        self.exception()
        report = import_primary(self.p)
        self.assertEqual(report['mode'], 'documented-original-fallback')
        self.assertEqual({x['id'] for x in report['fallback']}, {'b01', 'b02'})


if __name__ == '__main__':
    unittest.main()
