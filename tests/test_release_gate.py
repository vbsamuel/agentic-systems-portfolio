import hashlib
import tempfile
import unittest
from pathlib import Path
from agentic_portfolio.release_gate import CAPABILITIES, SYSTEMS, assess

class ReleaseQualificationTests(unittest.TestCase):
    def test_empty_evidence_cannot_release(self):
        report=assess({"evidence":[]}, ".")
        self.assertEqual(report["release"],"BLOCKED")
        self.assertEqual(report["required"],18)
        self.assertEqual(report["passed"],0)

    def test_legacy_fixture_evidence_cannot_release(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"observation.json"
            path.write_text('{"observed":true}')
            row=self.make_row(path, "engineering",CAPABILITIES[0])
            row["environment"]="local-integrations"
            result=assess({"evidence":[row]},directory)
            self.assertEqual(result["passed"],0)
            self.assertIn("NOT_PRODUCTION_PATH",result["gates"][0]["errors"])

    def test_digest_mismatch_and_missing_gates_block(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"observation.json"
            path.write_text('{"observed":true}')
            row=self.make_row(path,"engineering",CAPABILITIES[0])
            row["evidence_sha256"]="0"*64
            report=assess({"evidence":[row]},directory)
            self.assertEqual(report["release"],"BLOCKED")
            self.assertIn("ARTIFACT_DIGEST_MISMATCH",report["gates"][0]["errors"])

    def test_all_attested_paths_required(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"observation.json"
            path.write_text('{"observed":true}')
            rows=[self.make_row(path,system,capability)
                  for system in SYSTEMS for capability in CAPABILITIES]
            report=assess({"evidence":rows},directory)
            self.assertEqual(report["passed"],18)
            self.assertEqual(report["release"],"PASS")
            rows.append(rows[0])
            self.assertEqual(assess({"evidence":rows},directory)["release"],"BLOCKED")

    @staticmethod
    def make_row(path,system,capability):
        return {"check_id":system+":"+capability,"system":system,
                "capability":capability,"status":"PASS",
                "source_revision":"deadbeef",
                "environment":"external-integration",
                "run_id":"run-one","evidence_file":path.name,
                "evidence_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                "independent_verifier":"verifier-two",
                "measured_result":{"observed_events":1}}

if __name__=="__main__":
    unittest.main()
