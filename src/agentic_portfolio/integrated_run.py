"""One integrated execution of two configured real model-backed agents.

Requires an OpenAI-compatible chat-completions endpoint, a Git worktree, a
catalog GET endpoint, and a channel GET/PUT endpoint. All inputs come from a
single JSON configuration; no fake model fallback or generated success.
Model proposals are recommendations; external mutation requires explicit
operator approval of the exact proposed action.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from .catalog import report
from .engineering_flow import git_revision
from .http_integration import Endpoint, call
from .trace_spans import emit as trace_emit


def invoke_model(config, prompt):
    request = {"model":config["model"], "messages":[
        {"role":"system","content":config["system_prompt"]},
        {"role":"user","content":prompt}], "temperature":0}
    if "max_tokens" in config:
        request["max_tokens"]=int(config["max_tokens"])
    data=json.dumps(request).encode()
    req=Request(config["url"],data=data,method="POST",
                headers={"Content-Type":"application/json",
                         "Authorization":"Bearer "+config["token"]})
    span=trace_emit("model_call_started",{"model":config["model"],"prompt_sha256":hashlib.sha256(prompt.encode()).hexdigest()})
    started=time.perf_counter_ns()
    try:
        with urlopen(req,timeout=config["timeout_seconds"]) as response:
            raw=response.read(config["max_response_bytes"]+1)
            if len(raw)>config["max_response_bytes"]:
                raise ValueError("model response exceeds configured byte limit")
            result=json.loads(raw)
        answer=result["choices"][0]["message"]["content"]
        if not isinstance(answer,str) or not answer.strip():
            raise ValueError("empty model response")
    except Exception as error:
        trace_emit("model_call_failed",{"model":config["model"],
                   "error_type":type(error).__name__,
                   "duration_ms":round((time.perf_counter_ns()-started)/1e6,3)},
                   parent_id=span)
        raise
    trace_emit("model_call_completed",{"model":config["model"],"latency_ms":round((time.perf_counter_ns()-started)/1e6,3),
                 "response_sha256":hashlib.sha256(answer.encode()).hexdigest(),
                 "usage":result.get("usage",{})},parent_id=span)
    return {"response":answer,"response_digest":hashlib.sha256(answer.encode()).hexdigest(),
            "model":config["model"],"usage":result.get("usage",{})}


def run_command(argv,cwd,timeout):
    result=subprocess.run(argv,cwd=cwd,timeout=timeout,capture_output=True,text=True,check=False)
    return {"command":argv,"exit_code":result.returncode,
            "stdout":result.stdout[-16000:],"stderr":result.stderr[-16000:]}


def stage(events,system,name,operation):
    start=time.perf_counter_ns()
    timestamp=datetime.now(timezone.utc).isoformat()
    try:
        observation=operation()
        events.append({"system":system,"stage":name,"started":timestamp,
                       "duration_ms":round((time.perf_counter_ns()-start)/1e6,3),
                       "status":"PASS","observation":observation})
        return observation
    except Exception as exc:
        events.append({"system":system,"stage":name,"started":timestamp,
                       "duration_ms":round((time.perf_counter_ns()-start)/1e6,3),
                       "status":"FAILED","error":type(exc).__name__+": "+str(exc)})
        raise


def execute(config):
    events=[]
    run_id=str(uuid.uuid4())
    repo=str(Path(config["engineering"]["repository"]).resolve(strict=True))
    validation=config["engineering"]["validation_command"]
    max_time=config["engineering"]["timeout_seconds"]
    source=stage(events,"engineering","capture_source",
                 lambda:{"revision":git_revision(repo),"repository":repo})
    diagnostic=stage(events,"engineering","reproduce_defect",
                     lambda:run_command(validation,repo,max_time))
    analysis=stage(events,"engineering","model_investigation",
                   lambda:invoke_model(config["model_endpoint"],json.dumps({
                       "task":"Diagnose the actual observed engineering failure and propose bounded repair steps. Do not claim modifications occurred.",
                       "git_revision":source["revision"],"validation":diagnostic})))
    catalog_ep=Endpoint(**config["catalog"]["authoritative"])
    channel_ep=Endpoint(**config["catalog"]["published"])
    truth=stage(events,"catalog","fetch_authoritative",lambda:call(catalog_ep))
    observed=stage(events,"catalog","fetch_published",lambda:call(channel_ep))
    findings=stage(events,"catalog","reconcile",
                   lambda:report(truth["body"],observed["body"]))
    catalog_analysis=stage(events,"catalog","model_investigation",
                   lambda:invoke_model(config["model_endpoint"],json.dumps({
                       "task":"Investigate these observed catalog discrepancies and propose safe remediation. Do not claim updates occurred.",
                       "findings":findings})))
    approval=config.get("approved_actions",{})
    engineering_mutation={"status":"NOT_AUTHORIZED"}
    if approval.get("engineering_validation"):
        engineering_mutation=stage(events,"engineering","independent_verification",
            lambda:run_command(validation,repo,max_time))
    catalog_mutation={"status":"NOT_AUTHORIZED"}
    if approval.get("catalog_writeback"):
        if not observed["etag"]:
            raise ValueError("catalog mutation requires If-Match version")
        if not findings["findings"]:
            catalog_mutation={"status":"NO_CHANGE_NEEDED"}
        else:
            if any(f["field"] in ("page","catalog_record") for f in findings["findings"]):
                raise ValueError("catalog identities ambiguous; automatic writeback denied")
            products={p["sku"]:dict(p) for p in observed["body"]}
            for product in truth["body"]:
                if product["sku"] not in products:
                    raise ValueError("SKU mismatch")
                for field in ("title","description","price","currency","availability","image_url"):
                    if field not in product or product[field] is None:
                        raise ValueError("missing authoritative value: "+field)
                    products[product["sku"]][field]=product[field]
            catalog_mutation=stage(events,"catalog","conditional_publish",
                lambda:call(channel_ep,method="PUT",
                    payload={"products":list(products.values())},
                    version=observed["etag"]))
    post=stage(events,"catalog","independent_post_observation",lambda:call(channel_ep))
    post_result=stage(events,"catalog","verify_post_observation",
                      lambda:report(truth["body"],post["body"]))
    final_rev=stage(events,"engineering","verify_final_source_revision",
                    lambda:git_revision(repo))
    engineering_ok=(diagnostic["exit_code"]==0
                    and final_rev==source["revision"]
                    and engineering_mutation.get("exit_code",1)==0)
    catalog_ok=(post_result["status"]=="PASS"
                and (not findings["findings"] or catalog_mutation.get("status")==200))
    return {"run_id":run_id,"status":"PASS" if engineering_ok and catalog_ok else "BLOCKED",
            "engineering":{"status":"PASS" if engineering_ok else "BLOCKED",
                           "initial_exit_code":diagnostic["exit_code"],
                           "initial_revision":source["revision"],
                           "final_revision":final_rev,
                           "model_response_digest":analysis["response_digest"]},
            "catalog":{"status":"PASS" if catalog_ok else "BLOCKED",
                       "initial_findings":findings["findings"],
                       "remaining_findings":post_result["findings"],
                       "model_response_digest":catalog_analysis["response_digest"],
                       "mutation":catalog_mutation},
            "events":events,
            "qualification":"INTEGRATED_CONFIGURED_AGENT_RUN; NOT_PRODUCTION_QUALIFICATION"}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    destination=Path(args.output)
    events=[]
    try:
        config=json.loads(Path(args.config).read_text())
        result=execute(config)
    except Exception as exc:
        result={"status":"FAILED","error":type(exc).__name__+": "+str(exc),
                "qualification":"NOT_QUALIFIED"}
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,indent=2,default=str)+"\n")
    print(json.dumps({"status":result["status"],"report":str(destination)}))
    return 0 if result["status"]=="PASS" else 2


if __name__=="__main__":
    sys.exit(main())
