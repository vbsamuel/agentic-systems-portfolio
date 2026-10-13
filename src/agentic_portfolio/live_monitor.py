"""Read-only local execution monitor. GET reads actual atomic run evidence.

Loopback-only server; no mutation, approval, inference or fabricated events.
Browser polls /api/run for state changes and reloads the actual report view.
"""
import argparse
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .workbench import PAGE
from .causal_graph import normalize
from .event_journal import EventJournal

LIVE_SCRIPT = """
const notice=document.createElement("span");
notice.className="pill";
notice.textContent="LIVE EVIDENCE · POLLING";
document.querySelector("header").append(notice);
let lastDigest=__DIGEST__;
async function refresh(){
  try{
    const response=await fetch("/api/run",{cache:"no-store"});
    if(!response.ok)throw Error("Evidence unavailable: HTTP "+response.status);
    const body=await response.json();
    notice.textContent="LIVE · "+String(body.state||"UNKNOWN");
    const next=response.headers.get("X-Evidence-Digest");
    if(next && next!==lastDigest)location.reload();
  }catch(error){notice.textContent="EVIDENCE DISCONNECTED";notice.title=String(error)}
}
setInterval(refresh,__POLL_INTERVAL__);
"""

def handler_for(report, interval_ms):
    report=Path(report).resolve()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            return
        def respond(self,status,content_type,body,digest=None):
            self.send_response(status)
            self.send_header("Content-Type",content_type)
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Length",str(len(body)))
            if digest:self.send_header("X-Evidence-Digest",digest)
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            route=urlsplit(self.path).path
            if route not in ("/","/api/run","/api/events"):
                return self.respond(404,"application/json",b'{"error":"not_found"}')
            try:
                raw=report.read_bytes()
                data=json.loads(raw)
                if not isinstance(data,dict) or not data.get("run_id"):
                    raise ValueError("invalid run evidence")
            except (OSError,ValueError,UnicodeError):
                return self.respond(503,"application/json",b'{"error":"evidence_unavailable"}')
            digest=hashlib.sha256(raw).hexdigest()
            if route=="/api/events":
                path=report.with_suffix(".events.sqlite3")
                if not path.is_file():
                    return self.respond(404,"application/json",b'{"error":"journal_not_found"}')
                journal=EventJournal(path)
                try:
                    journal.verify()
                    events=journal.read(data["run_id"])
                except (ValueError, OSError):
                    return self.respond(409,"application/json",b'{"error":"journal_integrity_failure"}')
                payload=json.dumps({"run_id":data["run_id"],"events":events}).encode()
                return self.respond(200,"application/json",payload,hashlib.sha256(payload).hexdigest())
            if route=="/api/run":
                return self.respond(200,"application/json",raw,digest)
            data["execution_graph"]=normalize(data)
            escaped=json.dumps(data,ensure_ascii=True).replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026")
            script=LIVE_SCRIPT.replace("__DIGEST__",json.dumps(digest)).replace("__POLL_INTERVAL__",str(interval_ms))
            page=PAGE.replace("__EVIDENCE__",escaped).replace("</script></body>",script+"</script></body>")
            self.respond(200,"text/html; charset=utf-8",page.encode(),digest)
    return Handler

def create_server(report,host="127.0.0.1",port=8765,interval_ms=1500):
    if host not in ("127.0.0.1","::1"):
        raise ValueError("monitor binding is restricted to loopback")
    if not 250<=interval_ms<=60000:
        raise ValueError("poll interval must be 250..60000 ms")
    return ThreadingHTTPServer((host,port),handler_for(report,interval_ms))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--report",required=True)
    parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--poll-ms",type=int,default=1500)
    args=parser.parse_args()
    server=create_server(args.report,port=args.port,interval_ms=args.poll_ms)
    print(json.dumps({"url":"http://127.0.0.1:"+str(server.server_port),
                      "report":args.report,"read_only":True}),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=="__main__":
    main()
