"""Workbench rendering checks: real report values; no substituted visual states."""
import json
import tempfile
import unittest
from pathlib import Path
from agentic_portfolio.workbench import build

class WorkbenchTests(unittest.TestCase):
    def test_renders_actual_run_fields_and_escapes_embedded_markup(self):
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/"run.json"
            source.write_text(json.dumps({"run_id":"real-123","state":"BLOCKED_CATALOG",
                "stages":[{"name":"catalog","elapsed_ms":24.5}],
                "engineering":{"status":"VERIFIED_CANDIDATE_PERSISTED",
                    "events":[{"stage":"actual_mutation","diff":"<script>alert(1)</script>"}]},
                "catalog":{"status":"AWAITING_APPROVAL","decision":{"action":"CORRECT"}}}))
            out=build(source,Path(td)/"workbench.html")
            text=out.read_text()
            self.assertIn("real-123",text)
            self.assertIn("VERIFIED_CANDIDATE_PERSISTED",text)
            self.assertNotIn("<script>alert(1)</script>",text)
            self.assertIn("Execution dependency graph",text)
    def test_reject_missing_run_identity(self):
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/"run.json"
            source.write_text("{}")
            with self.assertRaises(ValueError):
                build(source,Path(td)/"workbench.html")

if __name__=="__main__":
    unittest.main()
