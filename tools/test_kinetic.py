# -*- coding: utf-8 -*-
"""اختبارات الكتابة المتحرّكة (tools/kinetic.py) — بلا توليد ولا خدمات، وتتخطّى ما يحتاج مكتباتٍ غائبة."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cards  # noqa: E402
import kinetic as k  # noqa: E402
import thrill_gate as g  # noqa: E402

HAS_AR = importlib.util.find_spec('arabic_reshaper') is not None and importlib.util.find_spec('bidi') is not None


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

    def test_base_filters_only_when_needed(self):
        self.assertEqual(k.base_filters([], [], 4.0), '')
        f = k.base_filters([1.0], [2.0], 4.0)
        self.assertIn('zoompan', f)
        self.assertIn('crop=w=iw-64', f)


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

    def test_keyout_makes_solid_background_transparent(self):
        from PIL import Image
        im = Image.new('RGBA', (200, 80), (255, 255, 255, 255))
        im.paste((20, 20, 20, 255), (60, 20, 140, 60))
        out = k.keyout(im)
        self.assertEqual(out.getpixel((5, 5))[3], 0)
        self.assertEqual(out.getpixel((100, 40))[3], 255)

    def test_compose_draws_inside_frame(self):
        from PIL import Image
        e = k.El(Image.new('RGBA', (300, 120), (247, 199, 74, 255)), 100, 100, 0.0, 'slam', 0.2)
        im = k.compose([e], 0.5)
        self.assertEqual(im.size, (k.W, k.H))
        self.assertIsNotNone(im.getbbox())


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
