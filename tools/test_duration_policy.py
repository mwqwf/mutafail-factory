import unittest
from duration_policy import audit_duration

class DurationPolicyTests(unittest.TestCase):
    def test_default_rejects_eighteen_minutes(self):
        self.assertTrue(audit_duration(18.09, {}))
    def test_default_accepts_thirty_to_forty(self):
        self.assertEqual(audit_duration(30, {}), [])
        self.assertEqual(audit_duration(40, {"targetMinutes": 40}), [])
    def test_thin_topic_needs_specific_exception(self):
        self.assertTrue(audit_duration(24, {"durationException": "قصير"}))
        self.assertEqual(audit_duration(24, {"durationException": "نفدت المادة الموثقة بعد بحث المحاور كلها"}), [])
    def test_invalid_target_and_hard_bounds(self):
        self.assertTrue(audit_duration(31, {"targetMinutes": 25}))
        self.assertTrue(audit_duration(56, {"targetMinutes": 35}))

if __name__ == '__main__': unittest.main()
