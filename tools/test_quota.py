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


if __name__ == "__main__":
    unittest.main()
