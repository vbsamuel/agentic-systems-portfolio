"""OpenSSH public-key verified approval grant.

The reviewer signs the exact run/decision/scope/expiry with a personal SSH
private key. The runtime verifies against a pinned allowed_signers file;
it never receives the signer's private key.
"""
import base64
import json
import subprocess
import tempfile
import time
from pathlib import Path
from .approval_grants import grant_message
from .event_journal import canonical

NAMESPACE="agentic-catalog-publish"

def sign(key_path,**fields):
    payload=grant_message(**fields)
    message=canonical(payload).encode()
    key=Path(key_path).expanduser()
    if not key.is_file():
        raise ValueError("reviewer SSH private key not found: "+str(key))
    result=subprocess.run(["ssh-keygen","-Y","sign","-f",str(key),"-n",NAMESPACE],
                          input=message,capture_output=True,timeout=30)
    if result.returncode:
        detail=result.stderr.decode(errors="replace").strip()[-1200:]
        raise ValueError("SSH signing failed (rc="+str(result.returncode)+"): "+detail)
    signature=result.stdout.decode()
    if "BEGIN SSH SIGNATURE" not in signature:
        raise ValueError("SSH signer did not return a signature")
    return {**payload,"auth_type":"openssh","signature":signature}

def verify(allowed_signers,grant,*,run_id,decision_digest,now=None):
    if set(grant)!={"run_id","decision_digest","reviewer","expires_at","scope","auth_type","signature"}:
        raise ValueError("invalid SSH approval shape")
    if grant["auth_type"]!="openssh":
        raise ValueError("unsupported approval algorithm")
    fields={k:grant[k] for k in ("run_id","decision_digest","reviewer","expires_at","scope")}
    message=grant_message(**fields)
    if message["run_id"]!=run_id or message["decision_digest"]!=decision_digest:
        raise ValueError("approval identity mismatch")
    if message["expires_at"]<=int(time.time() if now is None else now):
        raise ValueError("approval expired")
    with tempfile.TemporaryDirectory(prefix="catalog-approval-") as temporary:
        signature=Path(temporary)/"grant.sig"
        signature.write_text(grant["signature"])
        process=subprocess.run(["ssh-keygen","-Y","verify",
            "-f",str(allowed_signers),"-I",message["reviewer"],
            "-n",NAMESPACE,"-s",str(signature)],
            input=canonical(message).encode(),capture_output=True,timeout=20)
    if process.returncode:
        raise ValueError("reviewer SSH signature is not trusted or invalid")
    return True
