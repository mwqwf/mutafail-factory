# -*- coding: utf-8 -*-
"""دراسة الأسلوب (tools/style_study.py) بلا شبكة: فصل التحليل عن التفريغ ولو قُطع الجواب، واختيار أشدّ نافذة أكشن،
وتوزيع أجوبة المصغّرات على صورها، والاستئناف الذي يُبقي الناجح ويعدّ المحاولات — نداء جيميناي والصفحة والصور مستبدَلة."""
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style_study as ss  # noqa: E402


class ParseTest(unittest.TestCase):
    def test_film_json_then_transcript_even_if_cut(self):
        txt = '```json\n{"duration_s": 600, "chapters": []}\n```\n' + ss.MARK + '\n[0] (راوٍ) جملةٌ أولى\n[4] (راوٍ) وثانيةٌ مقطو'
        out = ss.parse_film(txt)
        self.assertEqual(out['duration_s'], 600)
        self.assertEqual(out['_lines'], 2)
        self.assertTrue(out['transcript'].startswith('[0]'))

    def test_marker_variants_minutes_and_inner_transcript(self):
        # العلامة بصيغةٍ أخرى، والزمن دقائق:ثوانٍ (نصف أفلام الشوط 37329810245)
        out = ss.parse_film('{"duration_s": 90}\n=== TRANSCRIPT ===\n[00:05] (راوٍ) أ\n[1:02:03] (راوٍ) ب')
        self.assertEqual(out['transcript'], '[5] (راوٍ) أ\n[3723] (راوٍ) ب')
        self.assertEqual(out['_lines'], 2)
        # بلا علامة: ما بعد الكائن تفريغ، ولو أحاطت به أسوار الشيفرة
        out = ss.parse_film('```json\n{"duration_s": 90, "chapters": [{"from": 0}]}\n```\n[0] (راوٍ) أ\n[12] (راوٍ) ب')
        self.assertEqual((out['chapters'], out['_lines']), ([{'from': 0}], 2))
        # والتفريغ داخل الكائن قائمةً
        out = ss.parse_film('{"duration_s": 90, "transcript": [{"s": 3, "speaker": "خالد", "text": "ج"}]}')
        self.assertEqual(out['transcript'], '[3] (خالد) ج')

    def test_thin_transcript_and_needs_more(self):
        full = "\n".join('[%d] (راوٍ) س' % (i * 30) for i in range(40))           # سطرٌ كلّ نصف دقيقة لعشرين دقيقة
        self.assertFalse(ss.thin({'duration_s': 1200, 'transcript': full}))
        self.assertTrue(ss.thin({'duration_s': 1625, 'transcript': '[0] (راوٍ) الفيلم كلّه في سطر'}))
        self.assertTrue(ss.thin({'duration_s': 600, 'transcript': ''}))
        self.assertFalse(ss.thin({'error': 'x'}))
        self.assertTrue(ss.needs_more({'الأفلام': [{'duration_s': 600, 'transcript': ''}]}))
        self.assertFalse(ss.needs_more({'الأفلام': [{'duration_s': 600, 'transcript': '', '_tries': ss.MAX_TRIES}]}))
        self.assertTrue(ss.needs_more({'الريلزات': [{'error': '429', '_tries': 1}]}))
        self.assertFalse(ss.needs_more({'الأفلام': [{'duration_s': 1200, 'transcript': full}]}))

    def test_strongest_action_window_clamped_to_end(self):
        a = {'action_scenes': [{'from': 100, 'intensity': 6}, {'from': 570, 'intensity': 9}],
             'chapters': [{'from': 300, 'role': 'battle_action', 'intensity': 8}]}
        self.assertEqual(ss.strongest_action(a, 600), (510.0, 600.0))      # أشدّها عند 570 ⇒ تُسحب لتسع 90 ث
        self.assertIsNone(ss.strongest_action({'chapters': [{'from': 0, 'role': 'context'}]}, 600))


