import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agentic_portfolio.operator_session import session

class OperatorSessionTests(unittest.TestCase):
    def fake_review(self,*args):
        report=Path(args[3])
        report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text(json.dumps({"run_id":"actual-run","state":"BLOCKED_CATALOG",
            "engineering":{"candidate_revision":"sha"},
            "catalog":{"status":"AWAITING_APPROVAL",
                "decision":{"action":"CORRECT","skus":["P-1"]},
                "decision_digest":"approved-sha",
                "before":{"findings":[{"sku":"P-1","field":"price",
                    "expected":"100.00","observed":"119.00"}]}}}))
        return {"candidate_revision":"sha"}
    def invoke(self,root,confirmed):
        with patch("agentic_portfolio.operator_session.prepare",side_effect=self.fake_review):
            with patch("agentic_portfolio.operator_session.qualify",
                       return_value={"scope":"LOCAL_TWO_MODEL_VERTICAL_PASS"}) as release:
                result=session("base",root,"reviewer","private-key","public-trust",
                               confirm=lambda prompt:confirmed)
                return result,release
    def test_refused_digest_causes_no_effect(self):
        with tempfile.TemporaryDirectory() as td:
            result,release=self.invoke(td,"reject")
            self.assertEqual(result["state"],"REJECTED")
            release.assert_not_called()
    def test_approved_word_authorizes_exact_bound_run(self):
        with tempfile.TemporaryDirectory() as td:
            result,release=self.invoke(td,"approved")
            self.assertEqual(result["scope"],"LOCAL_TWO_MODEL_VERTICAL_PASS")
            release.assert_called_once()
            self.assertTrue(release.call_args.kwargs["confirmed"])

    def test_defer_preserves_without_write(self):
        with tempfile.TemporaryDirectory() as td:
            result,release=self.invoke(td,"3")
            self.assertEqual(result["state"],"DEFERRED")
            self.assertFalse(result["publication_performed"])
            release.assert_not_called()

    def test_unrecognized_response_rejected_without_write(self):
        with tempfile.TemporaryDirectory() as td:
            result,release=self.invoke(td,"maybe")
            self.assertEqual(result["state"],"INVALID_DECISION")
            release.assert_not_called()

    def test_exact_digest_uses_same_run_for_single_release(self):
        with tempfile.TemporaryDirectory() as td:
            result,release=self.invoke(td,"approved-sha")
            self.assertEqual(result["scope"],"LOCAL_TWO_MODEL_VERTICAL_PASS")
            release.assert_called_once()
            self.assertEqual(Path(release.call_args.kwargs["report"]).name,"run.json")

if __name__=="__main__":
    unittest.main()
