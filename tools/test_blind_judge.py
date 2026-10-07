# -*- coding: utf-8 -*-
"""المقارنة العمياء، الإصدار الثاني (tools/blind_judge.py)، بلا شبكة. يُختبر فيها:
- المقاطع، والتكافؤ بلا تشكيلٍ ولا ترقيم.
- أزواج الصلاحية من منحنياتنا.
- الحكم بالترتيبين مع التعادل عند الانقلاب، وإبطال الحَكَمين إن التقيا على نموذجٍ واحد.
- نصف البوّابة بلا أسباب، والشرط المركّب، والتداخل اللفظيّ.
- الأهمّ أوّلاً، والحفظ بعد كلّ مقارنة، والموعد، والاستئناف بالبصمة (الشوطان 37342135465 و37344320201).
والحَكَم مستبدَل."""
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blind_judge as bj  # noqa: E402


def transcript(n_lines, step=5, word='كلمة', words=12):
    return "\n".join('[%d] (راوٍ) %s' % (i * step, " ".join([word] * words)) for i in range(n_lines))


def comp(i):
    return {'id': i, 'الجهة': 'منافس', 'الوسم': 'قناة %s: فيلم' % i, 'transcript': transcript(80, word='خصم'),
            'action': {'from': 200, 'to': 290, 'narration': " ".join(['ضربة'] * 60)}}


# فيلمٌ لنا من 1200 ث: «ثبات» حيث صعد الأداء النسبيّ في النافذة، و«هبوط» حيث نزل، والأداء يبقى على مستواه الجديد بعدها
HOLD, DROP = ((300, 360), (700, 760)), ((480, 540), (880, 940))
inside = lambda t, spans: any(a <= t < b for a, b in spans)
OURS = {'id': 'o1', 'الجهة': 'نحن', 'الوسم': 'لنا', 'duration_s': 1200,
        'transcript': "\n".join('[%d] (راوٍ) %s' % (t, " ".join([('ثبات' if inside(t, HOLD) else 'هبوط' if inside(t, DROP)
                                                                  else 'سرد')] * 12)) for t in range(0, 1200, 6))}


def rel_at(t):
    r = 0.5
    for a, b in HOLD:
        r += 0.1 * min(max((t - a) / (b - a), 0), 1)
    for a, b in DROP:
        r -= 0.1 * min(max((t - a) / (b - a), 0), 1)
    return round(r, 4)


CURVE = [[k / 100.0, 0.5, rel_at(k * 12.0)] for k in range(1, 101)]
STATS = {'الحقيقة': {'منحنى_البقاء_الطبيعي': {'o1': CURVE}, 'لكل_فيديو': [{'id': 'o1', 'الطول_ث': 1200}]}}


class SegTest(unittest.TestCase):
    def test_segments_and_plain(self):
        s = bj.segments(comp('c1'))
        self.assertEqual(set(s), {'opening', 'danger', 'action'})
        self.assertEqual(bj.clip('سَيْفٌ،  مَكْسُورٌ… «فِي» الْيَدِ؟', 3), 'سيف مكسور في')
        self.assertEqual(bj.channel_names({'الأفلام': [comp('c1')]}), ['قناة c1'])

    def test_calib_pairs_by_relative_change(self):
        pairs = bj.calib_pairs(OURS, CURVE, 1200)
        self.assertEqual(len(pairs), 2)
        for hold, drop, th, td in pairs:
            self.assertIn('ثبات', hold)
            self.assertIn('هبوط', drop)
            self.assertGreaterEqual(abs(th - td), 60)

    def test_overlap_ignores_quotes(self):
        theirs = [" ".join(['أ', 'ب', 'ج', 'د', 'ه', 'و'])]
        self.assertEqual(bj.overlap('أ ب ج د ه و', theirs), 1.0)
        self.assertEqual(bj.overlap('«أ ب ج د ه و» ز ح ط ي ك ل', theirs), 0.0)


