# -*- coding: utf-8 -*-
"""اختبارات الكتابة المتحرّكة (tools/kinetic.py) — بلا توليد ولا خدمات، وتتخطّى ما يحتاج مكتباتٍ غائبة."""
import importlib.util
import json
import os
import shutil
import subprocess as sp
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cards  # noqa: E402
import kinetic as k  # noqa: E402
import thrill_gate as g  # noqa: E402

HAS_AR = importlib.util.find_spec('arabic_reshaper') is not None and importlib.util.find_spec('bidi') is not None
HAS_CV = importlib.util.find_spec('cv2') is not None and importlib.util.find_spec('numpy') is not None
HAS_FF = shutil.which('ffmpeg') is not None and shutil.which('ffprobe') is not None


class TokensAndTiming(unittest.TestCase):
    def test_tokens_split_words_and_pauses(self):
        t = k.tokens('آلَافُ الْفُرْسَانِ… يَنْقَضُّونَ عَلَى رَجُلٍ وَاحِدْ.')
        words = [w for w, p in t if not p]
        pauses = [w for w, p in t if p]
        self.assertEqual(words[0], 'آلاف')
        self.assertIn('…', pauses)
        self.assertEqual(len(words), 6)

    def test_bare_matches_vocalized_field_words(self):
        self.assertEqual(k.bare('يَنْقَضُّونَ'), k.bare('ينقضون'))
        self.assertEqual(k.bare('الْخَلِيفَةْ!'), k.bare('الخليفة'))

    def test_word_times_without_audio_are_monotonic_and_bounded(self):
        wt = k.block_word_times('فَأَيْنَ كَانَ الْخَلِيفَةُ؟ وَلِمَاذَا كَانَ وَزِيرُهُ تَحْتَ رَايَاتِهِ؟', None, 4.0)
        starts = [a for _, a, _ in wt]
        self.assertEqual(len(wt), 8)
        self.assertEqual(starts, sorted(starts))
        self.assertGreaterEqual(starts[0], 0.0)
        self.assertLessEqual(wt[-1][2], 4.0)

    def test_find_word_and_default(self):
        wt = [('لكنه', 0.1, 0.4), ('لم', 0.6, 0.7), ('يكن', 0.75, 0.9), ('الخليفة!', 1.0, 1.6)]
        self.assertAlmostEqual(k.find_word(wt, 'يَكُنِ', 9.0), 0.70, places=2)
        self.assertEqual(k.find_word(wt, 'غائبة', 9.0), 9.0)
        self.assertEqual(k.find_word(wt, None, 2.5), 2.5)

    def test_has_fx_and_spread(self):
        self.assertTrue(k.has_fx({'slam': {'text': 'x'}}))
        self.assertTrue(k.has_fx({'_chapter': 'عنوان'}))
        self.assertFalse(k.has_fx({'id': 'K01', 'sfx': 'wind'}))
        self.assertEqual(k.spread(3, 0.0, 3.0), [0.0, 1.0, 2.0])

    def test_camera_shake_and_punch(self):
        self.assertEqual(k.cam(1.0, [], []), (1.0, 0.0, 0.0))
        z, dx, dy = k.cam(0.5, [1.0], [])                 # قبل الارتجاج: تكبيرٌ أساسيّ ثابت فلا قفزة عند بدئه
        self.assertAlmostEqual(z, 1.035); self.assertEqual((dx, dy), (0.0, 0.0))
        self.assertNotEqual(k.cam(1.05, [1.0], [])[1], 0.0)
        self.assertGreater(k.cam(2.0, [], [2.0])[0], 1.1)
        self.assertEqual(k.cam(2.7, [], [2.0])[0], 1.0)   # التكبير الخاطف ينتهي
        self.assertEqual(k.flash_alpha(5.0, [1.0]), 0.0)
        self.assertGreater(k.flash_alpha(1.02, [1.0]), 0.8)


