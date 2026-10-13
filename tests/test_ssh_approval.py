import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from agentic_portfolio.ssh_approval import sign,verify

@unittest.skipUnless(shutil.which("ssh-keygen"),"OpenSSH ssh-keygen required")
class SSHApprovalTests(unittest.TestCase):
    def test_real_reviewer_signature_trust_and_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            private=Path(td)/"reviewer"
            subprocess.run(["ssh-keygen","-q","-t","ed25519","-N","",
                            "-f",str(private)],check=True,capture_output=True,timeout=20)
            trusted=Path(td)/"allowed_signers"
            trusted.write_text("actual-reviewer "+private.with_suffix(".pub").read_text())
            grant=sign(private,run_id="run",decision_digest="digest",
                       reviewer="actual-reviewer",scope="catalog:publish",
                       expires_at=2000)
            self.assertTrue(verify(trusted,grant,run_id="run",
                                   decision_digest="digest",now=1000))
            with self.assertRaises(ValueError):
                verify(trusted,grant,run_id="run",decision_digest="changed",now=1000)
            with self.assertRaises(ValueError):
                verify(trusted,{**grant,"reviewer":"other"},run_id="run",
                       decision_digest="digest",now=1000)
            with self.assertRaises(ValueError):
                verify(trusted,grant,run_id="run",decision_digest="digest",now=2000)
if __name__=="__main__":
    unittest.main()
