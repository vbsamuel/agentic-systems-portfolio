import fcntl
import tempfile
import unittest
from pathlib import Path
from agentic_portfolio.vertical import run

class OperatorLockTests(unittest.TestCase):
    def test_second_operator_cannot_enter_same_vertical(self):
        with tempfile.TemporaryDirectory() as td:
            report=Path(td)/"run.json"
            lock=report.with_suffix(".operator.lock")
            with lock.open("a+") as owner:
                fcntl.flock(owner.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                try:
                    with self.assertRaisesRegex(RuntimeError,"holds this run lock"):
                        run({},str(report))
                finally:
                    fcntl.flock(owner.fileno(),fcntl.LOCK_UN)

if __name__=="__main__":
    unittest.main()
