import calendar
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quota  # noqa: E402


class QuotaDayTests(unittest.TestCase):
    def test_day_turns_at_pacific_midnight_in_winter_and_summer(self):
        ts = lambda *t: calendar.timegm(t)
        self.assertEqual(quota._today(ts(2026, 1, 15, 7, 30, 0)), "2026-01-14")   # شتاءً: التجدّد 08:00Z
        self.assertEqual(quota._today(ts(2026, 1, 15, 8, 30, 0)), "2026-01-15")
        self.assertEqual(quota._today(ts(2026, 7, 15, 6, 30, 0)), "2026-07-14")   # صيفاً: 07:00Z
        self.assertEqual(quota._today(ts(2026, 7, 15, 7, 30, 0)), "2026-07-15")


class QuotaBucketTests(unittest.TestCase):
    """منذ 2026-06-01: للرفع وللبحث حصّتان مستقلّتان، وسائر الطرق من العشرة آلاف."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.old = quota.STATE
        quota.STATE = str(Path(self.tmp.name) / "quota_usage.json")

    def tearDown(self):
        quota.STATE = self.old
        self.tmp.cleanup()

    def write(self, ops, units):
        import json
        ops = [{"ما": k, "متى": "", "عن": ""} for k in ops]
        Path(quota.STATE).write_text(json.dumps(
            {"يوتيوب": {"اليوم": quota._today(), "وحدات": units, "عمليات": ops}}, ensure_ascii=False), encoding="utf-8")

    def test_day_written_with_old_upload_price_is_recomputed(self):
        # دفتر 2026-10-07 كما هو: خمس رفعاتٍ حُسبت 1600 لكلٍّ منها، فأُجِّل ريلز الأرك r1 بلا سبب
        self.write(["upload", "thumbnail", "playlist_insert", "upload", "upload", "upload", "thumbnail", "upload"], 8150)
        y = quota.load()["يوتيوب"]
        self.assertEqual(y["وحدات"], 150)
        self.assertEqual(y["رفعات"], 5)
        self.assertEqual(quota.can("upload"), (True, 5, 90))
        self.assertEqual(quota.remaining(), 10000 - 400 - 150)

    def test_upload_bucket_runs_out_after_its_own_cap(self):
        self.write(["upload"] * 95, 0)
        ok, used, left = quota.can("upload")
        self.assertFalse(ok)
        self.assertEqual((used, left), (95, 0))
        self.assertTrue(quota.can("thumbnail")[0])      # الحصّة العامّة لا تنقص بالرفع

    def test_spend_goes_to_the_right_bucket(self):
        quota.spend("upload", "ريلز")
        quota.spend("thumbnail", "فيلم")
        quota.spend("search", "موضوع")
        y = quota.load()["يوتيوب"]
        self.assertEqual((y["رفعات"], y["بحث"], y["وحدات"]), (1, 1, 50))
        self.assertEqual(quota.remaining("search"), 100 - 5 - 1)

    def test_new_day_starts_empty(self):
        import json
        Path(quota.STATE).write_text(json.dumps(
            {"يوتيوب": {"اليوم": "2000-01-01", "وحدات": 9999, "عمليات": [{"ما": "upload"}] * 99}}), encoding="utf-8")
        y = quota.load()["يوتيوب"]
        self.assertEqual((y["وحدات"], y["رفعات"], y["بحث"]), (0, 0, 0))

    def test_topic_demand_allowance_uses_the_search_bucket(self):
        import topic_demand
        self.write(["search"] * 10, 0)
        self.assertEqual(topic_demand.allowance(), 100 - 5 - 10)


if __name__ == "__main__":
    unittest.main()
