import unittest

from data_pipeline.models.candidate import CandidateCategory, CandidatePuzzle
from data_pipeline.models.review import AgentReview
from data_pipeline.agents.critic import AgentCriticError, parse_review, review_candidate
from data_pipeline.agents.prompts import build_review_prompt
from data_pipeline.models.source import SourceDataset, SourceValue
from data_pipeline.transforms import four_plus_other, meaningful_subset
from data_pipeline.validation import diagnostics_for, validate_candidate, validate_candidate_against_source, validate_source


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

    def test_critic_parses_json_and_prompt_excludes_raw_payload(self):
        candidate = CandidatePuzzle(
            source_name="Example", source_dataset_id="example-1", topic="Example", title="How is it divided?",
            transformation_type="natural-five",
            categories=[CandidateCategory(id=str(i), label=str(i), raw_value=i) for i in range(1, 6)],
            source_metadata={"provenance": "example"},
        )
        response = '{"verdict":"review","semantic_validity":true,"denominator_clear":true,"question_accurate":true,"general_audience_fit":4,"intuition_potential":3,"obviousness_risk":"low","niche_risk":"low","misleading_risk":"low","category_quality":"good","issues":[],"suggested_title":null,"suggested_context":null,"recommended_action":"human_review"}'

        class FakeTransport:
            def complete(self, *, system_prompt: str, user_prompt: str) -> str:
                self.prompt = user_prompt
                return response

        transport = FakeTransport()
        parsed = review_candidate(candidate, None, transport)
        self.assertEqual(parsed.verdict, "review")
        self.assertNotIn("raw_payload", transport.prompt)

    def test_critic_rejects_malformed_json(self):
        with self.assertRaises(AgentCriticError):
            parse_review("not json")

    def test_four_plus_other_is_verified_against_source(self):
        source = SourceDataset(
            source_name="Example", source_dataset_id="example-1", measure="count",
            values=[SourceValue(category_id=letter, category_label=letter, value=value) for letter, value in zip("ABCDEFG", [30, 25, 15, 10, 8, 7, 5])],
            raw_payload={},
        )
        categories, metadata = four_plus_other(
            [CandidateCategory(id=letter, label=letter, raw_value=value) for letter, value in zip("ABCDEFG", [30, 25, 15, 10, 8, 7, 5])],
            ["A", "B", "C", "D"],
        )
        candidate = CandidatePuzzle(
            source_name="Example", source_dataset_id="example-1", topic="Example", title="How is it divided?",
            transformation_type="four-plus-other", categories=categories, transformation_metadata=metadata,
        )
        self.assertTrue(validate_candidate_against_source(candidate, source).valid)

    def test_four_plus_other_rejects_incorrect_other_value(self):
        source = SourceDataset(
            source_name="Example", source_dataset_id="example-1", measure="count",
            values=[SourceValue(category_id=letter, category_label=letter, value=value) for letter, value in zip("ABCDEFG", [30, 25, 15, 10, 8, 7, 5])],
            raw_payload={},
        )
        categories, metadata = four_plus_other(
            [CandidateCategory(id=letter, label=letter, raw_value=value) for letter, value in zip("ABCDEFG", [30, 25, 15, 10, 8, 7, 5])],
            ["A", "B", "C", "D"],
        )
        categories[-1] = CandidateCategory(id="other", label="Other", raw_value=19)
        candidate = CandidatePuzzle(
            source_name="Example", source_dataset_id="example-1", topic="Example", title="How is it divided?",
            transformation_type="four-plus-other", categories=categories, transformation_metadata=metadata,
        )
        report = validate_candidate_against_source(candidate, source)
        self.assertFalse(report.valid)
        self.assertIn("Other does not equal the sum of its source categories", report.issues)


if __name__ == "__main__":
    unittest.main()
