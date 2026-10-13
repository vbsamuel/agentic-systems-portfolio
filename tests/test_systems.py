import tempfile
import unittest
from pathlib import Path
from agentic_portfolio.catalog import report, reconcile
from agentic_portfolio.orchestrator import Queue

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.row = {'sku':'A','title':'Widget','description':'Useful','price':'10.00','currency':'USD','availability':'in stock','image_url':'img'}
    def test_equal(self):
        self.assertEqual(report([self.row],[self.row])['status'], 'PASS')
    def test_price_discrepancy_requires_review(self):
        changed = dict(self.row,price='11.00')
        result = report([self.row],[changed])
        self.assertEqual(result['status'],'REVIEW_REQUIRED')
        self.assertFalse(result['auto_published'])
    def test_duplicate_fail_closed(self):
        with self.assertRaises(ValueError): reconcile([self.row,self.row],[self.row])
    def test_missing_source_value(self):
        self.assertEqual(reconcile([dict(self.row,price=None)],[self.row])[0].severity,'high')

class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.queue = Queue(str(Path(self.temp.name)/'jobs.db'))
    def tearDown(self):
        self.queue.db.close();self.temp.cleanup()
    def test_single_owner_and_approval(self):
        a = self.queue.enqueue('repo','sha1','fix a'); b = self.queue.enqueue('repo','sha1','fix b')
        self.assertEqual(self.queue.claim(a,'sha1'),'RUNNING')
        self.assertEqual(self.queue.claim(b,'sha1'),'BUSY')
        self.queue.complete(a,'sha2',True)
        self.queue.review(a,True,'QA reviewer','independent check')
        self.assertTrue(self.queue.verify_chain())
        self.assertEqual(self.queue.claim(b,'sha1'),'RUNNING')
    def test_stale_request(self):
        a = self.queue.enqueue('repo','sha1','fix')
        self.assertEqual(self.queue.claim(a,'sha2'),'SOURCE_DRIFT')
        self.assertTrue(self.queue.verify_chain())
    def test_failed_check_cannot_approve(self):
        a = self.queue.enqueue('repo','sha1','fix')
        self.queue.claim(a,'sha1'); self.queue.complete(a,'sha2',False)
        with self.assertRaises(ValueError): self.queue.review(a,True,'QA','looks fine')
    def test_tamper_detected(self):
        a = self.queue.enqueue('repo','sha1','fix')
        self.queue.db.execute("UPDATE events SET payload='{}' WHERE job_id=?",(a,))
        self.assertFalse(self.queue.verify_chain())

if __name__ == '__main__': unittest.main()
