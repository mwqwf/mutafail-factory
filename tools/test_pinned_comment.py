# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import tempfile
from pathlib import Path

import pinned_comment as p


class PinnedCommentTests(unittest.TestCase):
    def test_middle_episode_with_ids(self):
        # السابقة اليمامة بلا معرّف بعد، والتالية أُلّيس لها معرّف
        text = p.render({"slug": "walaja"}, {})
        self.assertIn("حديقة الموت", text)
        self.assertNotIn("https://youtu.be/al2AeXMgZ-Q", text)
        self.assertIn("سمّ ساعة", text)
        self.assertIn("https://youtu.be/Ah2VnLPpMU0", text)
        self.assertIn("سؤال للتعليق:", text)
        self.assertIn("الولجة", text)

    def test_episode_with_previous_id(self):
        text = p.render({"slug": "ullais"}, {})
        self.assertIn("https://youtu.be/AQW7phGZJUE", text)
        self.assertIn("https://youtu.be/ilFEoE-JGa4", text)

    def test_first_episode_omits_previous(self):
        text = p.render({"slug": "mutah"}, {})
        self.assertIn("هذه أولى حلقات قصة خالد بن الوليد", text)
        self.assertNotIn("الحلقة السابقة", text)
        self.assertNotIn("قادمة قريباً", text)  # لا وعد بحلقة لم تُنشر
        self.assertIn("حديقة الموت", text)  # التالية منشورة: يُذكر رابطها لا وعدها

    def test_last_known_without_next_id(self):
        text = p.render({"slug": "ajnadayn"}, {})
        self.assertIn("خمس ليالٍ بلا ماء", text)
        self.assertNotIn("قادمة قريباً", text)  # لا وعد بحلقة لم تُنشر (2026-11-27)
        self.assertIn("أجنادين", text)

    def test_override_question_and_neighbors(self):
        pub = {
            "slug": "ajnadayn",
            "pinned_question": "ما رأيك في ثبات الصف؟",
            "prev_episode": {"title": "حلقة سابقة تجريبية", "id": "AAAAAAAAAAA"},
            "next_episode": {"title": "حلقة تالية تجريبية", "id": "BBBBBBBBBBB"},
        }
        text = p.render(pub, {})
        self.assertIn("ما رأيك في ثبات الصف؟", text)
        self.assertIn("https://youtu.be/AAAAAAAAAAA", text)
        self.assertIn("https://youtu.be/BBBBBBBBBBB", text)

    def test_write_and_text_gate(self):
        d = Path(tempfile.mkdtemp())
        (d / "publish.json").write_text(json.dumps({"slug": "mutah", "series": "سيف الله"}, ensure_ascii=False), encoding="utf-8")
        (d / "meta.json").write_text("{}", encoding="utf-8")
        path, text = p.generate(str(d))
        self.assertTrue(Path(path).exists())
        self.assertEqual(Path(path).read_text(encoding="utf-8"), text)

    def test_non_series_refused(self):
        d = Path(tempfile.mkdtemp())
        (d / "publish.json").write_text(json.dumps({"slug": "nimrod", "series": "قصص القرآن"}, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(ValueError):
            p.generate(str(d))


if __name__ == "__main__":
    unittest.main()
