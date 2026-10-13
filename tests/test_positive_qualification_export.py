import hashlib
import json
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from agentic_portfolio.event_journal import EventJournal
from agentic_portfolio.effect_ledger import EffectLedger
from agentic_portfolio.ssh_approval import sign
from agentic_portfolio.export_qualification import collect

@unittest.skipUnless(shutil.which("ssh-keygen"),"OpenSSH reviewer qualification requires ssh-keygen")
class PositiveQualificationExportTests(unittest.TestCase):
    def test_git_journal_effect_and_reviewer_signature_all_required(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            workspace=root/"workspace"
            project=workspace/"defective_project"
            project.mkdir(parents=True)
            def git(*args):
                return subprocess.run(["git","-C",str(project),*args],
                    check=True,capture_output=True,text=True).stdout.strip()
            git("init","-q")
            (project/"source.py").write_text("corrected = True\n")
            git("add",".")
            git("-c","user.name=Test","-c","user.email=t@example.invalid",
                "commit","-qm","verified candidate")
            head=git("rev-parse","HEAD")
            ref="refs/agentic-repairs/"+head
            git("update-ref",ref,head)
            reviewer_key=root/"reviewer"
            subprocess.run(["ssh-keygen","-q","-t","ed25519","-N","",
                            "-f",str(reviewer_key)],check=True,capture_output=True)
            signers=root/"allowed_signers"
            signers.write_text("operator "+reviewer_key.with_suffix(".pub").read_text())
            grant=sign(reviewer_key,run_id="run-real",decision_digest="reviewed",
                       reviewer="operator",scope="catalog:publish",
                       expires_at=int(time.time())+600)
            report=root/"run.json"
            journal=EventJournal(report.with_suffix(".events.sqlite3"))
            stages=None
            started={}
            calls={
                "git_call_completed":"git_call_started",
                "validation_completed":"validation_started",
                "model_call_completed":"model_call_started",
                "http_call_completed":"http_call_started"}
            kinds=("execution_started","stage_started","git_call_started",
                   "git_call_completed","validation_started","validation_completed",
                   "model_call_started","model_call_completed","stage_completed",
                   "stage_started","http_call_started","http_call_completed",
                   "model_call_started","model_call_completed","http_call_started",
                   "http_call_completed","execution_finalized")
            root_id=None
            for kind in kinds:
                if kind=="execution_started":
                    parent=None
                elif kind=="stage_started":
                    parent=root_id
                elif kind in started or kind.endswith("_started"):
                    parent=stages
                elif kind in calls:
                    parent=started[calls[kind]]
                else:
                    parent=stages or root_id
                entry=journal.append("run-real",kind,{"name":kind},parent_id=parent)
                if kind=="execution_started":
                    root_id=entry["event_id"]
                if kind=="stage_started":
                    stages=entry["event_id"]
                if kind in ("git_call_started","validation_started",
                            "model_call_started","http_call_started"):
                    started[kind]=entry["event_id"]
            effect_id=hashlib.sha256(b"run-real|reviewed").hexdigest()
            ledger=EffectLedger(report.with_suffix(".effects.sqlite3"))
            ledger.prepare(effect_id,"run-real","reviewed",{"desired_products":[],"previous_products":[]})
            ledger.outcome(effect_id,"VERIFIED",{"external_observation":"confirmed"})
            report.write_text(json.dumps({
                "run_id":"run-real","state":"PASS","vertical_workspace":str(workspace),
                "engineering":{"status":"VERIFIED_CANDIDATE_PERSISTED",
                               "base_revision":head,"candidate_revision":head,
                               "candidate_ref":ref},
                "catalog":{"status":"VERIFIED","verified":True,"writeback_performed":True,
                           "effect_id":effect_id,"decision_digest":"reviewed",
                           "approval_evidence":{"auth_type":"openssh",
                               "signature_sha256":hashlib.sha256(grant["signature"].encode()).hexdigest(),
                               "signed_grant":grant},
                           "publish_evidence":{"update_status":200,
                                               "after":{"status":"PASS","findings":[]}}},
                "stages":[]}))
            result=collect(report,allowed_signers=signers)
            self.assertEqual(result["qualification"],"LOCAL_TWO_MODEL_VERTICAL_PASS")
            self.assertEqual(result["native_model_invocations"],2)
            self.assertTrue(result["trusted_reviewers_sha256"])
if __name__=="__main__":
    unittest.main()
