import unittest

from app import classify_role, is_target_location


class LocationFilterTests(unittest.TestCase):
    def test_hyderabad_india_locations_are_accepted(self):
        self.assertTrue(is_target_location("Hyderabad, Telangana, India"))
        self.assertTrue(is_target_location("hyderabad"))
        self.assertTrue(is_target_location("Hyderabad, India"))

    def test_non_hyderabad_locations_are_rejected(self):
        self.assertFalse(is_target_location("Bengaluru, Karnataka, India"))
        self.assertFalse(is_target_location("Remote"))
        self.assertFalse(is_target_location("Pune, India"))

    def test_role_classification_matches_role_keywords(self):
        self.assertEqual(classify_role("Data Scientist", "Uses Python and ML models"), "data-scientist")
        self.assertEqual(classify_role("Data Analyst", "Builds dashboards and SQL reports"), "data-analyst")
        self.assertEqual(classify_role("Data Engineer", "Builds ETL pipelines with Spark"), "data-engineer")


if __name__ == "__main__":
    unittest.main()
