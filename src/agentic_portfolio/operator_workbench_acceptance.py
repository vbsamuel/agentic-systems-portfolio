"""Read-only, integrated operator-workbench acceptance from real run artifacts.

Requalifies native journal, reviewer SSH signature, Git ref and publication
effect before rendering the UI; never executes models or sends HTTP writes.
"""
import argparse
import json
from pathlib import Path
from .export_qualification import collect
from .event_journal import EventJournal
from .causal_graph import native_graph
from .workbench_projection import project
from .workbench import build

def accept(report_path, output_path, allowed_signers):
    source=Path(report_path)
    evidence=collect(source, allowed_signers=allowed_signers, historical=True)
    report=json.loads(source.read_text(encoding="utf-8"))
    journal=EventJournal(source.with_suffix(".events.sqlite3"))
    journal.verify()
    graph=native_graph(evidence["run_id"], journal.read(evidence["run_id"]))
    view=project(report, graph)
    if view["total_native_events"]!=evidence["native_event_count"]:
        raise ValueError("native event denominator mismatch")
    lifecycle={x["key"]:x for x in view["lifecycle"]}
    required={"engineering":"VERIFIED_CANDIDATE_PERSISTED",
              "review":"AWAITING_APPROVAL",
              "approval":"SIGNED",
              "readback":"VERIFIED"}
    for key,state in required.items():
        if lifecycle[key]["state"]!=state:
            raise ValueError("operator lifecycle not closed: "+key+"="+lifecycle[key]["state"])
    if lifecycle["publish"]["state"] not in ("WRITE_OBSERVED","RECOVERED"):
        raise ValueError("publication was not observed or recovered")
    if not any(x["tool"]=="model call" and x["state"]=="COMPLETED" for x in view["operations"]):
        raise ValueError("model span not paired")
    if not any(x["tool"]=="http call" and x["state"]=="COMPLETED" for x in view["operations"]):
        raise ValueError("HTTP span not paired")
    destination=build(source,output_path)
    rendered=destination.read_text(encoding="utf-8")
    for expected in ('"operator_view"', 'id="lifecycle"', 'id="operation-mode"',
                     'id="event-mode"', 'id="detail-summary"'):
        if expected not in rendered:
            raise ValueError("missing workbench surface: "+expected)
    return {"status":"PASS","scope":"LOCAL_OPERATOR_WORKBENCH_VERTICAL",
            "run_id":evidence["run_id"],
            "verified_native_events":evidence["native_event_count"],
            "paired_operations":len(view["operations"]),
            "failed_historical_operations":sum(x["state"]=="FAILED" for x in view["operations"]),
            "stage_attempts":len(view["stages"]),
            "lifecycle":[[x["key"],x["state"]] for x in view["lifecycle"]],
            "workbench":str(destination),
            "external_production_qualification":"NOT_PERFORMED",
            "browser_visual_acceptance":"NOT_AUTOMATICALLY_VERIFIED"}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--report",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--allowed-signers",required=True)
    args=parser.parse_args()
    try:
        result=accept(args.report,args.output,args.allowed_signers)
        print(json.dumps(result,indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status":"BLOCKED","error":type(exc).__name__+": "+str(exc)}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
