"""Authority-policy qualification: observed mismatch alone cannot authorize correction."""
import unittest
from unittest.mock import patch
from agentic_portfolio.catalog_agent import decide

class CatalogAuthorityTests(unittest.TestCase):
    def test_correction_requires_trusted_authority_and_allowlisted_field(self):
        def observed(price, digest):
            return {"body":[{"sku":"P-1","title":"Device","description":"Device",
                "price":price,"currency":"USD","availability":"in stock",
                "image_url":"device"}],"sha256":digest,"etag":"1"}
        response={"response":'{"action":"CORRECT","skus":["P-1"],"rationale":"Authoritative price differs"}',
                  "model":"model","usage":{},"response_digest":"digest"}
        src=observed("100.00","truth")
        published=observed("119.00","published")
        with patch("agentic_portfolio.catalog_agent.invoke_model",return_value=response):
            with self.assertRaisesRegex(ValueError,"authority policy"):
                decide({},src,published)
            with self.assertRaisesRegex(ValueError,"authority policy"):
                decide({},src,published,{"catalog_is_source_of_truth":True,
                                         "correctable_fields":["description"]})
            approved=decide({},src,published,{"catalog_is_source_of_truth":True,
                                               "correctable_fields":["price"]})
            self.assertEqual(approved["decision"]["action"],"CORRECT")
            self.assertTrue(approved["decision_digest"])

if __name__=="__main__":
    unittest.main()
