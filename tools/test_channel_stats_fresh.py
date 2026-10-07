# -*- coding: utf-8 -*-
"""مؤشّرات الأفلام الجديدة على خطّة القياس (channel_stats.fresh): البقاء عند 30 ث و150 ث من المنحنى الطبيعيّ،
وحصّة المقترحات بلا المدفوع، وما سقط دون الحدّ — وتُستبعد الريلزات وما خرج عن نافذة 3–14 يوماً."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import channel_stats as cs  # noqa: E402


class _Q:
    def __init__(self, rows):
        self.rows = rows

    def execute(self):
        return {'rows': self.rows}


class _Reports:
    def __init__(self, rows):
        self.rows, self.calls = rows, 0

    def query(self, **kw):
        self.calls += 1
        assert 'audienceType==ORGANIC' in kw['filters']
        return _Q(self.rows)


class _YA:
    def __init__(self, rows):
        self.r = _Reports(rows)

    def reports(self):
        return self.r


def film(**kw):
    base = {'id': 'v1', 'العنوان': 'فيلم', 'النشر': '2026-10-01', 'الأيام': 4, 'الطول_ث': 1000, 'ريلز': False,
            'بقاء_الطبيعية_ث': 200.0, 'طبيعية_يومياً': 120.0,
            'المصادر': {'RELATED_VIDEO': [60, 200], 'SUBSCRIBER': [10, 150], 'YT_SEARCH': [30, 90], 'ADVERTISING': [900, 40]}}
    base.update(kw)
    return base


class FreshTest(unittest.TestCase):
    def test_points_share_and_flags(self):
        # 1٪ من 1000 ث = 10 ث: النقاط عند 10، 20، 30، … ⇒ عند 30 ث القيمة 0.62 وعند 150 ث القيمة 0.31
        rows = [[i / 100, v, r] for i, v, r in [(1, 0.99, 0.5), (2, 0.8, 0.5), (3, 0.62, 0.5), (4, 0.5, 0.5), (10, 0.4, 0.38),
                                                (15, 0.31, 0.5), (16, 0.3, 0.5), (50, 0.2, 0.61), (90, 0.1, 0.52)]]
        out = cs.fresh(_YA(rows), [film()], dt.date(2026, 10, 5))
        k = out['v1']
        self.assertEqual((k['بقاء_30ث'], k['بقاء_150ث']), (62, 31))
        self.assertEqual(k['حصة_المقترحات'], 70)          # (60+10)/(60+10+30): المدفوع خارج المقام
        self.assertEqual((k['نسبي_عشر'], k['نسبي_نصف'], k['نسبي_تسعة_أعشار']), (38, 61, 52))
        self.assertEqual(set(k['تحت_الحدّ']), {'بقاء_30ث', 'بقاء_150ث', 'متوسط_المشاهدة_ث', 'طبيعية_يومياً', 'نسبي_عشر'})

    def test_nearest_point_on_coarse_curve(self):
        # فيلم 1668 ث: النقاط عند 16.7 ث (1.02) و33.4 ث (0.63) ⇒ أقرب نقطةٍ إلى 30 ث هي 33.4 لا 16.7 (كان 102٪ خطأً)
        rows = [[0.01, 1.02], [0.02, 0.63], [0.09, 0.33], [0.10, 0.31]]
        k = cs.fresh(_YA(rows), [film(الطول_ث=1668)], dt.date(2026, 10, 5))['v1']
        self.assertEqual((k['بقاء_30ث'], k['عند_ث'][0]), (63, 33))
        self.assertEqual((k['بقاء_150ث'], k['عند_ث'][1]), (33, 150))

    def test_window_and_reels_skipped(self):
        ya = _YA([])
        out = cs.fresh(ya, [film(id='r', ريلز=True), film(id='old', الأيام=20), film(id='new', الأيام=2)], dt.date(2026, 10, 5))
        self.assertEqual(out, {})
        self.assertEqual(ya.r.calls, 0)

    def test_missing_curve_is_not_a_failure(self):
        out = cs.fresh(_YA([]), [film()], dt.date(2026, 10, 5))
        self.assertIsNone(out['v1']['بقاء_30ث'])
        self.assertNotIn('بقاء_30ث', out['v1']['تحت_الحدّ'])


if __name__ == '__main__':
    unittest.main()
