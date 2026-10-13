# One integrated vertical: release contract and evidence boundary

**Release unit:** One actual run, not six independent feature demos.

## Immutable acceptance invariants

1. **Event identity:** Every coordinator stage has a native journal event ID, run ID, durable sequence, parent reference, timestamp and hash. Instrumented model/tool child spans must identify the invoking stage and their real input/output digests; mere inferred stage order is not sufficient.
2. **Graph fidelity:** The interactive DAG must derive nodes and parent/dependency edges from journal records, validate causal ancestry and clearly identify unobserved or inferred relationships. Rendering decorative stages does not satisfy this gate.
3. **Single external effect:** A catalog correction must bind the exact observed source digest, published ETag, approved decision, immutable target payload and idempotency key. Crash recovery must reconcile whether the HTTP write already committed *before* any retry. Ambiguous effects must hold for operator review, not replay blindly.
4. **Authenticated review:** An authorized human must approve the exact proposed effect and the grant must bind reviewer identity, run identity, decision digest, scope and expiry. A signature generated from a locally configured HMAC key proves key possession; **identity proof requires a trusted external identity provider**. A plain approval boolean or digest alone is insufficient.
5. **True post-effect verification:** The real model decision, signed grant, HTTP mutation, independent GET, zero-difference comparison and final state must all belong to the same run evidence. Until this is observed, the two-model run is not qualified.
6. **External production interoperability:** Real customer-approved PIM/CMS and source APIs must pass authentication, ETag/conditional write or equivalent versioning, rate-limit and error semantics, production-like failure injection, authorization review, security testing and load/recovery measurement. A local SQLite service is an integration test, **not** qualification against external production infrastructure.

## Work completed and boundaries

- **Previously observed:** Real DeepSeek engineering correction, independently verified Git candidate, local HTTP catalog correction (deterministic path), live two-model catalog `CORRECT` decision, 43/43 automated tests at commit `3cf3cd6` (user-observed).
- **Implemented in subsequent tranche, not yet operator qualified:** HMAC-SHA256 scoped approval grant with exact run/digest/expiry and rejection tests; model-governed publication now requires such a grant in addition to existing source/version checks.
- **Still unclosed:** End-to-end replay-safe external effect ledger, native model/tool-call child spans, journal-driven graph using those native children, proof of a real signed-grant local publication, authenticated identity provider, and actual external deployment qualification.

## Do not bypass the pending decision

The real catalog review is `AWAITING_APPROVAL`; run ID
`31398dd5-ef83-4ac4-8124-efbacf17e44e`, reviewed digest
`e8b1b13926564ee73ab7965e54812002e7e76e2ce14825f72949a8e34d5c94ca`.
The reviewer must examine and explicitly authorize publication of SKU `P-1` at the authoritative local price. No signed grant was supplied for this run.

The HMAC key must never be committed. The current key is a local trust mechanism only, and this release is **blocked** pending a proper authenticated operator flow and corresponding observed result.

## Release evidence to commit after qualification

A *redacted*, machine-generated run report; journal hash-chain verification result; root and child event spans; Git candidate SHA; source/channel digests and ETags; exact decision+grant digest (not signing secret); pre/post HTTP observations; failure-injection results; supported external adapter contract tests; environment and deployed service revision; and an explicit closing or failing gate decision.

**Release classification: NOT QUALIFIED.** Do not claim completed production deployment or 100% release until every invariant is observed in one integrated run.
