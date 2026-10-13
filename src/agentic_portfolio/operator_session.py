"""One interactive operator session: actual review, cryptographic approval, effect, evidence.

Starts fresh; no mock models, silent permissions, or synthetic PASS. The
operator confirms the exact model decision digest after reviewing the findings.
"""
import argparse
import json
import uuid
from pathlib import Path
from .operator_review import prepare
from .operator_release import qualify

def session(base_config,root,reviewer,ssh_private_key,allowed_signers,
            confirm=input):
    directory=Path(root).expanduser().resolve()/uuid.uuid4().hex
    workspace=directory/"workspace"
    runtime=directory/"runtime.json"
    report=directory/"run.json"
    review=prepare(base_config,workspace,runtime,report)
    result=json.loads(report.read_text(encoding="utf-8"))
    catalog=result["catalog"]
    decision=catalog["decision"]
    print(json.dumps({"review":"AWAITING_OPERATOR",
        "run_id":result["run_id"],"candidate_sha":review["candidate_revision"],
        "decision":decision,"findings":catalog["before"]["findings"],
        "digest":catalog["decision_digest"]},indent=2),flush=True)
    entered=confirm("To authorize the exact local publication, enter the decision digest: ").strip()
    if entered!=catalog["decision_digest"]:
        return {"state":"AWAITING_APPROVAL","run_id":result["run_id"],
                "report":str(report),"private_config":str(runtime),
                "reason":"operator did not authorize exact proposal"}
    return qualify(config=str(runtime),report=str(report),reviewer=reviewer,
                   ssh_private_key=ssh_private_key,allowed_signers=allowed_signers,
                   evidence_output=str(directory/"qualification.json"),
                   workbench_output=str(directory/"workbench.html"),confirmed=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base-config",required=True)
    p.add_argument("--run-root",required=True)
    p.add_argument("--reviewer",required=True)
    p.add_argument("--ssh-private-key",required=True)
    p.add_argument("--allowed-signers",required=True)
    a=p.parse_args()
    try:
        result=session(a.base_config,a.run_root,a.reviewer,
                       a.ssh_private_key,a.allowed_signers)
        print(json.dumps(result))
        return 0 if result.get("scope")=="LOCAL_TWO_MODEL_VERTICAL_PASS" else 2
    except (Exception,KeyboardInterrupt) as exc:
        print(json.dumps({"state":"BLOCKED","error_type":type(exc).__name__,
                          "details":"Inspect the preserved run artifacts; no success claimed"}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
