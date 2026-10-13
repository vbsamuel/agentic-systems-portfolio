import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agentic_portfolio.trace_spans import stage_scope
from agentic_portfolio.event_journal import EventJournal
from agentic_portfolio.integrated_run import invoke_model
from agentic_portfolio.causal_graph import native_graph,verify

class Response:
    def __init__(self,value):
        self.value=json.dumps(value).encode()
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,*args):return self.value

class NativeSpanTests(unittest.TestCase):
    def test_actual_inference_boundary_emits_child_ids_and_model_usage(self):
        with tempfile.TemporaryDirectory() as td:
            journal=EventJournal(Path(td)/"trace.db")
            stage=journal.append("run","stage_started",{"name":"catalog"})
            cfg={"model":"actual-model-id","url":"http://127.0.0.1:1234/v1/chat/completions",
                 "system_prompt":"Return JSON","token":"private-not-for-journal",
                 "timeout_seconds":3,"max_response_bytes":5000}
            result={"choices":[{"message":{"content":"{\"action\":\"CORRECT\"}"}}],
                    "usage":{"prompt_tokens":3,"completion_tokens":4}}
            with patch("agentic_portfolio.integrated_run.urlopen",return_value=Response(result)):
                with stage_scope(journal,"run",stage["event_id"]):
                    response=invoke_model(cfg,"real user prompt")
            self.assertEqual(response["model"],"actual-model-id")
            self.assertTrue(journal.verify())
            events=journal.read("run")
            kinds=[e["kind"] for e in events]
            self.assertIn("model_call_started",kinds)
            self.assertIn("model_call_completed",kinds)
            spans=native_graph("run",events)
            self.assertTrue(verify(spans))
            self.assertEqual(spans["semantics"],"native parent IDs recorded at execution time")
            self.assertNotIn("private-not-for-journal",json.dumps(events))
            self.assertEqual(events[-1]["payload"]["usage"]["completion_tokens"],4)

if __name__=="__main__":
    unittest.main()
