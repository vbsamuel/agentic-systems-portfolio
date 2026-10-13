# Operator Quickstart — Local Two-Model Workflow

**Start here.** This guide is for an operator running the **working, qualified local vertical** on Ubuntu/WSL. It runs (1) DeepSeek-driven Python repair and Git candidate verification, (2) a second model's catalog discrepancy decision, (3) an explicit human approval, and (4) an authorized change to the bundled **local SQLite-backed HTTP catalog**, followed by independent readback and evidence export. This is **not a customer production connector**.

**License:** Proprietary, all rights reserved. Prior written authorization is required for use; commercial use requires a separately negotiated paid license. Read [LICENSE](LICENSE) before use.

## What you need

- Ubuntu / WSL with `python3` (3.10+), `git`, `ssh-keygen`, and the project checked out at `~/agentic-systems-portfolio`.
- LM Studio running its local OpenAI-compatible API at `http://127.0.0.1:1234/v1/chat/completions` with model `deepseek/deepseek-r1-0528-qwen3-8b` loaded. The precise URL and model ID must match your machine; edit `config/local-vertical.example.json` if different.
- Disk space for generated private workspaces and time for two model inferences.
- Authority to approve the **local test** correction; approval is never automatic.

## Step 1 — Verify the repository and LM Studio

```bash
cd ~/agentic-systems-portfolio

git pull --ff-only origin main
printf 'PULL_RC=%s\n' "$?"

python3 --version
git --version
ssh -V

# LM Studio CLI, if installed:
if command -v lms >/dev/null 2>&1; then
    lms ps
else
    printf 'LM_STUDIO_CLI=NOT_FOUND; check the server in the LM Studio application\n'
fi

# Check API reachability; do not print tokens or private runtime files.
python3 - <<'PY'
import json
from pathlib import Path
from urllib.request import urlopen
cfg=json.loads(Path("config/local-vertical.example.json").read_text())
for key in ("model_endpoint","catalog_model_endpoint"):
    item=cfg[key]
    print(key.upper(),"MODEL=",item["model"],"URL=",item["url"])
    try:
        from urllib.parse import urlsplit
        u=urlsplit(item["url"])
        with urlopen(f"{u.scheme}://{u.netloc}/v1/models",timeout=5) as r:
            print(key.upper(),"HTTP_STATUS=",r.status)
    except Exception as exc:
        print(key.upper(),"CONNECTIVITY_CHECK_FAILED=",type(exc).__name__,str(exc))
PY
```

A reachable model-list endpoint alone does not prove that the configured model is loaded. Confirm the model ID in LM Studio. Do not proceed with publishing when endpoint identity is uncertain.

## Step 2 — Set up the reviewer key (once)

Use a dedicated signing identity; **never overwrite an existing key**. The following creates an unencrypted key for a *local-only* qualification; use an appropriately protected identity for sensitive or production workflows.

```bash
cd ~/agentic-systems-portfolio

KEY="$HOME/.ssh/agentic-approval-ed25519"
TRUST="$HOME/.config/agentic-systems-portfolio/allowed_signers"
mkdir -p "$HOME/.ssh" "$HOME/.config/agentic-systems-portfolio"
chmod 700 "$HOME/.ssh"

if [ ! -e "$KEY" ] && [ ! -e "$KEY.pub" ]; then
    ssh-keygen -t ed25519 -f "$KEY" -N "" -C "local-agentic-reviewer"
else
    printf 'KEY_EXISTS=YES; not overwriting\n'
fi

if [ -f "$KEY.pub" ]; then
    printf 'local-agentic-reviewer %s\n' "$(cat "$KEY.pub")" > "$TRUST"
    chmod 600 "$TRUST"
fi

if [ -f "$KEY" ] && [ -f "$TRUST" ]; then
    printf 'SIGNING_PREREQUISITES=PRESENT\n'
else
    printf 'SIGNING_PREREQUISITES=INCOMPLETE\n'
fi
```

Keep the private key and `runtime.json` out of Git. For organizations, use separately provisioned approver identities and trust policy.

## Step 3 — Execute qualification tests

```bash
cd ~/agentic-systems-portfolio

PYTHONPATH=src python3 -m unittest discover -s tests -v
TEST_RC=$?
printf 'TEST_RC=%s\n' "$TEST_RC"
```

Proceed only with `TEST_RC=0`. A previous operator run passed the local integrated vertical; this does not guarantee your current configuration works.

