"""Integrated catalog write boundary rejects an unsigned authorization."""
import unittest
from unittest.mock import patch
from agentic_portfolio.catalog_agent import model_governed_reconcile

class AuthenticatedPublicationTests(unittest.TestCase):
    def test_digest_alone_never_licenses_writeback(self):
        observation={"body":[{"sku":"P-1","title":"Device","description":"Device",
            "price":"100.00","currency":"USD","availability":"in stock","image_url":"d"}],
            "sha256":"source","etag":"1"}
        published={"body":[{**observation["body"][0],"price":"119.00"}],
                   "sha256":"published","etag":"2"}
        response={"response":'{"action":"CORRECT","skus":["P-1"],"rationale":"Authorized price discrepancy"}',
                  "model":"inference","usage":{},"response_digest":"model-response"}
        policy={"catalog_is_source_of_truth":True,"correctable_fields":["price"]}
        with patch("agentic_portfolio.catalog_agent.invoke_model",return_value=response):
            with patch("agentic_portfolio.catalog_agent.call",side_effect=[observation,published]):
                result=model_governed_reconcile({},object(),object(),writeback=False,authority_policy=policy)
        digest=result["decision_digest"]
        with patch("agentic_portfolio.catalog_agent.invoke_model",return_value=response):
            with patch("agentic_portfolio.catalog_agent.call",side_effect=[observation,published]):
                with patch("agentic_portfolio.http_integration.synchronize") as mutate:
                    blocked=model_governed_reconcile({},object(),object(),writeback=True,
                        approved_digest=digest,authority_policy=policy,run_id="run-id")
                    mutate.assert_not_called()
        self.assertEqual(blocked["status"],"AUTHENTICATED_APPROVAL_REQUIRED")
        self.assertFalse(blocked["writeback_performed"])

if __name__=="__main__":
    unittest.main()
