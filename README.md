# Agentic Systems Portfolio

**Operator start:** **[QUICKSTART — install, run, approve, recover and inspect](QUICKSTART.md)**

> **Proprietary — All Rights Reserved.** Source availability does **not** grant permission to use, reproduce, modify, deploy or redistribute this software except as legally permitted. Prior written permission is required; commercial use requires a separately executed **paid license**. See [LICENSE](LICENSE). This repository is **not Apache-licensed or open source**.

## Current qualification (2026-10-13)

| Scope | Observed result |
|---|---|
| Local DeepSeek engineering repair → verified Git candidate | **PASS** |
| Separate catalog model → reviewed price discrepancy | **PASS** |
| Human reviewer approval → Ed25519 SSH-bound grant | **PASS** |
| Local authenticated SQLite-backed HTTP publication → conditional write and independent readback | **PASS** |
| Integrated operator console with lifecycle, native event and tool-span drill-down | **PASS**, local machine acceptance |
| Latest operator-reported Python regression | **76/76 PASS** |
| Latest saved-run integrated acceptance | **LOCAL_OPERATOR_WORKBENCH_VERTICAL**, RC **0** |
| Native journal evidence | **64 events**, **25 paired operations**, **3 stage attempts**, **0 failed historical operations** |
| External customer/enterprise production deployment | **NOT PERFORMED** |

The most recently verified workbench run was `cc4ec0f2-effd-441a-8ddd-951c18a590af`. Its saved evidence demonstrates **engineering verified → catalog review awaiting approval → signed human authorization → HTTP write observed → independent readback verified**. The correction was SKU `P-1`, published price `119.00` to authoritative `100.00`. The read-only workbench acceptance was confirmed with exit code 0. A Chrome screenshot confirms the five-phase layout and no major clipping; screenshots do not establish that every interactive control has been independently click-tested.

**The first earlier operator-confirmed integrated release** was run `8b5d0b96-6c30-4ea3-8d01-9919e44052e6`. These are distinct evidence runs, **not competing current results**. [Dated first-release record](LOCAL_RELEASE_2026-10-13.md) · [Sanitized public qualification JSON](evidence/local-two-model-qualification-2026-10-13.json).

## Quickstart: operate the actual local vertical

**Full step-by-step procedure and prerequisite checks: [QUICKSTART.md](QUICKSTART.md).**

Prerequisites: authorized use, Python 3.10+, Git, OpenSSH `ssh-keygen`, LM Studio serving the configured DeepSeek model, an operator signing key and a trusted `allowed_signers` file. The Quickstart has non-destructive key setup and model endpoint checks.

Run tests:

```bash
cd ~/agentic-systems-portfolio
git pull --ff-only origin main
PYTHONPATH=src python3 -m unittest discover -s tests -q
printf 'TEST_RC=%s\n' "$?"
```

Start a **new** private local run:

```bash
cd ~/agentic-systems-portfolio
PYTHONPATH=src python3 -m agentic_portfolio.operator_session \
  --base-config config/local-vertical.example.json \
  --run-root artifacts/operator-runs \
  --reviewer local-agentic-reviewer \
  --ssh-private-key "$HOME/.ssh/agentic-approval-ed25519" \
  --allowed-signers "$HOME/.config/agentic-systems-portfolio/allowed_signers"
printf 'RELEASE_RC=%s\n' "$?"
```

At the **explicit operator menu**, enter **1 / approve / approved / accept** to sign and authorize the **exact displayed local correction**, **2 / reject** to decline, or **3 / defer** to retain the review without publishing. A deliberate reject or defer returns exit code 0 **without release PASS**. Only a verified `LOCAL_TWO_MODEL_VERTICAL_PASS` result establishes release acceptance. The user controls authorization; no approval is inferred from the model decision.

To re-qualify an already approved saved run **without model inference or another HTTP write**, use the one-command `agentic_portfolio.operator_workbench_acceptance` procedure in [QUICKSTART.md](QUICKSTART.md). It revalidates the signed grant at the original journal-recorded completion time, verified Git ref, journal, effect ledger, lifecycle and paired calls, and regenerates offline HTML. Never commit private runtime configs, SQLite journals or signing material; `.gitignore` excludes local `artifacts/` run outputs.

## Architecture and actual capability boundaries

- **Engineering agent:** [repair_agent.py](src/agentic_portfolio/repair_agent.py) diagnoses an observed failing test with local inference, applies bounded edits in a detached Git worktree, executes validation and persists a verified candidate without overwriting the source branch.
- **Catalog agent:** [catalog_agent.py](src/agentic_portfolio/catalog_agent.py) observes source and published data over the bundled authenticated HTTP service, independently reconciles SKU/fields and requires authority-policy grounding of a `CORRECT` model decision.
- **Operator and recovery:** [operator_session.py](src/agentic_portfolio/operator_session.py), [operator_release.py](src/agentic_portfolio/operator_release.py), [effect_ledger.py](src/agentic_portfolio/effect_ledger.py) enforce authenticated, proposal-bound approval; prepared-effect persistence; conditional write; and no blind replay of uncertain writes.
- **Evidence and workbench:** [event_journal.py](src/agentic_portfolio/event_journal.py), [workbench_projection.py](src/agentic_portfolio/workbench_projection.py), [workbench.py](src/agentic_portfolio/workbench.py), [operator_workbench_acceptance.py](src/agentic_portfolio/operator_workbench_acceptance.py) produce hash-linked native events, real parent relationships, paired tool calls, five-phase lifecycle and read-only HTML.
- **Earlier deterministic examples:** [orchestrator.py](src/agentic_portfolio/orchestrator.py), [catalog_flow.py](src/agentic_portfolio/catalog_flow.py), and [qualification.py](src/agentic_portfolio/qualification.py) remain additional component examples; they are **not** the controlling integrated local release.

This is a **local reference implementation**, not a production SaaS control plane or a qualified customer PIM/CMS deployment. The HTML workbench is generated from a persisted run, not a continuous live-service monitor. The generic [external conformance probe](src/agentic_portfolio/external_conformance.py) is read-only; actual customer endpoints, credentials, hardening, security, SSO and production qualification have not been provided or exercised.

## Canonical documentation

| Document | Purpose |
|---|---|
| **[QUICKSTART.md](QUICKSTART.md)** | **Start here:** prerequisites, key setup, first run, review decisions, recovery and workbench |
| [OPERATOR_RELEASE.md](OPERATOR_RELEASE.md) | Detailed signed release and failure/reconciliation procedure |
| [INTEGRATED_VERTICAL_RELEASE_CONTRACT.md](INTEGRATED_VERTICAL_RELEASE_CONTRACT.md) | Acceptance invariants and qualified boundaries |
| [LOCAL_RELEASE_2026-10-13.md](LOCAL_RELEASE_2026-10-13.md) | First operator-confirmed release and historical provenance |
| [evidence/local-two-model-qualification-2026-10-13.json](evidence/local-two-model-qualification-2026-10-13.json) | Public sanitized machine-generated evidence from the first verified release |
| [PROVENANCE.md](PROVENANCE.md) | Authorship and evidence boundaries |
| [LICENSE](LICENSE) | Proprietary source-available terms |

The original run-specific private evidence remains on the operator's WSL filesystem, excluded from Git. Reported regression and acceptance observations belong to the specific commits and runs shown; **future changes require new verification**. No external production claims are made.
