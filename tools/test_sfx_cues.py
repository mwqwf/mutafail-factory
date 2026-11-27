# -*- coding: utf-8 -*-
"""المؤثّرات بإشاراتٍ مسوَّغة (أمر المالك 2026-11-27): الورقة تُرفض بلا سبب أو فوق جملةٍ مفتاحية أو بكثافة أو تكرار،
والمسار المصيَّر يبقى تحت الكلام، والمطابقة بالكلمة كاملة (درس «فيلم» ⇒ فيلة في أجنادين)."""
import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfx_auto  # noqa: E402
import sfx_cues  # noqa: E402

SR = sfx_cues.SR
BLOCKS = [
    {'id': 'b1', 'role': 'N', 'text': 'عَلَى خَيْلِ الْمُشْرِكِينَ كَانَ خَالِدٌ فَوْقَ الْكَثِيبِ وَالرِّيحُ تَهُبُّ'},
    {'id': 'b2', 'role': 'N', 'text': 'فَقَالَ النَّبِيُّ صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ: الْإِسْلَامُ يَجُبُّ مَا كَانَ قَبْلَهُ'},
    {'id': 'b3', 'role': 'N', 'text': 'ثُمَّ الْتَقَتِ السُّيُوفُ وَعَلَا صَلِيلُهَا وَرَكَضَتِ الْخَيْلُ'},
]
BT = {'b1': (0.0, 6.0), 'b2': (6.5, 12.0), 'b3': (12.5, 20.0)}


def noise_ogg(path, seconds=8.0, hp=None):
    af = ['highpass=f=%d' % hp] if hp else ['lowpass=f=1500']
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anoisesrc=c=pink:r=48000:a=0.3:seed=3',
                    '-t', str(seconds), '-af', ','.join(af), '-ac', '1', '-c:a', 'libopus', '-b:a', '64k', path], check=True)


def good_sheet():
    return {'cues': [
        {'id': 'c1', 'block': 'b1', 'event': 'wind', 'anchor': 'خيل', 'dur': 5.5, 'why': 'كثيب مكشوف والريح في النص'},
        {'id': 'c2', 'block': 'b3', 'event': 'sword_clash', 'anchor': 'السيوف', 'why': 'صليل السيوف مذكور حرفياً'},
        {'id': 'c3', 'block': 'b3', 'event': 'hooves', 'anchor': 'ركضت', 'offset': 0.5, 'why': 'الخيل تركض'},
    ]}


class Lint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        for n in ('wind_1', 'swords_1', 'hooves_1', 'hooves_2', 'crowd_1'):
            noise_ogg(os.path.join(cls.tmp.name, n + '.ogg'))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def lint(self, sheet):
        return sfx_cues.lint(sheet, BLOCKS, BT, self.tmp.name)

    def test_good_sheet_passes(self):
        self.assertEqual(self.lint(good_sheet()), [])

    def test_unmotivated_anchor_fails(self):
        s = good_sheet(); s['cues'][0]['anchor'] = 'الفيلة'
        self.assertTrue(any('غير مُسوَّغ' in e for e in self.lint(s)))

    def test_no_reason_fails(self):
        s = good_sheet(); s['cues'][1]['why'] = ''
        self.assertTrue(any('بلا سبب' in e for e in self.lint(s)))

    def test_no_place_fails(self):
        s = good_sheet(); del s['cues'][1]['anchor']
        self.assertTrue(any('بلا مكانٍ مسمّى' in e for e in self.lint(s)))

    def test_key_line_auto_detected_and_protected(self):
        s = good_sheet(); s['cues'].append({'id': 'c4', 'block': 'b2', 'event': 'crowd', 'at': 0.5, 'why': 'جموع الصحابة حوله'})
        self.assertTrue(any('مفتاحية' in e for e in self.lint(s)))
        s['cues'][-1]['event'] = 'silence'
        self.assertEqual(self.lint(s), [])

    def test_too_loud_under_voice_fails(self):
        s = good_sheet(); s['cues'][0]['level'] = -14
        self.assertTrue(any('أعلى من الحدّ' in e for e in self.lint(s)))

    def test_density_and_repetition_fail(self):
        s = {'cues': [{'id': 'h%d' % i, 'block': 'b3', 'event': 'hooves', 'at': i * 1.0, 'why': 'الخيل تركض'} for i in range(7)]}
        errs = self.lint(s)
        self.assertTrue(any('متقاربتان' in e for e in errs))
        self.assertTrue(any('تكرار' in e for e in errs))
        self.assertTrue(any('كثافة' in e for e in errs))

    def test_unknown_event_and_music_like_names_rejected(self):
        s = good_sheet(); s['cues'][0]['event'] = 'drums'
        self.assertTrue(any('حدث مجهول' in e for e in self.lint(s)))

    def test_files_rotate_without_same_offset_reuse(self):
        cues = [{'id': 'a', 'block': 'b3', 'event': 'hooves', 'at': 0, 'why': 'x' * 8},
                {'id': 'b', 'block': 'b3', 'event': 'hooves', 'at': 4, 'why': 'x' * 8},
                {'id': 'c', 'block': 'b3', 'event': 'hooves', 'at': 7, 'why': 'x' * 8}]
        by = {b['id']: b for b in BLOCKS}
        spans = [sfx_cues.cue_window(c, BT, by) + ('spot', 'hooves', c['id']) for c in cues]
        files = sfx_cues.pick_files(cues, spans, self.tmp.name, {})
        self.assertNotEqual(files[0][0], files[1][0])
        self.assertEqual(sfx_cues.reuse_errors(spans, files), [])