def _word_card(path, widths, gap=70, h=200):
    """بطاقةٌ اصطناعية: كتلٌ معتمة بعرض كلّ كلمة، بينها فراغ (ومن داخل الكلمة فراغاتٌ صغيرة كالحروف المنفصلة)."""
    from PIL import Image
    W_ = sum(widths) + gap * (len(widths) - 1) + 40
    im = Image.new('RGBA', (W_, h), (0, 0, 0, 0))
    x = W_ - 20
    for w in widths:                                     # الكلمة الأولى يميناً
        x -= w
        im.paste((247, 199, 74, 255), (x, 40, x + w // 2 - 6, h - 40))      # «حرفٌ» منفصل داخل الكلمة
        im.paste((247, 199, 74, 255), (x + w // 2, 40, x + w, h - 40))
        x -= gap
    im.save(path)
    return W_


def _cards_proj(keys_sizes: dict) -> str:
    """مشروعٌ مؤقّت فيه بطاقاتٌ PNG شفّافة بمقاساتٍ معلومة (تقوم مقام بطاقات كوديكس)."""
    from PIL import Image
    d = Path(tempfile.mkdtemp()); (d / 'cards').mkdir()
    for key, (w, h) in keys_sizes.items():
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        im.paste((247, 199, 74, 255), (20, 20, w - 20, h - 20))
        im.save(d / 'cards' / (key + '.png'))
    return str(d)


class Layout(unittest.TestCase):
    def test_slam_moves_above_cards_when_both(self):
        # الأرك K09f: كانت الضربة «صفٌّ واحد» تغطّي بطاقات الصور في وسط الشاشة
        s = {'slam': {'text': 'صف واحد', 'word': 'واحد'},
             'cards': [{'img': 'x', 'label': 'أ'}, {'img': 'y', 'label': 'ب'}]}
        specs = cards.shot_cards(s, {})
        proj = _cards_proj({c['key']: ((1536, 384) if c['role'] == 'slam' else (1024, 256)) for c in specs})
        els, shakes, _, flashes = k.shot_els(proj, s, [('صف', 0.2, 0.6), ('واحد', 0.6, 1.1)], 4.0, {})
        slam = [e for e in els if e.anim == 'slam'][0]
        labels = [e for e in els if e.anim == 'rise']
        self.assertLess(slam.y + slam.img.height, k.H / 2 + 110 - 124)   # فوق أعلى البطاقات المنخفضة
        self.assertTrue(labels and min(e.y for e in labels) > k.H / 2)
        self.assertEqual(len(shakes), 1); self.assertEqual(len(flashes), 1)

    def test_missing_card_is_skipped_not_drawn(self):
        # أمر المالك: لا يرسم Claude نصّاً — البطاقة الغائبة يُتخطّى عنصرها
        s = {'name': {'text': 'يعقوب المنصور', 'sub': 'الخليفة الموحّدي'}}
        els, _, _, _ = k.shot_els(tempfile.mkdtemp(), s, [], 3.0, {})
        self.assertEqual(els, [])

    def test_spoken_lines_follow_word_times(self):
        texts = {'b1': 'أَيُّهَا النَّاسُ… اغْفِرُوا لِي فِيمَا عَسَى أَنْ يَكُونَ صَدَرَ مِنِّي.'}
        s = {'blocks': ['b1'], 'kt': {'style': 'quote'}}
        specs = cards.shot_cards(s, texts)
        lines = [c for c in specs if c['role'] == 'line']
        self.assertEqual([c['text'] for c in lines], ['أيها الناس', 'اغفروا لي فيما عسى', 'أن يكون صدر مني'])
        words = cards.shot_words(s, texts)[0]
        wt = [(w, 0.5 * i, 0.5 * i + 0.4) for i, w in enumerate(words)]
        proj = _cards_proj({c['key']: (1536, 384) for c in lines})
        els, _, _, _ = k.shot_els(proj, s, wt, 6.0, texts)
        wipes = sorted((e.t0 for e in els if e.anim == 'wipe'))
        self.assertEqual(wipes, [0.0, 1.0, 3.0])           # كلّ سطرٍ يبدأ مع أوّل كلمةٍ منه

    @unittest.skipUnless(HAS_CV, 'numpy/cv2 غير مثبّتة')
    def test_word_spans_cut_at_word_gaps(self):
        from PIL import Image
        d = tempfile.mkdtemp(); f = os.path.join(d, 'c.png')
        _word_card(f, [300, 160, 420])
        im = Image.open(f).convert('RGBA')
        sp_ = k.word_spans(im, ['كلمةطويلة', 'قصيرة', 'كلمةأطولبكثير'])
        self.assertEqual(len(sp_), 3)
        self.assertEqual(sp_[0][1], im.width); self.assertEqual(sp_[-1][0], 0)   # تقسّم العرض كلّه
        self.assertTrue(all(sp_[i][0] == sp_[i + 1][1] for i in range(2)))     # بلا فجوةٍ ولا تداخل
        x = im.width - 20
        for (a, b), w in zip(sp_, [300, 160, 420]):                              # كلّ قطعٍ في الفراغ بين كلمتين
            self.assertLessEqual(a, x - w); self.assertGreaterEqual(a, x - w - 70)
            x -= w + 70

    @unittest.skipUnless(HAS_CV, 'numpy/cv2 غير مثبّتة')
    def test_words_enter_when_spoken(self):
        # حكم المالك 2026-10-04: الكلمة تظهر لحظة نطقها لا السطر كلّه
        texts = {'b1': 'جَيْشٌ ثَانٍ كَبِيرْ.'}
        s = {'blocks': ['b1'], 'kt': {'style': 'center'}}
        lines = [c for c in cards.shot_cards(s, texts) if c['role'] == 'line']
        self.assertEqual(len(lines), 1)
        proj = tempfile.mkdtemp(); os.makedirs(os.path.join(proj, 'cards'))
        _word_card(os.path.join(proj, 'cards', lines[0]['key'] + '.png'), [240, 200, 260])
        words = cards.shot_words(s, texts)[0]
        wt = [(w, 0.5 + 0.6 * i, 0.9 + 0.6 * i) for i, w in enumerate(words)]
        els, _, _, _ = k.shot_els(proj, s, wt, 4.0, texts)
        ws = sorted((e for e in els if e.kind == 'img'), key=lambda e: e.t0)
        self.assertEqual([round(e.t0, 2) for e in ws], [0.46, 1.06, 1.66])
        self.assertTrue(ws[0].x > ws[1].x > ws[2].x)              # الأولى يميناً
        self.assertTrue(all(e.t1 is not None for e in els))      # تخرج قبل الانتقال
        im = k.compose(els, 0.8)                                  # بعد الأولى وقبل الثانية: كلمةٌ واحدة ظاهرة
        self.assertIsNotNone(im.getbbox())

    def test_keyout_makes_solid_background_transparent(self):
        from PIL import Image
        im = Image.new('RGBA', (200, 80), (255, 255, 255, 255))
        im.paste((20, 20, 20, 255), (60, 20, 140, 60))
        out = k.keyout(im)
        self.assertEqual(out.getpixel((5, 5))[3], 0)
        self.assertEqual(out.getpixel((100, 40))[3], 255)

    @unittest.skipUnless(HAS_CV, 'numpy/cv2 غير مثبّتة')
    def test_compose_draws_inside_frame(self):
        from PIL import Image
        e = k.El(Image.new('RGBA', (300, 120), (247, 199, 74, 255)), 100, 100, 0.0, 'slam', 0.2)
        im = k.compose([e], 0.5)
        self.assertEqual(im.size, (k.W, k.H))
        self.assertIsNotNone(im.getbbox())


@unittest.skipUnless(HAS_CV and HAS_FF, 'numpy/cv2/ffmpeg غير مثبّتة')
class RenderFrames(unittest.TestCase):
    def test_render_keeps_frame_count_with_head_handle(self):
        from PIL import Image
        d = tempfile.mkdtemp(); seg = os.path.join(d, 's.mp4'); res = os.path.join(d, 'r.mp4')
        sp.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=navy:s=1920x1080:r=25', '-frames:v', '30',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', seg], check=True)
        e = k.El(Image.new('RGBA', (400, 120), (247, 199, 74, 255)), 760, 480, 0.2, 'pop', 0.3)
        k.render(seg, res, 34, 0.48, [e], [0.3], [], [0.3], ['-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', '-an'])
        n = sp.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=nb_read_packets',
                    '-of', 'csv=p=0', res], capture_output=True, text=True).stdout.strip()
        self.assertEqual(int(n), 34)                              # المقطع أقصر (30) ⇒ يُكرَّر آخر إطار، ولا ينقص العدد


