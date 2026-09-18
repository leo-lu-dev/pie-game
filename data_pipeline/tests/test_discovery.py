import unittest

from data_pipeline.discovery import _ordered_selection
from data_pipeline.models.source import SourceValue


class DiscoverySelectionTests(unittest.TestCase):
    def test_age_groups_select_youngest_four_in_order(self):
        values = [
            SourceValue(category_id="a", category_label="5 to 17 years", value=10),
            SourceValue(category_id="b", category_label="18 to 24 years", value=1),
            SourceValue(category_id="c", category_label="25 to 44 years", value=20),
            SourceValue(category_id="d", category_label="45 to 64 years", value=30),
            SourceValue(category_id="e", category_label="65 to 74 years", value=25),
            SourceValue(category_id="f", category_label="75 years or more", value=5),
        ]
        self.assertEqual(_ordered_selection(values), ["a", "b", "c", "d"])

    def test_education_groups_select_lowest_four_in_order(self):
        values = [
            SourceValue(category_id="doctorate", category_label="Doctorate degree", value=10),
            SourceValue(category_id="high-school", category_label="High school", value=20),
            SourceValue(category_id="associate", category_label="Associate degree", value=30),
            SourceValue(category_id="bachelor", category_label="Bachelor degree", value=20),
            SourceValue(category_id="master", category_label="Master degree", value=15),
        ]
        self.assertEqual(_ordered_selection(values), ["high-school", "associate", "bachelor", "master"])


if __name__ == "__main__":
    unittest.main()
