"""Concrete defect-to-review workflow executing real Git and test subprocesses.

Mutating agent steps are intentionally not automatic: a human must provide an
existing candidate revision; this workflow independently validates it.
"""
from dataclasses import dataclass
from pathlib import Path
import subprocess
from .orchestrator import Queue

@dataclass(frozen=True)
class Verification:
    job_id: int
    baseline: str
    candidate: str
    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str
    status: str

def git_revision(repository: str) -> str:
    path = Path(repository).resolve(strict=True)
    proc = subprocess.run(
        ['git', '-C', str(path), 'rev-parse', '--verify', 'HEAD'],
        capture_output=True, text=True, timeout=30, check=True)
    return proc.stdout.strip()

def verify_change(queue: Queue, repository: str, base_revision: str,
                  candidate_revision: str, command: tuple[str, ...],
                  timeout: int = 120) -> Verification:
    """Execute allowlisted argv without a shell, bound to a candidate revision."""
    if not command or not isinstance(command, tuple) or command[0] not in ('python', 'python3', 'pytest'):
        raise ValueError('only explicit Python test commands are supported')
    if not 1 <= timeout <= 3600:
        raise ValueError('invalid timeout')
    current = git_revision(repository)
    job = queue.enqueue(repository, current, 'independent-verify')
    if base_revision != current:
        queue.claim(job, base_revision)
        raise ValueError('baseline mismatch')
    if queue.claim(job, current) != 'RUNNING':
        raise RuntimeError('repository already claimed')
    if candidate_revision != current:
        queue.complete(job, current, False)
        raise ValueError('candidate revision drift')
    try:
        result = subprocess.run(command, cwd=repository, text=True,
                                capture_output=True, timeout=timeout, check=False)
        code, out, err = result.returncode, result.stdout[-16000:], result.stderr[-16000:]
    except subprocess.TimeoutExpired as exc:
        code, out, err = 124, str(exc.stdout or '')[-16000:], 'TIMEOUT'
    after = git_revision(repository)
    passed = code == 0 and after == candidate_revision
    queue.complete(job, after, passed)
    return Verification(job, base_revision, after, command, code, out, err,
                        'AWAITING_REVIEW' if passed else 'FAILED')
