"""كل اسم فيلم جديد ملزم بصور OpenAI؛ لا ثغرة بتغيير الاسم."""
import json
from pathlib import Path
import tempfile
import unittest
from image_sources import import_primary


class NewImagePolicy(unittest.TestCase):
    def test_new_names_cannot_use_original_silently(self):
        for slug in ('waraq', 'nahl', 'future-film'):
            with self.subTest(slug=slug), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                (root / 'meta.json').write_text(json.dumps({'slug': slug}))
                (root / 'images.json').write_text('[]')
                with self.assertRaises(RuntimeError):
                    import_primary(root)
