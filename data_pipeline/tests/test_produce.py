import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from data_pipeline.commands import produce as module


class ProducerTests(unittest.TestCase):
    def test_empty_and_rejected_batches_continue_until_target(self):
        planner = MagicMock()
        transport_context = MagicMock()
        transport_context.__enter__.return_value = planner
        connection_context = MagicMock()
        connection = connection_context.__enter__.return_value
        connection.cursor.return_value.__enter__.return_value.fetchall.return_value = []
        recipe = Path(__file__).resolve().parents[1] / 'examples/usa_marital_status.json'
        rejected = SimpleNamespace(verdict='reject', recommended_action='reject', issues=['Too similar'])
        approved = SimpleNamespace(verdict='approve', recommended_action='approve', issues=[],
                                   semantic_validity=True, denominator_clear=True, question_accurate=True)
        generated_dir = Path(tempfile.mkdtemp())
        with patch.object(module, 'connect', return_value=connection_context), \
             patch.object(module, 'STATE_PATH', Path(tempfile.mkdtemp()) / 'state.json'), \
             patch.object(module, 'GENERATED_DIR', generated_dir), \
             patch.object(module, 'topic_search_terms', return_value=['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth', 'eleventh', 'twelfth']), \
             patch.object(module, 'critic_transport_from_env', return_value=transport_context), \
             patch.object(module, 'discover_configs', side_effect=[[], [], [], [], [recipe], [recipe]]) as discover, \
             patch.object(module, 'ingest', side_effect=['rejected-id', 'accepted-id']) as ingest, \
             patch.object(module, 'candidate_detail', return_value={'validations': [{'diagnostics_json': {}}]}), \
             patch.object(module, 'CandidateDiagnostics'), \
             patch.object(module, 'candidate_from_detail'), \
             patch.object(module, 'existing_candidate_summaries', return_value=[]), \
             patch.object(module, 'review_candidate', side_effect=[rejected, approved]), \
             patch.object(module, 'persist_agent_review') as persist:
            module.produce(1)
        self.assertEqual(discover.call_count, 6)
        self.assertEqual(ingest.call_count, 2)
        self.assertEqual(persist.call_count, 2)
        self.assertTrue((generated_dir / 'accepted-id.json').exists())

    def test_approval_with_failed_semantic_check_does_not_count(self):
        review = SimpleNamespace(verdict='approve', recommended_action='approve',
                                 semantic_validity=False, denominator_clear=True, question_accurate=True)
        self.assertFalse(module.passed(review))
