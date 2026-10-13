import unittest
from agentic_portfolio.repair_agent import parse_proposal

class ProposalContractTests(unittest.TestCase):
    def test_valid_structured_edit(self):
        p=parse_proposal('{"path":"app.py","old_text":"x+1","new_text":"x+2","rationale":"fix contract"}')
        self.assertEqual(p["path"],"app.py")
    def test_reject_noop(self):
        with self.assertRaises(ValueError):
            parse_proposal('{"path":"app.py","old_text":"x+1","new_text":"x+1","rationale":"nothing"}')
    def test_reject_extra_privileged_keys(self):
        with self.assertRaises(ValueError):
            parse_proposal('{"path":"app.py","old_text":"x+1","new_text":"x+2","rationale":"fix","execute":"rm -rf"}')
    def test_reject_non_json(self):
        with self.assertRaises(ValueError):
            parse_proposal('Patch the code manually.')
if __name__=="__main__":
    unittest.main()
