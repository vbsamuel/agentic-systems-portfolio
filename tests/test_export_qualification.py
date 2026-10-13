import json
import tempfile
import unittest
from pathlib import Path
from agentic_portfolio.export_qualification import collect

class QualificationExportTests(unittest.TestCase):
    def test_no_unobserved_publication_can_be_exported_as_pass(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"run.json"
            path.write_text(json.dumps({"run_id":"r","state":"BLOCKED_CATALOG",
                "engineering":{"status":"VERIFIED_CANDIDATE_PERSISTED"},
                "catalog":{"status":"AWAITING_APPROVAL","verified":False}}))
            with self.assertRaisesRegex(ValueError,"did not PASS"):
                collect(path)
    def test_no_missing_native_journal_can_produce_qualified_output(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"run.json"
            path.write_text(json.dumps({"run_id":"r","state":"PASS",
                "engineering":{"status":"VERIFIED_CANDIDATE_PERSISTED"},
                "catalog":{"status":"VERIFIED","verified":True,"writeback_performed":True,
                    "publish_evidence":{"after":{"status":"PASS","findings":[]}}}}))
            with self.assertRaisesRegex(ValueError,"native journal missing"):
                collect(path)

if __name__=="__main__":
    unittest.main()
