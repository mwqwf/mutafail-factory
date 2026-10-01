# -*- coding: utf-8 -*-
"""الظهور الأوّل للراوي (أمر المالك 2026-10-01): لا افتتاحية بلا لقطة مدخل، ولا مدخلٌ مكرّر من فيلمٍ آخر."""
import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from thrill_gate import check

def proj(shots, slug):
    d = Path(tempfile.mkdtemp())
    (d / 'blocks.json').write_text(json.dumps([{'id': 'n_01', 'text': 'جَيْشٌ يَقْتَرِبُ مِنَ الْمَدِينَةِ؟'}]), encoding='utf-8')
    (d / 'shots.json').write_text(json.dumps(shots), encoding='utf-8')
    (d / 'publish.json').write_text(json.dumps({'slug': slug}), encoding='utf-8')
    return d

class Entrance(unittest.TestCase):
    def test_missing_entrance(self):
        errs, _ = check(proj([{'id': 'N01', 'avatar': True}], 'x'), None)
        self.assertTrue(any('مدخل' in e for e in errs))
    def test_repeated_entrance(self):
        s = [{'id': 'EN1', 'end_image': 'N01', 'entrance': 'حطّين: هبوطٌ جوّيّ فوق القرنين في ستار الدخان ينقشع عن الراوي'}, {'id': 'N01', 'avatar': True}]
        errs, _ = check(proj(s, 'new-film'), None)
        self.assertTrue(any('مكرّر' in e for e in errs))
    def test_new_entrance_passes(self):
        s = [{'id': 'EN1', 'end_image': 'N01', 'entrance': 'مدخلٌ جديد تماماً'}, {'id': 'N01', 'avatar': True}]
        errs, _ = check(proj(s, 'new-film'), None)
        self.assertFalse(any('مدخل' in e for e in errs))

if __name__ == '__main__': unittest.main()
