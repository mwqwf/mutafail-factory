import unittest
from duration_policy import audit_duration

class DurationPolicyTests(unittest.TestCase):
    def test_material_accepts_short_feature_and_long_films(self):
        self.assertEqual(audit_duration(9.5, {}), [])
        self.assertEqual(audit_duration(18.09, {}), [])
        self.assertEqual(audit_duration(30, {}), [])
        self.assertEqual(audit_duration(40, {"targetMinutes": 40}), [])
        self.assertEqual(audit_duration(56, {}), [])

    def test_tiny_film_needs_a_note_unless_it_is_a_reel(self):
        self.assertTrue(audit_duration(1.5, {}))
        self.assertEqual(audit_duration(1.5, {"durationNote": "مادّة موثّقة قصيرة اكتملت في هذا الحيّز"}), [])
        self.assertEqual(audit_duration(1.2, {"kind": "reel"}), [])

    def test_invalid_duration(self):
        self.assertTrue(audit_duration(0, {}))
        self.assertTrue(audit_duration(-3, {}))

if __name__ == '__main__':
    unittest.main()
