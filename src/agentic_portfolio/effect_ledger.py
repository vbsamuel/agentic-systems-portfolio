"""Durable, single-writer publication effect ledger.

A prepared HTTP effect is recorded *before* issuing PUT. An interrupted
attempt is never blindly replayed. Reconciliation observes the remote
content: desired state -> VERIFIED; unchanged state -> RETRY_REQUIRES_REVIEW;
other state -> UNCERTAIN. Recovery does not make another PUT automatically.
"""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .event_journal import canonical

class EffectLedger:
    def __init__(self,path):
        self.path=str(path)
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        with self.db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS effects (effect_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, decision_digest TEXT NOT NULL, state TEXT NOT NULL, intent TEXT NOT NULL, result TEXT)")
    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=15,isolation_level=None)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            yield db
        finally:
            db.close()
    def prepare(self,effect_id,run_id,decision_digest,intent):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT run_id,decision_digest,intent,state FROM effects WHERE effect_id=?",(effect_id,)).fetchone()
            if row is not None:
                if row[:3]!=(run_id,decision_digest,canonical(intent)):
                    raise ValueError("effect identity collision")
                raise ValueError("effect already prepared; reconcile before retry")
            db.execute("INSERT INTO effects VALUES(?,?,?,?,?,NULL)",
                       (effect_id,run_id,decision_digest,"PREPARED",canonical(intent)))
            db.execute("COMMIT")
    def outcome(self,effect_id,state,result):
        if state not in ("VERIFIED","UNCERTAIN","RETRY_REQUIRES_REVIEW"):
            raise ValueError("invalid effect state")
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT state FROM effects WHERE effect_id=?",(effect_id,)).fetchone()
            if not row or not (row[0]=="PREPARED" or
                (row[0] in ("UNCERTAIN","RETRY_REQUIRES_REVIEW") and state=="VERIFIED")):
                raise ValueError("effect transition prohibited")
            db.execute("UPDATE effects SET state=?,result=? WHERE effect_id=?",
                       (state,canonical(result),effect_id))
            db.execute("COMMIT")
    def get(self,effect_id):
        with self.db() as db:
            row=db.execute("SELECT run_id,decision_digest,state,intent,result FROM effects WHERE effect_id=?",(effect_id,)).fetchone()
        if row is None:return None
        return {"run_id":row[0],"decision_digest":row[1],"state":row[2],
                "intent":json.loads(row[3]),"result":json.loads(row[4]) if row[4] else None}
    def reconcile(self,effect_id,observed_records):
        from .catalog import report
        entry=self.get(effect_id)
        if entry is None:raise ValueError("effect not found")
        expected=entry["intent"]["desired_products"]
        if report(expected,observed_records)["status"]=="PASS":
            state="VERIFIED"
        elif report(entry["intent"]["previous_products"],observed_records)["status"]=="PASS":
            state="RETRY_REQUIRES_REVIEW"
        else:
            state="UNCERTAIN"
        if entry["state"]=="PREPARED" or (
            state=="VERIFIED" and entry["state"] in ("UNCERTAIN","RETRY_REQUIRES_REVIEW")):
            self.outcome(effect_id,state,{"observed_products":observed_records})
        return state
