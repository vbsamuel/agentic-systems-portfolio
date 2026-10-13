> **Historical implementation note.** This document describes an earlier development tranche. The controlling operator procedure is [OPERATOR_RELEASE.md](OPERATOR_RELEASE.md), using one fresh instrumented run, a frozen catalog decision, explicit SSH-signed reviewer approval, crash-safe no-blind-retry effect reconciliation, and strict evidence export. Do not use older digest-only or regenerated-proposal commands as production instructions.

# Catalog agent: actual model decision and source-bound publication

The [catalog agent](src/agentic_portfolio/catalog_agent.py) inspects genuine
authenticated catalog and published-channel HTTP observations. It calls a
configured OpenAI-compatible model, validates its JSON decision against the
actual discrepancy SKUs, and computes a SHA-256 decision digest bound to both
source response hashes and the published ETag.

The model cannot set prices directly or issue arbitrary HTTP requests.
Authorized deterministic reconciliation still defines the permitted mutation.
Missing product identities must be escalated.

## Two-stage operator workflow

Use a private configuration file containing `model_endpoint`, as well as
`catalog.authoritative` and `catalog.published` endpoint objects. See
[LIVE_E2E.md](LIVE_E2E.md) for the expected fields.

First create a review proposal without writing:

```bash
cd ~/agentic-systems-portfolio
PYTHONPATH=src python3 -m agentic_portfolio.catalog_cli \
  --config /actual/private/runtime.json \
  --output artifacts/catalog-review.json
```

Inspect the discrepancy evidence, action and decision digest. To explicitly
authorize that exact observed action, pass its digest:

```bash
PYTHONPATH=src python3 -m agentic_portfolio.catalog_cli \
  --config /actual/private/runtime.json \
  --output artifacts/catalog-publication.json \
  --approve-digest THE_REVIEWED_DECISION_DIGEST
```

This second invocation reruns the actual model. If its decision or any source
observation differs from the reviewed digest, no write occurs. A read-back
after the conditional PUT must reconcile to the authoritative data.

**Current limitations:** The operator's digest is not cryptographically
authenticated to an individual reviewer. Execution does not have crash-safe
resume or a durable exactly-once write journal. This catalog agent is not yet
wired into the single-command vertical coordinator, which continues to use
deterministic catalog correction. Do not claim the combined two-model run or
the full 18-gate production release is complete.
