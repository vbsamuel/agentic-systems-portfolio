"""Authenticated, scoped review grants for one frozen catalog decision.

HMAC-SHA256 attests an operator-issued grant from a private signing key.
The trusted key is provided out-of-band; a matching signature proves key
possession, not individual identity without a separate identity provider.
"""
import hashlib
import hmac
import json
import time
from .event_journal import canonical

def grant_message(*,run_id,decision_digest,reviewer,expires_at,scope):
    if not all(isinstance(x,str) and x for x in (run_id,decision_digest,reviewer,scope)):
        raise ValueError("invalid approval fields")
    if scope!="catalog:publish":
        raise ValueError("wrong grant scope")
    return {"run_id":run_id,"decision_digest":decision_digest,"reviewer":reviewer,
            "expires_at":int(expires_at),"scope":scope}

def issue(key, **fields):
    if not isinstance(key,str) or len(key)<32:
        raise ValueError("signing key must be at least 32 characters")
    message=grant_message(**fields)
    signature=hmac.new(key.encode(),canonical(message).encode(),hashlib.sha256).hexdigest()
    return {**message,"signature":signature}

def verify(key,grant,*,run_id,decision_digest,now=None):
    if not isinstance(grant,dict) or set(grant)!={"run_id","decision_digest","reviewer","expires_at","scope","signature"}:
        raise ValueError("malformed approval grant")
    message=grant_message(**{k:grant[k] for k in ("run_id","decision_digest","reviewer","expires_at","scope")})
    if message["run_id"]!=run_id or message["decision_digest"]!=decision_digest:
        raise ValueError("approval is not bound to this run and proposal")
    if message["expires_at"]<=int(time.time() if now is None else now):
        raise ValueError("approval expired")
    expected=issue(key,**message)["signature"]
    if not hmac.compare_digest(expected,grant["signature"]):
        raise ValueError("approval signature mismatch")
    return True
