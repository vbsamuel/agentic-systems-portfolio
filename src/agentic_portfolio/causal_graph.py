"""Causal event normalization for recorded execution stages.

Only creates edges supported by sequential coordinator ordering or the
recorded engineering sequence. Historical stages lacking parent IDs are
marked inferred_sequence, never asserted as true distributed causality.
"""
import hashlib
import json

def normalize(record):
    run_id=record["run_id"]
    nodes=[]
    def add(kind, label, observation, parent=None, relation=None):
        index=len(nodes)
        identifier=hashlib.sha256((run_id+"|"+str(index)+"|"+kind+"|"+label).encode()).hexdigest()[:24]
        node={"id":identifier,"sequence":index,"kind":kind,"label":label,
              "observation":observation,"parent_id":parent,
              "edge_type":relation,"run_id":run_id}
        nodes.append(node)
        return identifier
    root=add("run","Execution "+run_id,{"state":record.get("state")})
    prev=None
    for stage in record.get("stages",[]):
        name=stage.get("name","unnamed stage")
        branch="engineering" if "engineering" in name else "catalog" if "catalog" in name else "orchestration"
        relation="recorded_stage_order" if prev is not None else "run_membership"
        identifier=add(branch,name,stage,prev or root,relation)
        prev=identifier
    for system in ("engineering",):
        parent=next((n["id"] for n in nodes if n["kind"]==system and "real_model_to_git" in n["label"]),root)
        previous=None
        for event in (record.get(system) or {}).get("events",[]):
            identifier=add("tool",system+" / "+event.get("stage","unnamed"),event,
                           previous or parent,"recorded_substage_order" if previous else "stage_membership")
            previous=identifier
    ids={n["id"] for n in nodes}
    if len(ids)!=len(nodes):
        raise ValueError("duplicate graph identity")
    for node in nodes:
        if node["parent_id"] is not None and node["parent_id"] not in ids:
            raise ValueError("dangling graph edge")
    return {"schema_version":1,"run_id":run_id,"nodes":nodes,
            "semantics":"stage-order graph; historical records lack guaranteed causal span IDs"}

def verify(graph):
    nodes=graph["nodes"]
    known=set()
    for n in nodes:
        if n["id"] in known or (n["parent_id"] is not None and n["parent_id"] not in known):
            raise ValueError("duplicate identity, cycle, or non-topological parent")
        known.add(n["id"])
    return True
