"""Create and execute one fresh, instrumented two-model REVIEW session.

Review is one stage of the SAME release identity; the approved continuation
uses the same private config and JSON/journal/effect paths. No artificial PASS.
"""
import argparse
import json
import os
from pathlib import Path
from .vertical import run

def prepare(base_config,workspace,private_config,report):
    base=Path(base_config)
    cfg=json.loads(base.read_text(encoding="utf-8"))
    destination=Path(private_config)
    artifact=Path(report)
    target=Path(workspace).expanduser().resolve()
    if destination.exists() or artifact.exists() or target.exists():
        raise FileExistsError("fresh workspace, private config and report paths required")
    if not cfg.get("catalog_model_driven"):
        raise ValueError("model-driven catalog mode is required")
    policy=cfg.get("catalog_authority_policy") or {}
    if policy.get("catalog_is_source_of_truth") is not True:
        raise ValueError("source-of-truth authority policy must be explicit")
    cfg["vertical"]["workspace"]=str(target)
    cfg["resume_verified_engineering"]=False
    cfg["catalog_approved_digest"]=None
    cfg["catalog_approval_grant"]=None
    cfg["approvals"]["catalog_writeback"]=False
    cfg["approvals"]["engineering_worktree_mutation"]=True
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(cfg,indent=2)+"\n",encoding="utf-8")
    os.chmod(destination,0o600)
    result=run(cfg,str(artifact))
    catalog=result.get("catalog") or {}
    if (result.get("state")!="BLOCKED_CATALOG" or
        (result.get("engineering") or {}).get("status")!="VERIFIED_CANDIDATE_PERSISTED" or
        catalog.get("status")!="AWAITING_APPROVAL" or
        catalog.get("decision",{}).get("action")!="CORRECT"):
        raise ValueError("actual two-model review did not reach authorized CORRECT proposal")
    return {"review":"READY","run_id":result["run_id"],
            "decision_digest":catalog["decision_digest"],
            "candidate_revision":result["engineering"]["candidate_revision"],
            "report":str(artifact),"private_config":str(destination)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base-config",required=True)
    p.add_argument("--workspace",required=True)
    p.add_argument("--private-config",required=True)
    p.add_argument("--report",required=True)
    a=p.parse_args()
    try:
        result=prepare(a.base_config,a.workspace,a.private_config,a.report)
        print(json.dumps(result))
        return 0
    except Exception as exc:
        print(json.dumps({"review":"BLOCKED","error":type(exc).__name__+": "+str(exc)}))
        return 2
if __name__=="__main__":
    raise SystemExit(main())
