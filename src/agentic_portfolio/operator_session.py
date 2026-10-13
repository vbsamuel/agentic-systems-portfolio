"""One interactive operator session: actual review, cryptographic approval, effect, evidence.

Starts fresh; no mock models, silent permissions, or synthetic PASS. The
operator confirms the exact model decision digest after reviewing the findings.
"""
import argparse
import json
import uuid
import threading
import time
from pathlib import Path
from .operator_review import prepare
from .operator_release import qualify

def session(base_config,root,reviewer,ssh_private_key,allowed_signers,
            confirm=input,resume_report=None):
    if resume_report:
        report=Path(resume_report).expanduser().resolve()
        directory=report.parent
        runtime=directory/"runtime.json"
        if not report.is_file() or not runtime.is_file():
            raise ValueError("resume requires the saved run.json and runtime.json")
        prior=json.loads(report.read_text(encoding="utf-8"))
        engineering=prior.get("engineering") or {}
        if engineering.get("status")!="VERIFIED_CANDIDATE_PERSISTED":
            raise ValueError("resume refused: engineering candidate unverified")
        configuration=json.loads(runtime.read_text(encoding="utf-8"))
        if base_config:
            updated=json.loads(Path(base_config).read_text(encoding="utf-8"))
            configuration["catalog_model_endpoint"]=updated["catalog_model_endpoint"]
        configuration["resume_verified_engineering"]=True
        configuration["approvals"]["catalog_writeback"]=False
        configuration["catalog_approved_digest"]=None
        from .vertical import run
        print(json.dumps({"phase":"CATALOG_RECOVERY",
                          "run_id":prior["run_id"],"report":str(report)}),flush=True)
        outcome=run(configuration,str(report))
        catalog=outcome.get("catalog") or {}
        if catalog.get("status")!="AWAITING_APPROVAL" or (catalog.get("decision") or {}).get("action")!="CORRECT":
            raise ValueError("catalog recovery not review-ready: "+
                             str(catalog.get("status"))+" report="+str(report))
        review={"candidate_revision":engineering["candidate_revision"]}
    else:
        directory=Path(root).expanduser().resolve()/uuid.uuid4().hex
        workspace=directory/"workspace"
        runtime=directory/"runtime.json"
        report=directory/"run.json"
        print(json.dumps({"phase":"REVIEW_STARTED","report":str(report)}),flush=True)
        stop=threading.Event()
        started=time.monotonic()
        def heartbeat():
            while not stop.wait(15):
                phase="engineering model or validation"
                try:
                    if report.exists():
                        snapshot=json.loads(report.read_text(encoding="utf-8"))
                        if (snapshot.get("engineering") or {}).get("status")=="VERIFIED_CANDIDATE_PERSISTED":
                            phase="catalog model or reconciliation"
                except (OSError, ValueError):
                    pass
                print(json.dumps({"phase":"EXECUTION_IN_PROGRESS","operation":phase,
                                  "elapsed_seconds":int(time.monotonic()-started),
                                  "report":str(report)}),flush=True)
        watcher=threading.Thread(target=heartbeat,daemon=True)
        watcher.start()
        try:
            review=prepare(base_config,workspace,runtime,report)
        except KeyboardInterrupt:
            print(json.dumps({"phase":"INTERRUPTED","report":str(report),
                              "note":"Inspect preserved run; no approval was granted."}),flush=True)
            raise
        finally:
            stop.set()
            watcher.join(timeout=2)
    result=json.loads(report.read_text(encoding="utf-8"))
    catalog=result["catalog"]
    decision=catalog["decision"]
    print(json.dumps({"review":"AWAITING_OPERATOR",
        "run_id":result["run_id"],"candidate_sha":review["candidate_revision"],
        "decision":decision,"findings":catalog["before"]["findings"],
        "digest":catalog["decision_digest"]},indent=2),flush=True)
    print("Operator decision for the exact reviewed LOCAL catalog proposal:",flush=True)
    print("  [1] APPROVE  - sign the bound proposal and publish to local HTTP service",flush=True)
    print("  [2] REJECT   - no publication; retain the run for audit",flush=True)
    print("  [3] DEFER    - no publication; retain the run for later review",flush=True)
    print("Enter 1/approve/approved/accept, 2/reject, or 3/defer.",flush=True)
    entered=confirm("Decision [1/2/3]: ").strip().lower()
    approve_words={"1","approve","approved","accept","accepted","yes"}
    reject_words={"2","reject","rejected","decline","declined","no"}
    defer_words={"3","defer","deferred","later",""}
    # The already-displayed immutable digest is bound into the verified SSH grant
    # by qualify/close. Keep direct digest entry compatible with previous clients.
    if entered in reject_words or entered in defer_words:
        return {"state":"REJECTED" if entered in reject_words else "DEFERRED",
                "run_id":result["run_id"],"report":str(report),
                "private_config":str(runtime),"publication_performed":False,
                "reason":"operator explicitly rejected the proposal" if entered in reject_words
                         else "operator deferred approval"}
    if entered not in approve_words and entered!=catalog["decision_digest"].lower():
        return {"state":"INVALID_DECISION","run_id":result["run_id"],
                "report":str(report),"private_config":str(runtime),
                "publication_performed":False,
                "reason":"unrecognized input; use 1/approve, 2/reject, or 3/defer"}
    return qualify(config=str(runtime),report=str(report),reviewer=reviewer,
                   ssh_private_key=ssh_private_key,allowed_signers=allowed_signers,
                   evidence_output=str(directory/"qualification.json"),
                   workbench_output=str(directory/"workbench.html"),confirmed=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base-config")
    p.add_argument("--resume-report")
    p.add_argument("--run-root",required=True)
    p.add_argument("--reviewer",required=True)
    p.add_argument("--ssh-private-key",required=True)
    p.add_argument("--allowed-signers",required=True)
    a=p.parse_args()
    if not a.base_config and not a.resume_report:
        p.error("provide --base-config or --resume-report")
    try:
        result=session(a.base_config,a.run_root,a.reviewer,
                       a.ssh_private_key,a.allowed_signers,
                       resume_report=a.resume_report)
        print(json.dumps(result))
        return 0 if result.get("scope")=="LOCAL_TWO_MODEL_VERTICAL_PASS" or result.get("state") in ("REJECTED","DEFERRED") else 2
    except (Exception,KeyboardInterrupt) as exc:
        message=str(exc)
        print(json.dumps({"state":"BLOCKED","error_type":type(exc).__name__,
                          "reason":message,
                          "details":"Inspect the preserved run artifacts; no success claimed"}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
