"""Integrated operational coordinator for actual model-authored repair and HTTP publishing.

No model, service, or tool result is simulated here. Two independent mutation
paths must qualify for overall success. Evidence is written after each stage,
including on failures. Source checkout remains untouched; repaired candidate
is saved as a Git ref. Catalog writeback requires explicit runtime authority.
"""
import argparse
import subprocess
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .repair_agent import execute as execute_repair
from .http_integration import Endpoint, synchronize
from .catalog_agent import model_governed_reconcile

def atomic_json(path, value):
    target=Path(path)
    target.parent.mkdir(parents=True,exist_ok=True)
    scratch=target.with_name(target.name+".pending")
    with scratch.open("w",encoding="utf-8") as stream:
        json.dump(value,stream,indent=2,default=str)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(scratch,target)

def execute(config, output):
    run_id=str(uuid.uuid4())
    record={"schema_version":1,"run_id":run_id,"started_at":datetime.now(timezone.utc).isoformat(),
            "state":"RUNNING","stages":[],"engineering":None,"catalog":None}
    prior=None
    if config.get("resume_verified_engineering") and Path(output).exists():
        prior=json.loads(Path(output).read_text(encoding="utf-8"))
        candidate=prior.get("engineering") or {}
        if candidate.get("status")!="VERIFIED_CANDIDATE_PERSISTED":
            raise ValueError("resume refused: previous engineering verification missing")
        repo=config["engineering"]["repository"]
        def rev(*parts):
            return subprocess.run(["git","-C",repo,*parts],capture_output=True,
                                  text=True,check=True,timeout=30).stdout.strip()
        if (rev("rev-parse","HEAD")!=candidate["base_revision"] or
            rev("rev-parse",candidate["candidate_ref"])!=candidate["candidate_revision"] or
            rev("status","--porcelain")):
            raise ValueError("resume refused: candidate ref, baseline, or clean source changed")
        record=prior
        record["state"]="RUNNING"
        record["stages"].append({"name":"resume_verified_engineering","state":"REUSED",
                                  "outcome":candidate["candidate_revision"]})
    atomic_json(output,record)
    def step(name, action):
        beginning=time.perf_counter_ns()
        try:
            result=action()
            stage={"name":name,"state":"COMPLETED","elapsed_ms":round((time.perf_counter_ns()-beginning)/1e6,3)}
            if isinstance(result,dict): stage["outcome"]=result.get("status",result.get("verified"))
            record["stages"].append(stage)
            atomic_json(output,record)
            return result
        except Exception as error:
            record["stages"].append({"name":name,"state":"FAILED",
                "error":type(error).__name__+": "+str(error),
                "elapsed_ms":round((time.perf_counter_ns()-beginning)/1e6,3)})
            record["state"]="FAILED"
            atomic_json(output,record)
            raise

    policy=config["approvals"]
    if not isinstance(policy.get("engineering_worktree_mutation"),bool) or not isinstance(policy.get("catalog_writeback"),bool):
        raise ValueError("both explicit approval booleans required")
    # Do not advance if an earlier candidate fails or requires review.
    engineering=(record["engineering"] if prior else
        step("engineering_real_model_to_git_repair",
            lambda:execute_repair(config,approve=policy["engineering_worktree_mutation"])))
    record["engineering"]=engineering
    atomic_json(output,record)
    if engineering["status"]!="VERIFIED_CANDIDATE_PERSISTED":
        record["state"]="BLOCKED_ENGINEERING"
        atomic_json(output,record)
        return record

    catalog=config["catalog"]
    model_catalog = config.get("catalog_model_driven", False)
    if model_catalog:
        catalog_result=step("catalog_real_model_decision_and_conditional_publication",
            lambda:model_governed_reconcile(
                config["model_endpoint"],
                Endpoint(**catalog["authoritative"]),
                Endpoint(**catalog["published"]),
                writeback=policy["catalog_writeback"],
                approved_digest=config.get("catalog_approved_digest")))
    else:
        catalog_result=step("catalog_live_http_reconcile_and_verify",
            lambda:synchronize(Endpoint(**catalog["authoritative"]),
                               Endpoint(**catalog["published"]),
                               writeback=policy["catalog_writeback"]))
    record["catalog"]=catalog_result
    catalog_ok=catalog_result["verified"] and (
        (catalog_result.get("before",{}).get("status")=="PASS" and not model_catalog)
        or catalog_result.get("writeback_performed",False))
    record["state"]="PASS" if catalog_ok else "BLOCKED_CATALOG"
    record["finished_at"]=datetime.now(timezone.utc).isoformat()
    atomic_json(output,record)
    return record

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args(argv)
    try:
        cfg=json.loads(Path(args.config).read_text(encoding="utf-8"))
        result=execute(cfg,args.output)
    except Exception as exc:
        destination=Path(args.output)
        if destination.exists():
            try: artifact=json.loads(destination.read_text(encoding="utf-8"))
            except (ValueError,OSError): artifact={}
        else: artifact={}
        artifact.update(state="FAILED",error=type(exc).__name__+": "+str(exc))
        atomic_json(destination,artifact)
        result=artifact
    print(json.dumps({"state":result["state"],"report":args.output,
                      "run_id":result.get("run_id")}))
    return 0 if result["state"]=="PASS" else 2

if __name__=="__main__":
    sys.exit(main())
