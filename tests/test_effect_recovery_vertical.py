"""Interrupted HTTP response after remote commit is reconciled, never replayed."""
import tempfile
import threading
import time
import unittest
import hashlib
from pathlib import Path
from unittest.mock import patch
from agentic_portfolio.product_service import create_db,serve
from agentic_portfolio.http_integration import Endpoint,call
from agentic_portfolio.effect_ledger import EffectLedger
from agentic_portfolio.approval_grants import issue
from agentic_portfolio.catalog_agent import model_governed_reconcile

def row(price):
    return {"sku":"P-1","title":"A","description":"A","price":price,
            "currency":"USD","availability":"in stock","image_url":"/p.jpg"}

class EffectRecoveryVerticalTests(unittest.TestCase):
    def test_observed_remote_commit_recovers_with_no_second_put_or_model_call(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"catalog.db"
            create_db(db,[row("100.00")],[row("119.00")])
            server=serve(str(db),"authorized","127.0.0.1",0)
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            try:
                base="http://127.0.0.1:"+str(server.server_port)
                src=Endpoint(base+"/catalog","authorized")
                dst=Endpoint(base+"/published","authorized")
                run_id="run-crashed-after-remote-commit"
                digest="reviewed-decision"
                effect_id=hashlib.sha256((run_id+"|"+digest).encode()).hexdigest()
                truth=call(src)
                before=call(dst)
                intent={"desired_products":truth["body"],"previous_products":before["body"],
                        "source_sha256":truth["sha256"],"published_sha256":before["sha256"],
                        "published_etag":before["etag"]}
                ledger_path=Path(td)/"effects.db"
                ledger=EffectLedger(ledger_path)
                ledger.prepare(effect_id,run_id,digest,intent)
                put=call(dst,method="PUT",payload={"products":truth["body"]},version=before["etag"])
                self.assertEqual(put["status"],200)
                # Simulate a crash: no local outcome was persisted.
                self.assertEqual(ledger.get(effect_id)["state"],"PREPARED")
                key="local-test-only-signing-key-32-characters-min"
                grant=issue(key,run_id=run_id,decision_digest=digest,
                            reviewer="operator",scope="catalog:publish",
                            expires_at=int(time.time())+120)
                with patch("agentic_portfolio.catalog_agent.invoke_model") as model:
                    result=model_governed_reconcile({},src,dst,writeback=True,
                        approved_digest=digest,approval_grant=grant,approval_key=key,
                        run_id=run_id,effect_ledger_path=ledger_path)
                    model.assert_not_called()
                self.assertEqual(result["status"],"VERIFIED_RECOVERED")
                self.assertTrue(result["effect_recovered"])
                self.assertFalse(result["writeback_performed"])
                self.assertEqual(ledger.get(effect_id)["state"],"VERIFIED")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

if __name__=="__main__":
    unittest.main()
