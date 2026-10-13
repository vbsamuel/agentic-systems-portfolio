import unittest
from unittest.mock import patch
from agentic_portfolio.catalog_agent import decide, model_governed_reconcile

def observation(price, digest, etag=None):
    row={"sku":"A","title":"A","description":"A","price":price,
         "currency":"USD","availability":"in stock","image_url":"a"}
    return {"body":[row],"sha256":digest,"etag":etag}

class CatalogAgentTests(unittest.TestCase):
    def test_actual_findings_bound_to_model_decision(self):
        source=observation("1.00","source")
        channel=observation("2.00","published","v1")
        result={"response":'{"action":"CORRECT","skus":["A"],"rationale":"observed price discrepancy"}',
                "model":"model","usage":{"total_tokens":19},"response_digest":"modeldigest"}
        with patch("agentic_portfolio.catalog_agent.invoke_model",return_value=result):
            first=decide({},source,channel,{"catalog_is_source_of_truth":True,"correctable_fields":["price"]})
            second=decide({},source,channel,{"catalog_is_source_of_truth":True,"correctable_fields":["price"]})
        self.assertEqual(first["decision_digest"],second["decision_digest"])
        self.assertEqual(first["before"]["findings"][0]["field"],"price")
    def test_reject_unobserved_sku(self):
        response={"response":'{"action":"CORRECT","skus":["UNSEEN"],"rationale":"invented"}',
                  "model":"model","usage":{},"response_digest":"test"}
        with patch("agentic_portfolio.catalog_agent.invoke_model",return_value=response):
            with self.assertRaises(ValueError):
                decide({},observation("1.00","a"),observation("2.00","b","v1"),{"catalog_is_source_of_truth":True,"correctable_fields":["price"]})
    def test_no_write_without_exact_approval(self):
        observations=[observation("1.00","a"),observation("2.00","b","v1")]
        response={"response":'{"action":"CORRECT","skus":["A"],"rationale":"price mismatch"}',
                  "model":"model","usage":{},"response_digest":"test"}
        with patch("agentic_portfolio.catalog_agent.call",side_effect=observations):
            with patch("agentic_portfolio.catalog_agent.invoke_model",return_value=response):
                with patch("agentic_portfolio.http_integration.synchronize") as write:
                    outcome=model_governed_reconcile({},object(),object(),writeback=True,
                                                      approved_digest="not-the-decision",
                                                      authority_policy={"catalog_is_source_of_truth":True,"correctable_fields":["price"]})
                    write.assert_not_called()
        self.assertEqual(outcome["status"],"APPROVAL_MISMATCH")
        self.assertFalse(outcome["verified"])
if __name__=="__main__":
    unittest.main()
