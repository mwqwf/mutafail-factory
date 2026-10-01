import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import thrill_gate as g  # noqa: E402


def proj(blocks, sections, reels, title="سؤال؟"):
    d = Path(tempfile.mkdtemp())
    for name, obj in (("blocks.json", blocks), ("sections.json", sections), ("reels.json", reels), ("publish.json", {"title": title})):
        (d / name).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return d


def B(i, t, **k):
    return dict({"id": i, "voice": "Charon", "text": t}, **k)


GOOD = [B("d1", "سُفُنٌ تَمْشِي عَلَى ظُهُورِ الْإِبِلْ."), B("d2", "فَمَنْ صَاحِبُ الْفِكْرَةِ؟"), B("d3", "وَإِلَى أَيْنَ؟ سَنَكْشِفُ لَكُمْ"),
        B("d4", "ثُمَّ مَاذَا جَرَى؟"), B("d5", "فَصْلٌ ثَانٍ يَبْدَأُ قَصِيرًا"), B("d6", "وَلَكِنَّ الْمُفَاجَأَةَ لَمْ تَأْتِ بَعْدُ…")]
REELS = [{"id": f"r{i}", "blocks": [f"x{i}a", f"x{i}b"]} for i in (1, 2, 3)]
RB = [b for i in (1, 2, 3) for b in (B(f"x{i}a", "صَدْمَةٌ قَصِيرَةٌ.", reel_only=True), B(f"x{i}b", "فَمَنْ؟ الْجَوَابُ فِي الْفِيلْمْ.", reel_only=True))]
SECS = [{"id": "d1", "title": "أ"}, {"id": "d5", "title": "ب"}]


class ThrillGateTests(unittest.TestCase):
    def test_good_structure_passes(self):
        errs, _ = g.check(proj(GOOD + RB, SECS, REELS), None)
        self.assertEqual(errs, [])

    def test_greeting_first_flat_chapter_and_two_reels_fail(self):
        blocks = [B("d0", "السَّلَامُ عَلَيْكُمْ")] + GOOD[1:3] + [B("d4", "وَانْتَهَى الْفَصْلُ.")] + GOOD[4:] + RB
        errs, _ = g.check(proj(blocks, SECS, REELS[:2]), None)
        text = "\n".join(errs)
        self.assertIn("تحيّة", text)
        self.assertIn("بمعلّقة", text)
        self.assertIn("2 ريلز", text)

    def test_thumb_text_with_tashkeel_or_too_long_fails(self):
        d = proj(GOOD + RB, SECS, REELS)
        t = d / "thumbs.json"
        t.write_text(json.dumps({"thumbs": [{"file": "a.png", "text": ["أسوارٌ صمدت ألف عام"]}]}, ensure_ascii=False), encoding="utf-8")
        errs, _ = g.check(d, t)
        self.assertTrue(any("مشكول" in e for e in errs) and any("طويل" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
