import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import thrill_gate as g  # noqa: E402


def proj(blocks, sections, reels, title="سؤال؟", shots=None, genre=None):
    d = Path(tempfile.mkdtemp())
    pub = {"film": {"title": title}, **({"genre": genre} if genre else {})}
    files = [("blocks.json", blocks), ("sections.json", sections), ("reels.json", reels), ("publish.json", pub)]
    if shots is not None:
        files.append(("shots.json", shots))
    for name, obj in files:
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

    def test_owner_reel_count_override(self):
        # الأرك 2026-10-04: «الريلزات يكفي اثنان فقط لهذا الفيلم» ⇒ publish.json: reels_required = 2
        d = proj(GOOD + RB, SECS, REELS[:2])
        pub = json.loads((d / "publish.json").read_text(encoding="utf-8")); pub["reels_required"] = 2
        (d / "publish.json").write_text(json.dumps(pub, ensure_ascii=False), encoding="utf-8")
        errs, _ = g.check(d, None)
        self.assertFalse(any("ريلز (المطلوب" in e for e in errs))

    def test_thumb_text_with_tashkeel_or_too_long_fails(self):
        d = proj(GOOD + RB, SECS, REELS)
        t = d / "thumbs.json"
        t.write_text(json.dumps({"thumbs": [{"file": "a.png", "text": ["أسوارٌ صمدت ألف عام"]}]}, ensure_ascii=False), encoding="utf-8")
        errs, _ = g.check(d, t)
        self.assertTrue(any("مشكول" in e for e in errs) and any("طويل" in e for e in errs))


    # ⭐ الإيقاع والتركيز على المعركة (أمر المالك 2026-10-03)
    def battle(self, phases, words_per=(4, 4, 4, 4)):
        w = lambda n, tail="": " ".join(["كَلِمَةٌ"] * n) + tail
        blocks = [B("d1", "سُيُوفٌ فِي اللَّيْلِ"), B("d2", "فَمَنْ؟"), B("d3", "وَلِمَاذَا؟")]
        secs = [{"id": "d1", "title": "افتتاح"}]
        for k, (ph, n) in enumerate(zip(phases, words_per)):
            i = f"c{k}"
            blocks.append(B(i, w(n, "؟")))
            secs.append({"id": i, "title": ph, "phase": ph})
        return blocks + RB, secs

    def test_battle_film_needs_phases_and_battle_focus(self):
        blocks, secs = self.battle(["setup", "buildup", "battle", "aftermath"], (40, 20, 20, 20))
        errs, _ = g.check(proj(blocks, secs, REELS, genre="battle"), None)
        text = "\n".join(errs)
        self.assertIn("المعركة 20%", text)
        self.assertIn("التمهيد 40%", text)
        self.assertIn("أوّل كتلة قتالٍ", text)
        for x in secs:
            x.pop("phase", None)
        errs, _ = g.check(proj(blocks, secs, REELS, genre="battle"), None)
        self.assertTrue(any("phase" in e for e in errs))

    def test_battle_focused_film_passes(self):
        blocks, secs = self.battle(["setup", "battle", "battle", "aftermath"], (5, 50, 40, 5))
        errs, _ = g.check(proj(blocks, secs, REELS, genre="battle"), None)
        self.assertEqual(errs, [])

    def test_long_still_shot_fails_pacing(self):
        long_ = B("d4", " ".join(["كَلِمَةٌ"] * 40) + "؟")
        blocks = GOOD[:3] + [long_] + GOOD[4:] + RB
        shots = [{"id": "S1", "blocks": ["d1", "d2", "d3"]}, {"id": "S2", "blocks": ["d4"]}, {"id": "S3", "blocks": ["d5", "d6"]}]
        errs, _ = g.check(proj(blocks, SECS, REELS, shots=shots), None)
        self.assertTrue(any("أطول من" in e and "S2" in e for e in errs))

    def test_absolute_superlative_in_title_fails_but_qualified_and_takbir_pass(self):
        errs, _ = g.check(proj(GOOD + RB, SECS, REELS, title="أعظم معركة في التاريخ؟"), None)
        self.assertTrue(any("تفضيلٌ مطلق" in e for e in errs))
        ok = GOOD[:4] + [B("d5", "اللَّهُ أَكْبَرُ")] + GOOD[5:] + RB
        errs, warns = g.check(proj(ok, SECS, REELS, title="من أعظم معارك التاريخ؟"), None)
        self.assertEqual(errs, [])
        self.assertFalse(any("تفضيلٌ مطلق" in w for w in warns))


    def test_source_citation_in_narration_fails(self):
        blocks = GOOD[:4] + [B("d5", "رَوَاهُ الْإِمَامُ أَحْمَدُ وَحَسَّنَهُ الْهَيْثَمِيُّ.")] + GOOD[5:] + RB
        errs, _ = g.check(proj(blocks, SECS, REELS), None)
        self.assertTrue(any("ذكرُ مصدرٍ" in e and "d5" in e for e in errs))

    def test_animation_cost_must_fit_budget(self):
        long_ = [B(f"L{i}", " ".join(["كَلِمَةٌ"] * 15) + "؟") for i in range(60)]
        blocks = GOOD + long_ + RB
        shots = [{"id": f"S{i}", "kind": "حيّة", "blocks": [f"L{i}"]} for i in range(60)]
        d = proj(blocks, SECS, REELS, shots=shots)
        pub = json.loads((d / "publish.json").read_text(encoding="utf-8")); pub["budget_total_usd"] = 15
        (d / "publish.json").write_text(json.dumps(pub, ensure_ascii=False), encoding="utf-8")
        errs, _ = g.check(d, None)
        self.assertTrue(any("قصّر الفيلم" in e for e in errs))   # 60 × 6.9 ث × 0.07$ ≈ 29$ > 13.5$
        pub["budget_total_usd"] = 65
        (d / "publish.json").write_text(json.dumps(pub, ensure_ascii=False), encoding="utf-8")
        errs, _ = g.check(d, None)
        self.assertFalse(any("قصّر الفيلم" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
