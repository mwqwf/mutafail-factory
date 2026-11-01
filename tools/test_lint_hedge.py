# -*- coding: utf-8 -*-
"""اختبار منع صيغ التمريض في كلام الراوي (حكم المالك 2026-10-11، والمرجع الموحّد 2026-11-01)."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(__file__))
import lint


class HedgeTests(unittest.TestCase):
    def run_on(self, text):
        with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(text)
        try:
            return [w for _, w in lint.hedge(f.name)]
        finally:
            os.unlink(f.name)

    def test_narrator_hedge_caught(self):
        self.assertEqual(self.run_on('d_001|N|يُرْوَى أَنَّهُ خَرَجَ\n'), ['يروى'])
        self.assertEqual(self.run_on('d_002|N|وَتَقُولُ الرِّوَايَاتُ إِنَّهُمْ كَثِيرٌ\n'), ['تقول الروايات'])

    def test_quote_and_lookalikes_pass(self):
        self.assertEqual(self.run_on('d_001|Q|قِيلَ لَهُ ارْجِعْ\n'), [])
        self.assertEqual(self.run_on('d_002|N|بَثَّ التَّرْوِيعَ فِي الصُّفُوفِ\n'), [])
        self.assertEqual(self.run_on('d_003|N|قِيلَ لَهُ ارْجِعْ فَأَبَى\n'), [])


if __name__ == '__main__':
    unittest.main()
