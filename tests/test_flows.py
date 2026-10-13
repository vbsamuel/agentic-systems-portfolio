import csv
import subprocess
import tempfile
import unittest
from pathlib import Path
from agentic_portfolio.catalog_flow import Cases
from agentic_portfolio.engineering_flow import git_revision, verify_change
from agentic_portfolio.orchestrator import Queue

class ExecutionTests(unittest.TestCase):
    def test_real_git_and_python_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(['git','init','-q',tmp],check=True)
            subprocess.run(['git','-C',tmp,'-c','user.name=Test',
                            '-c','user.email=test@example.com','commit',
                            '--allow-empty','-qm','baseline'],check=True)
            db=Queue(str(Path(tmp)/'jobs.db'))
            rev=git_revision(tmp)
            result=verify_change(db,tmp,rev,rev,
                ('python3','-c','print("verified")'))
            self.assertEqual(result.status,'AWAITING_REVIEW')
            self.assertTrue(db.verify_chain())
            db.review(result.job_id,True,'Reviewer','Independent approval')
            db.db.close()

    def test_failed_test_is_not_approved(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(['git','init','-q',tmp],check=True)
            subprocess.run(['git','-C',tmp,'-c','user.name=Test',
                            '-c','user.email=test@example.com','commit',
                            '--allow-empty','-qm','baseline'],check=True)
            db=Queue(str(Path(tmp)/'jobs.db'))
            rev=git_revision(tmp)
            result=verify_change(db,tmp,rev,rev,
                ('python3','-c','raise SystemExit(3)'))
            self.assertEqual(result.status,'FAILED')
            with self.assertRaises(ValueError):
                db.review(result.job_id,True,'Reviewer','Cannot approve')
            db.db.close()

class ReconciliationTests(unittest.TestCase):
    def test_review_requires_actual_reconciliation(self):
        with tempfile.TemporaryDirectory() as tmp:
            cat=Path(tmp)/'catalog.csv'; page=Path(tmp)/'pages.csv'
            fields=['sku','title','description','price','currency','availability','image_url']
            source=dict(zip(fields,['A','Item','Description','10.00','USD','in stock','image']))
            def write(path,row):
                with open(path,'w',newline='') as fp:
                    writer=csv.DictWriter(fp,fieldnames=fields)
                    writer.writeheader();writer.writerow(row)
            write(cat,source);write(page,dict(source,price='11.00'))
            cases=Cases(str(Path(tmp)/'cases.db'))
            outcome=cases.ingest(str(cat),str(page))
            self.assertEqual(outcome['open_cases'],1)
            fingerprint=cases.db.execute('SELECT fingerprint FROM cases').fetchone()[0]
            with self.assertRaises(ValueError):
                cases.resolve(fingerprint,'Operator','Corrected',str(cat),str(page))
            write(page,source)
            cases.resolve(fingerprint,'Operator','Verified source match',str(cat),str(page))
            self.assertEqual(cases.db.execute(
                "SELECT status FROM cases").fetchone()[0],'RESOLVED')
            cases.db.close()
