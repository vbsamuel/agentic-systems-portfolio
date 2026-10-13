import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen
from agentic_portfolio.live_monitor import create_server

class LiveMonitorTests(unittest.TestCase):
    def test_live_evidence_changes_without_simulation(self):
        with tempfile.TemporaryDirectory() as td:
            evidence=Path(td)/"run.json"
            evidence.write_text(json.dumps({"run_id":"test-run","state":"RUNNING","stages":[]}))
            server=create_server(evidence,port=0,interval_ms=250)
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            try:
                base="http://127.0.0.1:"+str(server.server_port)
                with urlopen(base+"/api/run",timeout=3) as response:
                    first=json.load(response)
                    old_digest=response.headers["X-Evidence-Digest"]
                self.assertEqual(first["state"],"RUNNING")
                evidence.write_text(json.dumps({"run_id":"test-run","state":"BLOCKED_CATALOG",
                    "catalog":{"status":"AWAITING_APPROVAL"},"stages":[]}))
                with urlopen(base+"/api/run",timeout=3) as response:
                    second=json.load(response)
                    new_digest=response.headers["X-Evidence-Digest"]
                self.assertEqual(second["state"],"BLOCKED_CATALOG")
                self.assertNotEqual(old_digest,new_digest)
                with urlopen(base,timeout=3) as response:
                    page=response.read().decode()
                self.assertIn("LIVE EVIDENCE",page)
                self.assertIn("AWAITING_APPROVAL",page)
                with self.assertRaises(HTTPError) as blocked:
                    urlopen(base+"/other",timeout=3)
                self.assertEqual(blocked.exception.code,404)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
    def test_refuse_non_loopback(self):
        with self.assertRaises(ValueError):
            create_server("ignored",host="0.0.0.0",port=0)

if __name__=="__main__":
    unittest.main()
