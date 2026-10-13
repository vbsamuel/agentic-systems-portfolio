import unittest
from unittest.mock import patch
from agentic_portfolio.external_conformance import probe

class ExternalConformanceTests(unittest.TestCase):
    def test_loopback_cannot_masquerade_as_external(self):
        cfg={"catalog":{"authoritative":{"url":"http://127.0.0.1:8/catalog","token":"t"},
                        "published":{"url":"http://127.0.0.1:8/published","token":"t"}}}
        with self.assertRaisesRegex(ValueError,"non-loopback HTTPS"):
            probe(cfg)
    def test_external_requires_etag_and_live_schema(self):
        cfg={"catalog":{"authoritative":{"url":"https://catalog.example.invalid/products","token":"t"},
                        "published":{"url":"https://publish.example.invalid/products","token":"t"}}}
        record={"sku":"P","title":"A","description":"A","price":"1","currency":"USD",
                "availability":"in stock","image_url":"/a"}
        with patch("agentic_portfolio.external_conformance.call",
                   side_effect=[{"body":[record],"sha256":"a","duration_ms":1},
                                {"body":[record],"sha256":"b","etag":None,"duration_ms":1}]):
            with self.assertRaisesRegex(ValueError,"ETag"):
                probe(cfg)
if __name__=="__main__":
    unittest.main()
