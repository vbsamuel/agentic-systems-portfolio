"""Coordinator must use the model decision and refuse unapproved publication."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agentic_portfolio.live_e2e import execute

class ModelCatalogCoordinatorTests(unittest.TestCase):
    def config(self):
        return {
            "model_endpoint":{"model":"example"},
            "catalog_model_driven":True,
            "approvals":{"engineering_worktree_mutation":True,"catalog_writeback":False},
            "catalog":{"authoritative":{"url":"http://127.0.0.1:1/catalog","token":"token"},
                       "published":{"url":"http://127.0.0.1:1/published","token":"token"}}
        }

    def test_review_blocks_release_and_uses_catalog_agent(self):
        cfg=self.config()
        with tempfile.TemporaryDirectory() as d:
            path=str(Path(d)/"evidence.json")
            with patch("agentic_portfolio.live_e2e.execute_repair",
                       return_value={"status":"VERIFIED_CANDIDATE_PERSISTED"}):
                with patch("agentic_portfolio.live_e2e.model_governed_reconcile",
                           return_value={"status":"AWAITING_APPROVAL",
                                         "verified":False,"writeback_performed":False,
                                         "decision_digest":"digest-one"}) as model:
                    outcome=execute(cfg,path)
                    model.assert_called_once()
            self.assertEqual(outcome["state"],"BLOCKED_CATALOG")
            self.assertEqual(outcome["catalog"]["decision_digest"],"digest-one")
            self.assertEqual(json.loads(Path(path).read_text())["state"],"BLOCKED_CATALOG")

    def test_only_verified_approved_model_decision_can_pass(self):
        cfg=self.config()
        cfg["approvals"]["catalog_writeback"]=True
        cfg["catalog_approved_digest"]="authorized-digest"
        with tempfile.TemporaryDirectory() as d:
            with patch("agentic_portfolio.live_e2e.execute_repair",
                       return_value={"status":"VERIFIED_CANDIDATE_PERSISTED"}):
                with patch("agentic_portfolio.live_e2e.model_governed_reconcile",
                           return_value={"status":"VERIFIED","verified":True,
                                         "writeback_performed":True}) as model:
                    outcome=execute(cfg,str(Path(d)/"evidence.json"))
                    self.assertEqual(model.call_args.kwargs["approved_digest"],"authorized-digest")
            self.assertEqual(outcome["state"],"PASS")

if __name__=="__main__":
    unittest.main()
