"""One vertical cross-cut acceptance for native workbench lifecycle and pairing."""
import unittest
from agentic_portfolio.workbench_projection import project

class OperatorProjectionTests(unittest.TestCase):
    def event(self, i, kind, parent=None, **payload):
        return {"id":str(i),"sequence":i,"kind":kind,
                "parent_id":str(parent) if parent is not None else None,
                "observation":payload,"label":kind,"run_id":"r","created_ns":i*1000000}

    def report(self):
        return {"run_id":"r","state":"PASS",
                "engineering":{"status":"VERIFIED_CANDIDATE_PERSISTED"},
                "catalog":{"status":"VERIFIED","verified":True,"writeback_performed":True,
                           "decision":{"action":"CORRECT"},"approval_evidence":{"reviewer":"authorized"}}}

    def test_five_phase_lifecycle_and_native_pairing(self):
        events=[
            self.event(1,"execution_started",state="RUNNING"),
            self.event(2,"stage_started",1,name="engineering_real_model_to_git_repair"),
            self.event(3,"git_call_started",2,operation="status"),
            self.event(4,"git_call_completed",3,status=0,duration_ms=12),
            self.event(5,"stage_completed",2,name="engineering_real_model_to_git_repair",outcome="VERIFIED_CANDIDATE_PERSISTED",elapsed_ms=20),
            self.event(6,"stage_started",5,name="catalog_real_model_decision_and_conditional_publication"),
            self.event(7,"model_call_started",6,model="deepseek"),
            self.event(8,"model_call_completed",7,duration_ms=110,usage={"tokens":20}),
            self.event(9,"stage_completed",6,name="catalog_real_model_decision_and_conditional_publication",outcome="AWAITING_APPROVAL"),
            self.event(10,"stage_started",9,name="catalog_real_model_decision_and_conditional_publication"),
            self.event(11,"http_call_started",10,method="PUT"),
            self.event(12,"http_call_completed",11,status=200,duration_ms=9),
            self.event(13,"stage_completed",10,name="catalog_real_model_decision_and_conditional_publication",outcome="VERIFIED"),
        ]
        view=project(self.report(),{"nodes":events})
        self.assertEqual(len(view["lifecycle"]),5)
        self.assertEqual([p["state"] for p in view["lifecycle"]],
                         ["VERIFIED_CANDIDATE_PERSISTED","AWAITING_APPROVAL","SIGNED","WRITE_OBSERVED","VERIFIED"])
        self.assertEqual([s["attempt"] for s in view["stages"]],[1,1,2])
        self.assertEqual(view["stages"][1]["outcome"],"AWAITING_APPROVAL")
        self.assertEqual(view["stages"][2]["outcome"],"VERIFIED")
        self.assertEqual(len(view["operations"]),3)
        self.assertEqual(view["operations"][0]["start_event"],"3")
        self.assertEqual(view["operations"][0]["end_event"],"4")
        self.assertEqual(view["operations"][0]["duration_ms"],12)
        self.assertEqual(view["operations"][2]["stage_event"],"10")
        self.assertEqual(view["operations"][2]["result"],200)

    def test_incomplete_call_is_not_a_success(self):
        view=project({"run_id":"r","state":"RUNNING"},
                     {"nodes":[self.event(1,"stage_started",name="engineering"),
                               self.event(2,"model_call_started",1,model="deepseek")]})
        self.assertEqual(view["operations"][0]["state"],"INCOMPLETE")
        self.assertEqual(view["lifecycle"][2]["state"],"NOT_OBSERVED")
        self.assertEqual(view["lifecycle"][3]["state"],"NOT_OBSERVED")

    def test_orphan_completion_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"orphan"):
            project({"run_id":"r"},{"nodes":[self.event(1,"http_call_completed",status=200)]})

    def test_duplicate_completed_effect_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"multiple completions"):
            project({"run_id":"r"},{"nodes":[self.event(1,"http_call_started",method="PUT"),
                 self.event(2,"http_call_completed",1,status=200),
                 self.event(3,"http_call_completed",1,status=200)]})
