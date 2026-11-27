# -*- coding: utf-8 -*-
"""معيار التحريك (أمر المالك 2026-11-27): الحركة من الشعور لا من البذرة، والمهمّ حيّ، والرعشة والتجمّد يُرفضان."""
import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motion_plan as mp  # noqa: E402


def clip(path, offsets):
    rng = np.random.default_rng(0)
    base = (rng.random((300, 560)) * 255).astype(np.uint8)
    import cv2
    base = cv2.GaussianBlur(base, (0, 0), 2.0)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'gray', '-s', '480x270', '-r', '25',
                          '-i', '-', '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', path], stdin=subprocess.PIPE)
    for ox in offsets:
        M = np.float32([[1, 0, -ox], [0, 1, -10]])
        p.stdin.write(cv2.warpAffine(base, M, (480, 270), flags=cv2.INTER_LINEAR).tobytes())
    p.stdin.close(); p.wait()


class Lint(unittest.TestCase):
    def test_apply_then_lint_passes(self):
        shots = [{'id': 'a', 'emotion': 'awe', 'kind': 'live', 'video_prompt': 'slow crane'},
                 {'id': 'b', 'emotion': 'reflection'}, {'id': 'c', 'emotion': 'reflection'}, {'id': 'd', 'emotion': 'journey'}]
        mp.apply(shots)
        self.assertNotEqual(shots[1]['move3d'], shots[2]['move3d'])
        self.assertEqual(shots[1]['ease'], 'inout')
        self.assertEqual(mp.lint(shots, [0, 40, 45, 50]), [])

    def test_wrong_move_for_emotion_and_repeat_fail(self):
        shots = [{'id': 'b', 'emotion': 'reflection', 'move3d': 'orbit', 'tr': 'fade'},
                 {'id': 'c', 'emotion': 'grief', 'move3d': 'dolly_out', 'tr': 'fade'},
                 {'id': 'd', 'emotion': 'grief', 'move3d': 'dolly_out', 'tr': 'fade'}]
        errs = mp.lint(shots, [40, 45, 50])
        self.assertTrue(any('لا تناسب' in e for e in errs))
        self.assertTrue(any('رتابة' in e for e in errs))

    def test_important_must_be_live(self):
        errs = mp.lint([{'id': 'h', 'emotion': 'tension', 'move3d': 'dolly_in'}], [3.0])
        self.assertTrue(any('بلا تحريك حيّ' in e for e in errs))

    def test_missing_emotion_and_unmotivated_transition(self):
        errs = mp.lint([{'id': 'x', 'emotion': 'reflection', 'move3d': 'dolly_in'},
                        {'id': 'y'}, {'id': 'z', 'emotion': 'grief', 'move3d': 'dolly_out', 'tr': 'whip'}], [40, 41, 42])
        self.assertTrue(any('غائب' in e for e in errs))
        self.assertTrue(any('غير مسوَّغ' in e for e in errs))


class Clip(unittest.TestCase):
    def test_smooth_passes_jitter_and_freeze_fail(self):
        with tempfile.TemporaryDirectory() as d:
            smooth = os.path.join(d, 's.mp4'); jit = os.path.join(d, 'j.mp4'); frz = os.path.join(d, 'f.mp4')
            t = np.arange(50) / 49.0
            clip(smooth, 40 * (t * t * t * (t * (6 * t - 15) + 10)))
            clip(jit, 40 * t + np.random.default_rng(1).normal(0, 1.2, 50))
            clip(frz, np.concatenate([np.zeros(30), np.linspace(0, 20, 20)]))
            self.assertEqual(mp.clip_check(smooth), [])
            self.assertTrue(any('رعشة' in e for e in mp.clip_check(jit)))
            self.assertTrue(any('تجمّد' in e for e in mp.clip_check(frz)))


class Ease(unittest.TestCase):
    def test_eases_hit_endpoints(self):
        import importlib
        kb3d = importlib.import_module('kb3d')
        for k, f in kb3d.EASES.items():
            self.assertAlmostEqual(f(0.0), 0.0, places=6, msg=k)
            self.assertAlmostEqual(f(1.0), 1.0, places=6, msg=k)
        self.assertEqual(set(m for e in mp.EMOTIONS.values() for m in e[0]) - set(kb3d.MOVE_NAMES), set())


if __name__ == '__main__':
    unittest.main()
