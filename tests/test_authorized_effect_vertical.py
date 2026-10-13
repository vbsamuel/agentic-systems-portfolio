"""Real HTTP effect with signed approval; only the external inference output is controlled."""
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from agentic_portfolio.product_service import create_db, serve
from agentic_portfolio.http_integration import Endpoint, call
from agentic_portfolio.catalog_agent import decide, model_governed_reconcile
from agentic_portfolio.approval_grants import issue
from agentic_portfolio.effect_ledger import EffectLedger

def product(price):
    return {"sku":"P-1","title":"Device","description":"Device","price":price,
            "currency":"USD","availability":"in stock","image_url":"/device.jpg"}

class AuthorizedEffectVerticalTests(unittest.TestCase):
    def test_signed_decision_real_put_readback_and_no_replay(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"products.sqlite3"
            create_db(db,[product("100.00")],[product("119.00")])
            server=serve(str(db),"secret","127.0.0.1",0)
            worker=threading.Thread(target=server.serve_forever,daemon=True)
            worker.start()
            try:
                origin="http://127.0.0.1:"+str(server.server_port)
                src=Endpoint(origin+"/catalog","secret")
                dst=Endpoint(origin+"/published","secret")
                policy={"catalog_is_source_of_truth":True,"correctable_fields":["price"]}
                model={"response":'{"action":"CORRECT","skus":["P-1"],"rationale":"Trusted source price differs"}',
                       "model":"controlled-LLM-contract","usage":{},"response_digest":"observed"}
                with patch("agentic_portfolio.catalog_agent.invoke_model",return_value=model):
                    proposal=decide({},call(src),call(dst),policy)
                key="test-only-signature-key-at-least-32-characters"
                grant=issue(key,run_id="integration",decision_digest=proposal["decision_digest"],
                            reviewer="local-tester",expires_at=int(time.time())+100,
                            scope="catalog:publish")
                effects=Path(td)/"effects.sqlite3"
                with patch("agentic_portfolio.catalog_agent.invoke_model",return_value=model):
                    result=model_governed_reconcile({},src,dst,writeback=True,
                        approved_digest=proposal["decision_digest"],
                        authority_policy=policy,approval_grant=grant,
                        approval_key=key,run_id="integration",effect_ledger_path=effects)
                self.assertEqual(result["status"],"VERIFIED")
                self.assertTrue(result["writeback_performed"])
                self.assertEqual(call(dst)["body"][0]["price"],"100.00")
                self.assertEqual(EffectLedger(effects).get(result["effect_id"])["state"],"VERIFIED")
                with self.assertRaisesRegex(ValueError,"already prepared"):
                    EffectLedger(effects).prepare(result["effect_id"],"integration",
                        proposal["decision_digest"],EffectLedger(effects).get(result["effect_id"])["intent"])
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=5)

if __name__=="__main__":
    unittest.main()
