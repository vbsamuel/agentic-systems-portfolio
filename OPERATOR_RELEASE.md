# Operator release: one integrated two-agent vertical

**Release unit:** One real run from defect and catalog inputs through two model
inferences, independently verified code correction, an exact human-reviewed
catalog decision, a durable HTTP effect, independent post-write verification,
native event tracing and one machine-generated qualification artifact.

**Controlling implementation:** `agentic_portfolio.operator_session`. Do
not qualify six isolated demos or claim a production release because individual
unit tests pass.

## 1. Requirements and safety

This guide runs the bundled **real local SQLite-backed HTTP service** and
your configured LM Studio model. It will mutate the published price in that
local service only after you explicitly authorize the displayed digest.
It does **not** connect to or mutate a customer website by default.

Your previously recorded two-model run
`31398dd5-ef83-4ac4-8124-efbacf17e44e` remains legitimate historical
evidence, but it predates native inference and tool child spans. It cannot
be retroactively represented as a complete six-gate native trace. For
definitive qualification, create one new instrumented session and approve
the subsequent publication **under that same run ID**.

The last operator-confirmed test baseline was **46/46 PASS**, before this
new tranche. These new changes must be independently run and inspected on WSL.

## 2. One-time reviewer trust setup

Use an existing SSH signing key whose public key is trusted by your
organization, or create a dedicated, passphrase-protected personal key:

```bash
cd ~/agentic-systems-portfolio

mkdir -p "$HOME/.ssh" "$HOME/.config/agentic-systems-portfolio"
chmod 700 "$HOME/.ssh"

ssh-keygen -t ed25519 -f "$HOME/.ssh/agentic-approval-ed25519" \
  -C "local-agentic-reviewer"

printf 'local-agentic-reviewer %s\n' \
  "$(cat "$HOME/.ssh/agentic-approval-ed25519.pub")" \
  > "$HOME/.config/agentic-systems-portfolio/allowed_signers"

chmod 600 "$HOME/.config/agentic-systems-portfolio/allowed_signers"
```

Do not overwrite an existing private key. A passphrase is recommended.
The runtime checks the private-key signature against the public-key trust
file and binds it to reviewer ID, run ID, scope, exact proposal digest and
expiry. A reviewer-held SSH key is much stronger than an unchecked checkbox.
This does **not** substitute for independently established enterprise
identity/SSO, role provisioning and revocation.

## 3. Qualify current code before operating

```bash
cd ~/agentic-systems-portfolio

git pull --ff-only origin main
PULL_RC=$?

if [ "$PULL_RC" -eq 0 ]; then
    PYTHONPATH=src python3 -m unittest discover -s tests -v
    TEST_RC=$?
    printf '\nTEST_RC=%s\n' "$TEST_RC"
else
    printf '\nPULL_RC=%s\n' "$PULL_RC"
fi
```

**Stop before publication if any test fails.** The shell remains open.
Do not use `set -e` or `exit 1`.

## 4. One executable vertical and one human approval

Check the configured LM Studio model is loaded using `lms ps`.
Run the following **only if you intend to review and potentially authorize
the displayed correction to the local test publishing service**:

```bash
cd ~/agentic-systems-portfolio

PYTHONPATH=src python3 -m agentic_portfolio.operator_session \
  --base-config config/local-vertical.example.json \
  --run-root artifacts/operator-runs \
  --reviewer local-agentic-reviewer \
  --ssh-private-key "$HOME/.ssh/agentic-approval-ed25519" \
  --allowed-signers "$HOME/.config/agentic-systems-portfolio/allowed_signers"

RELEASE_RC=$?
printf '\nINTEGRATED_RELEASE_RC=%s\n' "$RELEASE_RC"
```

The command creates a fresh unique workspace/config/report, starts its
SQLite HTTP service, reproduces a real failing Git test, obtains an actual
model-authored correction, validates it and persists a candidate commit.
The second model invocation uses real HTTP observations and an explicit
source-of-truth policy, then displays the **actual** SKU, mismatches,
model rationale and decision digest.

At the prompt, inspect the findings. To authorize the exact local
publication, **type the entire displayed decision digest**. Any other input
retains the review and stops with no publication.

If approved, the same run verifies a reviewer-held SSH signature, freezes
the actual model proposal (no fresh model inference), checks source
digests/ETag, writes a PREPARED effect ledger entry, applies a conditional
HTTP PUT, rereads the service, independently verifies all product fields,
finalizes the effect record, verifies both model/tool native spans and the
event-journal hash chain, and exports evidence and the DAG workbench.

**Failure semantics:** When effects are ambiguous, publication is held;
the system does not blindly retry the PUT. A second attempted closure
checks actual remote state before taking another action. Concurrent
operator executions targeting one report are blocked.

## 5. Required result and evidence

A successful run prints `LOCAL_TWO_MODEL_VERTICAL_PASS`, including
the unique run ID and actual artifact paths. Files are retained together:

- `run.json`: both agent outcomes, diff, source digests, approval review,
  observed writeback and post-write independent comparison
- `run.events.sqlite3`: transactionally persisted, parent-linked native
  inference, Git, validation and HTTP spans with hash-chain verification
- `run.effects.sqlite3`: PREPARED → VERIFIED or explicit uncertain outcome
- `qualification.json`: **strict** machine-produced acceptance decision
- `workbench.html`: interactive evidence-driven DAG for that run
- `runtime.json`: private configuration, mode 0600, do not commit

The exporter fails if one model invocation or a required child-tool trace
is absent, if reviewer SSH evidence is missing, if the Git candidate is not
retained, if the final HTTP comparison is not clean, or if the durable effect
is not VERIFIED. There is no fallback fabricated PASS.

You may then inspect and commit the **redacted, nonsecret**
`qualification.json` to the repository's `evidence/` folder. Never
commit the private runtime config, a review private key, access tokens or
unredacted customer data. A successful local run is not proof of production
deployment.

## 6. External service qualification (additional, never inferred)

The configured JSON HTTP contract can target real authenticated HTTPS
source/publishing services. However, a real customer service, supported
credentials, reviewer identity provider and service-specific API contract
have **not** been supplied or tested in this conversation.

For an authorized external provider, perform the non-mutating endpoint
conformance check with a **private** configuration:

```bash
cd ~/agentic-systems-portfolio

PYTHONPATH=src python3 -m agentic_portfolio.external_conformance \
  --config /actual/private/external-runtime.json \
  --output evidence/external-preflight.json
```

This checks nonloopback HTTPS, token authentication, field schema,
channel ETag/versioning and live reconciliation. It is **read-only**
preflight, not production signoff. A customer-approved sandbox must
then qualify actual authorized writes, rate limits, retry/recovery,
security, identity lifecycle and load. No production PASS is invented.

**Release classification:** Local integrated qualification is attainable
with the operator session; full external production qualification remains
blocked until independently observed on the actual target service.