class RunTest(unittest.TestCase):
    def fake(self, same_model=False, flip=False):
        seen = []

        def call(self_, mk, tag, budget_s=420, parse=None, cap_s=240, models=None):
            txt = json.loads(mk(False))['contents'][0]['parts'][0]['text']
            a = txt.split('النصّ A:')[1].split('النصّ B:')[0]
            b = txt.split('النصّ B:')[1]
            seen.append(models[0])
            # الحَكَم يختار «ثبات» على «هبوط»، والمسوّدة («سيف») على الخصم، والخصم على أفلامنا القديمة («سرد»)
            score = lambda t: 3 if 'ثبات' in t else 2 if 'سيف' in t else 1 if 'خصم' in t or 'ضربة' in t else 0
            w = 'A' if flip or score(a) >= score(b) else 'B'        # flip: انحيازٌ للموضع، يختار الأوّل دائماً
            return {'winner': w, 'why': 'سبب', '_model': 'one' if same_model else models[0]}
        return call, seen

    def req(self, **k):
        return dict({'المحاولة': 1, 'المرجع': ['c1', 'c2', 'c3', 'c4'], 'السقف': ['c5'], 'المعايرة': ['o1'],
                     'المسوّدة': [{'id': 'm', 'النوع': 'opening', 'النصّ': " ".join(['سيف'] * 100)}]}, **k)

    STYLE = {'الأفلام': [comp('c%d' % i) for i in range(1, 6)] + [OURS]}

    def test_gate_passes_with_valid_judge_and_all_conditions(self):
        call, seen = self.fake()
        with mock.patch.object(bj.Gem, 'call', call), mock.patch.object(bj, 'PAIRS_MIN', 2):
            rep = bj.run(self.req(), self.STYLE, STATS, bj.Gem(['k']), workers=2)
        s = rep['الخلاصة']
        self.assertEqual((s['الصلاحية']['أزواج'], s['الصلاحية']['دقّة_اختيار_الثبات']), (2, 1.0))
        self.assertTrue(s['الصلاحية']['صالح'])
        self.assertEqual(rep['المرجع'], {'تطوير': ['c1', 'c3'], 'بوّابة': ['c2', 'c4'], 'سقف': ['c5']})
        self.assertEqual(s['أفلامنا']['نسبة_الفوز'], 0.0)
        self.assertEqual(s['المسوّدة']['m/opening']['الفوز_بوّابة'], 1.0)
        self.assertEqual(rep['تجتاز'], {'m/opening': True}, s['المسوّدة'])
        self.assertEqual(set(seen), {bj.JUDGE_CHAINS[0][0], bj.JUDGE_CHAINS[1][0]})      # حَكَمان من سلسلتين
        self.assertTrue(all('why' not in r for r in rep['التفصيل']['المسوّدة_بوّابة']['m/opening']))  # بلا أسباب
        self.assertTrue(all('why' in r for r in rep['التفصيل']['المسوّدة_تطوير']['m/opening']))

    def test_each_condition_fails_alone(self):
        call, _ = self.fake()
        with mock.patch.object(bj.Gem, 'call', call), mock.patch.object(bj, 'PAIRS_MIN', 2):
            rep = bj.run(self.req(**{'المحاولة': 4}), self.STYLE, STATS, bj.Gem(['k']), workers=2)
            self.assertFalse(rep['تجتاز']['m/opening'])
            copy = {'id': 'm', 'النوع': 'opening', 'النصّ': transcript(30, word='خصم').replace('(راوٍ)', '')}
            rep = bj.run(self.req(**{'المسوّدة': [copy]}), self.STYLE, STATS, bj.Gem(['k']), workers=2)
            self.assertTrue(any('تداخل' in x for x in rep['الخلاصة']['المسوّدة']['m/opening']['أسباب_الرفض']))
        with mock.patch.object(bj.Gem, 'call', call):                    # الحدّ الأصليّ: 8 أزواج > 2
            rep = bj.run(self.req(), self.STYLE, STATS, bj.Gem(['k']), workers=2)
        self.assertFalse(rep['الخلاصة']['الصلاحية']['صالح'])
        self.assertTrue(any('صلاحيته' in x for x in rep['الخلاصة']['المسوّدة']['m/opening']['أسباب_الرفض']))

    def test_flip_is_tie_and_same_model_is_void(self):
        call, _ = self.fake(flip=True)
        with mock.patch.object(bj.Gem, 'call', call):
            rows = bj.duel(bj.Gem(['k']), 'سيف ' * 50, 'خصم ' * 50, 'opening', 't')
        self.assertEqual([r['score'] for r in rows], [0.5, 0.5])
        call, _ = self.fake(same_model=True)
        with mock.patch.object(bj.Gem, 'call', call):
            rows = bj.duel(bj.Gem(['k']), 'سيف ' * 50, 'خصم ' * 50, 'opening', 't')
        self.assertTrue(all('error' in r for r in rows))


