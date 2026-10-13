"""SQLite-backed HTTP product service with real authenticated, versioned mutations."""
import argparse
import json
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FIELDS = ("sku", "title", "description", "price", "currency", "availability", "image_url")

def create_db(path, authoritative, published):
    db=sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS products(channel TEXT NOT NULL, sku TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(channel,sku))")
    db.execute("CREATE TABLE IF NOT EXISTS revisions(channel TEXT PRIMARY KEY, revision INTEGER NOT NULL)")
    for channel,rows in (("catalog",authoritative),("published",published)):
        if db.execute("SELECT COUNT(*) FROM products WHERE channel=?",(channel,)).fetchone()[0]:
            continue
        if not rows or any(any(key not in row for key in FIELDS) for row in rows):
            raise ValueError("each initial product requires all fields")
        for row in rows:
            db.execute("INSERT INTO products VALUES(?,?,?)",(channel,row["sku"],json.dumps(row,sort_keys=True)))
        db.execute("INSERT OR IGNORE INTO revisions VALUES(?,?)",(channel,1))
    db.commit()
    db.close()

def serve(path,token,host,port):
    lock=threading.RLock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            return
        def send_json(self,status,body,etag=None):
            raw=json.dumps(body,sort_keys=True).encode()
            self.send_response(status)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(raw)))
            if etag is not None:
                self.send_header("ETag",str(etag))
            self.end_headers()
            self.wfile.write(raw)
        def allowed(self):
            if self.headers.get("Authorization") != "Bearer "+token:
                self.send_json(401,{"error":"unauthorized"})
                return False
            return True
        def channel(self):
            return {"catalog":"catalog","published":"published"}.get(self.path.lstrip("/"))
        def do_GET(self):
            if not self.allowed(): return
            channel=self.channel()
            if channel is None: return self.send_json(404,{"error":"unknown route"})
            with lock, sqlite3.connect(path) as db:
                rows=[json.loads(x[0]) for x in db.execute("SELECT body FROM products WHERE channel=? ORDER BY sku",(channel,))]
                rev=db.execute("SELECT revision FROM revisions WHERE channel=?",(channel,)).fetchone()[0]
            self.send_json(200,rows,rev)
        def do_PUT(self):
            if not self.allowed(): return
            if self.channel()!="published": return self.send_json(403,{"error":"immutable source"})
            try:
                length=int(self.headers.get("Content-Length","0"))
                if not 0 < length <= 2_000_000: return self.send_json(413,{"error":"invalid body size"})
                body=json.loads(self.rfile.read(length))
                records=body["products"]
                if not isinstance(records,list) or not records: raise ValueError("products must be nonempty list")
                ids=[p["sku"] for p in records]
                if len(ids)!=len(set(ids)) or any(any(k not in p for k in FIELDS) for p in records):
                    raise ValueError("invalid product records")
            except (ValueError,TypeError,KeyError,UnicodeDecodeError):
                return self.send_json(400,{"error":"invalid request"})
            with lock,sqlite3.connect(path) as db:
                db.execute("BEGIN IMMEDIATE")
                rev=db.execute("SELECT revision FROM revisions WHERE channel='published'").fetchone()[0]
                if self.headers.get("If-Match")!=str(rev):
                    return self.send_json(412,{"error":"version conflict"},rev)
                for p in records:
                    changed=db.execute("UPDATE products SET body=? WHERE channel='published' AND sku=?",
                                       (json.dumps(p,sort_keys=True),p["sku"]))
                    if changed.rowcount!=1: return self.send_json(409,{"error":"unknown SKU"})
                db.execute("UPDATE revisions SET revision=revision+1 WHERE channel='published'")
                db.commit()
                self.send_json(200,{"updated":len(records)},rev+1)
    server=ThreadingHTTPServer((host,port),Handler)
    return server

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",required=True)
    args=ap.parse_args()
    cfg=json.loads(Path(args.config).read_text())
    data=cfg["service"]
    server=serve(data["database"],data["token"],data["host"],data["port"])
    print(json.dumps({"listen":server.server_address}),flush=True)
    try: server.serve_forever()
    finally: server.server_close()

if __name__=="__main__":
    main()
