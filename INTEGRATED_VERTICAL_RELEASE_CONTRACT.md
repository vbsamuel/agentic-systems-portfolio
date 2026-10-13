# Indivisible six-gate integrated vertical — controlling release contract

The release unit is **one actual two-model execution** carried from the
initial failing-code observation through a human-approved HTTP correction
with the **same run ID**, native execution journal, and independently
verifiable qualification output. Isolated tests or attractive UI do not
satisfy this contract.

## First-principles correctness properties

| Mandatory gate | Required invariant | Current implementation |
|---|---|---|
| Native model/tool child spans | Every real inference, Git/validation and HTTP call records a native event ID, invoking-stage parent, input/output digest or measured outcome and duration | `trace_spans.py`; instrumented `integrated_run.py`, `repair_agent.py`, `http_integration.py`, `live_e2e.py` |
| Journal-driven DAG | Nodes and edges come from actual journal event IDs and parent links, not illustrative sequence arrows | `event_journal.py`, `causal_graph.py`, `workbench.py`, `live_monitor.py`; integrity-checked SQLite WAL journal |
| Crash-safe publication reconciliation | Persist the exact proposed effect before PUT; never auto-repeat an uncertain external effect; reconcile actual remote post-crash state | `effect_ledger.py` with FULL synchronous WAL, source digest/ETag binding, no-blind-replay recovery in `catalog_agent.py`, exclusive operator lock |
| Authenticated proposal-bound approval | Reviewer signs run, decision digest, scope and expiry; validation uses independently pinned public-key trust root | `ssh_approval.py`, operator reviewer trust file, frozen reviewed decision and independent re-verification in evidence export |
| Two-model authorized publication | Both actual model decisions, verified Git candidate, signed grant, real conditional HTTP PUT, independent GET and zero residual differences | `operator_session.py` → `operator_review.py` → `operator_release.py` → `export_qualification.py`, one run ID |
| External production integration and qualification | Real customer-authorized HTTPS source/channel APIs, trusted reviewer identity, provider contract tests, failure/recovery, load/security and operational measurement | Generic HTTPS JSON/ETag adapter and read-only `external_conformance.py` exist. **Actual customer production integration and qualification remain unperformed without access and service credentials** |

## One operator command, one release decision

See [OPERATOR_RELEASE.md](OPERATOR_RELEASE.md) for the complete WSL procedure.
The main entry is:

```bash
cd ~/agentic-systems-portfolio

PYTHONPATH=src python3 -m agentic_portfolio.operator_session \
  --base-config config/local-vertical.example.json \
  --run-root artifacts/operator-runs \
  --reviewer local-agentic-reviewer \
  --ssh-private-key "$HOME/.ssh/agentic-approval-ed25519" \
  --allowed-signers "$HOME/.config/agentic-systems-portfolio/allowed_signers"
```

The session executes two real model inferences, produces one frozen
proposal, displays observed differences and **requires the human operator
to type the exact decision digest** before signing/publication. Refusal
leaves the output `AWAITING_APPROVAL`. Approval cannot bypass stale
source and ETag checks, durable prepared-effect checks or independent
post-write verification. A committed but unacknowledged PUT is reconciled
by a fresh read, not repeated blindly.

## Machine acceptance oracle

The strict exporter `export_qualification.collect` refuses to issue
`LOCAL_TWO_MODEL_VERTICAL_PASS` unless all of these are observed:

- Top-level same-run `PASS`, engineering verified Git commit and retained ref.
- Actual catalog `VERIFIED`, observed effect identified, durable ledger
  `VERIFIED`, and independent post-write comparison `PASS` with no findings.
- Native journal hash-chain verified and finalized with **two completed real
  inference spans**, Git validation operations and HTTP operations.
- Original signed SSH reviewer grant independently verified again using the
  reviewer public-key trust file, bound to the identical run and decision.
- Qualification artifact contains source report digest, last journal hash,
  native span counts, effect identity, and public approval attestation.

No "success" branch is permitted for absent evidence or failed invariants.
Tests deliberately include tampering, missing/expired/mismatched approvals,
untrusted source, invalid graph parents, interrupted publication, no
blind retry, concurrent writer rejection, missing spans and missing journal.

## Qualification status — precise boundary

**Observed before this tranche:** 46/46 automated tests PASS on commit
`65b6ac5`; real DeepSeek engineering repair and catalog decision, local
deterministic publication, and read-only monitor worked in prior user
execution. These prove their described stages only.

**New implementation after that evidence:** The fully integrated,
reviewer-signed, effect-ledger-protected operator session, native span
instrumentation and strict final exporter have been committed. The new
regression suite and the newly instrumented full live run **have not
yet been observed passing on the user's WSL machine**.

**External production:** not qualified. No customer PIM/CMS endpoint,
production credential, identity provider or externally measured operation
was provided. A local SQLite-backed service is a legitimate real HTTP
integration test, not proof of a customer production environment.

**Final verdict today:** code implemented for a locally operator-run six-gate
vertical; local acceptance and external production release are **not yet
closed by observed evidence**. Never assert production deployment or
business outcomes without independently verifiable records.
