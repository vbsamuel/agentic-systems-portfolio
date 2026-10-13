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
            self.assertIn("Execution overview",text)
    def test_native_graph_renders_observed_parent_child_ids(self):
        from agentic_portfolio.event_journal import EventJournal
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=root/"run.json"
            source.write_text(json.dumps({"run_id":"observed-123","state":"PASS",
                                          "stages":[],"engineering":{},"catalog":{}}))
            journal=EventJournal(source.with_suffix(".events.sqlite3"))
            parent=journal.append("observed-123","stage_started",{"name":"engineering"})
            child=journal.append("observed-123","model_call_started",
                                 {"model":"local-test-model"},parent_id=parent["event_id"])
            out=build(source,root/"workbench.html")
            html=out.read_text()
            self.assertIn(parent["event_id"],html)
            self.assertIn(child["event_id"],html)
            self.assertIn('"schema_version": 2',html)
            self.assertIn('"edge_type": "native_parent_id"',html)
            self.assertIn("Search recorded events",html)
            self.assertIn("Parent event",html)
            self.assertIn("function ancestorStage(n)",html)
            self.assertIn("function renderStageFlow()",html)
            self.assertIn("Show raw evidence JSON",html)
            self.assertIn("Paired operations",html)
            self.assertIn("Native events",html)
            self.assertIn("Observed operator lifecycle",html)
            self.assertIn('"operator_view":',html)
            self.assertIn("Inspect completion event",html)
            self.assertIn("Inspect causal parent",html)
            self.assertIn("Observed correction and publication",html)
            self.assertIn("attempt ",html)
            self.assertIn("Duration / result",html)
            self.assertIn("Evidence inspector",html)
            self.assertIn("Recorded stage flow",html)

    def test_reject_missing_run_identity(self):
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/"run.json"
            source.write_text("{}")
            with self.assertRaises(ValueError):
                build(source,Path(td)/"workbench.html")

if __name__=="__main__":
    unittest.main()
