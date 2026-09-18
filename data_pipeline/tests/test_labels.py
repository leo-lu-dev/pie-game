import unittest

from data_pipeline.labels import concise_category_label


class CategoryLabelTests(unittest.TestCase):
    def test_simplifies_verbose_race_label(self):
        self.assertEqual(
            concise_category_label("Population: civilian, non-institutionalized, white alone"),
            "White",
        )

    def test_preserves_race_exclusion(self):
        self.assertEqual(
            concise_category_label("White alone, not Hispanic or Latino"),
            "White (not Hispanic or Latino)",
        )

    def test_simplifies_age_band(self):
        self.assertEqual(concise_category_label("Count of housing unit: years 35 to 44, occupied housing unit"), "35–44")
        self.assertEqual(concise_category_label("Count of housing unit: years upto 35, occupied housing unit"), "35 or younger")

    def test_simplifies_degree_label(self):
        self.assertEqual(concise_category_label("Population: years 25 onwards, associates degree"), "25+ Associate's degree")


if __name__ == "__main__":
    unittest.main()
