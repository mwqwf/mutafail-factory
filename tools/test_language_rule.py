# -*- coding: utf-8 -*-
"""حارسُ قاعدة اللغة: كلُّ جلسةٍ تعمل على هذا الفرع تقرأ قاعدةَ العربيّة أوّلاً.

⛔ السببُ المقيس (2026-09-24): فرعُ الإنتاج تاريخٌ منفصلٌ عن `master` فلا يرث
`.claude/settings.json` ولا كتلةَ اللغة المولَّدة في `CLAUDE.md`، فانزلقت جلساتٌ إلى
الإنجليزيّة. ⇒ تبقى القاعدةُ في رأس الملفّين، ولا تُحذف ولا تُزاح إلى الأسفل.
"""
import io
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def head(name, n=1500):
    return io.open(os.path.join(ROOT, name), encoding="utf-8").read()[:n]


class LanguageRule(unittest.TestCase):
    def test_claude_md_opens_with_arabic_rule(self):
        h = head("CLAUDE.md")
        self.assertIn("lang-rule:begin", h)
        self.assertIn("العربية حصراً", h)
        self.assertIn("وصفُ كل أمرٍ أو أداة", h)

    def test_agents_md_opens_with_arabic_rule(self):
        h = head("AGENTS.md", 600)
        self.assertIn("اللغة", h)
        self.assertIn("العربيةُ حصراً", h)


if __name__ == "__main__":
    unittest.main()
