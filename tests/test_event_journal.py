import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agentic_portfolio.event_journal import EventJournal
from agentic_portfolio.live_e2e import execute

class EventJournalTests(unittest.TestCase):
    def test_append_parent_hash_verify_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            journal=EventJournal(Path(td)/"events.sqlite3")
            a=journal.append("run","start",{"status":"RUNNING"})
            b=journal.append("run","finished",{"status":"PASS"},parent_id=a["event_id"])
            self.assertTrue(journal.verify())
            self.assertEqual(journal.read("run")[1]["parent_id"],a["event_id"])
            with self.assertRaises(ValueError):
                journal.append("other","invalid",{},parent_id=b["event_id"])
            with sqlite3.connect(journal.path) as db:
                db.execute("UPDATE events SET payload=? WHERE event_id=?",('{"status":"FAKE"}',b["event_id"]))
            with self.assertRaisesRegex(ValueError,"hash chain broken"):
                journal.verify()
    def test_coordinator_emits_native_events_from_real_stage_boundaries(self):
        with tempfile.TemporaryDirectory() as td:
            artifact=Path(td)/"run.json"
            config={"model_endpoint":{},"catalog_model_driven":True,
                "approvals":{"engineering_worktree_mutation":True,"catalog_writeback":False},
                "catalog":{"authoritative":{"url":"http://127.0.0.1:1/s","token":"t"},
                           "published":{"url":"http://127.0.0.1:1/p","token":"t"}}}
            with patch("agentic_portfolio.live_e2e.execute_repair",
                       return_value={"status":"VERIFIED_CANDIDATE_PERSISTED","candidate_revision":"abc"}):
                with patch("agentic_portfolio.live_e2e.model_governed_reconcile",
                           return_value={"status":"AWAITING_APPROVAL","verified":False,
                                         "writeback_performed":False}):
                    result=execute(config,str(artifact))
            journal=EventJournal(artifact.with_suffix(".events.sqlite3"))
            self.assertTrue(journal.verify())
            kinds=[x["kind"] for x in journal.read(result["run_id"])]
            self.assertIn("stage_started",kinds)
            self.assertIn("stage_completed",kinds)
            self.assertIn("catalog_outcome",kinds)
            self.assertEqual(result["state"],"BLOCKED_CATALOG")

if __name__=="__main__":
    unittest.main()
