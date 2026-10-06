# -*- coding: utf-8 -*-
"""مختبر الأصوات (tools/voice_lab.py) بلا شبكة ولا ffmpeg: لا فائز بلا حكمٍ فعليّ (درس مؤتة 2026-10-05)، والناقص يمنع الحكم،
ولكلّ دورٍ فائزه بغرضه، وتعذّر حكم المعالجة يُبقي الافتراض."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voice_lab as vl  # noqa: E402

NARR = {'slug': 't', 'voices': ['A', 'B', 'C'],
        'styles': {'epic': 'EPIC NOTES', 'urgent': 'URGENT NOTES'},
        'lines': [{'id': 'L1', 'text': 'أ'}, {'id': 'L2', 'text': 'ب'}, {'id': 'L3', 'text': 'ج'}],
        'stage1_lines': ['L1', 'L2'], 'finalists': 2}
ROLES = {'slug': 't-voices', 'voices': ['A', 'B'],
         'styles': {'quote': 'QUOTE NOTES', 'recitation': 'RECITE NOTES'},
         'lines': [{'id': 'Q1', 'text': 'ق'}, {'id': 'P1', 'text': 'ش'}, {'id': 'P2', 'text': 'ش٢'}],
         'roles': {'quote': {'styles': ['quote'], 'lines': ['Q1'], 'finalists': 2, 'purpose': 'اقتباس'},
                   'poetry': {'styles': ['recitation'], 'lines': ['P1', 'P2'], 'stage1_lines': ['P1'], 'finalists': 2,
                              'purpose': 'إلقاء'}}}


class FakeJudge:
    """يرتّب بالترتيب الأبجديّ المعكوس (C قبل B قبل A) إلا حيث يُطلب التعذّر."""
    def __init__(self, fail_on=()):
        self.fail_on, self.calls, self.seen = set(fail_on), 0, []

    def rank(self, clips, text, purpose):
        self.calls += 1
        self.seen.append((purpose, sorted(lab for lab, _ in clips)))
        labels = [lab for lab, _ in clips]
        if purpose in self.fail_on or text in self.fail_on:
            return labels, {'error': 'لا حكم'}
        return sorted(labels, reverse=True), {'leaked': [], 'notes': {}, 'model': 'fake'}


def fake_generate(skip=()):
    def gen(vdir, blocks, keys):
        lab = Path(vdir).name.replace('_', '·')
        return {b['id']: '%s/%s.wav' % (vdir, b['id']) for b in blocks if '%s/%s' % (lab, b['id']) not in skip}
    return gen


class LabTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.patches = [mock.patch.object(vl, 'measure', lambda f, t: {'dur': 3.0}),
                        mock.patch.object(vl, 'join_lines', lambda files, out: str(out)),
                        mock.patch.object(vl, 'apply_chain', lambda src, flt, out: str(out)),
                        mock.patch.object(vl, 'to_mp3', lambda *a, **k: None)]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])

    def role(self, spec, judge, gen=None, name=None):
        cfg = vl.roles_of(spec)
        name = name or next(iter(cfg))
        with mock.patch.object(vl, 'generate', gen or fake_generate()):
            return vl.lab_role(name, cfg[name], spec, judge, self.d, self.d, 'k.json')

    def test_judged_lab_names_a_winner_with_judged_chain(self):
        r = self.role(NARR, FakeJudge())
        self.assertEqual(r['finalists'], ['C·urgent', 'C·epic'])          # بوردا على جملتين محكَّمتين
        self.assertEqual((r['winner']['voice'], r['winner']['style']), ('C', 'urgent'))
        self.assertEqual(r['winner']['director'], 'URGENT NOTES')
        self.assertEqual(r['winner']['chain'], 'M2')                      # الأبجديّ المعكوس لـ M0 M1 M2
        self.assertNotIn('error', r)
        self.assertEqual(r['generated'], 3 * 2 * 2 + 2 * 1)               # المرحلة الأولى + الجملة الثالثة للمتأهّلَين

    def test_failed_final_judgement_is_not_a_winner(self):
        r = self.role(NARR, FakeJudge(fail_on={'أ / ب / ج'}))               # نصّ الحكم الأخير المتّصل
        self.assertNotIn('winner', r)
        self.assertIn('تعذّر الحكم الأخير', r['error'])
        self.assertEqual(r['finalists'], ['C·urgent', 'C·epic'])

    def test_failed_stage1_line_stops_without_random_order(self):
        r = self.role(NARR, FakeJudge(fail_on={'ب'}))
        self.assertEqual(r['stage1']['L2']['order'], [])                   # لا ترتيبَ مخلوطاً يُحسب حكماً
        self.assertIn('error', r['stage1']['L2'])
        self.assertNotIn('finalists', r)
        self.assertNotIn('winner', r)

    def test_missing_samples_block_judging(self):
        j = FakeJudge()
        r = self.role(NARR, j, fake_generate(skip={'B·epic/L2'}))
        self.assertIn('ناقص التوليد', r['error'])
        self.assertEqual(j.calls, 0)                                       # لا حصّة حكمٍ على مقارنةٍ ظالمة
        j = FakeJudge()
        r = self.role(NARR, j, fake_generate(skip={'C·urgent/L3'}))         # الناقص في متأهّلٍ: لا حكم أخير
        self.assertIn('C·urgent', r['error'])
        self.assertNotIn('winner', r)

    def test_unjudged_chain_keeps_default_processing(self):
        r = self.role(NARR, FakeJudge(fail_on={vl.CHAIN_PURPOSE}))
        self.assertEqual(r['winner']['voice'], 'C')
        self.assertIsNone(r['winner']['chain'])
        self.assertIsNone(r['winner']['filter'])

    def test_roles_have_separate_winners_purposes_and_no_chains(self):
        j = FakeJudge()
        q = self.role(ROLES, j, name='quote')
        p = self.role(ROLES, j, name='poetry')
        self.assertEqual((q['winner']['voice'], q['winner']['style']), ('B', 'quote'))
        self.assertEqual((p['winner']['voice'], p['winner']['style']), ('B', 'recitation'))
        purposes = {x[0] for x in j.seen}
        self.assertEqual(purposes, {'اقتباس', 'إلقاء'})                    # لا غرضَ الراوي على صوت الاقتباس
        self.assertNotIn('chains', q)
        self.assertEqual(q['stage1'], {})                                  # مرشّحان لا يزيدان على الأوائل: حكمٌ أخيرٌ وحده

    def test_main_writes_roles_and_fails_without_every_winner(self):
        spec = self.d / 'spec.json'
        spec.write_text(json.dumps(ROLES, ensure_ascii=False), encoding='utf-8')
        out = self.d / 'out'
        cwd = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, cwd)
        with mock.patch.object(vl, 'generate', fake_generate()), mock.patch.object(vl, 'Judge', lambda keys: FakeJudge()):
            self.assertEqual(vl.main([str(spec), '--keys', 'k.json', '--out', str(out)]), 0)
        res = json.loads((out / 't-voices-results.json').read_text(encoding='utf-8'))
        self.assertEqual(set(res['roles']), {'quote', 'poetry'})
        self.assertNotIn('winner', res)                                    # الأعلى للراوي الواحد وحده
        with mock.patch.object(vl, 'generate', fake_generate()), \
             mock.patch.object(vl, 'Judge', lambda keys: FakeJudge(fail_on={'إلقاء'})):
            self.assertEqual(vl.main([str(spec), '--keys', 'k.json', '--out', str(out)]), 1)

    def test_single_narrator_keeps_first_result_format(self):
        spec = self.d / 'n.json'
        spec.write_text(json.dumps(dict(NARR, pos_styles={'medina': 'epic'}), ensure_ascii=False), encoding='utf-8')
        cwd = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, cwd)
        with mock.patch.object(vl, 'generate', fake_generate()), mock.patch.object(vl, 'Judge', lambda keys: FakeJudge()):
            self.assertEqual(vl.main([str(spec), '--keys', 'k.json', '--out', str(self.d / 'o')]), 0)
        res = json.loads((self.d / 'o' / 't-results.json').read_text(encoding='utf-8'))
        self.assertEqual(res['winner']['voice'], 'C')
        self.assertEqual(res['roles']['narrator']['winner'], res['winner'])
        self.assertEqual(res['pos_styles'], {'medina': 'epic'})
        self.assertEqual(res['styles']['urgent'], 'URGENT NOTES')


class TournamentTest(unittest.TestCase):
    def test_error_in_a_group_round_voids_the_line(self):
        clips = {'V%d·s' % i: 'f%d' % i for i in range(10)}               # أكثر من ثمانية: جولة مجموعات
        order, info = vl.tournament(FakeJudge(fail_on={'نصّ'}), clips, 'نصّ', 'غرض')
        self.assertEqual(order, [])
        self.assertEqual(info['error'], 'لا حكم')
        order, info = vl.tournament(FakeJudge(), clips, 'نصّ', 'غرض')
        self.assertEqual(len(order), 4)                                     # اثنان من كلّ مجموعة
        self.assertNotIn('error', info)


if __name__ == '__main__':
    unittest.main()