## Step 4 — Start a NEW operator session

```bash
cd ~/agentic-systems-portfolio

PYTHONPATH=src python3 -m agentic_portfolio.operator_session \
  --base-config config/local-vertical.example.json \
  --run-root artifacts/operator-runs \
  --reviewer local-agentic-reviewer \
  --ssh-private-key "$HOME/.ssh/agentic-approval-ed25519" \
  --allowed-signers "$HOME/.config/agentic-systems-portfolio/allowed_signers"

RELEASE_RC=$?
printf 'INTEGRATED_RELEASE_RC=%s\n' "$RELEASE_RC"
```

The command prints `REVIEW_STARTED` with a new report path and then stage progress plus a 15-second heartbeat during lengthy local inference. Engineering runs real tests, uses the configured model to propose a code repair, revalidates the candidate and preserves it as a Git ref. The catalog agent observes the bundled local authoritative/published product records and requests a separate model decision.

**At `AWAITING_OPERATOR`:** Read `decision`, `findings`, proposed SKU and value, and `digest`. The CLI explicitly offers **[1] APPROVE**, **[2] REJECT**, and **[3] DEFER**. Type `1`, `approve`, `approved`, or `accept` to authorize the exact reviewed local change. Type `2`/`reject` or `3`/`defer` for a deliberate no-write outcome. The signed reviewer grant remains bound to the displayed run ID and proposal digest. Do not approve unfamiliar data or a customer endpoint. Explicit rejection or deferral returns exit code 0 **without** a release PASS; this is not a qualification. Do **not** approve unfamiliar data or a customer endpoint. A positive local example may show SKU `P-1` with published `119.00` versus authoritative `100.00`; those values are illustrative configuration, not a universal rule.

On success, the program prints `status: PASS`, `scope: LOCAL_TWO_MODEL_VERTICAL_PASS`, `run_id`, `evidence`, `workbench`, and `external_production_qualification: NOT_PERFORMED`. **Only a real completed output with exit code 0 is PASS.**


**Long-running calls:** While engineering and catalog models work, the operator now prints actual `STAGE_STARTED` / `STAGE_COMPLETED` events and a 15-second `EXECUTION_IN_PROGRESS` heartbeat. Waiting is normal for local inference; `Ctrl+C` deliberately interrupts the workflow and returns a blocked result. If you interrupt, inspect the saved `run.json` and only use catalog recovery if its engineering candidate was verified. Do not assume `REVIEW_STARTED` means completion.

## Step 5 — Inspect the run and workbench

Copy the *report path printed for your actual run*, not a historic path:

```bash
cd ~/agentic-systems-portfolio

python3 - <<'PY'
import json
from pathlib import Path
reports=sorted(Path("artifacts/operator-runs").glob("*/run.json"),
               key=lambda p:p.stat().st_mtime,reverse=True)
if not reports:
    print("NO_RUNS_FOUND")
else:
    p=reports[0]; d=json.loads(p.read_text())
    root=p.parent
    print("RUN_ID=",d.get("run_id"),"STATE=",d.get("state"))
    print("ENGINEERING=",(d.get("engineering") or {}).get("status"))
    print("CATALOG=",(d.get("catalog") or {}).get("status"))
    for s in d.get("stages",[]):
        print("STAGE=",s.get("name"),s.get("state"),s.get("error"))
    for name in ("qualification.json","workbench.html","run.events.sqlite3",
                 "run.effects.sqlite3","runtime.json"):
        print(name, "EXISTS=", (root/name).exists())
    if (root/"qualification.json").exists():
        q=json.loads((root/"qualification.json").read_text())
        print("QUALIFICATION=",q.get("qualification"))
        print("EXTERNAL_PRODUCTION=",q.get("external_production_qualification"))
    print("WORKBENCH_PATH=",root/"workbench.html")
PY
```

Open the printed `workbench.html` in your browser from WSL or Windows. It is a local HTML artifact; the execution journal is a separate persisted SQLite file. The `artifacts/` outputs are **ignored by Git** and should remain private. The reviewed, sanitized public example is at [evidence/local-two-model-qualification-2026-10-13.json](evidence/local-two-model-qualification-2026-10-13.json).

## Workbench navigation

The offline workbench is an **operator evidence console**, not an editable workflow graph or a live control plane. It groups engineering, catalog and orchestration summaries above a searchable native-event table. Select an event to inspect its observed payload, stable event ID and recorded parent ID. Filter by lane or search event descriptions/IDs to investigate tool execution. Times are local display conversions of the recorded nanosecond timestamps.

