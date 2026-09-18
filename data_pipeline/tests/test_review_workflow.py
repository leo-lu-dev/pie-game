import unittest
from contextlib import nullcontext
from datetime import date

from data_pipeline.review_workflow import promote_candidate, record_decision


class FakeCursor:
    def __init__(self, results):
        self.results = iter(results)
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def execute(self, query, params):
        self.executed.append((query, params))

    def executemany(self, query, params):
        self.executed.append((query, params))

    def fetchone(self):
        return next(self.results)

    def fetchall(self):
        return next(self.results)


class FakeConnection:
    def __init__(self, results):
        self.fake_cursor = FakeCursor(results)

    def transaction(self):
        return nullcontext()

    def cursor(self):
        return self.fake_cursor


class ReviewWorkflowTests(unittest.TestCase):
    def test_approval_requires_passing_validation(self):
        connection = FakeConnection([{'status': 'validated'}, {'technical_valid': True, 'dimension_valid': False, 'transformation_valid': True}])
        with self.assertRaisesRegex(ValueError, 'passing validation'):
            record_decision(connection, 'candidate-1', 'approved', 'editor')
        self.assertFalse(any('UPDATE puzzle_candidates' in query for query, _ in connection.fake_cursor.executed))

    def test_promotion_requires_human_approval(self):
        connection = FakeConnection([{'status': 'validated', 'human_status': None}])
        with self.assertRaisesRegex(ValueError, 'human approval'):
            promote_candidate(connection, 'candidate-1', date(2026, 10, 1))
        self.assertFalse(any('INSERT INTO puzzles' in query for query, _ in connection.fake_cursor.executed))

    def test_promotion_creates_scheduled_puzzle(self):
        candidate = {
            'status': 'approved', 'human_status': 'approved', 'source_dataset_id': 'dataset-1',
            'transformation_type': 'natural-five', 'transformation_metadata_json': {}, 'source_metadata_json': {},
            'title': 'Example', 'context': None, 'source_name': 'Source', 'source_url': None,
        }
        categories = [{'category_key': str(index), 'label': str(index), 'raw_value': str(index), 'display_order': index - 1} for index in range(1, 6)]
        connection = FakeConnection([candidate, {'technical_valid': True, 'dimension_valid': True, 'transformation_valid': True}, categories, None])
        slug = promote_candidate(connection, 'candidate-1', date(2026, 10, 1))
        self.assertTrue(slug.startswith('real-'))
        puzzle_insert = next(params for query, params in connection.fake_cursor.executed if 'INSERT INTO puzzles' in query)
        self.assertEqual(puzzle_insert[5], 'scheduled')
        self.assertEqual(puzzle_insert[-1], 'candidate-1')


if __name__ == '__main__':
    unittest.main()
