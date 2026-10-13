# Live evidence workbench

The prior static HTML renderer remains available. The new
`agentic_portfolio.live_monitor` serves that same workbench over a **loopback-only,
read-only HTTP server** and polls its authoritative run JSON at a configurable
interval. There are no simulated events, fake status transitions, direct
approvals, network CDN dependencies, or destructive controls.

## Start the local monitor

```bash
cd ~/agentic-systems-portfolio
git pull --ff-only origin main
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m agentic_portfolio.live_monitor \
  --report artifacts/two-model-review.json \
  --port 8765 \
  --poll-ms 1500
```

Open **http://127.0.0.1:8765/** from the Windows browser when your WSL
loopback forwarding is available. Keep the monitor terminal running while
the browser is open; use Ctrl+C to stop just that process.

The HTML displays original run identifiers and evidence; browser polling
calls `/api/run` and reloads the dashboard when the raw report digest
changes. The endpoint responds 503 when the report is unavailable or
malformed. Only `GET /` and `GET /api/run` are exposed.

**Limitations:** This is actual near-real-time polling of persisted stage
snapshots, not socket-level streaming, event replay, rich graph topology,
authenticated approvals or a remote multi-user control plane. Report
atomicity and correctness depend on the writer. The catalog run remains
`AWAITING_APPROVAL` until an authorized local writeback is performed,
verified and the report updated. Do not mark completion based on the monitor
starting or a read-only test passing.
