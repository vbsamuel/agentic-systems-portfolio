"""One-command live vertical: real local LM inference, Git mutation, HTTP publication.

The defect fixture and catalog scenario are explicitly configurable. The
service is a SQLite-backed HTTP API, not a mocked adapter. Does not represent
a customer deployment. No remote Git push or external publishing system used.
"""
import argparse
import json
import secrets
import subprocess
import tempfile
import threading
from pathlib import Path

from .live_e2e import execute
from .product_service import create_db, serve

def git(cwd,*args):
    return subprocess.run(["git","-C",str(cwd),*args],text=True,capture_output=True,
                          timeout=30,check=True).stdout.strip()

def run(configuration, output):
    spec=configuration["vertical"]
    root=Path(spec["workspace"]).expanduser().resolve()
    root.mkdir(parents=True,exist_ok=True)
    project=root/"defective_project"
    project.mkdir(exist_ok=True)
    if not (project/".git").exists():
        git(project,"init","-q")
        for filename,source in spec["project_files"].items():
            path=project/filename
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(source,encoding="utf-8")
        git(project,"add",".")
        git(project,"-c","user.name="+spec["commit_identity"]["name"],
            "-c","user.email="+spec["commit_identity"]["email"],
            "commit","-qm","baseline observed defect")
    if git(project,"status","--porcelain"):
        raise ValueError("defective project is not clean")
    database=root/"catalog.db"
    create_db(str(database),spec["authoritative_products"],spec["published_products"])
    token=secrets.token_urlsafe(32)
    server=serve(str(database),token,"127.0.0.1",0)
    worker=threading.Thread(target=server.serve_forever,daemon=True)
    worker.start()
    try:
        base="http://127.0.0.1:"+str(server.server_port)
        config={
            "model_endpoint":configuration["model_endpoint"],
            "catalog_model_endpoint":configuration.get("catalog_model_endpoint",configuration["model_endpoint"]),
            "engineering":{
                "repository":str(project),
                "allowed_files":spec["allowed_files"],
                "validation_command":spec["validation_command"],
                "timeout_seconds":spec["timeout_seconds"],
                "commit_identity":spec["commit_identity"]
            },
            "catalog":{
                "authoritative":{"url":base+"/catalog","token":token,
                                 "timeout_seconds":spec["http_timeout_seconds"]},
                "published":{"url":base+"/published","token":token,
                             "timeout_seconds":spec["http_timeout_seconds"]}
            },
            "approvals":configuration["approvals"],
            "catalog_model_driven":configuration.get("catalog_model_driven",False),
            "catalog_approved_digest":configuration.get("catalog_approved_digest"),
            "catalog_authority_policy":configuration.get("catalog_authority_policy"),
            "catalog_approval_grant":configuration.get("catalog_approval_grant"),
            "catalog_approval_grant_file":configuration.get("catalog_approval_grant_file"),
            "approval_verification_key":configuration.get("approval_verification_key"),
            "resume_verified_engineering":configuration.get("resume_verified_engineering",False)
        }
        result=execute(config,output)
        result["vertical_workspace"]=str(root)
        result["service_database"]=str(database)
        result["execution_scope"]="REAL_LOCAL_GIT_LM_STUDIO_SQLITE_HTTP_NOT_EXTERNAL_PRODUCTION"
        from .live_e2e import atomic_json
        atomic_json(output,result)
        return result
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    try:
        result=run(json.loads(Path(args.config).read_text()),args.output)
        print(json.dumps({"status":result["state"],"report":args.output,
                          "run_id":result["run_id"]}))
        return 0 if result["state"]=="PASS" else 2
    except Exception as error:
        print(json.dumps({"status":"FAILED","error":type(error).__name__+": "+str(error)}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
