import unittest
from agentic_portfolio.approval_grants import issue,verify

class ApprovalGrantsTests(unittest.TestCase):
    def test_bound_grant_and_expiry(self):
        key="operator-private-key-with-at-least-32-characters"
        grant=issue(key,run_id="run-1",decision_digest="sha-1",reviewer="reviewer-1",
                    expires_at=2000,scope="catalog:publish")
        self.assertTrue(verify(key,grant,run_id="run-1",decision_digest="sha-1",now=1000))
        for run,digest,now in (("run-2","sha-1",1000),("run-1","sha-2",1000),("run-1","sha-1",2000)):
            with self.assertRaises(ValueError):
                verify(key,grant,run_id=run,decision_digest=digest,now=now)
        altered={**grant,"reviewer":"other"}
        with self.assertRaisesRegex(ValueError,"signature"):
            verify(key,altered,run_id="run-1",decision_digest="sha-1",now=1000)
    def test_bad_scope_rejected(self):
        with self.assertRaises(ValueError):
            issue("a"*40,run_id="r",decision_digest="d",reviewer="p",
                  expires_at=1000,scope="git:push")
if __name__=="__main__":
    unittest.main()
