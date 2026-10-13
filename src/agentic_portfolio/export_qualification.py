"""Strict local vertical evidence exporter. Never manufactures success.

Requires actual observed PASS, verified Git candidate, catalog HTTP readback,
native journal integrity, and durable effect state VERIFIED.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from .event_journal import EventJournal
from .effect_ledger import EffectLedger
from .ssh_approval import verify as verify_ssh_approval
from .live_e2e import atomic_json

def collect(report_path, allowed_signers=None):
    path=Path(report_path)
    report=json.loads(path.read_text(encoding="utf-8"))
    eng=report.get("engineering") or {}
    catalog=report.get("catalog") or {}
    if report.get("state")!="PASS":
        raise ValueError("release evidence refused: integrated run did not PASS")
    if eng.get("status")!="VERIFIED_CANDIDATE_PERSISTED":
        raise ValueError("release evidence refused: engineering not verified")
    if not catalog.get("verified"):
        raise ValueError("release evidence refused: catalog not verified")
    if not (catalog.get("writeback_performed") or catalog.get("effect_recovered")):
        raise ValueError("release evidence refused: model-driven publication not observed")
    final=(catalog.get("publish_evidence") or {}).get("after") or {}
    if final.get("status")!="PASS" or final.get("findings")!=[]:
        raise ValueError("release evidence refused: independent post-write comparison missing")
    journal_path=path.with_suffix(".events.sqlite3")
    if not journal_path.exists():
        raise ValueError("release evidence refused: native journal missing")
    journal=EventJournal(journal_path)
    journal.verify()
    events=journal.read(report["run_id"])
    if not events or events[-1]["kind"]!="execution_finalized":
        raise ValueError("release evidence refused: final native event missing")
    event_kinds=[e["kind"] for e in events]
    required={"model_call_started","model_call_completed","git_call_started",
              "validation_completed","http_call_started","http_call_completed"}
    if not required.issubset(set(event_kinds)) or event_kinds.count("model_call_completed")<2:
        raise ValueError("release evidence refused: native inference and tool spans incomplete")
    workspace=report.get("vertical_workspace")
    if not workspace:
        raise ValueError("release evidence refused: source workspace unspecified")
    git_dir=str(Path(workspace)/"defective_project")
    def git(*parts):
        return subprocess.run(["git","-C",git_dir,*parts],check=True,
                              text=True,capture_output=True,timeout=15).stdout.strip()
    if git("rev-parse",eng["candidate_ref"])!=eng["candidate_revision"]:
        raise ValueError("release evidence refused: candidate ref invalid")
    if git("rev-parse","HEAD")!=eng["base_revision"]:
        raise ValueError("release evidence refused: source branch drift")
    approval=catalog.get("approval_evidence") or {}
    if approval.get("auth_type")!="openssh" or not approval.get("signature_sha256"):
        raise ValueError("release evidence refused: SSH identity-bound review evidence missing")
    if not allowed_signers or not approval.get("signed_grant"):
        raise ValueError("release evidence refused: independently verifiable SSH grant missing")
    verify_ssh_approval(allowed_signers,approval["signed_grant"],
                        run_id=report["run_id"],
                        decision_digest=catalog["decision_digest"])
    effect_id=catalog.get("effect_id")
    if not effect_id:
        raise ValueError("release evidence refused: publication effect identity missing")
    ledger=EffectLedger(path.with_suffix(".effects.sqlite3"))
    entry=ledger.get(effect_id)
    if not entry or entry["state"]!="VERIFIED" or entry["run_id"]!=report["run_id"]:
        raise ValueError("release evidence refused: durable effect is not verified")
    return {
        "qualification":"LOCAL_TWO_MODEL_VERTICAL_PASS",
        "not_production_signoff":True,
        "run_id":report["run_id"],"engineer_candidate":eng["candidate_revision"],
        "engineer_base":eng["base_revision"],"effect_id":effect_id,
        "decision_digest":catalog.get("decision_digest"),
        "approval_evidence":catalog.get("approval_evidence"),
        "trusted_reviewers_sha256":hashlib.sha256(Path(allowed_signers).read_bytes()).hexdigest(),
        "http_status":(catalog.get("publish_evidence") or {}).get("update_status"),
        "catalog_status":catalog["status"],
        "stage_count":len(report.get("stages",[])),
        "native_event_count":len(events),
        "native_model_invocations":event_kinds.count("model_call_completed"),
        "native_http_calls":event_kinds.count("http_call_completed"),
        "native_git_calls":event_kinds.count("git_call_completed"),
        "journal_last_hash":events[-1]["event_hash"],
        "source_report_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
        "external_production_qualification":"NOT_PERFORMED"
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--allowed-signers",required=True)
    args=p.parse_args()
    try:
        evidence=collect(args.report,allowed_signers=args.allowed_signers)
        atomic_json(args.output,evidence)
        print(json.dumps({"qualified":True,"scope":evidence["qualification"],"output":args.output}))
        return 0
    except Exception as exc:
        print(json.dumps({"qualified":False,"error":type(exc).__name__+": "+str(exc)}))
        return 2
if __name__=="__main__":
    raise SystemExit(main())
