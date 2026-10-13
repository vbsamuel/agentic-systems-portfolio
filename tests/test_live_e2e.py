import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agentic_portfolio.live_e2e import execute

class CoordinatorTests(unittest.TestCase):
    def config(self):
        return {"approvals":{"engineering_worktree_mutation":True,"catalog_writeback":True},
                "catalog":{"authoritative":{"url":"http://127.0.0.1:1/catalog","token":"test"},
                           "published":{"url":"http://127.0.0.1:1/channel","token":"test"}}}
    def test_real_paths_must_both_succeed_for_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=str(Path(tmp)/"evidence.json")
            with patch("agentic_portfolio.live_e2e.execute_repair",
                       return_value={"status":"VERIFIED_CANDIDATE_PERSISTED","candidate_revision":"abc"}), \
                 patch("agentic_portfolio.live_e2e.synchronize",
                       return_value={"verified":True,"before":{"status":"REVIEW_REQUIRED"},
                                     "writeback_performed":True}):
                result=execute(self.config(),out)
            self.assertEqual(result["state"],"PASS")
            saved=json.loads(Path(out).read_text())
            self.assertEqual(len(saved["stages"]),2)
            self.assertTrue(saved["run_id"])
    def test_model_repair_not_verified_stops_catalog_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=str(Path(tmp)/"evidence.json")
            with patch("agentic_portfolio.live_e2e.execute_repair",
                       return_value={"status":"FAILED_VERIFICATION"}), \
                 patch("agentic_portfolio.live_e2e.synchronize") as publish:
                result=execute(self.config(),out)
                publish.assert_not_called()
            self.assertEqual(result["state"],"BLOCKED_ENGINEERING")
    def test_unapproved_writeback_cannot_masquerade_as_corrected(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=self.config()
            config["approvals"]["catalog_writeback"]=False
            out=str(Path(tmp)/"evidence.json")
            with patch("agentic_portfolio.live_e2e.execute_repair",
                       return_value={"status":"VERIFIED_CANDIDATE_PERSISTED"}), \
                 patch("agentic_portfolio.live_e2e.synchronize",
                       return_value={"verified":False,"before":{"status":"REVIEW_REQUIRED"},
                                     "writeback_performed":False}):
                result=execute(config,out)
            self.assertEqual(result["state"],"BLOCKED_CATALOG")

if __name__=="__main__":
    unittest.main()
