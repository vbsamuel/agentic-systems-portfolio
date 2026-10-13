"""Scoped native causal instrumentation for actual tool and model calls.

No input bodies, authorization headers, tokens, secrets or full URLs are
persisted. Every child span belongs to the invoking recorded stage.
"""
from contextlib import contextmanager
from contextvars import ContextVar

_active=ContextVar("agentic_active_span",default=None)

@contextmanager
def stage_scope(journal,run_id,parent_id):
    token=_active.set((journal,run_id,parent_id))
    try:
        yield
    finally:
        _active.reset(token)

def emit(kind,payload,parent_id=None):
    active=_active.get()
    if active is None:
        return None
    journal,run_id,stage_parent=active
    return journal.append(run_id,kind,payload,parent_id=parent_id or stage_parent)["event_id"]
