"""CSV catalog-to-channel workflow with durable issue registry and explicit closure."""
import csv
import hashlib
import json
import sqlite3
from pathlib import Path
from .catalog import report

def csv_records(path: str) -> list[dict]:
    with open(path, newline='', encoding='utf-8-sig') as fp:
        reader = csv.DictReader(fp)
        if not reader.fieldnames or 'sku' not in reader.fieldnames:
            raise ValueError('CSV requires sku header')
        return list(reader)

class Cases:
    def __init__(self, database: str):
        self.db = sqlite3.connect(database)
        self.db.execute('''CREATE TABLE IF NOT EXISTS cases(
            fingerprint TEXT PRIMARY KEY, sku TEXT NOT NULL, field TEXT NOT NULL,
            expected TEXT, observed TEXT, severity TEXT NOT NULL,
            status TEXT NOT NULL, reviewer TEXT, note TEXT)''')
        self.db.commit()

    def ingest(self, catalog_path: str, channel_path: str) -> dict:
        output = report(csv_records(catalog_path), csv_records(channel_path))
        with self.db:
            for finding in output['findings']:
                raw = json.dumps({key: finding[key] for key in
                                  ('sku','field','expected','observed')},
                                 sort_keys=True)
                fingerprint = hashlib.sha256(raw.encode()).hexdigest()
                self.db.execute('''INSERT OR IGNORE INTO cases
                   (fingerprint,sku,field,expected,observed,severity,status)
                   VALUES(?,?,?,?,?,?,?)''',
                   (fingerprint, finding['sku'], finding['field'],
                    str(finding['expected']), str(finding['observed']),
                    finding['severity'], 'OPEN'))
        output['open_cases'] = self.db.execute(
            "SELECT COUNT(*) FROM cases WHERE status='OPEN'").fetchone()[0]
        return output

    def resolve(self, fingerprint: str, reviewer: str, note: str,
                catalog_path: str, channel_path: str) -> None:
        if not reviewer.strip() or not note.strip():
            raise ValueError('reviewer and rationale required')
        row = self.db.execute(
            'SELECT sku,field,expected,observed,status FROM cases WHERE fingerprint=?',
            (fingerprint,)).fetchone()
        if not row or row[-1] != 'OPEN':
            raise ValueError('unknown or closed discrepancy')
        live = report(csv_records(catalog_path), csv_records(channel_path))
        if any(x['sku'] == row[0] and x['field'] == row[1]
               for x in live['findings']):
            raise ValueError('live discrepancy remains; cannot close')
        with self.db:
            self.db.execute('''UPDATE cases SET status='RESOLVED',
              reviewer=?,note=? WHERE fingerprint=?''', (reviewer,note,fingerprint))
