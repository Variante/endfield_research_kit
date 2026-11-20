"""Ordered worker-process fan-out for independent per-row corpus checks.

A corpus sweep that reads, hashes and parses every stored row is bound by one
interpreter.  ``ordered_map`` runs one batch function in worker processes and
yields the batch results in submission order, so a caller that merges them
sequentially reproduces the single-process result exactly: row order, failure
order and every cross-row check (duplicates, coverage, joins) stay with the
caller, which is the only place that sees more than one row.

What it guarantees: results arrive in task order; one task (or one worker)
runs the same function in this process without starting a pool; an exception
raised in a worker is re-raised here with its original type; at most
``2 * jobs`` batches are in flight, so memory stays bounded by the batch size.

What it does not do: it proves nothing about the rows, shares no state between
batches beyond the read-only ``shared`` value each worker receives once, and
must not be handed a function whose result depends on another batch.

``ENDFIELD_CORPUS_JOBS`` sets the worker count; ``1`` keeps every sweep in one
process.  The default is capped because the sweeps run beside other builders.
"""
from __future__ import annotations

import os
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from itertools import chain, islice

JOBS_ENV = "ENDFIELD_CORPUS_JOBS"
DEFAULT_JOBS = 8

_SHARED = None


def worker_count() -> int:
    """The configured worker count; fails closed on an unusable setting."""
    value = os.environ.get(JOBS_ENV, "").strip()
    if not value:
        return max(1, min(DEFAULT_JOBS, os.cpu_count() or 1))
    try:
        jobs = int(value)
    except ValueError:
        jobs = 0
    if jobs < 1:
        raise ValueError(f"{JOBS_ENV} must be a positive integer: {value!r}")
    return jobs


def batches(rows, size: int):
    """Contiguous lists of at most ``size`` rows, in iteration order."""
    rows = iter(rows)
    while batch := list(islice(rows, size)):
        yield batch


def _install(shared) -> None:
    global _SHARED
    _SHARED = shared


def _call(function, task):
    return function(_SHARED, task)


def ordered_map(function, tasks, *, shared=None, jobs: int | None = None):
    """Yield ``function(shared, task)`` for every task, in task order.

    ``function`` must be importable at module level and depend only on its
    two arguments.  ``shared`` is sent to each worker once.
    """
    jobs = worker_count() if jobs is None else jobs
    tasks = iter(tasks)
    head = list(islice(tasks, 2))
    if jobs <= 1 or len(head) < 2:
        for task in chain(head, tasks):
            yield function(shared, task)
        return
    pool = ProcessPoolExecutor(max_workers=jobs, initializer=_install, initargs=(shared,))
    try:
        pending = deque()
        for task in chain(head, tasks):
            pending.append(pool.submit(_call, function, task))
            if len(pending) >= jobs * 2:
                yield pending.popleft().result()
        while pending:
            yield pending.popleft().result()
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
