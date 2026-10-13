> **Historical implementation note.** This document describes an earlier development tranche. The controlling operator procedure is [OPERATOR_RELEASE.md](OPERATOR_RELEASE.md), using one fresh instrumented run, a frozen catalog decision, explicit SSH-signed reviewer approval, crash-safe no-blind-retry effect reconciliation, and strict evidence export. Do not use older digest-only or regenerated-proposal commands as production instructions.

# Run closure and evidence workbench

## Actual current state (2026-10-13)

The machine-observed integrated run `31398dd5-ef83-4ac4-8124-efbacf17e44e` has:
- Independently tested, persisted engineering candidate `ed39b89c79094e9b949635bf778df8f9facd9e85`.
- Actual DeepSeek catalog model decision `CORRECT` scoped to price for SKU `P-1`.
- Decision digest `e8b1b13926564ee73ab7965e54812002e7e76e2ce14825f72949a8e34d5c94ca`.
- `BLOCKED_CATALOG` / `AWAITING_APPROVAL`, meaning **no writeback has been observed in this two-model run**.
- 35/35 automated tests passed before this workbench tranche; newer tests are not yet operator-verified.

Do not change the review outcome to `PASS` manually. Do not treat a model decision as publication permission.

## Produce the actual evidence workbench

```bash
cd ~/agentic-systems-portfolio
git pull --ff-only origin main
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m agentic_portfolio.workbench \
  --report artifacts/two-model-review.json \
  --output artifacts/agent-execution-workbench.html
```

Open `artifacts/agent-execution-workbench.html` using your browser or VS Code HTML preview. It is a single self-contained, offline, read-only report. The graph, stage names, durations, code diff, model usage, source digests and blocking states are drawn exclusively from the JSON evidence. No canned or generated event records are used. The workbench is **not** a live-control or approval surface yet; the operator must re-export to see new events.

## Approval-gated local publication

Publishing requires the operator to explicitly approve the **specific reviewed catalog decision**, after reading the observed authoritative price, target price, affected SKU and policy. The previous approval review in chat did not establish approval for this request, so the repository must not set `catalog_writeback=true` by default.

If the operator chooses to authorize the reviewed local mutation, set the following keys in the **existing private runtime JSON file** (not in the public example):

```json
{
  "catalog_approved_digest": "e8b1b13926564ee73ab7965e54812002e7e76e2ce14825f72949a8e34d5c94ca",
  "resume_verified_engineering": true,
  "approvals": {
    "engineering_worktree_mutation": true,
    "catalog_writeback": true
  }
}
```

This is an illustrative fragment, **not an entire replacement configuration**. Preserve the already configured source, published endpoint, model ID, workspace, and authority policy. Run the vertical with the *same* existing output path to preserve the run identity:

```bash
cd ~/agentic-systems-portfolio
PYTHONPATH=src python3 -m agentic_portfolio.vertical \
  --config /tmp/agentic-two-model-review.json \
  --output artifacts/two-model-review.json
RUN_RC=$?
printf 'RUN_RC=%s\n' "$RUN_RC"
```

The system independently calls the model again; this can generate a different rationale, which changes the digest and must block publication. Do **not** bypass the mismatch. In that case review a fresh proposal and its new digest before authorizing. The implementation does not yet persist a frozen proposal for a signature-bound, no-reinference commit. A successful HTTP PUT must subsequently be verified by an independent GET and a zero-discrepancy comparison.

## Definitive closure evidence requirements

A **definitive local two-model PASS** requires an actual operator-produced JSON report with all of:
1. Exact original run ID and previously verified engineering candidate SHA/ref.
2. Actual model decision of `CORRECT`, with approved decision digest and authority policy evidence.
3. `catalog.status=VERIFIED`, `catalog.writeback_performed=true`, `catalog.verified=true`.
4. `catalog.publish_evidence.update_status=200`, and `publish_evidence.after.findings=[]`.
5. A top-level `state=PASS` and no unresolved failed stages.

On such a run, retain a **redacted copy** of the machine-produced evidence in `evidence/` in a separate commit. Never fabricate a passing report or include access tokens in the evidence bundle. The workbench can then be regenerated from that verified JSON.

### Remaining release blockers beyond the local vertical

Authenticated reviewer identity, safe transactional crash recovery around external writes, real customer service connectors, deployment/security/load qualification, and sustained operational outcomes are not established by this local exercise.