class RunTest(unittest.TestCase):
    def test_resume_batches_and_tries(self):
        full = "\n".join('[%d] (راوٍ) س' % (i * 20) for i in range(30))
        req = {'الأفلام': [{'id': 'f1', 'الوسم': 'أ', 'الطول_د': 10}, {'id': 'f2', 'الوسم': 'ب', 'الطول_د': 10},
                            {'id': 'f3', 'الوسم': 'ج', 'الطول_د': 10}, {'id': 'f4', 'الوسم': 'د', 'الطول_د': 10}],
               'الريلزات': [{'id': 'r1', 'الوسم': 'ر'}],
               'المصغّرات': [{'id': 't%d' % i, 'العنوان': 'ع', 'المشاهدات': i} for i in range(7)]}
        prev = {'الأفلام': {'f1': {'id': 'f1', 'duration_s': 600, 'transcript': full},
                            'f3': {'id': 'f3', 'duration_s': 600, 'transcript': '', 'chapters': [1]},        # رقيق ⇒ يُعاد
                            'f4': {'id': 'f4', 'duration_s': 600, 'transcript': '[0] (راوٍ) أ\n[9] (راوٍ) ب'}},
                'الريلزات': {'r1': {'id': 'r1', 'error': '429', '_tries': 1}},
                'المصغّرات': {}}
        calls = []

        def fake_call(self, mk, tag, budget_s=420, parse=None, cap_s=240):
            calls.append(tag)
            if tag == 'f2':
                return {'duration_s': 600, 'action_scenes': [{'from': 60, 'intensity': 7}], 'transcript': '[0] (راوٍ) س'}
            if tag == 'f2#أكشن':
                return {'shots': 40}
            if tag == 'f3':
                return {'duration_s': 600, 'transcript': full}
            if tag == 'f4':
                return {'error': '429'}                                  # المحاولة أسوأ ⇒ يبقى القديم وتُحسب عليه
            if tag == 'r1':
                return {'error': '503'}
            body = json.loads(mk(False))
            n = sum(1 for p in body['contents'][0]['parts'] if 'inlineData' in p)
            return {'items': [{'i': i, 'words': i} for i in range(1, n + 1) if i != 2]}   # الصورة الثانية بلا جواب

        d = tempfile.mkdtemp()
        out = os.path.join(d, 'out.json')
        with mock.patch.object(ss.Gem, 'call', fake_call), mock.patch.object(ss, 'thumb', lambda vid: b'x' * 6000), \
             mock.patch.object(ss, 'page', lambda vid: {'heatmap': None}):
            st = ss.Study(req, prev, out, ss.Gem(['k']))
            st.run({'films', 'reels', 'thumbs', 'page'}, 3)
        rep = json.load(io.open(out, encoding='utf-8'))
        films = {f['id']: f for f in rep['الأفلام']}
        self.assertNotIn('f1', calls)                                  # الناجح لا يُعاد
        self.assertIn('f3', calls)                                     # والرقيق يُعاد
        self.assertEqual(films['f3']['_lines'] if '_lines' in films['f3'] else ss.n_lines(films['f3']['transcript']), 30)
        self.assertEqual(films['f4']['transcript'], '[0] (راوٍ) أ\n[9] (راوٍ) ب')
        self.assertEqual(films['f4']['_tries'], 2)
        self.assertEqual(films['f2']['action']['shots'], 40)
        self.assertEqual((films['f2']['action']['from'], films['f2']['action']['to']), (60.0, 150.0))
        self.assertIn('page', films['f2'])
        self.assertEqual(rep['الريلزات'][0]['_tries'], 2)
        th = {t['id']: t for t in rep['المصغّرات']}
        self.assertEqual(len(th), 7)
        self.assertIn('error', th['t1'])                               # الثانية في الدفعة الأولى
        self.assertEqual(th['t0']['words'], 1)
        self.assertEqual(th['t6']['words'], 1)                         # الدفعة الثانية تبدأ من 1
        self.assertEqual(rep['نجح'], {'الأفلام': 4, 'الريلزات': 0, 'المصغّرات': 6})   # 5 من الأولى + 1


class LocalTest(unittest.TestCase):
    def test_local_draft_inline_one_fps_with_action_window_no_page(self):
        d = tempfile.mkdtemp()
        src = os.path.join(d, 'preview.mp4')
        open(src, 'wb').write(b'0' * 10)
        sent = []

        def fake_call(self, mk, tag, budget_s=420, parse=None, cap_s=240):
            sent.append(json.loads(mk(False))['contents'][0]['parts'][0])
            return {'duration_s': 720, 'action_scenes': [{'from': 60, 'intensity': 9}], 'transcript': ''}

        def fake_proxy(path):
            p = path + '.proxy.mp4'
            open(p, 'wb').write(b'tiny')
            return p
        with mock.patch.object(ss.Gem, 'call', fake_call), mock.patch.object(ss, 'proxy', fake_proxy), \
             mock.patch.object(ss, 'page', lambda vid: self.fail('لا صفحة لمسوّدة')):
            st = ss.Study({'الأفلام': [{'id': 'mutah-draft', 'ملف': src, 'الطول_ث': 720}]}, {}, os.path.join(d, 'o.json'),
                          ss.Gem(['k']))
            st.run({'films', 'page'}, 1)
        self.assertEqual(len(sent), 2)                                   # التحليل ونافذة الأكشن، ولا صفحة
        self.assertEqual(sent[0]['inlineData']['mimeType'], 'video/mp4')
        self.assertEqual(sent[0]['videoMetadata'], {'fps': 1.0})        # إطارٌ في الثانية: يُرى الإيقاع
        self.assertEqual(sent[1]['videoMetadata'], {'startOffset': '60s', 'endOffset': '150s'})
        self.assertIn('inlineData', sent[1])


if __name__ == '__main__':
    unittest.main()
