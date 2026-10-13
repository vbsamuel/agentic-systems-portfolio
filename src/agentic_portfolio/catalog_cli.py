"""CLI for real catalog agent review and explicitly approved publish.

Stage 1 writes a grounded decision with digest. Stage 2 re-invokes the model
and checks the same digest against fresh source observations before publishing.
Any nondeterministic proposal or source change blocks writeback.
"""
import argparse
import json
import sys
from pathlib import Path
from .catalog_agent import model_governed_reconcile
from .http_integration import Endpoint
from .live_e2e import atomic_json

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--approve-digest")
    args=parser.parse_args(argv)
    try:
        config=json.loads(Path(args.config).read_text(encoding="utf-8"))
        endpoints=config["catalog"]
        outcome=model_governed_reconcile(
            config["model_endpoint"],
            Endpoint(**endpoints["authoritative"]),
            Endpoint(**endpoints["published"]),
            writeback=args.approve_digest is not None,
            approved_digest=args.approve_digest)
        atomic_json(args.output,outcome)
        print(json.dumps({"status":outcome["status"],"decision_digest":outcome["decision_digest"],
                          "verified":outcome["verified"],"report":args.output}))
        return 0 if outcome["status"] in ("VERIFIED",) else 2
    except Exception as exc:
        failure={"status":"FAILED","error_type":type(exc).__name__}
        atomic_json(args.output,failure)
        print(json.dumps(failure))
        return 2

if __name__=="__main__":
    sys.exit(main())
