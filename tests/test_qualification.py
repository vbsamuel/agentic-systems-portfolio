"""Contract tests for stage evidence and quality-gate semantics."""
import json
import tempfile
import unittest
from pathlib import Path
from agentic_portfolio.qualification import run, Qualification

class QualificationTests(unittest.TestCase):
    def test_actual_end_to_end_generates_stage_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'qualification.json'
            self.assertEqual(run(str(path)), 0)
            record = json.loads(path.read_text())
            self.assertTrue(record['passed'])
            self.assertGreaterEqual(len(record['stage_results']), 12)
            self.assertTrue(all(step['accepted'] for step in record['stage_results']))
            self.assertTrue(all(step['elapsed_ms'] >= 0 for step in record['stage_results']))
            self.assertEqual(set(record['workflows']), {'engineering', 'catalog'})
            self.assertFalse(record['autonomous_multi_agent_qualified'])
            self.assertFalse(record['live_catalog_connector_qualified'])

    def test_false_positive_check_blocks_release(self):
        q = Qualification()
        q.check('engineering', 'deliberately_failed_oracle', lambda: 0, lambda value: value == 1)
        self.assertFalse(q.summary()['passed'])
        self.assertFalse(q.summary()['workflows']['engineering']['qualified'])

if __name__ == '__main__':
    unittest.main()
