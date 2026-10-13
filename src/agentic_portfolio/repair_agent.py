"""Model-authored patch execution in a disposable Git worktree.

Uses a real OpenAI-compatible model call. The model must return strict JSON
with path, old_text and new_text. Changes cannot escape the worktree.
A passing baseline is rejected: the workflow must reproduce a real failure.
No shell=True, force-push, or mutation of the source checkout.
"""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from .integrated_run import invoke_model, run_command

def git(cwd, *args):
    result = subprocess.run(["git", "-C", str(cwd), *args],
                            text=True, capture_output=True, check=True, timeout=60)
    return result.stdout.strip()

def parse_proposal(raw):
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    proposal = json.loads(text)
    if set(proposal) != {"path", "old_text", "new_text", "rationale"}:
        raise ValueError("model proposal must have exactly four fields")
    if not all(isinstance(v, str) and v for v in proposal.values()):
        raise ValueError("invalid proposal fields")
    if proposal["old_text"] == proposal["new_text"]:
        raise ValueError("no-op proposal")
    return proposal

def run_isolated_check(command, directory, timeout):
    """Prevent stale Python bytecode from masking a same-size, same-second edit.

    Python timestamp caches can reuse a compiled module when the modification
    timestamp and source length remain unchanged. Each verification invocation
    receives a new PYTHONPYCACHEPREFIX, so imports must compile current source.
    """
    with tempfile.TemporaryDirectory(prefix="agent-bytecode-") as cache:
        environment = os.environ.copy()
        environment["PYTHONPYCACHEPREFIX"] = cache
        result = subprocess.run(command, cwd=directory, timeout=timeout,
                                capture_output=True, text=True, check=False,
                                env=environment)
        return {"command":command, "exit_code":result.returncode,
                "stdout":result.stdout[-16000:], "stderr":result.stderr[-16000:]}


def execute(config, *, approve=False):
    spec = config["engineering"]
    source = Path(spec["repository"]).resolve(strict=True)
    if git(source, "status", "--porcelain"):
        raise ValueError("source repository must be clean")
    head = git(source, "rev-parse", "HEAD")
    allowed = {str(Path(p)) for p in spec["allowed_files"]}
    if not allowed or any(Path(p).is_absolute() or ".." in Path(p).parts for p in allowed):
        raise ValueError("invalid allowlisted paths")
    timeout = int(spec["timeout_seconds"])
    command = spec["validation_command"]
    if not isinstance(command, list) or not command or not all(isinstance(a,str) for a in command):
        raise ValueError("validation_command must be argv")
    events = []
    with tempfile.TemporaryDirectory(prefix="agent-repair-") as temp:
        checkout = Path(temp) / "candidate"
        git(source, "worktree", "add", "--detach", str(checkout), head)
        try:
            started = time.perf_counter()
            baseline = run_isolated_check(command, str(checkout), timeout)
            events.append({"stage":"baseline_reproduction","result":baseline})
            if baseline["exit_code"] == 0:
                raise ValueError("baseline tests already pass; no observed defect")
            files = {}
            for rel in sorted(allowed):
                candidate = (checkout / rel).resolve()
                if not candidate.is_relative_to(checkout.resolve()) or not candidate.is_file() or candidate.is_symlink():
                    raise ValueError("invalid or symbolic-linked source file")
                files[rel] = candidate.read_text(encoding="utf-8")
            prompt = json.dumps({
                "instruction":"Return ONLY a JSON object with keys path, old_text, new_text, rationale. Fix the reproduced failure. path must be one allowed path; old_text must be an exact unique substring. No markdown.",
                "allowed_files":files, "test_command":command, "failure":baseline})
            model = invoke_model(config["model_endpoint"],prompt)
            proposal = parse_proposal(model["response"])
            events.append({"stage":"model_proposal","model":model["model"],
                           "usage":model["usage"],"proposal":proposal,
                           "response_digest":model["response_digest"]})
            rel = proposal["path"]
            if rel not in allowed:
                raise ValueError("model selected unauthorized path")
            file = (checkout / rel).resolve(strict=True)
            if not file.is_relative_to(checkout.resolve()) or file.is_symlink():
                raise ValueError("path traversal or symlink")
            original = file.read_text(encoding="utf-8")
            if original.count(proposal["old_text"]) != 1:
                raise ValueError("proposal precondition not unique")
            if not approve:
                return {"status":"AWAITING_APPROVAL","base_revision":head,
                        "proposal":proposal,"events":events,
                        "mutation_performed":False}
            file.write_text(original.replace(proposal["old_text"],proposal["new_text"],1),
                            encoding="utf-8")
            changed = git(checkout,"diff","--name-only").splitlines()
            if changed != [rel]:
                raise ValueError("mutation escaped declared scope")
            diff = git(checkout,"diff","--",rel)
            events.append({"stage":"actual_mutation","changed_files":changed,"diff":diff})
            check = run_isolated_check(command, str(checkout), timeout)
            events.append({"stage":"independent_test_execution","result":check})
            if check["exit_code"] != 0:
                return {"status":"FAILED_VERIFICATION","base_revision":head,
                        "proposal":proposal,"events":events,"mutation_performed":True}
            if git(source,"rev-parse","HEAD") != head:
                raise ValueError("original repository drifted during execution")
            identity = spec["commit_identity"]
            if not isinstance(identity, dict) or not identity.get("name") or not identity.get("email"):
                raise ValueError("commit_identity requires name and email")
            git(checkout, "add", "--", rel)
            git(checkout, "-c", "user.name="+identity["name"],
                "-c", "user.email="+identity["email"], "commit", "-m",
                "agent: verified correction")
            candidate_revision = git(checkout, "rev-parse", "HEAD")
            if git(source, "rev-parse", "HEAD") != head:
                raise ValueError("source revision drifted before candidate publication")
            ref = "refs/agentic-repairs/" + candidate_revision
            git(source, "update-ref", ref, candidate_revision)
            if git(source, "rev-parse", ref) != candidate_revision:
                raise ValueError("candidate ref persistence failed")
            events.append({"stage":"persistent_candidate",
                           "ref":ref,"candidate_revision":candidate_revision})
            return {"status":"VERIFIED_CANDIDATE_PERSISTED","base_revision":head,
                    "candidate_revision":candidate_revision, "candidate_ref":ref,
                    "proposal":proposal,"events":events,
                    "mutation_performed":True,"duration_seconds":round(time.perf_counter()-started,3),
                    "source_repository_unchanged":git(source,"rev-parse","HEAD")==head}
        finally:
            subprocess.run(["git","-C",str(source),"worktree","remove","--force",str(checkout)],
                           capture_output=True,timeout=60)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--approve",action="store_true",
                        help="Explicitly permit modification ONLY in a disposable worktree")
    args=parser.parse_args()
    out=Path(args.output)
    try:
        result=execute(json.loads(Path(args.config).read_text()),approve=args.approve)
    except Exception as error:
        result={"status":"FAILED","error":type(error).__name__+": "+str(error)}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"output":str(out)}))
    return 0 if result["status"]=="VERIFIED_CANDIDATE_PERSISTED" else 2

if __name__=="__main__":
    raise SystemExit(main())
