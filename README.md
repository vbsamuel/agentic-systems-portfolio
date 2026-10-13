# Agentic Systems Portfolio

> **Verified operator result (2026-10-13): LOCAL_TWO_MODEL_VERTICAL_PASS.** [Release evidence record](LOCAL_RELEASE_2026-10-13.md) · [Operator procedure](OPERATOR_RELEASE.md) · [Six-gate contract](INTEGRATED_VERTICAL_RELEASE_CONTRACT.md). The actual operator command completed with `INTEGRATED_RELEASE_RC=0` under run `8b5d0b96-6c30-4ea3-8d01-9919e44052e6`. This closes the **local** two-model HTTP vertical. External customer production qualification remains **NOT_PERFORMED**. The generated run artifacts are on the operator's WSL machine and are not yet published or independently inspected in this repository.


## 1. Multi-agent engineering: defect-to-reviewed-verification

**Problem.** Coding agents and CI systems can lose source-state consistency, race on the same repository and claim completion without an independent validation result.

**Flow.** Work intake → source revision captured → transactional repository-scoped writer claim → executable test subprocess → revision drift check → evidence stored in event journal → named human approval or failed status.

**Concrete components**
- `src/agentic_portfolio/orchestrator.py`: SQLite-backed queue, guarded state transitions, single active writer per repository, hash-chain event verification.
- `src/agentic_portfolio/engineering_flow.py`: actual Git revision inspection and bounded subprocess execution.
- `tests/test_flows.py`: real temporary Git repositories, passing/failing checks and review controls.

**Scope limitations.** There is no LLM planner, independent code-writing agent, sandbox, remote distributed agent scheduling, or production CI connector. The Python command execution interface is for **trusted operator-supplied commands only**; it is not a security sandbox.

## 2. Catalog accuracy: discrepancy-to-reviewed-closure

**Problem.** Published product content diverges from a source-of-truth catalog, causing price, inventory and product-content inaccuracies that are expensive to review manually.

**Flow.** CSV catalog + published snapshot intake → SKU identity reconciliation → field-level comparison → persistent exception case → human/operator correction outside the tool → independent re-read of both snapshots → block closure while mismatch remains → named reviewer and rationale.

**Concrete components**
- `src/agentic_portfolio/catalog.py`: deterministic product reconciliation, including high-risk pricing and availability differences.
- `src/agentic_portfolio/catalog_flow.py`: real CSV adapters, SQLite discrepancy case state and closure revalidation.
- `tests/test_flows.py`: discrepancy opened, premature closure rejected, corrected observation accepted.

**Scope limitations.** No authenticated live PIM/CMS connectors, AI semantic matcher, correction writeback, or ongoing production monitoring is claimed.

## Execute both systems

Requires Python 3.10+ and Git. No network, external API or LLM key is required.

```bash
git clone https://github.com/vbsamuel/agentic-systems-portfolio.git
cd agentic-systems-portfolio
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python examples/run_workflows.py
```

GitHub Actions runs the tests and both-workflow example on pushes and pull requests: [CI](.github/workflows/verify.yml).

## Evidence and authorship

See [PROVENANCE.md](PROVENANCE.md). This is newly authored reference code and does not relabel upstream forks as original work. Test results, deployments, users, production tenure and measurable business benefit are separate claims requiring operational evidence.


## Stage-by-stage measurable end-to-end qualification

Run from repository root:

```bash
cd ~/agentic-systems-portfolio
git pull --ff-only origin main
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m agentic_portfolio.qualification --output artifacts/qualification.json
cat artifacts/qualification.json
```

The qualification is **executed**, not a static report: it creates a real temporary Git repository, runs passing and intentionally failing validation commands, exercises reviewer gating and source-drift rejection, writes two independent product CSV snapshots, opens a price discrepancy, prevents premature closure, modifies the observed channel snapshot, and independently rechecks before case closure.

Each stage records the workflow, name, measured wall-clock duration in milliseconds, actual observation, and pass/fail evaluation. GitHub Actions must execute the qualification and retain the JSON report as a build artifact.

**Qualification boundaries:** Passing these local tests proves only the stated local execution paths. It does **not** certify autonomous LLM agents, a production Git authoring pipeline, authenticated PIM/ERP/CMS integrations, automatic catalog corrections, external runtime reliability, tenant isolation, security sandboxing, customer use, or production impact. Those must be built and independently tested in subsequent tranches before a production claim.

**Stage acceptance:** An expected negative path is a pass only when the dangerous operation is actually rejected. Any failed expectation marks the aggregate qualification failed. See [qualification.py](src/agentic_portfolio/qualification.py) and [qualification tests](tests/test_qualification.py).


## Live HTTP catalog integration (new)

[HTTP integration implementation](src/agentic_portfolio/http_integration.py) fetches actual JSON over HTTP(S) from separately configured catalog and publishing endpoints, with bearer authentication, finite timeouts, content-size bounds and SHA-256 observation digests. In read-only mode it emits discrepancies without mutation. With operator-enabled `writeback=True`, it requires an ETag, issues conditional HTTP PUT with `If-Match`, re-GETs the channel and verifies the changed content against the authoritative catalog. The publishing API must enforce atomic ETag compare-and-swap.

[HTTP execution test](tests/test_http_integration.py) spins up a real loopback HTTP server with separate catalog and channel routes, verifies read-only no-write behavior, sends a real conditional PUT, observes the changed server state and independently rechecks the response. This is a real local HTTP mutation, not a file rewritten by the harness. It is **not** an authenticated connection to an actual retailer or enterprise service.

