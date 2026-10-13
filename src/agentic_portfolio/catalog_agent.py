"""Model-governed catalog decision, with proposal digest and policy-bound action.

The model examines actual HTTP observations. It cannot invent prices or perform
arbitrary tool calls. Its decision is checked against independently observed
discrepancies before any network write occurs.
"""
import hashlib
import json
from .effect_ledger import EffectLedger
from .integrated_run import invoke_model
from .http_integration import call
from .catalog import report
from .approval_grants import verify as verify_approval
from .ssh_approval import verify as verify_ssh_approval

def decide(model_config, source, published, authority_policy=None):
    findings=report(source["body"],published["body"])
    authority_policy=authority_policy or {}
    prompt=json.dumps({"authority_policy":authority_policy,"instruction":"Return ONLY JSON with keys action, skus, rationale. action must be either CORRECT or ESCALATE. Choose CORRECT for a discrepancy only when authority_policy explicitly identifies the authoritative catalog as the trusted record, the affected fields are allowlisted, and identities are unambiguous. Otherwise choose ESCALATE. Do not invent product data. skus must be an array of product identifiers affected by the findings.",
        "authoritative_sha256":source["sha256"],
        "published_sha256":published["sha256"],
        "findings":findings["findings"]},sort_keys=True)
    if frozen_proposal is not None:
        if not isinstance(frozen_proposal,dict) or not isinstance(frozen_proposal.get("decision"),dict):
            raise ValueError("invalid frozen proposal")
        decision=frozen_proposal["decision"]
        response={"model":frozen_proposal.get("model","reviewed-model"),
                  "usage":frozen_proposal.get("usage",{}),
                  "response_digest":frozen_proposal.get("response_digest","reviewed-response")}
    else:
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
    if decision["action"]=="CORRECT":
        fields={f["field"] for f in findings["findings"]}
        if (authority_policy.get("catalog_is_source_of_truth") is not True or
            not fields.issubset(set(authority_policy.get("correctable_fields",[])))):
            raise ValueError("model correction not authorized by source authority policy")
    if any(f["field"] in ("catalog_record","page") for f in findings["findings"]):
        if decision["action"]!="ESCALATE":
            raise ValueError("identity ambiguity must escalate")
    canonical=json.dumps({"source":source["sha256"],"published":published["sha256"],
        "etag":published["etag"],"decision":decision,"authority_policy":authority_policy},sort_keys=True)
    digest=hashlib.sha256(canonical.encode()).hexdigest()
    return {"decision":decision,"decision_digest":digest,
            "model":response["model"],"usage":response.get("usage",{}),
            "response_digest":response["response_digest"],"before":findings}

