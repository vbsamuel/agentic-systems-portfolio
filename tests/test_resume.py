"""Verified candidate resume must never silently rerun the engineering model."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agentic_portfolio.live_e2e import execute

class ResumeTests(unittest.TestCase):
    def test_resume_reuses_valid_candidate_and_rejects_ref_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            repo=root/"repo"
            repo.mkdir()
            def git(*args):
                return subprocess.run(["git","-C",str(repo),*args],capture_output=True,
                                      text=True,check=True).stdout.strip()
            git("init","-q")
            (repo/"app.py").write_text("x=1\n")
            git("add",".")
            git("-c","user.name=Tester","-c","user.email=t@example.invalid",
                "commit","-qm","baseline")
            head=git("rev-parse","HEAD")
            ref="refs/agentic-repairs/"+head
            git("update-ref",ref,head)
            record={"schema_version":1,"run_id":"existing-run","state":"RUNNING",
                    "stages":[],"engineering":{"status":"VERIFIED_CANDIDATE_PERSISTED",
                    "base_revision":head,"candidate_revision":head,"candidate_ref":ref},
                    "catalog":None}
            artifact=root/"report.json"
            artifact.write_text(json.dumps(record))
            cfg={"resume_verified_engineering":True,
                 "engineering":{"repository":str(repo)},
                 "model_endpoint":{},"catalog_model_driven":True,
                 "catalog":{"authoritative":{"url":"http://127.0.0.1:1/c","token":"x"},
                            "published":{"url":"http://127.0.0.1:1/p","token":"x"}},
                 "approvals":{"engineering_worktree_mutation":True,
                              "catalog_writeback":False}}
            with patch("agentic_portfolio.live_e2e.execute_repair") as repair:
                with patch("agentic_portfolio.live_e2e.model_governed_reconcile",
                           return_value={"status":"AWAITING_APPROVAL",
                                         "verified":False,"writeback_performed":False}):
                    out=execute(cfg,str(artifact))
                repair.assert_not_called()
            self.assertEqual(out["run_id"],"existing-run")
            self.assertEqual(out["state"],"BLOCKED_CATALOG")
            git("update-ref","-d",ref)
            with self.assertRaises(subprocess.CalledProcessError):
                execute(cfg,str(artifact))
if __name__=="__main__":
    unittest.main()
