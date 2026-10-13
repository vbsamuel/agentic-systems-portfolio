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

## Evidence-based graph (new tranche)

The monitor now converts the recorded execution stages and engineering
sub-events into graph nodes with stable run-scoped identifiers and edges.
The static HTML export uses the same normalization. Selecting a node
displays the underlying recorded observation. The graph shows retries and
recovery stages when those stages were actually written.

**Provenance limitation:** The historical JSON schema records stage order,
not universal causal span identifiers. Graph edges are labelled
`recorded_stage_order`, `recorded_substage_order` or membership.
Those are not asserted to prove independent task dependencies or cross-service
happens-before. True distributed causality requires new instrumentation with
durable parent/span IDs and measured tool events at write time.

The monitor remains read-only. Starting the UI does not authorize publishing,
claim crash-safe replay, or establish production reliability.

## Native append-only execution journal

New coordinator executions now write a sibling SQLite WAL journal next to
the JSON report: `artifacts/two-model-review.events.sqlite3` for
`artifacts/two-model-review.json`. Each event has a UUID event ID,
run ID, native parent event ID, durable insertion sequence, nanosecond wall
timestamp, payload and SHA-256 chained digest. The writer validates parents
against the same run and the reader checks the complete hash chain.

The read-only monitor exposes `GET /api/events`, which returns journal events
for the report's run ID only after hash verification. It returns 404 for a
historical report without a journal and 409 when integrity verification fails.
Historical records are **not retroactively relabelled as native traces**.

This is a real append-only stage journal, not yet an exactly-once side-effect
transaction log or a cryptographically signed external attestation. The
coordinator currently records start/completion of its stage boundaries;
individual model token streams and tool processes still need native span
instrumentation, and the graph UI currently visualizes historical stage
normalization rather than rendering every native span.