class ThrillGateCost(unittest.TestCase):
    """Kling يحاسب مقطعاً من 5 ث لكلّ لقطةٍ حيّة: 22 لقطة قصيرة = 7.7$ لا أقلّ (الأرك 2026-10-04)."""
    def proj(self, n_live, cap):
        d = Path(tempfile.mkdtemp())
        blocks = [{'id': 'd%d' % i, 'voice': 'Charon', 'text': 'كَلِمَةٌ قَصِيرَةْ.'} for i in range(n_live)]
        shots = [{'id': 'S%d' % i, 'blocks': ['d%d' % i], 'kind': 'حيّة'} for i in range(n_live)]
        for name, obj in (('blocks.json', blocks), ('shots.json', shots), ('sections.json', []), ('reels.json', []),
                          ('publish.json', {'budget_total_usd': cap, 'film': {'title': 'سؤال؟'}})):
            (d / name).write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')
        return d

    def test_short_live_shots_are_billed_per_clip(self):
        d = self.proj(30, 9)                    # 30 × 0.35 = 10.5$ > 8.1$
        blocks = json.loads((d / 'blocks.json').read_text(encoding='utf-8'))
        errs, _ = g.pacing(d, blocks, blocks, [], json.loads((d / 'publish.json').read_text(encoding='utf-8')))
        self.assertTrue(any('التحريك المخطّط' in e for e in errs))

    def test_within_cap_passes(self):
        d = self.proj(22, 9)                    # 22 × 0.35 = 7.7$ ≤ 8.1$
        blocks = json.loads((d / 'blocks.json').read_text(encoding='utf-8'))
        errs, _ = g.pacing(d, blocks, blocks, [], json.loads((d / 'publish.json').read_text(encoding='utf-8')))
        self.assertFalse(any('التحريك المخطّط' in e for e in errs))


if __name__ == '__main__':
    unittest.main()
