# -*- coding: utf-8 -*-
"""فحص هوية القناة المعتمدة في 27 نوفمبر 2026: العبارة والوصف بلا شعار قديم وبلا وعد."""
from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import cta_gate  # noqa: E402

OLD_SLOGAN = re.compile(r"نبحث،?\s*ثمّ?\s*نروي")
TAGLINE = "معارك الإسلام وبطولات أبطاله"
IDENTITY = ROOT / "ops" / "CHANNEL_IDENTITY.md"
FOOTER = ROOT / "ops" / "templates" / "film_description_footer.md"
BRANDING = ROOT / "assets" / "branding" / "README.md"
PINNED = ROOT / "ops" / "templates" / "khalid_pinned_comment.md"

# ملفات يجب ألا تعتمد الشعار القديم هويةً قائمة (الذِكر النافي مسموح إن سبقت «بدل» أو «لا تُستخدم»)
CANONICAL = (IDENTITY, FOOTER, BRANDING, PINNED)


def fenced_blocks(text: str) -> list[str]:
    return re.findall(r"```(?:[^\n]*)\n(.*?)```", text, flags=re.S)


class ChannelIdentityTests(unittest.TestCase):
    def test_identity_file_has_approved_copy(self):
        text = IDENTITY.read_text(encoding="utf-8")
        self.assertIn(TAGLINE, text)
        self.assertLessEqual(len(TAGLINE), 40)
        blocks = fenced_blocks(text)
        self.assertTrue(blocks, "أوصاف الهوية يجب أن تكون في كتل منقول حرفياً")
        self.assertEqual(blocks[0].strip(), TAGLINE)
        desc = blocks[1].strip()
        self.assertLessEqual(len(desc), 1000)
        for term in ("معارك إسلامية", "خالد بن الوليد", "فتوحات", "أبطال المسلمين"):
            self.assertIn(term, desc)
        self.assertIsNone(cta_gate.FUTURE_PROMISE.search(cta_gate.plain(desc)))
        self.assertIsNone(OLD_SLOGAN.search(desc))
        self.assertIn("نوثّق ولا نحكم", desc)
        self.assertNotIn("قصص من القرآن", desc)
        self.assertIn("Cinematic ultra-wide", text)
        self.assertIn("Square 800x800", text)

    def test_footer_matches_new_identity(self):
        text = FOOTER.read_text(encoding="utf-8")
        self.assertIn(TAGLINE, text)
        self.assertIn("اشترك في القناة", text)
        body = "\n".join(fenced_blocks(text))
        self.assertIsNone(cta_gate.FUTURE_PROMISE.search(cta_gate.plain(body)))
        # الشعار القديم لا يظهر إلا للنهي عنه
        for m in OLD_SLOGAN.finditer(text):
            start = max(0, m.start() - 30)
            ctx = text[start : m.end() + 10]
            self.assertTrue(
                "لا تُستخدم" in ctx or "بدل" in ctx,
                "شعار قديم بلا نهي في التذييل: %s" % ctx,
            )

    def test_branding_readme_and_pinned_drop_old_identity(self):
        readme = BRANDING.read_text(encoding="utf-8")
        self.assertIn(TAGLINE, readme)
        self.assertIn("المعارك الإسلامية وبطولات أبطال المسلمين", readme)
        self.assertIn("بدل «نبحث، ثمّ نروي»", readme)
        # لا تُوصف هوية الكتاب بأنها المعتمدة الآن دون بيان أنها ستُستبدل
        self.assertIn("يُستبدلان", readme)
        pinned = PINNED.read_text(encoding="utf-8")
        self.assertIn("المعارك الإسلامية وبطولات أبطال المسلمين", pinned)
        self.assertIn("لا تُستخدم في التعليق عبارة «نبحث، ثمّ نروي»", pinned)

    def test_canonical_files_have_no_bare_old_slogan(self):
        for path in CANONICAL:
            text = path.read_text(encoding="utf-8")
            for m in OLD_SLOGAN.finditer(text):
                start = max(0, m.start() - 40)
                ctx = text[start : m.end() + 15]
                allowed = any(w in ctx for w in ("بدل", "لا تُستخدم", "القديمة", "حتى يُولَّد", "أُسقطت", "العبارة العامة"))
                self.assertTrue(allowed, "%s: شعار قديم بلا سياق نهي/استبدال: %s" % (path, ctx))


if __name__ == "__main__":
    unittest.main()
