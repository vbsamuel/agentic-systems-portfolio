"""Fail-closed release qualification for Engineering and Catalog systems.

Qualification is evidence-based. Local unit tests or the 12-stage fixture run
cannot satisfy a production-path gate. Evidence must bind a check to a Git
revision, environment, executable result, and independently observed artifact.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

SYSTEMS = ("engineering", "catalog")
CAPABILITIES = (
    "source_integration", "autonomous_investigation", "model_decisions",
    "real_mutations", "independent_verification", "durable_recovery",
    "stage_telemetry", "human_approval", "production_qualification",
)
REQUIRED = ("check_id", "system", "capability", "status", "source_revision",
            "environment", "run_id", "evidence_file", "evidence_sha256",
            "independent_verifier", "measured_result")


def assess(manifest, evidence_root):
    """Check all eighteen independent gates without accepting synthetic defaults."""
    observations = manifest.get("evidence", [])
    if not isinstance(observations, list):
        raise ValueError("evidence must be an array")
    indexed, duplicates = {}, []
    for item in observations:
        if not isinstance(item, dict):
            continue
        key = (item.get("system"), item.get("capability"))
        if key in indexed:
            duplicates.append(key)
        else:
            indexed[key] = item
    root = Path(evidence_root).resolve()
    gates = []
    for system in SYSTEMS:
        for capability in CAPABILITIES:
            item = indexed.get((system, capability))
            errors = []
            if item is None:
                errors.append("MISSING_EVIDENCE")
            else:
                missing = [field for field in REQUIRED
                           if item.get(field) is None or item.get(field) == ""]
                if missing:
                    errors.append("MISSING_FIELDS:" + ",".join(missing))
                if item.get("status") != "PASS":
                    errors.append("NOT_PASSED")
                if item.get("check_id") != system + ":" + capability:
                    errors.append("INVALID_CHECK_ID")
                if item.get("independent_verifier") == item.get("run_id"):
                    errors.append("NOT_INDEPENDENT")
                if item.get("environment") in ("fixture", "simulation", "mock", "local-integrations"):
                    errors.append("NOT_PRODUCTION_PATH")
                rel = item.get("evidence_file")
                if not isinstance(rel, str) or not rel:
                    errors.append("NO_ARTIFACT")
                else:
                    path = (root / rel).resolve()
                    if not path.is_relative_to(root) or not path.is_file():
                        errors.append("INVALID_ARTIFACT_PATH")
                    else:
                        digest = hashlib.sha256(path.read_bytes()).hexdigest()
                        if digest != item.get("evidence_sha256"):
                            errors.append("ARTIFACT_DIGEST_MISMATCH")
                if not isinstance(item.get("measured_result"), dict) or not item.get("measured_result"):
                    errors.append("NO_MEASUREMENT")
            gates.append({"system":system, "capability":capability,
                          "status":"PASS" if not errors else "BLOCKED",
                          "errors":errors})
    return {"schema_version":1, "release":"PASS" if all(
            g["status"] == "PASS" for g in gates) and not duplicates else "BLOCKED",
            "passed":sum(g["status"] == "PASS" for g in gates),
            "required":len(gates), "duplicate_checks":[list(d) for d in duplicates],
            "gates":gates}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    outcome = assess(manifest, args.evidence_root)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(outcome, indent=2, sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"release":outcome["release"],"passed":outcome["passed"],
                      "required":outcome["required"],"report":str(path)}))
    return 0 if outcome["release"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