class RobustTest(unittest.TestCase):
    """نفدت الحصّة فقُطعت الخطوة بلا تقرير ⇒ الأهمّ أوّلاً، وحفظٌ بعد كلّ مقارنة، وموعد، واستئنافٌ لا يعيد ما صحّ."""
    STYLE = RunTest.STYLE

    def req(self, **k):
        return RunTest.req(self, **k)

    def fake(self, fail=lambda tag: False):
        tags = []

        def call(self_, mk, tag, budget_s=420, parse=None, cap_s=240, models=None):
            tags.append(tag)
            if fail(tag):
                return {'error': 'Resource has been exhausted'}
            txt = json.loads(mk(False))['contents'][0]['parts'][0]['text']
            a = txt.split('النصّ A:')[1].split('النصّ B:')[0]
            return {'winner': 'A' if ('ثبات' in a or 'سيف' in a) else 'B', 'why': 'سبب', '_model': models[0]}
        return call, tags

    def test_priority_order_and_caps(self):
        call, tags = self.fake()
        ours = [dict(OURS, id='o%d' % i) for i in range(1, 7)]
        style = {'الأفلام': [comp('c%d' % i) for i in range(1, 8)] + ours}
        req = self.req(**{'المعايرة': [o['id'] for o in ours], 'السقف': ['c5', 'c6', 'c7']})
        with mock.patch.object(bj.Gem, 'call', call):
            rep = bj.run(req, style, STATS, bj.Gem(['k']), workers=1)
        order = []
        for t in tags:
            grp = t.split(':')[0]
            if not order or order[-1] != grp:
                order.append(grp)
        self.assertEqual(order, ['الصلاحية', 'المسوّدة_بوّابة', 'أفلامنا', 'المسوّدة_تطوير', 'المسوّدة_سقف'])
        self.assertEqual(rep['المرجع']['سقف'], ['c5', 'c6'])                          # CEIL_MAX
        self.assertEqual({sid.split('/')[0] for sid in rep['التفصيل']['أفلامنا']}, {'o1', 'o2', 'o3', 'o4'})  # BASE_MAX

    def test_save_after_each_duel_and_deadline(self):
        call, tags = self.fake()
        saved = []
        with mock.patch.object(bj.Gem, 'call', call):
            rep = bj.run(self.req(), self.STYLE, STATS, bj.Gem(['k']), workers=2, save=saved.append)
        self.assertEqual(len(saved), rep['التقدّم']['المقارنات'])
        self.assertTrue(rep['التقدّم']['مكتمل'])
        tags.clear()
        with mock.patch.object(bj.Gem, 'call', call):
            rep = bj.run(self.req(), self.STYLE, STATS, bj.Gem(['k']), workers=2, deadline_s=1e-9)
        self.assertEqual(tags, [])                                                    # بعد الموعد لا نداء
        self.assertEqual((rep['التقدّم']['أُنجز'], rep['التقدّم']['مكتمل']), (0, False))
        self.assertEqual(rep['التقدّم']['بعد_الموعد'], 2 * rep['التقدّم']['المقارنات'])

    def test_resume_reuses_only_valid_and_counts_passes(self):
        call, tags = self.fake(fail=lambda t: t.startswith('المسوّدة_سقف'))
        with mock.patch.object(bj.Gem, 'call', call):
            first = bj.run(self.req(), self.STYLE, STATS, bj.Gem(['k']), workers=2, fp='f1')
        p = first['التقدّم']
        self.assertFalse(p['مكتمل'])
        self.assertTrue(bj.needs_more(first, 'f1'))
        self.assertFalse(bj.needs_more(first, 'f2'))                                  # طلبٌ آخر ⇒ من جديد
        first = json.loads(json.dumps(first, ensure_ascii=False))                     # كما يُقرأ من الإصدار
        call, tags = self.fake()
        with mock.patch.object(bj.Gem, 'call', call):
            second = bj.run(self.req(), self.STYLE, STATS, bj.Gem(['k']), workers=2, prev=first, fp='f1')
        self.assertTrue(tags and all(t.startswith('المسوّدة_سقف') for t in tags))   # ما صحّ لا يُعاد
        self.assertTrue(second['التقدّم']['مكتمل'])
        self.assertEqual(second['التقدّم']['الأشواط'], 2)
        self.assertFalse(bj.needs_more(second, 'f1'))
        self.assertEqual(second['تجتاز'], first['تجتاز'] | second['تجتاز'])
        tags.clear()
        with mock.patch.object(bj.Gem, 'call', call):
            third = bj.run(self.req(), self.STYLE, STATS, bj.Gem(['k']), workers=2, prev=first, fp='f2')
        self.assertEqual(third['التقدّم']['الأشواط'], 1)
        self.assertEqual(len(tags), 2 * len(bj.JUDGE_CHAINS) * third['التقدّم']['المقارنات'])
        stale = dict(first, التقدّم=dict(p, الأشواط=bj.MAX_PASSES))
        self.assertFalse(bj.needs_more(stale, 'f1'))                                  # استنفد أشواطه

    def test_req_fp_follows_files(self):
        import tempfile
        d = tempfile.mkdtemp()
        r, e = os.path.join(d, 'j.json'), os.path.join(d, 'p.enc')
        io_w = lambda f, b: open(f, 'wb').write(b)
        io_w(r, b'{"a": 1}'); io_w(e, b'x')
        a = bj.req_fp(r, e)
        io_w(r, '{"a": 1, "_تشغيل": "2026-10-06"}'.encode('utf-8'))
        self.assertEqual(a, bj.req_fp(r, e))                                          # مفتاحُ «_» يطلق ولا يغيّر
        io_w(r, b'{"a": 2}')
        self.assertNotEqual(a, bj.req_fp(r, e))
        io_w(r, b'{"a": 1}'); io_w(e, b'y')
        self.assertNotEqual(a, bj.req_fp(r, e))                                       # مسوّدةٌ مختومةٌ أخرى


