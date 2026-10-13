# Unified live execution — two agents, one evidenced outcome

Use the [live coordinator](src/agentic_portfolio/live_e2e.py), **not**
`integrated_run.py`, for the actual defect-to-Git candidate and
catalog-to-published-update journey.

## Execution

1. Require config and explicit worktree/publishing permissions.
2. Reproduce an actual failing test in a detached Git worktree.
3. Send the actual failure and allowlisted source to the configured live LLM.
4. Parse and precondition-check a model-authored patch.
5. Apply it in that worktree, rerun tests, preserve a Git commit and ref.
6. Fetch an actual catalog and published channel over HTTP(S).
7. Reconcile observed fields; conditionally update the channel using its ETag.
8. Independently fetch again and re-evaluate all discrepancies.
9. Emit a single JSON record with run ID, both outcomes and stage timings.
10. Fail closed: failed engineering repair prevents catalog writeback.

This is **sequential coordination**, not an atomic transaction across Git
and a publishing API. A catalog error does not roll back a persisted Git
candidate. Crash-safe automatic resume, signed approval binding, and
authenticated human identity remain release blockers.

## Runtime configuration

Create a JSON config outside the Git repository. All provider addresses,
model IDs, source paths, test commands, authorization and Git author
identity are externally configured:

```json
{
  "model_endpoint": {
    "url": "http://127.0.0.1:1234/v1/chat/completions",
    "token": "local-development-only",
    "model": "deepseek/deepseek-r1-0528-qwen3-8b",
    "timeout_seconds": 180,
    "max_response_bytes": 100000,
    "system_prompt": "Return JSON source corrections grounded in observed test failures."
  },
  "engineering": {
    "repository": "/absolute/path/to/real/failing/git/project",
    "allowed_files": ["relative/path/of/defective_source.py"],
    "validation_command": ["python3", "-m", "unittest", "discover", "-s", "tests"],
    "timeout_seconds": 120,
    "commit_identity": {
      "name": "Engineering Agent",
      "email": "agent@example.invalid"
    }
  },
  "catalog": {
    "authoritative": {
      "url": "https://actual-catalog-service/api/products",
      "token": "REPLACE_WITH_AUTHORIZED_SECRET",
      "timeout_seconds": 10
    },
    "published": {
      "url": "https://actual-publishing-service/api/products",
      "token": "REPLACE_WITH_AUTHORIZED_SECRET",
      "timeout_seconds": 10
    }
  },
  "approvals": {
    "engineering_worktree_mutation": false,
    "catalog_writeback": false
  }
}
```

Paths, catalog endpoints and tokens in this sample are **examples only**.
There is intentionally no manufactured service, generated default product,
or mock LLM fallback.

```bash
cd ~/agentic-systems-portfolio
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m agentic_portfolio.live_e2e \
  --config /actual/private/runtime.json \
  --output artifacts/live-e2e.json
```

The new coordinator tests mock its boundaries to verify control flow.
The separate repair integration test operates real Git objects and the HTTP
test operates a real loopback HTTP server. Neither establishes a live
end-to-end run of **both** external systems; that must still be executed
in the operator's WSL environment with a real failing repository and
authorized publishing service.

**Release claim:** not qualified until actual observed E2E results, crash
recovery, meaningful tool and agent instrumentation, and independent
production assessment are supplied.
