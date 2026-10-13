# Integrated two-agent run

One command invokes **two real configured model calls** in sequence and records the
engineering and catalog evidence in one output artifact. Unlike the previous
qualification harness, this runner does not generate a fixture, manufacture a
model response, or silently fall back to a mock. It requires your real Git
working tree, a reachable OpenAI-compatible inference API and live
authenticated JSON catalog/channel endpoints.

**Current design boundary:** Both model calls are investigation agents that
produce recommendations. The code does **not** yet allow a model to author/apply
an engineering patch. The catalog mutation is deterministic, guarded by a
versioned channel API, and authorized by operator configuration rather than
being arbitrarily authored by the model. This does not yet qualify the
requested fully autonomous defect-to-fix outcome.

The current integrated runner also does not itself implement an external,
cryptographically bound approval mechanism, restart-safe orchestration, or
independent model-result scoring. Do not claim these capabilities.

## Inputs

Supply one JSON configuration file at runtime with these keys:

- `model_endpoint`: `url`, `token`, `model`, `timeout_seconds`,
  `max_response_bytes`, `system_prompt`
- `engineering`: `repository`, `validation_command` (JSON array of
  executable argv), `timeout_seconds`
- `catalog.authoritative` and `catalog.published`: `url`, `token`,
  `timeout_seconds`. The authoritative and published GET routes return
  JSON arrays of products. The publishing route supports versioned PUT.
- `approved_actions`: `engineering_validation` and `catalog_writeback`
  booleans. These are operator-controlled experimental permissions, **not**
  production-grade approvals.

Do not commit bearer tokens. Populate your configuration outside the repo,
restrict permissions, and do not enable catalog writeback against a real
production channel before integrating authenticated approval enforcement.

## Execute

```bash
cd ~/agentic-systems-portfolio
PYTHONPATH=src python3 -m agentic_portfolio.integrated_run \
  --config /secure/path/to/runtime.json \
  --output artifacts/integrated-run.json
```

The final artifact includes model response digests, source revision, observed
reproduction exit code, initial and final catalog findings, endpoint response
digests and timing, and per-stage measurements. A blocked outcome is expected
when tests fail, writeback is not authorized, or the observed content remains
incorrect.

## Criteria for future full release

Require model-selected tool calls, actual agent-generated code patching in an
isolated checkout, separate source/validation actor authority, persist/resume
after process termination, real human identity approvals, complete traces for
failure paths, and validated customer/operator impact. Keep the 18-gate
release decision **BLOCKED** until these capabilities are independently proven.
