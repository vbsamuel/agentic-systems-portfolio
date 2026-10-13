"""Deterministic, read-only operator projection from qualified run and native journal.

No generated success states: every phase cites report/effect evidence or an
actual event ID. Tool pairs use native parent pointers, never adjacency.
"""
from __future__ import annotations

def project(record, graph):
    nodes = graph["nodes"]
    index = {node["id"]: node for node in nodes}
    if len(index) != len(nodes):
        raise ValueError("duplicate native events")
    def stage_parent(node):
        visited = set()
        while node is not None:
            if node["id"] in visited:
                raise ValueError("causal cycle")
            visited.add(node["id"])
            if node["kind"] == "stage_started":
                return node["id"]
            node = index.get(node.get("parent_id"))
        return None
    stages = [n for n in nodes if n["kind"] == "stage_started"]
    outcomes = []
    seen_names = {}
    for n in stages:
        name = str(n["observation"].get("name", "unnamed"))
        count = seen_names.get(name, 0) + 1
        seen_names[name] = count
        matching = [ev for ev in nodes if ev["sequence"] > n["sequence"]
                    and ev["kind"] in ("stage_completed", "stage_failed")
                    and ev["observation"].get("name") == name
                    and not any(s["sequence"] > n["sequence"] and s["sequence"] < ev["sequence"]
                                and s["observation"].get("name") == name for s in stages)]
        end = min(matching, key=lambda ev: ev["sequence"]) if matching else None
        outcomes.append({"id": n["id"], "name": name, "attempt": count,
                         "started_event": n["id"], "finished_event": end["id"] if end else None,
                         "state": "FAILED" if end and end["kind"] == "stage_failed"
                                  else "COMPLETED" if end else "INCOMPLETE",
                         "outcome": (end or {}).get("observation", {}).get("outcome"),
                         "elapsed_ms": (end or {}).get("observation", {}).get("elapsed_ms"),
                         "child_count": sum(stage_parent(ev) == n["id"] for ev in nodes)})
    starts = {n["id"]: n for n in nodes if n["kind"].endswith("_call_started")
              or n["kind"] in ("model_call_started", "validation_started")}
    completed_types = {"git_call_completed", "git_call_failed", "http_call_completed",
                       "http_call_failed", "model_call_completed", "model_call_failed",
                       "validation_completed", "validation_failed"}
    pairs = {}
    for node in nodes:
        if node["kind"] not in completed_types:
            continue
        start = starts.get(node["parent_id"])
        if start is None:
            continue
        if node["id"] in pairs:
            raise ValueError("duplicate tool completion")
        pairs[node["id"]] = start["id"]
    used_start_ids = set(pairs.values())
    operations = []
    for start in starts.values():
        completions = [node for node in nodes if pairs.get(node["id"]) == start["id"]]
        if len(completions) > 1:
            raise ValueError("multiple completions for one native operation")
        end = completions[0] if completions else None
        payload = start["observation"]
        result = end["observation"] if end else {}
        operations.append({
            "id": start["id"], "start_event": start["id"],
            "end_event": end["id"] if end else None,
            "stage_event": stage_parent(start),
            "tool": start["kind"].replace("_started", "").replace("_", " "),
            "state": "FAILED" if end and end["kind"].endswith("_failed") else
                     "COMPLETED" if end else "INCOMPLETE",
            "duration_ms": result.get("duration_ms", result.get("latency_ms", result.get("elapsed_ms"))),
            "result": result.get("status", result.get("exit_code", result.get("error_type"))),
            "input": payload, "output": result,
            "parent_event": start.get("parent_id")})
    for node in nodes:
        if node["kind"] in completed_types and node["id"] not in pairs:
            raise ValueError("orphan tool completion " + node["id"])
    catalog = record.get("catalog") or {}
    engineer = record.get("engineering") or {}
    sequence = [
        {"key": "engineering", "title": "Engineering verification",
         "state": engineer.get("status", "NOT_OBSERVED"),
         "evidence": next((x["id"] for x in outcomes if "engineering" in x["name"]), None)},
        {"key": "review", "title": "Catalog review",
         "state": "AWAITING_APPROVAL" if any(x["outcome"] == "AWAITING_APPROVAL" for x in outcomes)
                   else "OBSERVED" if catalog.get("decision") else "NOT_OBSERVED",
         "evidence": next((x["id"] for x in outcomes if "catalog" in x["name"]), None)},
        {"key": "approval", "title": "Human authorization",
         "state": "SIGNED" if catalog.get("approval_evidence") else "NOT_OBSERVED",
         "evidence": None,
         "source": "catalog.approval_evidence"},
        {"key": "publish", "title": "Conditional HTTP publication",
         "state": "WRITE_OBSERVED" if catalog.get("writeback_performed") else
                  "RECOVERED" if catalog.get("effect_recovered") else "NOT_OBSERVED",
         "evidence": next((x["id"] for x in reversed(outcomes) if "catalog" in x["name"]), None)},
        {"key": "readback", "title": "Independent readback",
         "state": "VERIFIED" if catalog.get("verified") is True else "NOT_VERIFIED",
         "evidence": None,
         "source": "catalog.verified"}]
    return {"schema_version": 1, "run_id": record["run_id"], "stages": outcomes,
            "operations": operations, "lifecycle": sequence,
            "total_native_events": len(nodes),
            "semantics": "Chronological lifecycle positions; causal links only via native parent_event IDs"}
