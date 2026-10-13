# Real Engineering Repair Agent

`repair_agent.py` is an executable model-to-mutation loop, not a synthetic
diagnostic prompt. It requires the configured repository to contain an actual
failing test and the model to propose a structured source change.

The agent always creates a **disposable Git worktree**, reproduces the failure,
reads allowlisted real files, calls the configured OpenAI-compatible local
model, checks an exact unique edit precondition, applies the proposed edit
only if `--approve` is present, captures the Git diff and executes the
independent test command again. It rejects initially passing tests and
unauthorized paths.

The original repository is not modified. A verified result proves only a
candidate repair in the worktree, **not a committed or deployed release**.
The model is untrusted; source files may contain adversarial instructions.
Run only on a disposable trusted development machine. No OS-level sandbox
or full agent security isolation has been implemented.

## Configuration

Use one JSON file **outside version control** containing:

```json
{
  "model_endpoint": {
    "url": "http://127.0.0.1:1234/v1/chat/completions",
    "token": "local-development-only",
    "model": "deepseek/deepseek-r1-0528-qwen3-8b",
    "timeout_seconds": 180,
    "max_response_bytes": 100000,
    "system_prompt": "Return exact JSON source edits with evidence. Do not invent tool results."
  },
  "engineering": {
    "repository": "/absolute/path/to/actual/defective/repository",
    "allowed_files": ["src/file_with_observed_defect.py"],
    "validation_command": ["python3", "-m", "unittest", "discover", "-s", "tests"],
    "timeout_seconds": 120
  }
}
```

The paths are examples for the configuration schema, **not preexisting
services or files**. Configure them from the actual repository being repaired.

Run:

```bash
cd ~/agentic-systems-portfolio
PYTHONPATH=src python3 -m agentic_portfolio.repair_agent \
  --config /actual/path/to/runtime.json \
  --output artifacts/repair-review.json

# After reviewing authorized paths and understanding the scope:
PYTHONPATH=src python3 -m agentic_portfolio.repair_agent \
  --config /actual/path/to/runtime.json \
  --output artifacts/repair-execution.json --approve
```

Every invocation makes a fresh model call. The second run does not execute
a cryptographically locked approval of the first run's proposal. Therefore
this is still not a production-grade HITL approval mechanism; approval
binding and candidate persistence are release blockers.

The parallel catalog flow is presently a separate HTTP integration and is
not yet coordinated by this entry point. Both workflows do not yet complete
in one production-grade autonomous run.
