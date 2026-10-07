# -*- coding: utf-8 -*-
"""اختبارات مؤثّرات الإبهار (طلب المالك 2026-10-04: «أقوى وأكثر إبهاراً»): التدريج السينمائيّ، والمؤثّرات الصوتية المركّبة بلا نغمة،
والانقلاب المجسّم وغبش الحركة وموجة الارتطام والنصّ خلف العنصر في الكتابة، والأشعّة وقناع القريب في المجسّم."""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

HAS_CV = importlib.util.find_spec('cv2') is not None and importlib.util.find_spec('numpy') is not None
HAS_FF = shutil.which('ffmpeg') is not None and shutil.which('ffprobe') is not None


@unittest.skipUnless(HAS_CV, 'numpy/cv2 غير مثبّتة')
class Looks(unittest.TestCase):
    def test_grade_keeps_shape_and_darkens_corners(self):
        import numpy as np
        import look
        fr = np.full((180, 320, 3), 128, np.uint8)
        for sec in look.LOOKS:
            out = look.Look(sec, size=(320, 180))(fr)
            self.assertEqual((out.shape, out.dtype), (fr.shape, fr.dtype), sec)
            self.assertLess(int(out[2, 2].mean()), int(out[90, 160].mean()) - 5, sec)     # تعتيم الأطراف

    def test_sections_differ(self):
        import numpy as np
        import look
        fr = np.random.default_rng(0).integers(0, 255, (180, 320, 3), dtype=np.uint8)
        a, b = look.Look('battle', size=(320, 180))(fr), look.Look('aftermath', size=(320, 180))(fr)
        self.assertGreater(float(np.abs(a.astype(int) - b.astype(int)).mean()), 3.0)


@unittest.skipUnless(HAS_CV, 'numpy غير مثبّتة')
class SfxSynth(unittest.TestCase):
    def read(self, p):
        import numpy as np
        with wave.open(p) as w:
            return np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float) / 32767

    def test_bank_is_noise_not_tone(self):
        # ⛔ لا موسيقى ولا نغمة: لا قمّةٌ ضيّقة في الطيف تعلو وسيط جوارها كثيراً (النغمة الثابتة تعطي عشرات الأضعاف)
        import numpy as np
        import sfx_synth as s
        from numpy.lib.stride_tricks import sliding_window_view
        b = s.bank(tempfile.mkdtemp())
        for k, p in b.items():
            y = self.read(p)
            self.assertLessEqual(float(np.abs(y).max()), 1.0)
            sp = np.abs(np.fft.rfft(y * np.hanning(len(y))))
            f = np.fft.rfftfreq(len(y), 1 / s.SR)
            spb = sp[(f > 40) & (f < 8000)]
            med = np.median(sliding_window_view(np.pad(spb, 50, mode='edge'), 101), axis=1)
            self.assertLess(float((spb / np.maximum(med, 1e-9)).max()), 10.0, k)

    def test_thud_is_heavy(self):
        import numpy as np
        import sfx_synth as s
        y = s.thud()
        sp = np.abs(np.fft.rfft(y)) ** 2
        f = np.fft.rfftfreq(len(y), 1 / s.SR)
        self.assertGreater(float(sp[f < 300].sum() / sp.sum()), 0.6)

    def test_mix_places_hits(self):
        import numpy as np
        import sfx_synth as s
        d = tempfile.mkdtemp()
        b = s.bank(d)
        out = s.mix([(1.0, 'thud', 0.5)], 3.0, b, os.path.join(d, 'h.wav'))
        y = self.read(out)
        self.assertEqual(len(y), 3 * s.SR)
        self.assertLess(float(np.abs(y[:int(0.99 * s.SR)]).max()), 1e-4)
        self.assertGreater(float(np.abs(y[s.SR:int(1.2 * s.SR)]).max()), 0.1)


