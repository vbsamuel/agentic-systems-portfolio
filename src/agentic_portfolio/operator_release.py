"""One operator command for the entire approved LOCAL vertical qualification.

A verified result requires the real effect, its durable record, journal,
candidate Git object and independent HTTP reread. No partial pass allowed.
"""
import argparse
import json
from pathlib import Path
from .finish import close
from .export_qualification import collect
from .live_e2e import atomic_json
from .workbench import build

def qualify(*,config,report,reviewer,ssh_private_key,allowed_signers,
            evidence_output,workbench_output,confirmed):
    if not confirmed:
        raise ValueError("explicit local publication approval is required")
    completed=close(config,report,reviewer,True,
                    ssh_private_key=ssh_private_key,allowed_signers=allowed_signers)
    if completed["state"]!="PASS":
        raise ValueError("publication did not independently verify: "+
                         str((completed.get("catalog") or {}).get("status")))
    evidence=collect(report)
    atomic_json(evidence_output,evidence)
    build(report,workbench_output)
    return {"scope":evidence["qualification"],"run_id":evidence["run_id"],
            "evidence":str(evidence_output),"workbench":str(workbench_output),
            "external_production_qualification":"NOT_PERFORMED"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    p.add_argument("--report",required=True)
    p.add_argument("--reviewer",required=True)
    p.add_argument("--ssh-private-key",required=True)
    p.add_argument("--allowed-signers",required=True)
    p.add_argument("--evidence",required=True)
    p.add_argument("--workbench",required=True)
    p.add_argument("--confirm-local-publish",action="store_true")
    a=p.parse_args()
    try:
        result=qualify(config=a.config,report=a.report,reviewer=a.reviewer,
                       ssh_private_key=a.ssh_private_key,allowed_signers=a.allowed_signers,
                       evidence_output=a.evidence,workbench_output=a.workbench,
                       confirmed=a.confirm_local_publish)
        print(json.dumps({"status":"PASS",**result}))
        return 0
    except Exception as exc:
        print(json.dumps({"status":"BLOCKED","error":type(exc).__name__+": "+str(exc)}))
        return 2
if __name__=="__main__":
    raise SystemExit(main())
