# Two-agent vertical — observed qualification record

Date: 2026-10-13. Source: operator-supplied WSL terminal output in the associated ChatGPT session. **This record is not an independently signed or reproducible attestation file.** It accurately distinguishes observed evidence from work still needing verification.

## Q1. Previously completed local integrated execution

Run ID: `277b9020-2c0d-4564-b202-01d6ac3f49da`.
Observed outcome: `PASS` (local integration).
Regression: 27/27 PASS.
Engineering DeepSeek R1 8B produced a real source edit (`return x + 1` → `return x + 2`); baseline test failed; post-edit test passed; candidate Git SHA `7470b62c58f8c2349317557a9e3ff6ef93cf184b` persisted. Original checkout untouched. Engineering stage 20,319 ms.
Catalog deterministic reconciliation of SKU `P-1` observed published price `119.00` versus authoritative `100.00`; actual SQLite-backed HTTP conditional PUT returned 200; independent HTTP reread showed no remaining differences. Catalog stage 23.784 ms.
Scope: local LM Studio, Git, SQLite, HTTP. **Catalog publication was deterministic, not model-directed, in this run.** No external production deployment was demonstrated.

## Q2. Two-model interruption and recovery

Run ID: `31398dd5-ef83-4ac4-8124-efbacf17e44e`.
Engineer's actual repair succeeded with candidate SHA `ed39b89c79094e9b949635bf778df8f9facd9e85`, while original source revision `536b68d0bd280dce260a8bb99acb659f226ca5ab` was retained. Measured engineering stage 23,631.921 ms. The first catalog inference stalled and was interrupted (exit 130); a subsequent attempt returned empty model content (exit 2). The implemented resume path reused the already-verified Git candidate rather than repeating it.

Direct live DeepSeek model-format diagnostic completed in **2.438 seconds**, with a valid JSON response, 26 prompt tokens, 129 completion tokens and 105 reasoning tokens.

The resumed **real catalog-model invocation** returned:
```json
{
  "action":"ESCALATE",
  "skus":["P-1"],
  "rationale":"Price discrepancy observed for SKU P-1: expected value is 100.00 but actual price is 119.00, indicating uncertain evidence or an ambiguous record requiring review."
}
```
Catalog decision digest: `acf6f6f660254b63d66e1757f751fb124993563ccbe4270126dc26bb11352a13`.
Final state: `BLOCKED_CATALOG`; publication not performed. **This was a valid escalation and must not be silently reinterpreted as approval to publish.**

Operator later reported 34/34 automated tests PASS at commit `cf8f140`.

## Q3. Authority policy remediation committed AFTER those observations

The catalog agent now accepts configured authority policy identifying the trusted source and the precise set of correctable fields. An attempted model `CORRECT` without the matching source-authority policy is rejected. The policy is included in the review decision digest. A separate test was added for missing authority, excluded price field, and valid price authorization.

**These changes were not yet tested or exercised by the operator when this document was committed.** They do not prove a new successful catalog-model publication.

## Closure classification

| Requirement | Evidence and status |
|---|---|
| Genuine local DeepSeek engineering repair | Q1 and Q2 observed PASS |
| Baseline failure, actual patch, post-test PASS | Q1 and Q2 observed PASS |
| Persistent candidate SHA | Q1 and Q2 observed PASS |
| Real local HTTP conditional product update and independent readback | Q1 observed PASS |
| Second model invoked with observed catalog discrepancy | Q2 observed PASS, ESCALATE |
| Model-authorized catalog publication | **OPEN**: needs new CORRECT proposal, explicit digest review, HTTP PUT, reread |
| Source authority restricted to allowed fields | Committed; operator qualification **OPEN** |
| Durable once-only replay across interrupted publishing | **OPEN** |
| Identity-authenticated human approval / signature | **OPEN** |
| External customer production connectors and operational qualification | **OPEN** |

**Do not claim 100% production completion from these local results.** The next qualification must run the updated regression, obtain a new grounded correction decision with the explicit authority policy, record its reviewed digest, and independently verify the ensuing publication. Any missing or conflicting evidence is a blocking failure, not a PASS.


## Q4. Authority-policy regression and real two-model correction proposal (operator observed)

The first authority-policy regression was red: 34 tests succeeded and one existing decision-repeatability test errored because its second invocation omitted the now-required authority policy. This was a test-fixture error, **not** a reason to relax the runtime authorization guard. It was corrected in commit `e8dc43c`. The operator subsequently ran the complete suite: **35 tests passed; `TEST_RC=0`; 3.030 seconds**.

Using the existing run ID `31398dd5-ef83-4ac4-8124-efbacf17e44e` and reusing the previously verified engineering Git candidate, the operator supplied the explicit authority policy:

```json
{"catalog_is_source_of_truth":true,"correctable_fields":["price"]}
```

The actual loaded DeepSeek model independently evaluated the live catalog mismatch and returned:

```json
{
  "action":"CORRECT",
  "skus":["P-1"],
  "rationale":"The authoritative catalog is trusted as per authority_policy's 'catalog_is_source_of_truth': true, and the affected field 'price' is allowlisted in correctable_fields. Identities are unambiguous with a single SKU provided."
}
```

**Observed decision digest:** `e8b1b13926564ee73ab7965e54812002e7e76e2ce14825f72949a8e34d5c94ca`.

**Observed run result:** `BLOCKED_CATALOG`; `catalog.status=AWAITING_APPROVAL`; `engineering.status=VERIFIED_CANDIDATE_PERSISTED`; `writeback_performed=false`; `VERTICAL_RC=2`. The catalog model **did not publish**; this is the correct safety outcome while authorization remains pending.

The operator has not yet shown a new explicitly approved HTTP publication, post-write reread, or final `PASS` from the two-model run. The earlier deterministic publication Q1 is separate and cannot satisfy this missing gate.

### Evidence custody and reproducibility

The above values were transcribed from operator-supplied terminal output. Runtime JSON at `artifacts/two-model-review.json` and the original private configuration exist on the operator's WSL filesystem, **not in this repository by virtue of this Markdown document**. This document does not prove contents of files that have not been committed or independently fetched. Keep secrets out of committed configs and evidence. For reproducible qualification, retain the machine-generated stage report (with any sensitive tokens redacted), Git candidate object/ref and environment/model version together with this record.

### Updated closure

| Gate | Latest status |
|---|---|
| 35-test suite on `e8dc43c` | **PASS**, operator observed |
| Actual DeepSeek engineering patch, Git commit and independent test | **PASS**, operator observed |
| Recovery of persisted candidate | **PASS**, operator observed |
| Live catalog LLM decision grounded in observation and authority policy | **PASS**, operator observed |
| Model decision bound to content hashes, ETag and authority policy | Implementation and regression PASS; real `CORRECT` digest observed |
| Exact correction approved by identified human | **OPEN** |
| Two-model authorized publication and independent readback | **OPEN** |
| Safe publishing replay after process termination | **OPEN** |
| Production deployment security, connectors, loads and user impact | **OPEN** |