For the latest local run, regenerate the HTML **without any model inference or publication**:

```bash
cd ~/agentic-systems-portfolio

RUN_DIR="artifacts/operator-runs/7afab186563b4893834dbeaff71cee78"
PYTHONPATH=src python3 -m agentic_portfolio.workbench \
  --report "$RUN_DIR/run.json" \
  --output "$RUN_DIR/workbench.html"
printf 'WORKBENCH_RC=%s\n' "$?"
```

Replace `RUN_DIR` with your actual output path. The browser must be refreshed after regeneration. The journal is read and hash-verified; this viewer cannot mutate runs. Lane labels are UI classifications of observed event names and payloads, **not additional agent identities**. Parent IDs are actual journal relationships; the UI does not invent dependencies.

## Unified operator-workbench acceptance

The read-only workbench provides a complete *evidence-backed local* lifecycle:
**engineering verification → catalog review → human authorization →
conditional HTTP publication → independent readback**. Lifecycle cards
are the interface's documented interpretation of persisted run state.
Only fields supported by the run report are shown as confirmed. A
chronological handoff is **not** a native parent/child dependency.

The activity explorer opens in **Paired operations** mode. Each Git,
validation, model, and HTTP operation is paired using the exact native
start-event ID referenced by the completion event's `parent_id`.
Incomplete operations display `INCOMPLETE`; a failed operation is never
rendered as success. Select an operation to see its inputs, outputs,
measured latency or duration, outcome, exact causal parent, and buttons
to inspect its **original start/completion/parent journal events**. Use
**Native events** to see every source event in order. Both views use the
same verified source journal; switching modes does not execute code.

The stage timeline distinguishes each observed attempt. For example,
the catalog review attempt can report `AWAITING_APPROVAL`, followed by
a separately recorded authorized publication attempt. The generated
workbench and the input journal remain in the ignored private
`artifacts/operator-runs/` directory, not in Git.

**Full single-vertical acceptance:** Run the regression suite; regenerate
the HTML from a qualified run; open the result in Chrome; verify the
business change, signed approval/readback lifecycle, paired operations,
native event drill-down, attempt boundaries, and zero clipping at the
target operator viewport. A generated HTML file alone is not browser
qualification. Production PIM/CMS integration is not included in this
local evidence-workbench release.

## One-command complete workbench acceptance (no model calls or writes)

After an operator session has already returned `LOCAL_TWO_MODEL_VERTICAL_PASS`,
run this **single read-only closure command** against its preserved directory.
It independently re-checks the signed reviewer grant **at the original journal-recorded completion timestamp** (historical audit validity, not a renewal or new authorization), Git candidate, native
hash-linked journal, durable verified effect and final readback; checks the
five-phase lifecycle and paired model/HTTP spans; then rebuilds the UI.

```bash
cd ~/agentic-systems-portfolio

RUN_DIR="artifacts/operator-runs/7afab186563b4893834dbeaff71cee78"
PYTHONPATH=src python3 -m agentic_portfolio.operator_workbench_acceptance \
  --report "$RUN_DIR/run.json" \
  --output "$RUN_DIR/workbench.html" \
  --allowed-signers "$HOME/.config/agentic-systems-portfolio/allowed_signers"
ACCEPTANCE_RC=$?
printf 'OPERATOR_WORKBENCH_ACCEPTANCE_RC=%s\n' "$ACCEPTANCE_RC"
```

Expected successful classification: `LOCAL_OPERATOR_WORKBENCH_VERTICAL` and
return code 0, with the exact run ID, five lifecycle states, count of original
native events, count of paired operations, and rebuilt HTML path.
Failures remain `BLOCKED` and return code 2. This command **never** invokes
a model or HTTP PUT; it only revalidates existing local artifacts.
Opening the HTML in Chrome is still necessary to verify browser layout and
interactions: automated evidence acceptance is not a claim of visual
publisher-quality acceptance.

## Final Chrome operator interaction acceptance

After the read-only acceptance command returns `LOCAL_OPERATOR_WORKBENCH_VERTICAL`
with RC 0, refresh the regenerated local `workbench.html` in Chrome.
Verify these interactions on the **same preserved run**, without model calls
or HTTP publication:

