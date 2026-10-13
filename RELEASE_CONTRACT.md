# Full-system release contract

This is a **release blocker**, not a roadmap checkbox. The existing integration
qualification covers a limited local test environment and is NOT production qualification.

## 18 required capability gates

Every capability must be evaluated independently for **engineering** and **catalog**:

1. `source_integration` — production-authorized source records, revisions, and failure observations
2. `autonomous_investigation` — recorded model/agent observations and independently checked conclusions
3. `model_decisions` — real model invocation, provider/model identity, tool arguments and policy decisions
4. `real_mutations` — observed external Git or publishing-system mutation and mutation IDs
5. `independent_verification` — separate observer and exact before/after acceptance oracle
6. `durable_recovery` — crash/restart and retry evidence without double-application
7. `stage_telemetry` — spans for each agent invocation, external call, decision and result
8. `human_approval` — immutable approval identity, binding, rejection path and enforcement
9. `production_qualification` — qualified target environment, workload, operational error budget and security controls

## Required evidence per gate

A manifest JSON object contains an `evidence` array. Each record must include:

- `check_id`: `engineering:<capability>` or `catalog:<capability>`
- `system`, `capability`, `status` (only `PASS` accepted)
- `source_revision`, `environment`, `run_id`, `independent_verifier`
- `evidence_file` (relative to evidence root) and its `evidence_sha256`
- `measured_result`: real measurements, not an empty object

Execute from the repository root:

```bash
cd ~/agentic-systems-portfolio
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m agentic_portfolio.release_gate \
  --manifest artifacts/release-manifest.json \
  --evidence-root artifacts \
  --output artifacts/release-decision.json
```

Until the manifest and externally observed measurements actually exist, the gate
must refuse release. A schema-valid JSON record is not independent proof of real
production operation. The automated gate verifies completeness, file integrity,
and basic independence metadata. **A trusted verifier, source identity, model
execution trace, authenticated system logs, and operational assessment are also
required** to validate provenance and truthfulness before production acceptance.

No model API credentials, real customer deployments, or production metrics are
shipped in this repository. Values such as endpoint URLs, provider identities,
retry budgets, actor permissions, and deployment targets must come from versioned
configuration and secure secret stores, never example-source constants.

## Current release status

**BLOCKED** — the current implementation does not provide the 18 attested
production-path capabilities. All existing local integration successes remain
valid only within their explicitly stated scope.
