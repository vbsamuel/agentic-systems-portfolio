"""Actual Git mutation and persistent-commit integration qualification.

The model adapter is replaced by a deterministic proposal only in this
contract test. Real-model qualification must run separately in WSL.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agentic_portfolio.repair_agent import execute

class PersistentRepairTests(unittest.TestCase):
    def test_failed_before_passed_after_creates_durable_git_ref(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)/"target"
            repo.mkdir()
            def git(*args):
                return subprocess.run(["git","-C",str(repo),*args],
                    check=True,text=True,capture_output=True).stdout.strip()
            git("init","-q")
            (repo/"module.py").write_text("def add_two(x):\n    return x + 1\n")
            (repo/"test_module.py").write_text(
                "import unittest\nfrom module import add_two\n"
                "class TestMath(unittest.TestCase):\n"
                "    def test_contract(self):\n        self.assertEqual(add_two(3),5)\n")
            git("add","module.py","test_module.py")
            git("-c","user.name=Test","-c","user.email=test@example.invalid",
                "commit","-qm","initial defect")
            original=git("rev-parse","HEAD")
            config={"engineering":{
                "repository":str(repo), "allowed_files":["module.py"],
                "validation_command":["python3","-m","unittest","discover"],
                "timeout_seconds":30,
                "commit_identity":{"name":"Agent Qualification","email":"agent@example.invalid"}
                }, "model_endpoint":{}}
            proposal={"response":'{"path":"module.py","old_text":"return x + 1",'
                                 '"new_text":"return x + 2","rationale":"contract"}',
                      "model":"contract-fixture","usage":{},"response_digest":"test"}
            with patch("agentic_portfolio.repair_agent.invoke_model",return_value=proposal):
                outcome=execute(config,approve=True)
            self.assertEqual(outcome["status"],"VERIFIED_CANDIDATE_PERSISTED")
            self.assertEqual(git("rev-parse","HEAD"),original)
            self.assertEqual(git("rev-parse",outcome["candidate_ref"]),
                             outcome["candidate_revision"])
            content=git("show",outcome["candidate_revision"]+":module.py")
            self.assertIn("return x + 2",content)
            self.assertIn("return x + 1",(repo/"module.py").read_text())
            stages={x["stage"]:x for x in outcome["events"]}
            self.assertNotEqual(stages["baseline_reproduction"]["result"]["exit_code"],0)
            self.assertEqual(stages["independent_test_execution"]["result"]["exit_code"],0)
            self.assertEqual(git("status","--porcelain"),"")

if __name__=="__main__":
    unittest.main()
