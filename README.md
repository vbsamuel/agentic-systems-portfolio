# Agentic Systems Portfolio

Two executable workflows with **explicit problem definitions, real automation paths and measurable acceptance boundaries**. These implementations are standalone portfolio code, not historical evidence of client production deployments.

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
