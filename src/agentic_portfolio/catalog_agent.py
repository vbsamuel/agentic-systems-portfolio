"""Model-governed catalog decision, with proposal digest and policy-bound action.

The model examines actual HTTP observations. It cannot invent prices or perform
arbitrary tool calls. Its decision is checked against independently observed
discrepancies before any network write occurs.
"""
import hashlib
import json
from .integrated_run import invoke_model
from .http_integration import call
from .catalog import report

def decide(model_config, source, published):
    findings=report(source["body"],published["body"])
    prompt=json.dumps({"instruction":"Return ONLY JSON with keys action, skus, rationale. action must be either CORRECT or ESCALATE. Choose ESCALATE for ambiguous records, missing identities or uncertain evidence. Do not invent product data. skus must be an array of product identifiers affected by the findings.",
        "authoritative_sha256":source["sha256"],
        "published_sha256":published["sha256"],
        "findings":findings["findings"]},sort_keys=True)
    response=invoke_model(model_config,prompt)
    raw=response["response"].strip()
    if raw.startswith("```"):
        raw=raw.split("\n",1)[1].rsplit("```",1)[0].strip()
    decision=json.loads(raw)
    if set(decision)!={"action","skus","rationale"}:
        raise ValueError("catalog agent returned invalid contract")
    if decision["action"] not in ("CORRECT","ESCALATE"):
        raise ValueError("catalog agent returned unauthorized action")
    if not isinstance(decision["rationale"],str) or not decision["rationale"].strip():
        raise ValueError("missing model rationale")
    observed_skus={str(f["sku"]) for f in findings["findings"]}
    if not isinstance(decision["skus"],list) or set(decision["skus"])!=observed_skus:
        raise ValueError("decision not grounded in observed discrepancies")
    if any(f["field"] in ("catalog_record","page") for f in findings["findings"]):
        if decision["action"]!="ESCALATE":
            raise ValueError("identity ambiguity must escalate")
    canonical=json.dumps({"source":source["sha256"],"published":published["sha256"],
        "etag":published["etag"],"decision":decision},sort_keys=True)
    digest=hashlib.sha256(canonical.encode()).hexdigest()
    return {"decision":decision,"decision_digest":digest,
            "model":response["model"],"usage":response.get("usage",{}),
            "response_digest":response["response_digest"],"before":findings}

def model_governed_reconcile(model_config,catalog_endpoint,channel_endpoint,
                             *,writeback=False,approved_digest=None):
    from .http_integration import synchronize
    source=call(catalog_endpoint)
    published=call(channel_endpoint)
    outcome=decide(model_config,source,published)
    decision=outcome["decision"]
    if decision["action"]=="ESCALATE" or not writeback:
        outcome.update(verified=outcome["before"]["status"]=="PASS",
                       writeback_performed=False,status="ESCALATED" if decision["action"]=="ESCALATE" else "AWAITING_APPROVAL")
        return outcome
    if approved_digest!=outcome["decision_digest"]:
        outcome.update(verified=False,writeback_performed=False,status="APPROVAL_MISMATCH")
        return outcome
    # Re-read source and channel before a version-controlled write. A changed
    # observation invalidates the approved decision and requires fresh approval.
    live_source=call(catalog_endpoint)
    live_published=call(channel_endpoint)
    if (live_source["sha256"]!=source["sha256"] or
        live_published["sha256"]!=published["sha256"] or
        live_published["etag"]!=published["etag"]):
        outcome.update(verified=False,writeback_performed=False,status="SOURCE_DRIFT")
        return outcome
    published_result=synchronize(catalog_endpoint,channel_endpoint,writeback=True)
    outcome.update(verified=published_result["verified"],
                   writeback_performed=published_result["writeback_performed"],
                   status="VERIFIED" if published_result["verified"] else "FAILED_VERIFICATION",
                   publish_evidence=published_result)
    return outcome
