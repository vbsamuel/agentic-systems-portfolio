> **Historical implementation note.** This document describes an earlier development tranche. The controlling operator procedure is [OPERATOR_RELEASE.md](OPERATOR_RELEASE.md), using one fresh instrumented run, a frozen catalog decision, explicit SSH-signed reviewer approval, crash-safe no-blind-retry effect reconciliation, and strict evidence export. Do not use older digest-only or regenerated-proposal commands as production instructions.\n\n# Two-model integrated local vertical

The default config `config/local-vertical.example.json` now uses
`catalog_model_driven: true` and `catalog_writeback: false`.
The first run executes the real DeepSeek engineering repair, then invokes
DeepSeek a second time to investigate the observed catalog discrepancy.
It must produce a model decision digest and stop at `BLOCKED_CATALOG`,
with `catalog.status=AWAITING_APPROVAL`. A review-required stop is
**correct**, not a manufactured end-to-end success.

To approve the catalog action, independently inspect the resulting
`catalog.decision`, `catalog.before.findings`, and
`catalog.decision_digest`. Set `catalog_approved_digest` to that exact
digest and `approvals.catalog_writeback=true` in a private copy of the
configuration. A second run reevaluates the decision from live model
inference and checks the current source/version. A mismatch blocks
publication; a match permits conditional HTTP PUT followed by GET and
reconciliation. The engineering candidate is currently regenerated in the
second run, not resumed from its first candidate.

**Important limitations:** This is still not fully restart-safe. A process
crash during publishing can leave the first run's report incomplete; the
conditional HTTP operation is guarded by ETag but is not yet assigned a
durable idempotency key. Approval is a manually supplied digest, not an
authenticated identity-bound signature. Tests mock agent boundaries.
Full production release stays blocked.

## Commands

```bash
cd ~/agentic-systems-portfolio
git pull --ff-only origin main
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m agentic_portfolio.vertical \
  --config config/local-vertical.example.json \
  --output artifacts/two-model-review.json
```

Do **not** blindly use the previous workspace. The example specifies a
persistent project and database. If the catalog record was corrected by an
earlier run, it remains corrected. Choose a fresh distinct workspace in
your private configuration when testing the initial discrepancy workflow.

For the second pass, create a private configuration from the example and
set the explicit action digest only after reviewing the real proposal.
Never commit endpoint credentials or operator authorization secrets.
