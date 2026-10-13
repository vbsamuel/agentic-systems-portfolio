"""Operator CLI: issue an exact, time-bounded publication grant after review.

This is a local HMAC operator mechanism, NOT external identity-provider
authentication. The signing secret is supplied through an environment var.
"""
import argparse
import json
import os
import time
from pathlib import Path
from .approval_grants import issue

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",required=True)
    p.add_argument("--reviewer",required=True)
    p.add_argument("--minutes",type=int,default=10)
    p.add_argument("--output",required=True)
    p.add_argument("--confirm-local-publish",action="store_true",required=True)
    args=p.parse_args()
    evidence=json.loads(Path(args.report).read_text())
    catalog=evidence.get("catalog") or {}
    if catalog.get("status")!="AWAITING_APPROVAL" or catalog.get("decision",{}).get("action")!="CORRECT":
        raise ValueError("only a real reviewed CORRECT proposal may be approved")
    if not 1<=args.minutes<=60:
        raise ValueError("approval duration out of bounds")
    secret=os.environ.get("AGENTIC_APPROVAL_SIGNING_KEY")
    if not secret:
        raise ValueError("AGENTIC_APPROVAL_SIGNING_KEY is not configured")
    grant=issue(secret,run_id=evidence["run_id"],
                decision_digest=catalog["decision_digest"],
                reviewer=args.reviewer,scope="catalog:publish",
                expires_at=int(time.time())+args.minutes*60)
    destination=Path(args.output)
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        raise FileExistsError("grant file must not be overwritten")
    destination.write_text(json.dumps(grant,indent=2)+"\n")
    os.chmod(destination,0o600)
    print(json.dumps({"grant":str(destination),"run_id":grant["run_id"],
                      "decision_digest":grant["decision_digest"],
                      "expires_at":grant["expires_at"]}))
if __name__=="__main__":
    main()
