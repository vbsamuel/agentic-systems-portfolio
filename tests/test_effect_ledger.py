import tempfile
import unittest
from pathlib import Path
from agentic_portfolio.effect_ledger import EffectLedger

def record(price):
    return {"sku":"P","title":"A","description":"A","price":price,
            "currency":"USD","availability":"in stock","image_url":"a"}

class EffectLedgerTests(unittest.TestCase):
    def test_no_duplicate_effect_and_reconcile_after_crash(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"effects.db"
            ledger=EffectLedger(path)
            before=[record("119.00")]
            desired=[record("100.00")]
            intent={"previous_products":before,"desired_products":desired}
            ledger.prepare("effect-1","run","digest",intent)
            with self.assertRaisesRegex(ValueError,"already prepared"):
                ledger.prepare("effect-1","run","digest",intent)
            self.assertEqual(EffectLedger(path).reconcile("effect-1",desired),"VERIFIED")
            self.assertEqual(ledger.get("effect-1")["state"],"VERIFIED")
    def test_precommit_recovery_requires_review_not_duplicate_write(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=EffectLedger(Path(td)/"effects.db")
            intent={"previous_products":[record("119.00")],"desired_products":[record("100.00")]}
            ledger.prepare("effect-2","run","digest",intent)
            self.assertEqual(ledger.reconcile("effect-2",intent["previous_products"]),"RETRY_REQUIRES_REVIEW")
    def test_uncertain_effect_can_be_verified_by_readback_without_resending(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=EffectLedger(Path(td)/"effects.db")
            intent={"previous_products":[record("119.00")],"desired_products":[record("100.00")]}
            ledger.prepare("effect-4","run","digest",intent)
            ledger.outcome("effect-4","UNCERTAIN",{"cause":"lost_http_ack"})
            self.assertEqual(ledger.reconcile("effect-4",intent["desired_products"]),"VERIFIED")
            self.assertEqual(ledger.get("effect-4")["state"],"VERIFIED")
            with self.assertRaisesRegex(ValueError,"transition prohibited"):
                ledger.outcome("effect-4","UNCERTAIN",{})

    def test_concurrent_state_drift_is_uncertain(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=EffectLedger(Path(td)/"effects.db")
            intent={"previous_products":[record("119.00")],"desired_products":[record("100.00")]}
            ledger.prepare("effect-3","run","digest",intent)
            self.assertEqual(ledger.reconcile("effect-3",[record("105.00")]),"UNCERTAIN")

if __name__=="__main__":
    unittest.main()
