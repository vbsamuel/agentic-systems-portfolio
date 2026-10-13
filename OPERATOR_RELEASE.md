# Operator-ready integrated vertical — one release verdict

**Purpose:** Qualify the existing two-agent run from its actual reviewed decision to
a verified publication. This is *one end-to-end local release unit*, not a set
of independently accepted subfeatures.

This procedure never generates fake agent decisions. The existing DeepSeek
engineering repair and price review remain the input. The final action reuses
the persisted Git candidate, revalidates the frozen catalog proposal against
current HTTP observations, requires a separately held SSH reviewer private key,
performs a single ETag-bound HTTP PUT, rereads the published records, verifies
the native event journal and durable effect ledger, then exports the factual
local evidence and updated interactive workbench.

## Confirmed historical input

Run ID: `31398dd5-ef83-4ac4-8124-efbacf17e44e`.

Engineering candidate: `ed39b89c79094e9b949635bf778df8f9facd9e85`.

Reviewed catalog decision: `CORRECT`, SKU `P-1`, published price
`119.00`, authoritative price `100.00`.

Decision digest:
`e8b1b13926564ee73ab7965e54812002e7e76e2ce14825f72949a8e34d5c94ca`.

The last operator-confirmed suite before this tranche was **46/46 PASS** on
`65b6ac5`. The new code and tests remain unqualified until the operator
executes them. The reviewed local publication has **not** been executed or
authorized by the observed conversation so far.

## 1. Qualify the code

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

If tests are red, do **not** proceed to the publication step. Repair the
failed invariants first. This shell block never runs `exit 1` or closes a
terminal on failure.

## 2. Establish your reviewer key and trust root

Use your existing approved SSH signing key or create a **separate, personal
reviewer key** on your WSL machine. A dedicated key may be created with:

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

Choose a passphrase when prompted. Do not overwrite an existing private key;
use an approved existing key instead. `allowed_signers` is a pinned
public-key trust file. **The runtime never needs the SSH private key except
during the explicit operator signing action**. No key material is committed.

This is cryptographically authenticated **local reviewer-key possession**,
not enterprise SSO or a validated customer identity-provider assertion.

## 3. Review, then explicitly authorize the local effect

Inspect the review JSON and confirm that the actual proposal, run, SKU,
source-of-truth policy and target price match your intended operation.

Only after the operator actually authorizes this specific **local** catalog
correction, run:

```bash
cd ~/agentic-systems-portfolio

PYTHONPATH=src python3 -m agentic_portfolio.operator_release \
  --config /tmp/agentic-two-model-review.json \
  --report artifacts/two-model-review.json \
  --reviewer local-agentic-reviewer \
  --ssh-private-key "$HOME/.ssh/agentic-approval-ed25519" \
  --allowed-signers "$HOME/.config/agentic-systems-portfolio/allowed_signers" \
  --evidence evidence/local-two-model-final-qualification.json \
  --workbench artifacts/agent-execution-workbench.html \
  --confirm-local-publish

RELEASE_RC=$?
printf '\nLOCAL_RELEASE_RC=%s\n' "$RELEASE_RC"
```

**Safety:** The command has an explicit mutation-confirmation flag. Do not
execute it without personally approving this precise effect. No general
request to finish software development substitutes for reviewer consent.

The workflow refuses stale source/ETag observations, wrong reviewer keys,
mismatched proposal digests, concurrent runs, stale Git refs or invalid
verification. If an HTTP acknowledgment is lost, the effect remains durable
and the next attempted closure reconciles the actual published state **without
blindly replaying the PUT**. A still-unchanged or ambiguous effect is held for
review rather than automatically retried.

## 4. Definitive evidence and workbench

A successful command writes:
- `artifacts/two-model-review.json`: original run ID and full observed
  engineering and catalog results
- `artifacts/two-model-review.events.sqlite3`: native parent-linked and
  hash-chained events (including actual Git/test/model/HTTP operation spans)
- `artifacts/two-model-review.effects.sqlite3`: prepared effect and verified
  reconciliation state
- `evidence/local-two-model-final-qualification.json`: strict, machine-derived
  summary proving source Git candidate, journal integrity, and durable effect
- `artifacts/agent-execution-workbench.html`: real event DAG and evidence UI

The CLI produces `PASS` **only** when all of those observed checks succeed.
Review evidence content before committing it; remove any confidential
customer data. Do not commit private config or signing keys.

```bash
cd ~/agentic-systems-portfolio

git status --short
python3 -m json.tool evidence/local-two-model-final-qualification.json

git add evidence/local-two-model-final-qualification.json
git commit -m "evidence: qualified local two-model integrated vertical"
git push origin main
```

Commit and push only if `LOCAL_RELEASE_RC=0` and the evidence file exists
and is accurate. Do not create or push a manufactured PASS artifact.

## 5. External connector and production qualification

The real production endpoint is not known from the supplied conversation and
no production credentials were provided. The runtime supports configured
authenticated HTTPS catalog/channel endpoints with ETag/CAS; the bundled
SQLite service is a **real local integration service**, not a customer PIM/CMS.

Given a privately supplied external endpoint configuration, execute the
non-mutating conformance check:

```bash
cd ~/agentic-systems-portfolio

PYTHONPATH=src python3 -m agentic_portfolio.external_conformance \
  --config /path/to/authorized-external-runtime.json \
  --output evidence/external-endpoint-preflight.json
```

That proves only read-only schema/auth/version conformance. Production signoff
also requires authorized write/readback against a provider-owned sandbox or
production-equivalent, rate limit/error/failure tests, security assessment,
secret rotation, and an independently reviewed identity provider.
**No external production PASS is claimed or generated by the local tool.**

## One release decision

- `LOCAL_TWO_MODEL_VERTICAL_PASS`: only after the actual approved live write,
  independent readback, native journal, Git and effect-ledger qualification.
- `EXTERNAL_READ_ONLY_PREFLIGHT`: external connectivity check, not release.
- `PRODUCTION_RELEASE_PASS`: **not supported as a claim** without independent
  external integration, operational security and reliability evidence.
