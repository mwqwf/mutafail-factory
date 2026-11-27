# -*- coding: utf-8 -*-
"""معيار أوامر الصور وبوّابتها (أمر المالك 2026-11-27): الأمر المركَّب يمرّ، والمحظور والمفارقة والوجه يُرفضون، والصورة
الضبابية أو غير 16:9 أو بلا مراجعة يدوية لا تدخل المونتاج، والمرفوض ثلاثاً يُغيَّر لا يُعاد."""
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import image_prompts as ip  # noqa: E402


class Prompt(unittest.TestCase):
    def test_composed_prompt_passes(self):
        p = ip.compose({'subject': 'Rows of worshippers seen from behind on open sand', 'size': 'wide', 'angle': 'high'},
                       ip.bible(None))
        self.assertEqual(ip.lint(p), [])
        self.assertTrue(p.endswith(ip.REQUIRED_TAIL))

    def test_forbidden_and_anachronism_rejected(self):
        p = ip.compose({'subject': 'Courtyard with a green dome and blood on the sand'}, ip.bible(None))
        errs = ' '.join(ip.lint(p))
        self.assertIn('مفارقة عصر', errs); self.assertIn('دم', errs)

    def test_visible_face_and_unhidden_human_rejected(self):
        self.assertTrue(any('وجه' in e for e in ip.lint(ip.compose({'subject': 'push-in on the eyes of the commander'}, ip.bible(None)))))
        bare = 'A rider on a dune, wide shot, 35mm lens, sun, 7th-century. ' + ip.REQUIRED_TAIL
        self.assertTrue(any('إخفاء وجه' in e for e in ip.lint(bare)))

    def test_negatives_are_not_counted_as_content(self):
        p = ip.compose({'subject': 'Empty prayer mat in a shaft of light'}, ip.bible(None))
        self.assertNotIn('women', ' '.join(ip.lint(p)))

    def test_film_bible_overrides(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, 'style_bible.json'), 'w').write('{"light": {"day": "overcast flat light"}}')
            self.assertIn('overcast', ip.compose({'subject': 'distant dunes'}, ip.bible(d)))


class Gate(unittest.TestCase):
    def setUp(self):
        import cv2
        self.cv2 = cv2
        self.d = tempfile.TemporaryDirectory(); self.addCleanup(self.d.cleanup)
        rng = np.random.default_rng(0)
        self.good = []
        for i in range(5):
            im = (rng.random((720, 1280, 3)) * 120 + 60).astype(np.uint8)
            p = os.path.join(self.d.name, 'g%d.jpg' % i); cv2.imwrite(p, im); self.good.append(p)
        self.blur = os.path.join(self.d.name, 'blur.jpg')
        cv2.imwrite(self.blur, cv2.GaussianBlur((rng.random((720, 1280, 3)) * 120 + 60).astype(np.uint8), (0, 0), 12))
        self.square = os.path.join(self.d.name, 'sq.jpg')
        cv2.imwrite(self.square, (rng.random((1024, 1024, 3)) * 255).astype(np.uint8))

    def test_good_images_pass_with_review(self):
        rv = {os.path.basename(p): dict({k: 'pass' for k in ip.REVIEW_KEYS}) for p in self.good}
        self.assertEqual(ip.image_gate(self.good, rv), [])

    def test_blur_aspect_and_missing_review_fail(self):
        errs = ' '.join(ip.image_gate([self.blur, self.square], {}))
        self.assertIn('ضبابية', errs); self.assertIn('16:9', errs); self.assertIn('بلا مراجعة', errs)

    def test_rejected_review_regenerate_then_change_shot(self):
        n = os.path.basename(self.good[0])
        rv = {n: dict({k: 'pass' for k in ip.REVIEW_KEYS}, hands='fail', attempts=1)}
        self.assertIn('أعِد التوليد', ' '.join(ip.image_gate([self.good[0]], rv)))
        rv[n]['attempts'] = 3
        self.assertIn('غيّر اللقطة', ' '.join(ip.image_gate([self.good[0]], rv)))


if __name__ == '__main__':
    unittest.main()