class SealedDraftTest(unittest.TestCase):
    def test_main_reads_unsealed_draft_and_refuses_without_it(self):
        import tempfile
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, 'ops', 'stats'))
        json.dump({'المسوّدة_المختومة': True, 'المسوّدة': [], 'المعايرة': []},
                  open(os.path.join(d, 'ops', 'stats', 'judge.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        json.dump({'الأفلام': []}, open(os.path.join(d, 'style.json'), 'w', encoding='utf-8'))
        json.dump({'المسوّدة': [{'id': 'm', 'النوع': 'opening', 'النصّ': 'سيف'}]},
                  open(os.path.join(d, 'draft.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        seen = {}

        def fake_run(req, style, stats, g, workers=6, deadline_s=None, save=None, prev=None, fp=''):
            seen['req'] = req
            return {'الخلاصة': {'الصلاحية': {'أزواج': 0}, 'أفلامنا': {}, 'المسوّدة': {}}, 'تجتاز': {}}
        cwd = os.getcwd()
        try:
            os.chdir(d)
            with mock.patch.object(bj, 'keys_from', lambda p: ['k']), mock.patch.object(bj, 'run', fake_run):
                with mock.patch.object(sys, 'argv', ['bj', os.path.join(d, 'o.json'), '--keys', 'k', '--style', 'style.json']):
                    self.assertEqual(bj.main(), 1)                         # مختومةٌ ولم تُفضّ ⇒ لا حكم
                with mock.patch.object(sys, 'argv', ['bj', os.path.join(d, 'o.json'), '--keys', 'k', '--style', 'style.json',
                                                     '--draft', 'draft.json']):
                    bj.main()
        finally:
            os.chdir(cwd)
        self.assertEqual(seen['req']['المسوّدة'][0]['id'], 'm')


if __name__ == '__main__':
    unittest.main()
