# Verified local two-model integrated release — 2026-10-13

## Release decision

**LOCAL_TWO_MODEL_VERTICAL_PASS — operator observed.**

The operator executed `python3 -m agentic_portfolio.operator_release` with
a personally created local Ed25519 signing key and pinned public-key trust
file. The command completed and reported:

```text
status=PASS
scope=LOCAL_TWO_MODEL_VERTICAL_PASS
run_id=8b5d0b96-6c30-4ea3-8d01-9919e44052e6
INTEGRATED_RELEASE_RC=0
external_production_qualification=NOT_PERFORMED
```

This is evidence of **local end-to-end qualification** with actual DeepSeek
engineering and catalog inference, a persisted Git repair candidate,
a human-authorized catalog decision, local HTTP mutation, independent
verification, journal/effect persistence and a generated workbench. It is
**not** evidence that this workflow was deployed to a customer production
PIM/CMS or ran against an external customer endpoint.

## Observed operator execution

| Field | Observed value |
|---|---|
| Run ID | `8b5d0b96-6c30-4ea3-8d01-9919e44052e6` |
| Verified engineering candidate SHA | `ce04a85fbc3deabd4b58b1717b825cf10fb9bee8` |
| Catalog model action | `CORRECT` |
| Affected SKU | `P-1` |
| Observed channel price | `119.00` |
| Authoritative catalog price | `100.00` |
| Proposal decision digest | `13e0a8591e8f2e7111f7e6083f7e7f13494e9f2ddff515fb8e498457cefb4523` |
| Reviewer designation | `local-agentic-reviewer` |
| Grant method | Locally generated Ed25519 SSH signing key, trusted public-key file |
| Final command result | `PASS`, return code `0` |
| External production qualification | `NOT_PERFORMED` |

The operator first encountered an empty catalog model response, increased
catalog inference token budget and resumed under the **same run ID** without
repeating the independently verified engineering mutation. DeepSeek then
returned an actual discrepancy-grounded proposal. The initial human approval
prompt was interrupted, so no write was authorized at that point. A later
explicit operator release command first failed because the SSH signing key
and trusted signers file were missing. Those were created and verified locally;
the final command returned PASS.

**Observed execution sequencing:** engineering candidate verified → catalog
model CORRECT → operator-bound SSH grant → guarded local HTTP publication →
readback and effect verification → machine qualification/export → PASS.

## Local artifacts (not committed here)

These artifacts were generated on the operator's WSL machine and their exact
paths were reported in the successful command response:

- `artifacts/operator-runs/4bf56f1eee7b4c89b5a2d041c4e9ff10/run.json`
- `artifacts/operator-runs/4bf56f1eee7b4c89b5a2d041c4e9ff10/run.events.sqlite3`
- `artifacts/operator-runs/4bf56f1eee7b4c89b5a2d041c4e9ff10/run.effects.sqlite3`
- `artifacts/operator-runs/4bf56f1eee7b4c89b5a2d041c4e9ff10/qualification.json`
- `artifacts/operator-runs/4bf56f1eee7b4c89b5a2d041c4e9ff10/workbench.html`

The actual file bytes have **not** been fetched from the operator's machine
or uploaded to GitHub in this documentation commit. Therefore this repository
document records the **operator-reported result and artifact location**,
not an independently inspected, repository-hosted evidence bundle.
No test results, journal hashes, evidence JSON content, or artifact SHA-256
values have been fabricated.

## Automated test qualification

The operator previously observed **68/68 PASS** at `7cc1b88`. After changes
to diagnostics and catalog-only recovery, one regression run showed
**67/68 PASS**: the sole failing assertion expected the old diagnostic
message. That assertion compatibility was fixed at `04108c5`. The
operator subsequently reported that tests passed, but a new full-suite
terminal log with a precise test count is not included in the final
publication response. Do not imply that the production environment was
automatically qualified by this local test run.

## Scope of the closure

The single **local** vertical release contract is closed by the operator's
successful run. The built-in release oracle validates a verified Git
candidate, native model/tool trace records and journal integrity, signed
reviewer authorization, durable effect state, and independent HTTP readback.
The local crash-safe/no-blind-replay behavior also has targeted automated
tests, but this successful run alone does not demonstrate a real machine
power-loss or external distributed failure event.

**Not qualified:** external customer production PIM/CMS API integration,
production credentials and identity management, deployed high availability,
real-provider rate-limit/timeout semantics, load tests, external operational
security assurance, and production change-control approvals.

## Evidence promotion process

To make this result independently reviewable on GitHub, inspect and redact
the generated `qualification.json` before adding a copy to a tracked
`evidence/` path. Prefer a separately named public artifact with only
non-sensitive fields. Do not commit the `runtime.json`, SQLite databases,
source/HTTP credentials, personal SSH private key or unreviewed full
model prompts and product records.

The canonical process is documented in [OPERATOR_RELEASE.md](OPERATOR_RELEASE.md);
the six-gate boundary is documented in
[INTEGRATED_VERTICAL_RELEASE_CONTRACT.md](INTEGRATED_VERTICAL_RELEASE_CONTRACT.md).

**Qualification:** local PASS; external production NOT PERFORMED.