Endpoint contract: GET catalog and channel URLs must return arrays of records with `sku,title,description,price,currency,availability,image_url`. PUT channel URL accepts `{"products":[...]}` with `If-Match`. Only use configured services that implement and authorize this contract. In particular, do not enable writeback against production services without an operator-approved policy.

The engineering track still lacks an AI coding-agent runtime with independent defect diagnosis and actual generated patch application. No production release or non-stub fully autonomous qualification is claimed.

## Model-authored engineering repair

The new [repair agent](src/agentic_portfolio/repair_agent.py) performs an actual local-model proposal against a failing Git checkout, applies a bounded edit in a detached worktree after an explicit execution flag, and runs post-change tests. See [operator contract](REPAIR_AGENT.md). It is **not** yet part of a fully recoverable unified two-agent service, and no observed local-model repair run has been qualified.


## Current operational vertical and observed outcome (2026-10-13)

**Start here for the CURRENT system.** Some earlier sections of this README describe the original limited implementation and are retained as development history. They do **not** supersede this section.

The current working cross-cut consists of:
1. **Real inputs / local state:** Configured Git project with reproducible failing test and a SQLite-backed source-of-truth catalog plus HTTP publishing service. [Single vertical operator guide](SINGLE_VERTICAL.md), [configuration](config/local-vertical.example.json).
2. **Engineering model agent:** Reproduce test failure → feed observed failure and allowlisted source to LM Studio/DeepSeek → require a structured source edit → mutate a detached worktree → rerun the actual validation command → persist a verified candidate Git commit under `refs/agentic-repairs/<sha>`. Original branch is not overwritten. [Repair agent](src/agentic_portfolio/repair_agent.py).
3. **Recovery of already completed engineering work:** Verify candidate Git ref, exact revision and clean source before reusing the existing result. This avoids another expensive inference request. It is **not** crash-safe exactly-once execution across all steps. [Coordinator](src/agentic_portfolio/live_e2e.py).
4. **Catalog model agent:** GET the authoritative and published records → compare SKU and fields → send actual observations to the configured LLM → validate `CORRECT` or `ESCALATE` → require explicit trusted-authority policy and correctable-field allowlist for `CORRECT` → bind the decision to observed response digests, channel ETag and policy. [Catalog agent](src/agentic_portfolio/catalog_agent.py).
5. **Human authorization boundary:** A `CORRECT` decision by itself is **not approval**. The review output identifies `decision_digest`; publication requires explicitly supplying that exact approved digest, matching the rechecked decision and source state. The current digest mechanism is not an identity-authenticated approval signature.
6. **Publication and independent verification:** When authorized, the channel must accept a conditional ETag-bound HTTP PUT and then return corrected content on an independent GET. Model-originated arbitrary product values are **not** written; deterministic reconciliation is scoped to the approved authoritative source. [HTTP integration](src/agentic_portfolio/http_integration.py).
7. **Evidence and decision:** A unified run ID, intermediate stage measurements, model usage, Git candidate SHA, discrepancy/decision digest and publication readback are recorded in the JSON artifact. `PASS` is allowed only after required verification, not from model confidence alone.

### Latest observed actual results

See the [dated evidence record](evidence/2026-10-13-two-agent-vertical-qualification.md) for exact Git commits, run IDs, timings and negative paths.

- **Earlier local cross-cut:** real DeepSeek-authored code fix and successful deterministic HTTP product correction both independently verified: `PASS`. This was **not** a two-model autonomous publication.
- **Current two-model run ID:** `31398dd5-ef83-4ac4-8124-efbacf17e44e`; engineering repair candidate `ed39b89c79094e9b949635bf778df8f9facd9e85` preserved and reused.
- **Latest two-model review:** DeepSeek returned `CORRECT` for SKU `P-1` after explicit catalog-authority policy was applied. Review digest: `e8b1b13926564ee73ab7965e54812002e7e76e2ce14825f72949a8e34d5c94ca`. Run status `BLOCKED_CATALOG` / `AWAITING_APPROVAL`; `writeback_performed=false`. This is an expected approval hold, **not publication success**.
- **Latest WSL automated regression reported by operator:** **35/35 PASS**, `TEST_RC=0`, on commit `e8dc43c`.

### Execution and files

Run from the repository root in WSL, with LM Studio running and the configured model actually loaded:

```bash
cd ~/agentic-systems-portfolio
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m agentic_portfolio.vertical \
  --config /tmp/agentic-two-model-review.json \
  --output artifacts/two-model-review.json
RUN_RC=$?
printf 'RUN_RC=%s\\n' "$RUN_RC"
```

The second command needs the operator's **private, existing runtime config**, not merely the checked-in example. A review hold returns nonzero by design. For flow, initial configuration, model selection, resumption and approval steps, see [two-model operating guide](TWO_MODEL_VERTICAL.md), [catalog agent review contract](CATALOG_AGENT.md), and [observed evidence](evidence/2026-10-13-two-agent-vertical-qualification.md).

**Unclosed gates:** Model-approved catalog HTTP publication with post-write reread **under the two-model run**; authenticated reviewer identity; crash-safe replay for publishing; external PIM/CMS integration; security/load/reliability and sustained production use. No production-release or external-customer-impact claim is made.
