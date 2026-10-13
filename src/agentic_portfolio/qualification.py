"""Measured end-to-end qualification over real Git and CSV workflows.

No fake LLM calls, fabricated speedups, or production metrics. Every stage runs
an actual operation and stores observed results. This is an integration
qualification of the *implemented* workflows, not autonomous-agent readiness.
"""
import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from agentic_portfolio.orchestrator import Queue
from agentic_portfolio.engineering_flow import git_revision, verify_change
from agentic_portfolio.catalog_flow import Cases


class Qualification:
    def __init__(self):
        self.steps = []

    def check(self, workflow, name, execute, evaluate):
        start = time.perf_counter_ns()
        try:
            observation = execute()
            accepted = bool(evaluate(observation))
            detail = {'observation': observation, 'accepted': accepted}
        except Exception as exc:
            accepted = False
            detail = {'exception_type': type(exc).__name__, 'exception': str(exc),
                      'accepted': False}
        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        event = dict(workflow=workflow, stage=name, elapsed_ms=round(elapsed_ms, 3),
                     **detail)
        self.steps.append(event)
        return event

    def summary(self):
        workflows = {}
        for name in sorted({s['workflow'] for s in self.steps}):
            group = [s for s in self.steps if s['workflow'] == name]
            workflows[name] = {
                'passed': sum(s['accepted'] for s in group),
                'total': len(group),
                'duration_ms': round(sum(s['elapsed_ms'] for s in group), 3),
                'qualified': all(s['accepted'] for s in group),
            }
        return {
            'schema_version': 1, 'qualification_scope': 'local-integrations',
            'autonomous_multi_agent_qualified': False,
            'live_catalog_connector_qualified': False,
            'automated_correction_writeback_qualified': False,
            'stage_results': self.steps, 'workflows': workflows,
            'passed': all(s['accepted'] for s in self.steps),
        }


def run(output: str):
    q = Qualification()
    with tempfile.TemporaryDirectory(prefix='agentic-qualification-') as directory:
        root = Path(directory)
        worktree = root / 'code'
        worktree.mkdir()
        def git(*args):
            return subprocess.run(['git', '-C', str(worktree), *args],
                                  text=True, capture_output=True, check=True).stdout.strip()
        q.check('engineering', 'initialize_real_git_repository',
                lambda: (git('init', '-q'), git('-c', 'user.name=Qualification',
                '-c', 'user.email=qual@example.org', 'commit', '--allow-empty',
                '-qm', 'baseline'), git_revision(str(worktree)))[-1],
                lambda sha: isinstance(sha, str) and len(sha) == 40)
        baseline = git_revision(str(worktree))
        queue = Queue(str(root / 'work.db'))
        q.check('engineering', 'detect_source_drift',
                lambda: _expect_exception(
                    lambda: verify_change(queue, str(worktree), '0'*40, baseline,
                                          ('python3', '-c', 'print("not executed")')),
                    ValueError),
                lambda value: value == 'ValueError')
        good = q.check('engineering', 'run_actual_validation',
                lambda: vars(verify_change(queue, str(worktree), baseline, baseline,
                             ('python3', '-c', 'print("validated")'))),
                lambda result: result['exit_code'] == 0
                    and 'validated' in result['stdout']
                    and result['status'] == 'AWAITING_REVIEW')
        if good['accepted']:
            wid = good['observation']['job_id']
            q.check('engineering', 'approve_with_named_reviewer',
                    lambda: (queue.review(wid, True, 'QA', 'Independent validation passed'),
                             queue.db.execute('SELECT state FROM jobs WHERE id=?',
                                              (wid,)).fetchone()[0])[-1],
                    lambda state: state == 'APPROVED')
        q.check('engineering', 'reject_failed_validation',
                lambda: _failed_check(queue, str(worktree), baseline),
                lambda value: value == 'FAILED')
        q.check('engineering', 'verify_hash_chained_event_record',
                queue.verify_chain, lambda result: result is True)
        queue.db.close()

        keys = ['sku', 'title', 'description', 'price', 'currency',
                'availability', 'image_url']
        truth = dict(zip(keys, ['P-1', 'Example', 'Valid description', '100.00',
                               'USD', 'in stock', '/img/example.jpg']))
        page = dict(truth, price='119.00')
        catalog, channel = root/'catalog.csv', root/'published.csv'
        def write(path, value):
            with path.open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=keys)
                writer.writeheader()
                writer.writerow(value)
            return hashlib.sha256(path.read_bytes()).hexdigest()

        input_digest = q.check('catalog', 'create_two_independent_source_snapshots',
                               lambda: [write(catalog, truth), write(channel, page)],
                               lambda hashes: len(hashes) == 2
                                   and all(len(item) == 64 for item in hashes)
                                   and hashes[0] != hashes[1])
        cases = Cases(str(root/'cases.db'))
        q.check('catalog', 'identify_real_price_discrepancy',
                lambda: cases.ingest(str(catalog), str(channel)),
                lambda result: result['status'] == 'REVIEW_REQUIRED'
                    and result['open_cases'] == 1
                    and len(result['findings']) == 1
                    and result['findings'][0]['field'] == 'price'
                    and result['findings'][0]['severity'] == 'high'
                    and result['auto_published'] is False)
        fingerprint = cases.db.execute('SELECT fingerprint FROM cases').fetchone()[0]
        q.check('catalog', 'reject_premature_closure',
                lambda: _expect_exception(
                    lambda: cases.resolve(fingerprint, 'Reviewer', 'Looks fixed',
                                          str(catalog), str(channel)), ValueError),
                lambda value: value == 'ValueError')
        q.check('catalog', 'apply_external_observed_correction',
                lambda: write(channel, truth),
                lambda digest: digest == hashlib.sha256(catalog.read_bytes()).hexdigest())
        q.check('catalog', 'independently_recheck_and_close_case',
                lambda: (cases.resolve(fingerprint, 'Reviewer',
                     'Source and observed channel match after correction',
                     str(catalog), str(channel)),
                     cases.db.execute('SELECT status,reviewer FROM cases WHERE fingerprint=?',
                                      (fingerprint,)).fetchone())[-1],
                lambda value: value == ('RESOLVED', 'Reviewer'))
        q.check('catalog', 'verify_zero_remaining_differences',
                lambda: cases.ingest(str(catalog), str(channel)),
                lambda result: result['status'] == 'PASS'
                    and result['findings'] == []
                    and result['open_cases'] == 0)
        cases.db.close()

    artifact = q.summary()
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, indent=2, sort_keys=True) + '\n'
    output_path.write_text(payload, encoding='utf-8')
    print(json.dumps({'report': str(output_path),
                      'stages': len(artifact['stage_results']),
                      'passed': artifact['passed'],
                      'workflows': artifact['workflows']}))
    return 0 if artifact['passed'] else 2


def _expect_exception(callback, expected):
    try:
        callback()
    except expected as exc:
        return type(exc).__name__
    return 'NO_EXCEPTION'


def _failed_check(queue, repository, revision):
    result = verify_change(queue, repository, revision, revision,
                           ('python3', '-c', 'raise SystemExit(9)'))
    if result.status != 'FAILED' or result.exit_code != 9:
        return 'UNEXPECTED_EXECUTION_RESULT'
    try:
        queue.review(result.job_id, True, 'QA', 'Must not approve failed test')
    except ValueError:
        return 'FAILED'
    return 'INVALID_APPROVAL_ACCEPTED'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='artifacts/qualification.json')
    args = parser.parse_args()
    return run(args.output)


if __name__ == '__main__':
    sys.exit(main())
