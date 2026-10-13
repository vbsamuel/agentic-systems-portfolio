import unittest
from agentic_portfolio.causal_graph import normalize, verify

class CausalGraphTests(unittest.TestCase):
    def test_real_stages_have_stable_ids_and_topological_parents(self):
        report={"run_id":"observed-1","state":"BLOCKED_CATALOG",
                "stages":[{"name":"engineering_real_model_to_git_repair","state":"COMPLETED"},
                          {"name":"resume_verified_engineering","state":"REUSED"},
                          {"name":"catalog_real_model_decision_and_conditional_publication","state":"COMPLETED"}],
                "engineering":{"events":[{"stage":"baseline_reproduction","result":{"exit_code":1}},
                                         {"stage":"model_proposal","model":"actual"},
                                         {"stage":"independent_test_execution","result":{"exit_code":0}}]}}
        graph=normalize(report)
        self.assertTrue(verify(graph))
        self.assertEqual(graph,normalize(report))
        self.assertEqual(len(graph["nodes"]),7)
        self.assertTrue(any(n["edge_type"]=="recorded_substage_order" for n in graph["nodes"]))
        self.assertFalse(any(n["edge_type"]=="verified_causal_span" for n in graph["nodes"]))
    def test_reject_invalid_parent(self):
        with self.assertRaises(ValueError):
            verify({"nodes":[{"id":"a","parent_id":"missing"}]})

if __name__=="__main__":
    unittest.main()
