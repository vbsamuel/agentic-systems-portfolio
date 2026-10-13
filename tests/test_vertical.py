"""Integration qualification: real Git patch, real SQLite-backed HTTP server,
real conditional update and reread; only external model response is replaced.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agentic_portfolio.vertical import run

class VerticalTests(unittest.TestCase):
    def test_actual_git_and_http_mutations_under_one_run(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            config={
                "model_endpoint":{},
                "approvals":{"engineering_worktree_mutation":True,"catalog_writeback":True},
                "vertical":{
                    "workspace":str(base/"workspace"),
                    "project_files":{
                        "app.py":"def add_two(x):\n    return x + 1\n",
                        "test_app.py":"import unittest\nfrom app import add_two\nclass Verify(unittest.TestCase):\n    def test_contract(self):\n        self.assertEqual(add_two(3),5)\n"},
                    "allowed_files":["app.py"],
                    "validation_command":["python3","-m","unittest","discover"],
                    "timeout_seconds":30,"http_timeout_seconds":5,
                    "commit_identity":{"name":"Verifier","email":"verifier@example.invalid"},
                    "authoritative_products":[{"sku":"A","title":"A","description":"A",
                        "price":"1.00","currency":"USD","availability":"in stock","image_url":"a"}],
                    "published_products":[{"sku":"A","title":"A","description":"A",
                        "price":"2.00","currency":"USD","availability":"in stock","image_url":"a"}]
                }
            }
            response={"response":json.dumps({"path":"app.py","old_text":"return x + 1",
                "new_text":"return x + 2","rationale":"contract"}),"model":"test-adapter",
                "usage":{},"response_digest":"test"}
            artifact=base/"out.json"
            with patch("agentic_portfolio.repair_agent.invoke_model",return_value=response):
                result=run(config,str(artifact))
            self.assertEqual(result["state"],"PASS",result)
            self.assertEqual(result["engineering"]["status"],"VERIFIED_CANDIDATE_PERSISTED")
            self.assertTrue(result["catalog"]["verified"])
            self.assertTrue(result["catalog"]["writeback_performed"])
            self.assertEqual(result["catalog"]["after"]["findings"],[])
            self.assertEqual(len(result["stages"]),2)
            self.assertTrue(artifact.is_file())
            self.assertTrue((base/"workspace"/"catalog.db").is_file())
if __name__=="__main__":
    unittest.main()
