# -*- coding: utf-8 -*-
"""حدّ النسبة الحيّة (أمر المالك: ثابت واحد 75٪، وkb3d لا يُحسب) ومنع البديل الصامت."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envpaths  # noqa: E402
import live_share as ls  # noqa: E402
import motion_plan as mp  # noqa: E402


def _mp4(path, kind, frames=25, size='320x180'):
    """kind: اسم مصدر lavfi (testsrc/smptebars/color=c=blue...)."""
    src = kind if '=' in kind or kind.startswith('color') else {
        'red': 'testsrc=s=%s:r=25' % size,
        'green': 'testsrc2=s=%s:r=25' % size,
        'blue': 'smptebars=s=%s:r=25' % size,
    }.get(kind, 'color=c=%s:s=%s' % (kind, size))
    if 's=' not in src and src.startswith('color'):
        src = 'color=c=%s:s=%s' % (kind, size)
    subprocess.run(
        ['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi',
         '-i', '%s:d=%.3f' % (src, frames / 25.0) if ':d=' not in src else src,
         '-frames:v', str(frames),
         '-c:v', 'libx264', '-pix_fmt', 'yuv420p', path],
        check=True)


class Constant(unittest.TestCase):
    def test_single_constant_is_75_and_shared(self):
        self.assertEqual(ls.MIN_LIVE_SHARE, 0.75)
        self.assertIs(mp.MIN_LIVE_SHARE, ls.MIN_LIVE_SHARE)


class PlanShare(unittest.TestCase):
    def test_kb3d_is_not_counted_and_below_75_fails(self):
        shots = (
            [{'id': 'L%d' % i, 'kind': 'live', 'emotion': 'awe', 'video_prompt': 'p'} for i in range(2)]
            + [{'id': 'K%d' % i, 'kind': 'kb3d', 'emotion': 'journey', 'move3d': 'truck_r'} for i in range(2)]
        )
        durs = [10, 10, 10, 10]  # 50٪ حيّ
        share, live, total, _ = ls.plan_share(shots, durs)
        self.assertAlmostEqual(share, 0.5)
        self.assertAlmostEqual(live, 20)
        self.assertAlmostEqual(total, 40)
        errs = mp.lint(shots, starts=[0, 10, 20, 30], durations=durs)
        self.assertTrue(any('نسبة' in e or 'حيّ' in e for e in errs), errs)

    def test_75_percent_live_passes_and_waiver_counts_against(self):
        shots = (
            [{'id': 'L%d' % i, 'kind': 'live', 'emotion': 'awe', 'video_prompt': 'p'} for i in range(3)]
            + [{'id': 'K0', 'kind': 'kb3d', 'emotion': 'journey', 'move3d': 'truck_r'}]
        )
        durs = [10, 10, 10, 10]  # 75٪
        self.assertGreaterEqual(ls.plan_share(shots, durs)[0], ls.MIN_LIVE_SHARE)
        self.assertEqual(mp.lint(shots, starts=[0, 10, 20, 30], durations=durs), [])
        waived = ls.plan_share(shots, durs, waivers={'L2': 'رُفض بعد ثلاث محاولات'})
        self.assertAlmostEqual(waived[0], 0.5)
        errs = mp.lint(shots, starts=[0, 10, 20, 30], durations=durs,
                       waivers={'L2': 'رُفض بعد ثلاث محاولات'})
        self.assertTrue(any('نسبة' in e or 'حيّ' in e for e in errs), errs)


class WaiversAndEnforce(unittest.TestCase):
    def test_load_waivers_dict_and_list(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, 'live_waivers.json')
            json.dump({'S01': 'خريطة'}, open(p, 'w', encoding='utf-8'))
            self.assertEqual(ls.load_waivers(d)['S01'], 'خريطة')
            json.dump([{'id': 'S02', 'reason': 'أقل من 2.5 ث'}], open(p, 'w', encoding='utf-8'))
            self.assertEqual(ls.load_waivers(d)['S02'], 'أقل من 2.5 ث')
            json.dump(['S03'], open(p, 'w', encoding='utf-8'))
            self.assertIn('S03', ls.load_waivers(d))

    def test_enforce_rejects_live_without_clip(self):
        shots = [{'id': 'S01', 'kind': 'live'}, {'id': 'S02', 'kind': 'kb3d'}]
        with self.assertRaises(SystemExit) as cm:
            ls.enforce_live_clips('/tmp', shots, has_clip=lambda sid: False, allow=False, waivers={})
        self.assertIn('S01', str(cm.exception))
        self.assertNotIn('S02', str(cm.exception))

    def test_enforce_allow_and_waiver_warn_and_do_not_raise(self):
        shots = [{'id': 'S01', 'kind': 'live'}, {'id': 'S02', 'kind': 'live'}]
        fb, wv, warns = ls.enforce_live_clips(
            '/tmp', shots, has_clip=lambda sid: False, allow=True, waivers={})
        self.assertEqual(fb, ['S01', 'S02'])
        self.assertTrue(any('ALLOW_LIVE_FALLBACK' in w and 'غير صالح' in w for w in warns), warns)
        fb, wv, warns = ls.enforce_live_clips(
            '/tmp', shots, has_clip=lambda sid: False, allow=False,
            waivers={'S01': 'خريطة', 'S02': 'رُفض'})
        self.assertEqual(sorted(wv), ['S01', 'S02'])
        self.assertTrue(any('إعفاء' in w or 'live_waivers' in w for w in warns), warns)

    def test_apply_reserve_is_not_silent(self):
        shots = [{'id': 'S01', 'kind': 'live'}, {'id': 'S02', 'kind': 'live'}]
        reserve = {'S01': ('dolly_in', 1.2, 'in'), 'S02': ('crane_up', 1.0, 'out')}
        applied, warns = ls.apply_kb3d_reserve(shots, reserve, waivers={}, allow=False)
        self.assertEqual(applied, [])
        self.assertFalse(any(s.get('move3d') for s in shots))
        self.assertTrue(any('صامت' in w or 'ALLOW_LIVE_FALLBACK' in w for w in warns), warns)
        applied, warns = ls.apply_kb3d_reserve(shots, reserve, waivers={'S01': 'سبب'}, allow=False)
        self.assertEqual(applied, ['S01'])
        self.assertEqual(shots[0]['move3d'], 'dolly_in')
        self.assertTrue(any('⚠️' in w or 'إعفاء' in w or 'احتياط' in w for w in warns), warns)


class Measure(unittest.TestCase):
    def test_measure_counts_only_visible_live_clips_not_kb3d(self):
        with tempfile.TemporaryDirectory() as d:
            clips = Path(d, 'clips'); clips.mkdir()
            live = str(clips / 'L1.mp4')
            other = str(Path(d, 'kb.mp4'))
            film = str(Path(d, 'film.mp4'))
            _mp4(live, 'red', 50)
            _mp4(other, 'blue', 50)
            # فيلم: 2 ث حيّ (أحمر) ثم 2 ث kb3d (أزرق) = 50٪ ظاهرة — دون العتبة
            subprocess.run(
                ['ffmpeg', '-v', 'error', '-y', '-i', live, '-i', other,
                 '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0[v]', '-map', '[v]',
                 '-c:v', 'libx264', '-pix_fmt', 'yuv420p', film], check=True)
            shots = [{'id': 'L1', 'kind': 'live'}, {'id': 'K1', 'kind': 'kb3d'}]
            tl = {'L1': [0.0, 2.0], 'K1': [2.0, 2.0]}
            json.dump(shots, open(Path(d, 'shots.json'), 'w', encoding='utf-8'))
            json.dump(tl, open(Path(d, 'timeline.json'), 'w', encoding='utf-8'))
            res = ls.measure_film(d, film)
            self.assertAlmostEqual(res['share'], 0.5, delta=0.08)
            self.assertLess(res['share'], ls.MIN_LIVE_SHARE)
            self.assertFalse(res['ok'])
            # 3 ث حيّ + 1 ث kb3d = 75٪
            live3 = str(Path(d, 'live3.mp4')); _mp4(live3, 'green', 75)
            kb1 = str(Path(d, 'kb1.mp4')); _mp4(kb1, 'blue', 25)
            film2 = str(Path(d, 'film2.mp4'))
            subprocess.run(
                ['ffmpeg', '-v', 'error', '-y', '-i', live3, '-i', kb1,
                 '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0[v]', '-map', '[v]',
                 '-c:v', 'libx264', '-pix_fmt', 'yuv420p', film2], check=True)
            shots2 = [{'id': 'L1', 'kind': 'live'}, {'id': 'K1', 'kind': 'kb3d'}]
            # ضع المقطع الحيّ باسم L1.mp4 (استبدل الأحمر بالأخضر)
            os.replace(live3, live)
            json.dump(shots2, open(Path(d, 'shots.json'), 'w', encoding='utf-8'))
            json.dump({'L1': [0.0, 3.0], 'K1': [3.0, 1.0]}, open(Path(d, 'timeline.json'), 'w', encoding='utf-8'))
            res2 = ls.measure_film(d, film2)
            self.assertGreaterEqual(res2['share'], ls.MIN_LIVE_SHARE - 0.04)
            self.assertTrue(res2['ok'])

    def test_write_film_meta_marks_unpublishable_on_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'film.mp4.json')
            meta = ls.write_film_meta(path, share=0.4, fallback_ids=['S01'], waiver_ids=[], allow=True)
            self.assertFalse(meta['publishable'])
            self.assertTrue(json.load(open(path, encoding='utf-8'))['live_fallback'])
            self.assertIn('غير صالح', meta.get('note', '') + ''.join(meta.get('warnings', [])))


class LogoEnv(unittest.TestCase):
    def test_default_is_history_logo(self):
        os.environ.pop('MUTAFAIL_CHANNEL', None)
        p = envpaths.logo(required=True)
        self.assertTrue(p.endswith('assets/logo.png') or p.endswith('logo.png'))
        self.assertTrue(os.path.exists(p))

    def test_channel_env_reads_channel_json(self):
        with tempfile.TemporaryDirectory() as d:
            asset_dir = Path(d, 'ops', 'channels', 'demo')
            asset_dir.mkdir(parents=True)
            logo = Path(d, 'demo_logo.png')
            # انسخ شعاراً موجوداً أصلاً
            src = envpaths.logo()
            logo.write_bytes(Path(src).read_bytes())
            json.dump({'logo': {'asset': 'demo_logo.png'}}, open(asset_dir / 'channel.json', 'w', encoding='utf-8'))
            old = envpaths._REPO
            try:
                envpaths._REPO = d
                os.environ['MUTAFAIL_CHANNEL'] = 'demo'
                self.assertEqual(os.path.realpath(envpaths.logo()), os.path.realpath(str(logo)))
            finally:
                envpaths._REPO = old
                os.environ.pop('MUTAFAIL_CHANNEL', None)

    def test_missing_channel_logo_exits(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'ops', 'channels', 'demo').mkdir(parents=True)
            json.dump({'logo': {'asset': 'nope.png'}},
                      open(Path(d, 'ops', 'channels', 'demo', 'channel.json'), 'w', encoding='utf-8'))
            old = envpaths._REPO
            try:
                envpaths._REPO = d
                os.environ['MUTAFAIL_CHANNEL'] = 'demo'
                with self.assertRaises(SystemExit) as cm:
                    envpaths.logo()
                self.assertIn('demo', str(cm.exception))
            finally:
                envpaths._REPO = old
                os.environ.pop('MUTAFAIL_CHANNEL', None)


if __name__ == '__main__':
    unittest.main()
