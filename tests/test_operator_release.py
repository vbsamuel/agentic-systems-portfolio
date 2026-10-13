import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agentic_portfolio.operator_release import qualify

class OneReleaseContractTests(unittest.TestCase):
    def call(self,root,confirmed=True):
        return qualify(config="runtime",report="report",reviewer="reviewer",
            ssh_private_key="private",allowed_signers="public",
            evidence_output=str(Path(root)/"evidence.json"),
            workbench_output=str(Path(root)/"dashboard.html"),confirmed=confirmed)
    def test_missing_approval_blocks_before_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            with patch("agentic_portfolio.operator_release.close") as close:
                with self.assertRaisesRegex(ValueError,"approval"):
                    self.call(td,False)
                close.assert_not_called()
    def test_unverified_remote_effect_blocks_evidence_and_dashboard(self):
        with tempfile.TemporaryDirectory() as td:
            with patch("agentic_portfolio.operator_release.close",
                       return_value={"state":"BLOCKED_CATALOG",
                                     "catalog":{"status":"EFFECT_UNCERTAIN"}}):
                with patch("agentic_portfolio.operator_release.collect") as evidence:
                    with self.assertRaisesRegex(ValueError,"independently verify"):
                        self.call(td)
                    evidence.assert_not_called()
    def test_only_full_verified_run_exports_both_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            with patch("agentic_portfolio.operator_release.close",
                       return_value={"state":"PASS","run_id":"r"}):
                with patch("agentic_portfolio.operator_release.collect",
                           return_value={"qualification":"LOCAL_TWO_MODEL_VERTICAL_PASS",
                                         "run_id":"r"}) as evidence:
                    with patch("agentic_portfolio.operator_release.build") as dashboard:
                        result=self.call(td)
            evidence.assert_called_once()
            dashboard.assert_called_once()
            self.assertEqual(result["run_id"],"r")
            self.assertEqual(result["external_production_qualification"],"NOT_PERFORMED")
if __name__=="__main__":
    unittest.main()
