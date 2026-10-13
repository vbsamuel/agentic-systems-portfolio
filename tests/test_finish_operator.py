import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agentic_portfolio.finish import close

class OperatorClosureTests(unittest.TestCase):
    def test_explicit_confirmation_and_frozen_review_binding(self):
        with tempfile.TemporaryDirectory() as td:
            config_path=Path(td)/"runtime.json"
            report_path=Path(td)/"report.json"
            config_path.write_text(json.dumps({"catalog_model_driven":True,
                "catalog_authority_policy":{"catalog_is_source_of_truth":True,
                                             "correctable_fields":["price"]},
                "approvals":{"engineering_worktree_mutation":True,"catalog_writeback":False}}))
            report_path.write_text(json.dumps({"run_id":"original-run",
                "catalog":{"status":"AWAITING_APPROVAL","decision":{"action":"CORRECT",
                "skus":["P-1"]},"decision_digest":"actual-digest"},
                "engineering":{"status":"VERIFIED_CANDIDATE_PERSISTED"}}))
            key="a-local-test-key-that-is-longer-than-thirty-two-chars"
            with patch.dict(os.environ,{"AGENTIC_APPROVAL_SIGNING_KEY":key}):
                with self.assertRaisesRegex(ValueError,"confirmation"):
                    close(config_path,report_path,"reviewer",False)
                with patch("agentic_portfolio.finish.run",
                           return_value={"state":"PASS","run_id":"original-run"}) as run:
                    result=close(config_path,report_path,"reviewer",True)
                    cfg=run.call_args.args[0]
            self.assertEqual(result["state"],"PASS")
            self.assertTrue(cfg["resume_verified_engineering"])
            self.assertTrue(cfg["approvals"]["catalog_writeback"])
            self.assertEqual(cfg["catalog_approved_digest"],"actual-digest")
            self.assertEqual(cfg["catalog_approval_grant"]["run_id"],"original-run")
            self.assertEqual(run.call_args.args[1],str(report_path))
if __name__=="__main__":
    unittest.main()
