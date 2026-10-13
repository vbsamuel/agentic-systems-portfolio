import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agentic_portfolio.live_e2e import execute

class CatalogModelRoutingTests(unittest.TestCase):
    def test_separate_catalog_model_and_resumed_engineering(self):
        with tempfile.TemporaryDirectory() as td:
            cfg={"model_endpoint":{"model":"engineering"},
                 "catalog_model_endpoint":{"model":"catalog"},
                 "catalog_model_driven":True,
                 "approvals":{"engineering_worktree_mutation":True,
                              "catalog_writeback":False},
                 "catalog":{"authoritative":{"url":"http://127.0.0.1:1/source","token":"x"},
                            "published":{"url":"http://127.0.0.1:1/channel","token":"x"}}}
            with patch("agentic_portfolio.live_e2e.execute_repair",
                       return_value={"status":"VERIFIED_CANDIDATE_PERSISTED"}):
                with patch("agentic_portfolio.live_e2e.model_governed_reconcile",
                           return_value={"status":"AWAITING_APPROVAL","verified":False,
                                         "writeback_performed":False}) as model:
                    result=execute(cfg,str(Path(td)/"result.json"))
                    self.assertEqual(model.call_args.args[0]["model"],"catalog")
                    self.assertEqual(result["state"],"BLOCKED_CATALOG")
if __name__=="__main__":
    unittest.main()
