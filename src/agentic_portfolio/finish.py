"""Explicit operator closure of an existing local two-model review.

Requires --confirm-local-publish, a private signing key, a reviewed CORRECT
proposal, and the original report. No approval is inferred from model output.
This is local-key authenticated operation, not an external identity provider.
"""
import argparse
import json
import os
import time
from pathlib import Path
from .approval_grants import issue
from .ssh_approval import sign as ssh_sign, verify as ssh_verify
from .vertical import run

def close(config_path,report_path,reviewer,confirmed,ssh_private_key=None,allowed_signers=None):
    if not confirmed:
        raise ValueError("explicit local publication confirmation is required")
    secret=os.environ.get("AGENTIC_APPROVAL_SIGNING_KEY")
    if not ssh_private_key and (not secret or len(secret)<32):
        raise ValueError("operator SSH private key or local signing secret required")
    if ssh_private_key and not allowed_signers:
        raise ValueError("public allowed-signers trust file required")
    report=Path(report_path)
    reviewed=json.loads(report.read_text(encoding="utf-8"))
    catalog=reviewed.get("catalog") or {}
    if catalog.get("status") not in ("AWAITING_APPROVAL","EFFECT_UNCERTAIN","RETRY_REQUIRES_REVIEW") or catalog.get("decision",{}).get("action")!="CORRECT":
        raise ValueError("only a reviewed CORRECT proposal or its uncertain effect can be recovered")
    config=json.loads(Path(config_path).read_text(encoding="utf-8"))
    if not config.get("catalog_model_driven"):
        raise ValueError("model-driven catalog mode required")
    if not config.get("catalog_authority_policy",{}).get("catalog_is_source_of_truth"):
        raise ValueError("source authority not established")
    fields={"run_id":reviewed["run_id"],
            "decision_digest":catalog["decision_digest"],"reviewer":reviewer,
            "expires_at":int(time.time())+600,"scope":"catalog:publish"}
    if ssh_private_key:
        grant=ssh_sign(ssh_private_key,**fields)
        ssh_verify(allowed_signers,grant,run_id=reviewed["run_id"],
                   decision_digest=catalog["decision_digest"])
        config["approval_allowed_signers_file"]=str(allowed_signers)
    else:
        grant=issue(secret,**fields)
    config["catalog_approval_grant"]=grant
    config["catalog_approved_digest"]=catalog["decision_digest"]
    config["resume_verified_engineering"]=True
    config["approvals"]["catalog_writeback"]=True
    result=run(config,str(report))
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    p.add_argument("--report",required=True)
    p.add_argument("--reviewer",required=True)
    p.add_argument("--confirm-local-publish",action="store_true")
    p.add_argument("--ssh-private-key")
    p.add_argument("--allowed-signers")
    args=p.parse_args()
    try:
        result=close(args.config,args.report,args.reviewer,args.confirm_local_publish,
                     ssh_private_key=args.ssh_private_key,allowed_signers=args.allowed_signers)
        print(json.dumps({"state":result["state"],"run_id":result["run_id"],
                          "catalog_status":(result.get("catalog") or {}).get("status"),
                          "report":args.report}))
        return 0 if result["state"]=="PASS" else 2
    except Exception as exc:
        print(json.dumps({"state":"FAILED","error":type(exc).__name__+": "+str(exc)}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