1. The starting inspector displays the signed-approval, publication,
   independent-readback and operation-count overview; the table's Lane
   column shows `engineering` on one line at desktop width.
2. Select **Catalog** and confirm only its recorded operations remain.
   Select **All activity** to reset the filter.
3. Select **Paired operations**, then select an observed HTTP operation.
   The inspector must display its actual start/completion identifiers and
   any recorded result or duration. Select **Inspect completion event**
   to navigate to the exact native journal record.
4. Select **Inspect causal parent** on an operation whose parent is
   recorded. Verify that the inspector shows the actual native parent ID
   rather than an inferred dependency.
5. Switch between **Native events** and **Paired operations**, search by
   event identifier, select a stage attempt, then clear the search.
   Check that the original 64-event denominator is preserved.
6. Toggle raw evidence JSON on and off. The default view must remain
   concise, and no panel should overlap or conceal controls.

A screenshot verifies layout but does not demonstrate every click.
For complete browser interaction closure, record the results of these
six checks. This is a read-only local console, not a live control plane.

## Recovery without starting from scratch

**Catalog model returned an empty response or failed after engineering verified:** Use the **exact failed report path** from the `REVIEW_STARTED` output:

```bash
cd ~/agentic-systems-portfolio

PYTHONPATH=src python3 -m agentic_portfolio.operator_session \
  --base-config config/local-vertical.example.json \
  --resume-report /absolute/path/to/previous/run.json \
  --run-root artifacts/operator-runs \
  --reviewer local-agentic-reviewer \
  --ssh-private-key "$HOME/.ssh/agentic-approval-ed25519" \
  --allowed-signers "$HOME/.config/agentic-systems-portfolio/allowed_signers"

printf 'RECOVERY_RC=%s\n' "$?"
```

This recovery path requires a verified persisted engineering candidate and reissues the catalog model decision; it does not rerun successful engineering. Use it only for an incomplete review; **not** as a general replay of an already published effect.

**Catalog decision already shown, but approval prompt interrupted:** Do not rerun inference. Review the saved `run.json` and exact decision digest. If you explicitly approve that local correction, complete the preserved run using:

```bash
cd ~/agentic-systems-portfolio

RUN_DIR="/absolute/path/to/previous/run-directory"
PYTHONPATH=src python3 -m agentic_portfolio.operator_release \
  --config "$RUN_DIR/runtime.json" \
  --report "$RUN_DIR/run.json" \
  --reviewer local-agentic-reviewer \
  --ssh-private-key "$HOME/.ssh/agentic-approval-ed25519" \
  --allowed-signers "$HOME/.config/agentic-systems-portfolio/allowed_signers" \
  --evidence "$RUN_DIR/qualification.json" \
  --workbench "$RUN_DIR/workbench.html" \
  --confirm-local-publish

printf 'RELEASE_RC=%s\n' "$?"
```

**Signing failure (exit 255):** Verify that the specified private key and `allowed_signers` files exist, the key is readable and the trust-file reviewer name matches `--reviewer`. Do not share private keys or private configs.

**Partial or uncertain PUT:** Do not manually repeat writes. Inspect the event/effect state and follow the guarded reconciliation path described in [OPERATOR_RELEASE.md](OPERATOR_RELEASE.md). No automatic retry should be interpreted as a successful release.

## Operator state glossary

| Output | Meaning | Action |
|---|---|---|
| `REVIEW_STARTED` | New private execution allocated | Wait for model and validation |
| `CATALOG_RECOVERY` | Existing verified engineering reused | Wait for catalog decision |
| `AWAITING_OPERATOR` | A real proposal awaits explicit approval | Review findings, decide |
| `REJECTED` / `DEFERRED`, RC 0 | Explicit no-write decision (not a PASS) | Preserve run; no publication |\n| `INVALID_DECISION` / `BLOCKED`, RC 2 | Bad input or actual acceptance failure | Inspect preserved report; no PASS |
| `LOCAL_TWO_MODEL_VERTICAL_PASS`, RC 0 | Local integrated qualification completed | Open evidence and workbench |
| `NOT_PERFORMED` (external) | No customer production validation | Do not claim production release |

For architecture and full acceptance gates, see [INTEGRATED_VERTICAL_RELEASE_CONTRACT.md](INTEGRATED_VERTICAL_RELEASE_CONTRACT.md). For the operator-confirmed qualifying run, see [LOCAL_RELEASE_2026-10-13.md](LOCAL_RELEASE_2026-10-13.md).
