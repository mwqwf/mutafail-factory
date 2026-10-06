# -*- coding: utf-8 -*-
"""خريطة المعركة الحيّة (tools/battlemap.py): كشف السهم من ذيله ببعده داخل قناعه، والنابض، والكاميرا نحو نقطة الالتحام،
وتصييرٌ قصيرٌ بأصولٍ اصطناعيةٍ للاختبار وحده (لا صورة محتوى)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import battlemap as bm  # noqa: E402


def bar(w=1920, h=1080, x0=200, x1=1200, y=500, half=14):
    a = np.zeros((h, w), np.float32)
    a[y - half:y + half, x0:x1] = 1.0
    return a


class RevealTest(unittest.TestCase):
    def test_distance_grows_from_tail_inside_mask(self):
        a = bar()
        d = bm.tail_distance(a, (200, 500))
        self.assertLess(d[500, 250], d[500, 700])
        self.assertLess(d[500, 700], d[500, 1150])
        self.assertAlmostEqual(float(d[500, 1190]), 1.0, delta=0.05)
        rev = bm.reveal(d, 0.5) * a
        frac = rev.sum() / a.sum()
        self.assertAlmostEqual(frac, 0.5, delta=0.08)                  # نصف التقدّم ≈ نصف السهم
        self.assertEqual(float(bm.reveal(d, 0.0).max()), 0.0)
        self.assertEqual(float(bm.reveal(d, 1.0).min()), 1.0)

    def test_bent_arrow_reveals_along_its_path(self):
        a = np.zeros((1080, 1920), np.float32)
        a[480:520, 200:900] = 1.0                                       # ذراعٌ أفقيّ
        a[200:520, 860:900] = 1.0                                       # ثم يصعد
        d = bm.tail_distance(a, (200, 500))
        self.assertLess(d[500, 880], d[210, 880])                       # الكشف يلتفّ مع السهم لا يقفز

    def test_pop_overshoots_then_settles(self):
        self.assertAlmostEqual(bm.pop_scale(0.0), 0.6)
        peak = max(bm.pop_scale(i / 100 * bm.POP) for i in range(101))
        self.assertGreater(peak, 1.05)
        self.assertEqual(bm.pop_scale(bm.POP + 0.01), 1.0)

    def test_camera_moves_focus_toward_centre_and_always_fills_frame(self):
        T = bm.tilt_matrix(1920, 1080, 28)
        f = bm.project(T, 1500.0, 300.0)
        c = (bm.W / 2, bm.H / 2)
        dist = lambda tn: np.hypot(*(np.array(bm.project(bm.camera(tn, f, 1.05, 1.25, T), *f)) - c))
        self.assertLess(dist(1.0), dist(0.0))
        for tn in np.linspace(0, 1, 11):                               # لا حافّة ولا فراغ أسود في أيّ إطار
            self.assertTrue(bm.covered(bm.camera(tn, f, 1.05, 1.25, T) @ T))
        self.assertFalse(bm.covered(bm.camera(0.0, f, 1.0, 1.0) @ T))  # بلا تصحيحٍ كان اللوح يكشف حوافّه


class CardsTest(unittest.TestCase):
    def test_map_labels_become_codex_label_cards_with_the_key_battlemap_reads(self):
        import cards
        s = {'id': 'S1', 'blocks': [], 'map': {'labels': [{'text': 'مُؤْتَة', 'x': 470, 'y': 150}]}}
        specs = cards.shot_cards(s, {})
        self.assertEqual([(c['kind'], c['role'], c['text']) for c in specs], [('label', 'maplabel', 'مؤتة')])
        self.assertEqual(specs[0]['key'], cards.key('label', {'t': 'مؤتة', 's': None, 'h': None}))   # المفتاح الذي يقرؤه battlemap
        self.assertFalse([c for c in specs if c['role'] == 'label'])    # ولا يرسمها kinetic مرّةً ثانية بلا ميل


class RenderTest(unittest.TestCase):
    def test_short_clip_reveals_arrow_and_pops_unit(self):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, 'images')); os.makedirs(os.path.join(d, 'map'))
        cv2.imwrite(os.path.join(d, 'images', 'M.jpg'), np.full((1080, 1920, 3), 120, np.uint8))
        arrow = np.zeros((1080, 1920, 4), np.uint8); arrow[490:510, 300:1100] = (255, 255, 255, 255)
        unit = np.zeros((1080, 1920, 4), np.uint8); unit[700:760, 900:1020] = (40, 40, 200, 255)
        cv2.imwrite(os.path.join(d, 'map', 'arrow.png'), arrow); cv2.imwrite(os.path.join(d, 'map', 'unit.png'), unit)
        s = {'id': 'X1', 'file': 'M.jpg', 'map': {'focus': [700, 500], 'tilt': 28, 'zoom': [1.0, 1.0],
             'layers': [{'file': 'map/arrow.png', 'kind': 'arrow', 'tail': [300, 500], 'word': 'وحمل', 'dur': 0.6},
                        {'file': 'map/unit.png', 'kind': 'unit', 'word': 'ميمنة'}]}}
        wt = [('وحمل', 0.2, 0.5), ('ميمنة', 0.5, 0.8)]
        out = bm.render(d, s, os.path.join(d, 'anim', 'X1.mp4'), 1.2, 0.0, wt)
        cap = cv2.VideoCapture(out)
        frames = []
        ok, fr = cap.read()
        while ok:
            frames.append(fr); ok, fr = cap.read()
        self.assertEqual(len(frames), 30)
        T = bm.tilt_matrix(1920, 1080, 28)
        Mi = lambda i: bm.camera(i / (len(frames) - 1), bm.project(T, 700, 500), 1.0, 1.0, T) @ T   # الكاميرا تتحرّك إطاراً بإطار

        def at(i, x, y):
            px, py = bm.project(Mi(i), x, y)
            return frames[i][int(py) - 2:int(py) + 3, int(px) - 2:int(px) + 3].reshape(-1, 3).mean(axis=0)
        self.assertLess(at(3, 1080, 500).mean(), 160)                   # قبل فعله: لم يُكشف رأسه
        self.assertGreater(at(29, 1080, 500).mean(), 190)               # بعده: كُشف حتى رأسه
        self.assertLess(at(5, 960, 730)[2] - at(5, 960, 730)[0], 30)    # الرمز قبل ذكره غائب
        self.assertGreater(at(29, 960, 730)[2] - at(29, 960, 730)[0], 80)   # وبعده ظاهر


if __name__ == '__main__':
    unittest.main()