@unittest.skipUnless(HAS_CV, 'numpy/cv2 غير مثبّتة')
class KineticFx(unittest.TestCase):
    def card(self, w=300, h=100):
        from PIL import Image
        return Image.new('RGBA', (w, h), (247, 199, 74, 255))

    def test_flip_uses_perspective_then_settles(self):
        import kinetic as k
        e = k.El(self.card(), 500, 400, 0.0, 'flip', 0.5)
        self.assertEqual(k._place(e, 0.1)[1].shape, (3, 3))      # أثناء الانقلاب: منظورٌ مجسّم
        self.assertEqual(k._place(e, 0.9)[1].shape, (2, 3))      # بعد الاستقرار: تآلفيّ
        self.assertIsNotNone(k.compose([e], 0.12).getbbox())

    def test_motion_blur_spreads_fast_entrance(self):
        import numpy as np
        import kinetic as k
        e = k.El(self.card(), 800, 400, 0.0, 'slide', 0.5)
        a = np.asarray(k.compose([e], 0.05))[..., 3]
        cols = np.where(a.max(axis=0) > 0)[0]
        # الكلمة المندفعة من اليمين تُرى ممتدّةً على أعرض من عرضها (300) — غبش حركة لا قفزة
        self.assertGreater(cols[-1] - cols[0], 320)
        b = np.asarray(k.compose([e], 2.0))[..., 3]
        cols = np.where(b.max(axis=0) > 0)[0]
        self.assertLessEqual(cols[-1] - cols[0], 302)            # ساكنة: بعرضها بلا غبش

    def test_impact_moves_pixels_then_ends(self):
        import numpy as np
        import kinetic as k
        k.W, k.H = 320, 180
        try:
            fr = np.random.default_rng(1).integers(0, 255, (180, 320, 3), dtype=np.uint8)
            imp = k.Impact(1.0, 160, 90)
            self.assertTrue((imp.apply(fr.copy(), 1.1) != fr).any())
            self.assertTrue((imp.apply(fr.copy(), 2.0) == fr).all())
        finally:
            k.W, k.H = 1920, 1080

    def test_behind_decided_by_moderate_occlusion(self):
        import numpy as np
        import kinetic as k
        e1 = k.El(self.card(400, 100), 200, 200, 0.0, 'none', 0, occ=True)
        e2 = k.El(self.card(400, 100), 1000, 200, 0.0, 'none', 0, occ=True)
        e3 = k.El(self.card(400, 100), 1000, 600, 0.0, 'none', 0, occ=False)
        m = np.zeros((k.H, k.W), np.uint8)
        m[260:300, 200:600] = 255                                # يحجب 40% من e1 — كثيرٌ يُفقد القراءة
        m[285:300, 1000:1400] = 255                              # يحجب 15% من e2 — معتدل
        k._decide_behind([e1, e2, e3], m, 0.5)
        self.assertEqual((e1.behind, e2.behind, e3.behind), (False, True, None))
        fr = np.zeros((k.H, k.W, 3), np.uint8)
        base = fr.copy()
        k.draw(fr, [e2], 0.5, matte=m)
        self.assertTrue((fr[292, 1100] == base[292, 1100]).all())   # القريب فوق الكتابة
        self.assertTrue((fr[220, 1100] != base[220, 1100]).any())   # وما لا يحجبه القريب ظاهر

    def test_behind_refused_when_one_word_mostly_hidden(self):
        # «٧ إلى ٨ آلاف فارس»: حجبُ «فارس» وحدها يُفقد الخبر وإن كان الحجب الكلّيّ معتدلاً
        import numpy as np
        import kinetic as k
        from PIL import Image
        im = Image.new('RGBA', (900, 120), (0, 0, 0, 0))
        for x0 in (20, 330, 640):                                # ثلاث «كلمات» بينها فراغ
            im.paste((247, 199, 74, 255), (x0, 10, x0 + 240, 110))
        e = k.El(im, 400, 400, 0.0, 'none', 0, occ=True); e.words = ['أ', 'ب', 'ج']
        m = np.zeros((k.H, k.W), np.uint8)
        m[400:520, 420:620] = 255                                # يحجب الكلمة اليسرى كلّها تقريباً (ثلث الحبر)
        k._decide_behind([e], m, 0.5)
        self.assertFalse(e.behind)


@unittest.skipUnless(HAS_CV and HAS_FF, 'numpy/cv2/ffmpeg غير مثبّتة')
class Kb3dFx(unittest.TestCase):
    def test_light_none_for_flat_image(self):
        import numpy as np
        import kb3d
        self.assertIsNone(kb3d._light(np.full((540, 960, 3), 120, np.uint8)))

    def test_matte_written_for_clear_near_layer_else_marker(self):
        import numpy as np
        import kb3d
        from PIL import Image
        d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, 'img'))
        src = os.path.join(d, 'img', 'a.jpg')
        Image.fromarray(np.random.default_rng(2).integers(0, 255, (360, 640, 3), dtype=np.uint8)).save(src)
        dep = np.zeros((360, 640), np.uint8) + 60
        dep[200:, 100:300] = 250                                  # طبقةٌ قريبةٌ بارزة
        Image.fromarray(dep).save(os.path.join(d, 'img', 'a_depth.png'))
        m = os.path.join(d, 'a.matte.mp4')
        kb3d.render(src, os.path.join(d, 'a.mp4'), 0.4, 0, (320, 180), 1.0, m)
        self.assertTrue(os.path.exists(m) and not os.path.exists(m + '.none'))
        Image.fromarray(np.full((360, 640), 90, np.uint8)).save(os.path.join(d, 'img', 'a_depth.png'))   # مسطّح
        kb3d.render(src, os.path.join(d, 'a.mp4'), 0.4, 0, (320, 180), 1.0, m)
        self.assertTrue(os.path.exists(m + '.none') and not os.path.exists(m))


if __name__ == '__main__':
    unittest.main()