class Render(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        for n in ('wind_1', 'swords_1', 'hooves_1'):
            noise_ogg(os.path.join(self.tmp.name, n + '.ogg'))
        n = int(20.5 * SR); t = np.arange(n) / SR
        v = np.zeros(n, np.float32)
        for a, b in BT.values():                     # «كلام»: ضجيجٌ مشكَّل بجهارة الصوت داخل الكتل وصمتٌ بينها
            i, j = int(a * SR), int(b * SR)
            v[i:j] = (np.random.default_rng(1).normal(0, 0.12, j - i) * (0.6 + 0.4 * np.sin(2 * np.pi * 3 * t[i:j]))).astype(np.float32)
        self.voice = v

    def test_rendered_stem_sits_under_voice_and_passes_gate(self):
        stem = sfx_cues.render(good_sheet(), BLOCKS, BT, self.voice, None, self.tmp.name, {})
        key = [BT['b2']]
        self.assertEqual(sfx_cues.mix_gate(self.voice, stem, key), [])
        i, j = int(1 * SR), int(5 * SR)
        self.assertLess(sfx_cues.rms_db(stem[i:j]) - sfx_cues.rms_db(self.voice[i:j]), -18)
        a, b = int(BT['b2'][0] * SR), int(BT['b2'][1] * SR)
        self.assertLess(float(np.abs(stem[a + SR:b - SR]).max()), 1e-4)     # صمتٌ فوق الجملة المفتاحية

    def test_gate_fails_loud_and_harsh_stem(self):
        n = len(self.voice)
        loud = np.random.default_rng(2).normal(0, 0.3, n).astype(np.float32)
        errs = sfx_cues.mix_gate(self.voice, loud, [BT['b2']])
        self.assertTrue(any('نسبةً للكلام' in e for e in errs))
        self.assertTrue(any('ذروة' in e for e in errs))
        self.assertTrue(any('مفتاحية' in e for e in errs))
        t = np.arange(n) / SR
        hiss = (0.02 * np.sin(2 * np.pi * 3500 * t) + 0.01 * np.random.default_rng(3).normal(0, 1, n)).astype(np.float32)
        self.assertTrue(any('حدّة' in e for e in sfx_cues.mix_gate(self.voice, hiss)))


class WholeWord(unittest.TestCase):
    def test_partial_words_do_not_trigger(self):
        d = lambda t: sfx_auto.derive({'blocks': ['x']}, {'x': t}, 'setup')
        self.assertNotEqual(d('في هذا الفيلم'), 'elephants')
        self.assertNotEqual(d('ثم قال لفيلقي'), 'elephants')
        self.assertNotEqual(d('وهو قليل'), 'night')
        self.assertEqual(d('وتقدّمت الفيلة'), 'elephants')
        self.assertEqual(d('النار تشتعل'), 'fire')


if __name__ == '__main__':
    unittest.main()
