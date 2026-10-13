"""Append-only SQLite execution journal with explicit event IDs and hash links.

SQLite WAL provides transactional append and serializes concurrent writers.
Event payloads must exclude secrets; this journal is not a credential vault.
"""
import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True)

class EventJournal:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.path=str(path)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, event_id TEXT NOT NULL UNIQUE, parent_id TEXT, kind TEXT NOT NULL, payload TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL UNIQUE, created_ns INTEGER NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS ix_events_run ON events(run_id,seq)")
    def connect(self):
        db=sqlite3.connect(self.path,timeout=15)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        return db
    def append(self,run_id,kind,payload,parent_id=None):
        if not run_id or not kind or not isinstance(payload,dict):
            raise ValueError("invalid journal event")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if parent_id and not db.execute("SELECT 1 FROM events WHERE event_id=? AND run_id=?",(parent_id,run_id)).fetchone():
                raise ValueError("parent event missing or cross-run")
            last=db.execute("SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
            previous=last[0] if last else "GENESIS"
            event_id=str(uuid.uuid4())
            created_ns=time.time_ns()
            body={"run_id":run_id,"event_id":event_id,"parent_id":parent_id,"kind":kind,
                  "payload":payload,"previous_hash":previous,"created_ns":created_ns}
            digest=hashlib.sha256(canonical(body).encode()).hexdigest()
            db.execute("INSERT INTO events(run_id,event_id,parent_id,kind,payload,previous_hash,event_hash,created_ns) VALUES(?,?,?,?,?,?,?,?)",
                       (run_id,event_id,parent_id,kind,canonical(payload),previous,digest,created_ns))
            return {"event_id":event_id,"event_hash":digest}
    def read(self,run_id=None):
        with self.connect() as db:
            rows=db.execute("SELECT seq,run_id,event_id,parent_id,kind,payload,previous_hash,event_hash,created_ns FROM events ORDER BY seq").fetchall()
        result=[dict(zip(("seq","run_id","event_id","parent_id","kind","payload","previous_hash","event_hash","created_ns"),r)) for r in rows]
        for row in result:row["payload"]=json.loads(row["payload"])
        return [row for row in result if run_id is None or row["run_id"]==run_id]
    def verify(self):
        previous="GENESIS"
        seen={}
        for row in self.read():
            body={k:row[k] for k in ("run_id","event_id","parent_id","kind","payload","previous_hash","created_ns")}
            if row["previous_hash"]!=previous or hashlib.sha256(canonical(body).encode()).hexdigest()!=row["event_hash"]:
                raise ValueError("journal hash chain broken")
            parent=row["parent_id"]
            if parent and seen.get(parent)!=row["run_id"]:
                raise ValueError("invalid causal parent")
            seen[row["event_id"]]=row["run_id"]
            previous=row["event_hash"]
        return True
