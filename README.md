# Agentic Systems Portfolio

Two independently written, runnable reference implementations illustrating engineering controls for agentic systems. **These examples do not establish historical production deployment.**

## Multi-agent software engineering orchestration

`src/agentic_portfolio/orchestrator.py` provides a SQLite-backed queue, repository-scoped single active writer, source-revision drift rejection, explicit validation outcomes, named human approval, and a hash-chained event record. The chain is tamper-evident against accidental changes, not tamperproof against an administrator who can rewrite the database. This is not a distributed scheduler, integrated coding agent, or CI system.

## Catalog-to-web content accuracy

`src/agentic_portfolio/catalog.py` reconciles authoritative SKU records with published content, flags missing records and critical attribute discrepancies, rejects duplicate SKUs, and requires review of findings. It is deterministic, not an LLM semantic assessor or live web crawler.

## Run

```bash
git clone https://github.com/vbsamuel/agentic-systems-portfolio.git
cd agentic-systems-portfolio
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Provenance and scope

These are independent reference examples, not relabeled copies of `vbsamuel/ai-agents`, `vbsamuel/claude-code-flow`, or `auric`. See [PROVENANCE.md](PROVENANCE.md). Any upstream source incorporated later must preserve required attribution.

The repository does not verify production tenure, customers, throughput, impact, or implementation ownership of separately deployed systems. External APIs, authentication, real code execution, automated publication, and LLM matching are not implemented.