def model_governed_reconcile(model_config,catalog_endpoint,channel_endpoint,
                             *,writeback=False,approved_digest=None,authority_policy=None,approval_grant=None,approval_key=None,run_id=None,effect_ledger_path=None,frozen_proposal=None,approval_allowed_signers=None):
    def authorize():
        if approval_grant is None or not run_id:
            return False
        try:
            if approval_grant.get("auth_type")=="openssh":
                if not approval_allowed_signers:
                    return False
                verify_ssh_approval(approval_allowed_signers,approval_grant,
                                    run_id=run_id,decision_digest=approved_digest)
            else:
                if not approval_key:
                    return False
                verify_approval(approval_key,approval_grant,run_id=run_id,
                                decision_digest=approved_digest)
        except (ValueError,KeyError,TypeError):
            return False
        return True
    # Before re-invoking any model, reconcile a previously PREPARED effect.
    # A crashed publisher may have committed remotely without recording ACK.
    if writeback and run_id and approved_digest and effect_ledger_path:
        prior_id=hashlib.sha256((run_id+"|"+approved_digest).encode()).hexdigest()
        ledger=EffectLedger(effect_ledger_path)
        prior=ledger.get(prior_id)
        if prior is not None:
            if (prior["run_id"]!=run_id or prior["decision_digest"]!=approved_digest):
                raise ValueError("existing publication intent identity mismatch")
            if not authorize():
                return {"status":"AUTHENTICATED_APPROVAL_REJECTED",
                        "verified":False,"writeback_performed":False}
            latest_source=call(catalog_endpoint)
            latest_channel=call(channel_endpoint)
            if latest_source["sha256"]!=prior["intent"]["source_sha256"]:
                return {"status":"SOURCE_DRIFT","verified":False,"writeback_performed":False}
            state=ledger.reconcile(prior_id,latest_channel["body"])
            if state=="VERIFIED":
                return {"status":"VERIFIED_RECOVERED","verified":True,
                        "writeback_performed":False,"effect_recovered":True,
                        "effect_id":prior_id,"decision_digest":approved_digest,
                        "publish_evidence":{"after":report(latest_source["body"],latest_channel["body"]),
                                            "observed_digest":latest_channel["sha256"]}}
            return {"status":state,"verified":False,"writeback_performed":False,
                    "effect_id":prior_id,"decision_digest":approved_digest}
    source=call(catalog_endpoint)
    published=call(channel_endpoint)
    outcome=decide(model_config,source,published,authority_policy=authority_policy,
                   frozen_proposal=frozen_proposal)
    if frozen_proposal is not None and frozen_proposal.get("decision_digest")!=outcome["decision_digest"]:
        raise ValueError("frozen proposal no longer matches source observations")
    decision=outcome["decision"]
    if decision["action"]=="ESCALATE" or not writeback:
        outcome.update(verified=outcome["before"]["status"]=="PASS",
                       writeback_performed=False,status="ESCALATED" if decision["action"]=="ESCALATE" else "AWAITING_APPROVAL")
        return outcome
    if approved_digest!=outcome["decision_digest"]:
        outcome.update(verified=False,writeback_performed=False,status="APPROVAL_MISMATCH")
        return outcome
    if not authorize():
        outcome.update(verified=False,writeback_performed=False,
                       status="AUTHENTICATED_APPROVAL_REJECTED")
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
    if not effect_ledger_path:
        outcome.update(verified=False,writeback_performed=False,status="EFFECT_LEDGER_REQUIRED")
        return outcome
    ledger=EffectLedger(effect_ledger_path)
    effect_id=hashlib.sha256((run_id+"|"+outcome["decision_digest"]).encode()).hexdigest()
    ledger.prepare(effect_id,run_id,outcome["decision_digest"],
                   {"desired_products":[dict(p) for p in live_source["body"]],
                    "previous_products":[dict(p) for p in live_published["body"]],
                    "source_sha256":live_source["sha256"],
                    "published_sha256":live_published["sha256"],
                    "published_etag":live_published["etag"]})
    outcome["effect_id"]=effect_id
    try:
        update=call(channel_endpoint,method="PUT",
                    payload={"products":[dict(p) for p in live_source["body"]]},
                    version=live_published["etag"])
        confirmed=call(channel_endpoint)
        final=report(live_source["body"],confirmed["body"])
        if final["status"]!="PASS":
            ledger.outcome(effect_id,"UNCERTAIN",{"update_status":update["status"],
                                                  "observed_digest":confirmed["sha256"]})
            outcome.update(verified=False,writeback_performed=True,status="FAILED_VERIFICATION",
                           publish_evidence={"update_status":update["status"],"after":final})
            return outcome
        ledger.outcome(effect_id,"VERIFIED",{"update_status":update["status"],
                                            "observed_digest":confirmed["sha256"]})
        outcome.update(verified=True,writeback_performed=True,status="VERIFIED",
                       publish_evidence={"update_status":update["status"],"after":final,
                                         "catalog_digest":live_source["sha256"],
                                         "channel_digest_after":confirmed["sha256"]})
        return outcome
    except Exception:
        outcome.update(verified=False,writeback_performed=False,status="EFFECT_UNCERTAIN")
        return outcome

