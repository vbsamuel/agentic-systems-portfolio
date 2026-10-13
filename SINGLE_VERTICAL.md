> **Historical implementation note.** This document describes an earlier development tranche. The controlling operator procedure is [OPERATOR_RELEASE.md](OPERATOR_RELEASE.md), using one fresh instrumented run, a frozen catalog decision, explicit SSH-signed reviewer approval, crash-safe no-blind-retry effect reconciliation, and strict evidence export. Do not use older digest-only or regenerated-proposal commands as production instructions.\n\n# Single cross-cut execution: real LM Studio + Git + SQLite HTTP

This is one executable local vertical: input → model diagnosis and patch → Git
candidate commit → catalog discrepancy → authenticated conditional HTTP update
→ independent reread → final JSON outcome. It executes **one actual local
inference request**, Git subprocesses, unit tests, and a running HTTP service
with a persisted SQLite database. It uses no mock responses in the runtime.

The initial business defect and product discrepancy are configured test
inputs; they are deliberately not presented as historical customer production
events. The service implements actual persistent GET and conditional PUT
behavior but is **not** an external PIM/CMS integration.

## Run in WSL

Use the LM Studio server and loaded DeepSeek model already verified on port
1234. Use a fresh workspace for a new run; if the configured workspace already
contains the project or product database, the program preserves existing data.

```bash
cd ~/agentic-systems-portfolio
git pull --ff-only origin main
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m agentic_portfolio.vertical \
  --config config/local-vertical.example.json \
  --output artifacts/full-vertical.json
RUN_RC=$?
printf 'VERTICAL_RC=%s\n' "$RUN_RC"
python3 -m json.tool artifacts/full-vertical.json
```

The runner reads the configuration file, starts a real in-process localhost HTTP
service, invokes the real model on the observed test failure, applies the model
edit in a detached worktree, reruns tests, saves a Git candidate commit, then
publishes and independently rereads the corrected product record.

The result should be marked successful **only** if:
- baseline tests fail
- a model-authored proposal passes exact source preconditions
- corrected code passes tests
- the candidate Git ref is preserved
- a real conditional HTTP PUT succeeds
- the subsequent GET reconciles to the source-of-truth
- both outcomes appear under the same run ID

The test suite contains one combined integration test that replaces **only the
external inference response**, while exercising real Git and real HTTP+SQLite.
Only the operator command establishes that DeepSeek actually authored the
repair.

## Explicit limitations

This vertical is a working *local integrated qualification*, not production
signoff. Runtime flags do not equal authenticated human approval. The
coordinator has atomic JSON snapshots but no durable recovery FSM; interrupted
operations cannot yet be safely resumed. The Git candidate is not merged.
The HTTP server is a real implementation, but it is local, not an external
customer-owned commerce platform. No customer production availability,
throughput, tenant isolation, signed evidence, or value metrics are claimed.

The separate 18-capability release gate must remain blocked until those
properties are demonstrated.
