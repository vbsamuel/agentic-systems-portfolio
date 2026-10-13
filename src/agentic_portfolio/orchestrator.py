"""SQLite-backed, single-writer engineering work queue with independent review."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
 id INTEGER PRIMARY KEY, repository TEXT NOT NULL, base_revision TEXT NOT NULL,
 requested_action TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'QUEUED',
 result_revision TEXT, review_note TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL, kind TEXT NOT NULL,
 payload TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL,
 created_at TEXT NOT NULL, FOREIGN KEY(job_id) REFERENCES jobs(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_writer_per_repo
 ON jobs(repository) WHERE state='RUNNING';
"""

def utcnow():
    return datetime.now(timezone.utc).isoformat()

class Queue:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute('PRAGMA busy_timeout=5000')
        self.db.executescript(SCHEMA)

    def event(self, job_id, kind, details):
        previous = self.db.execute('SELECT event_hash FROM events ORDER BY id DESC LIMIT 1').fetchone()
        previous_hash = previous[0] if previous else 'GENESIS'
        payload = json.dumps(details, sort_keys=True, separators=(',', ':'))
        stamped = utcnow()
        digest = hashlib.sha256(json.dumps([job_id, kind, payload, previous_hash, stamped]).encode()).hexdigest()
        self.db.execute('INSERT INTO events(job_id,kind,payload,previous_hash,event_hash,created_at) VALUES(?,?,?,?,?,?)',
                        (job_id, kind, payload, previous_hash, digest, stamped))

    def enqueue(self, repository: str, revision: str, action: str) -> int:
        if not all((repository.strip(), revision.strip(), action.strip())):
            raise ValueError('repository, revision and action required')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            cur = self.db.execute('INSERT INTO jobs(repository,base_revision,requested_action,created_at) VALUES(?,?,?,?)',
                                  (repository, revision, action, utcnow()))
            self.event(cur.lastrowid, 'QUEUED', {'repository': repository, 'revision': revision})
            self.db.execute('COMMIT')
            return cur.lastrowid
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def claim(self, job_id: int, current_revision: str) -> str:
        self.db.execute('BEGIN IMMEDIATE')
        try:
            job = self.db.execute('SELECT repository,base_revision,state FROM jobs WHERE id=?', (job_id,)).fetchone()
            if not job or job[2] != 'QUEUED':
                outcome = 'INVALID_STATE'
            elif job[1] != current_revision:
                self.db.execute("UPDATE jobs SET state='REJECTED' WHERE id=?", (job_id,))
                self.event(job_id, 'REJECTED', {'reason': 'SOURCE_DRIFT'})
                outcome = 'SOURCE_DRIFT'
            elif self.db.execute("SELECT 1 FROM jobs WHERE repository=? AND state='RUNNING'", (job[0],)).fetchone():
                outcome = 'BUSY'
            else:
                self.db.execute("UPDATE jobs SET state='RUNNING' WHERE id=?", (job_id,))
                self.event(job_id, 'RUNNING', {'base_revision': current_revision})
                outcome = 'RUNNING'
            self.db.execute('COMMIT')
            return outcome
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def complete(self, job_id: int, result_revision: str, checks_passed: bool) -> None:
        if not result_revision:
            raise ValueError('result revision required')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row = self.db.execute('SELECT state FROM jobs WHERE id=?', (job_id,)).fetchone()
            if not row or row[0] != 'RUNNING':
                raise ValueError('job not running')
            state = 'AWAITING_REVIEW' if checks_passed else 'FAILED'
            self.db.execute('UPDATE jobs SET state=?,result_revision=? WHERE id=?', (state, result_revision, job_id))
            self.event(job_id, state, {'result_revision': result_revision, 'checks_passed': checks_passed})
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def review(self, job_id: int, approved: bool, reviewer: str, note: str) -> None:
        if not reviewer.strip() or not note.strip():
            raise ValueError('named reviewer and reason required')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row = self.db.execute('SELECT state FROM jobs WHERE id=?', (job_id,)).fetchone()
            if not row or row[0] != 'AWAITING_REVIEW':
                raise ValueError('review not permitted in current state')
            state = 'APPROVED' if approved else 'REJECTED'
            self.db.execute('UPDATE jobs SET state=?,review_note=? WHERE id=?', (state, note, job_id))
            self.event(job_id, state, {'reviewer': reviewer, 'note': note})
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def verify_chain(self) -> bool:
        previous = 'GENESIS'
        for jid, kind, payload, prior, digest, stamp in self.db.execute('SELECT job_id,kind,payload,previous_hash,event_hash,created_at FROM events ORDER BY id'):
            expected = hashlib.sha256(json.dumps([jid, kind, payload, prior, stamp]).encode()).hexdigest()
            if prior != previous or digest != expected:
                return False
            previous = digest
        return True
