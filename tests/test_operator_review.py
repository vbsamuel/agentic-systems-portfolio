import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agentic_portfolio.operator_review import prepare

class OperatorReviewTests(unittest.TestCase):
    def test_requires_fresh_paths_and_real_review_outcome(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=root/"base.json"
            source.write_text(json.dumps({
                "catalog_model_driven":True,
                "catalog_authority_policy":{"catalog_is_source_of_truth":True,
                                             "correctable_fields":["price"]},
                "approvals":{"catalog_writeback":True},
                "vertical":{"workspace":"obsolete"}}))
            private=root/"private.json"
            report=root/"report.json"
            workspace=root/"workspace"
            expected={"run_id":"new-run","state":"BLOCKED_CATALOG",
                "engineering":{"status":"VERIFIED_CANDIDATE_PERSISTED",
                               "candidate_revision":"candidate"},
                "catalog":{"status":"AWAITING_APPROVAL","decision":{"action":"CORRECT"},
                           "decision_digest":"observed"}}
            with patch("agentic_portfolio.operator_review.run",return_value=expected) as run:
                result=prepare(source,workspace,private,report)
                cfg=run.call_args.args[0]
            self.assertEqual(result["review"],"READY")
            self.assertEqual(result["run_id"],"new-run")
            self.assertFalse(cfg["resume_verified_engineering"])
            self.assertFalse(cfg["approvals"]["catalog_writeback"])
            self.assertTrue(cfg["approvals"]["engineering_worktree_mutation"])
            self.assertEqual(Path(cfg["vertical"]["workspace"]),workspace.resolve())
            with self.assertRaises(FileExistsError):
                prepare(source,workspace,private,report)
    def test_reject_fake_pass_without_review(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            base=root/"base.json"
            base.write_text(json.dumps({
                "catalog_model_driven":True,
                "catalog_authority_policy":{"catalog_is_source_of_truth":True},
                "approvals":{},"vertical":{}}))
            with patch("agentic_portfolio.operator_review.run",
                       return_value={"state":"PASS","engineering":{},"catalog":{}}):
                with self.assertRaisesRegex(ValueError,"actual two-model review"):
                    prepare(base,root/"workspace",root/"private.json",root/"report.json")
if __name__=="__main__":
    unittest.main()
