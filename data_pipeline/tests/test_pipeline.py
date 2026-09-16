import unittest

from data_pipeline.models.candidate import CandidateCategory, CandidatePuzzle
from data_pipeline.models.review import AgentReview
from data_pipeline.models.source import SourceDataset, SourceValue
from data_pipeline.transforms import four_plus_other, meaningful_subset
from data_pipeline.validation import diagnostics_for, validate_candidate, validate_source


class PipelineContractTests(unittest.TestCase):
    def test_source_and_candidate_validate(self):
        source = SourceDataset(
            source_name="Example",
            source_dataset_id="example-1",
            measure="count",
            values=[SourceValue(category_id=str(i), category_label=str(i), value=i) for i in range(1, 6)],
            raw_payload={"values": [1, 2, 3, 4, 5]},
        )
        self.assertTrue(validate_source(source).valid)
        candidate = CandidatePuzzle(
            source_name=source.source_name,
            source_dataset_id=source.source_dataset_id,
            topic="Example",
            title="How is the total divided?",
            transformation_type="natural-five",
            categories=[CandidateCategory(id=str(i), label=str(i), raw_value=i) for i in range(1, 6)],
        )
        result = validate_candidate(candidate)
        self.assertTrue(result.valid)
        self.assertAlmostEqual(sum(result.diagnostics.normalized_values), 100)

    def test_four_plus_other_preserves_total(self):
        source = [CandidateCategory(id=letter, label=letter, raw_value=value) for letter, value in zip("ABCDEFG", [30, 25, 15, 10, 8, 7, 5])]
        result, metadata = four_plus_other(source, ["A", "B", "C", "D"])
        self.assertEqual([category.raw_value for category in result], [30, 25, 15, 10, 20])
        self.assertEqual(metadata["otherIncludes"], ["E", "F", "G"])

    def test_meaningful_subset_records_selection_rule(self):
        source = [CandidateCategory(id=str(i), label=str(i), raw_value=i) for i in range(1, 7)]
        result, metadata = meaningful_subset(source, ["1", "2", "3", "4", "5"], "five-most-viewed")
        self.assertEqual(len(result), 5)
        self.assertEqual(metadata["selectionRule"], "five-most-viewed")

    def test_diagnostics_include_game_design_signals(self):
        diagnostics = diagnostics_for([68, 13, 8, 6, 5])
        self.assertAlmostEqual(diagnostics.largest_share, 68 / 100 * 100)
        self.assertGreater(diagnostics.dominance_ratio, 10)

    def test_agent_review_has_structured_scores(self):
        review = AgentReview(
            verdict="review",
            semantic_validity=True,
            denominator_clear=True,
            question_accurate=True,
            general_audience_fit=4,
            intuition_potential=3,
            obviousness_risk="medium",
            niche_risk="low",
            misleading_risk="low",
            category_quality="good",
            issues=["Confirm the source year."],
            recommended_action="human_review",
        )
        self.assertEqual(review.recommended_action, "human_review")


if __name__ == "__main__":
    unittest.main()

