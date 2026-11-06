"""Lazy parameter operations owned by one guarded LevelScript decode batch.

The codecs keep their existing prepared-capability checks. Only the exact
native scope, explicit game root and pool may borrow a batch operation; every
child's original fresh entry/exit validation still runs. Unused children are
never opened, failed entries are not cached, and no capability outlives exit.
"""
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from pathlib import Path

from scripts.game_data.memorypack.operation_native_validation import (
    _CURRENT as _NATIVE_SCOPE, _suspend_native_validation,
)


_CURRENT = ContextVar("levelscript_batch_param_operations", default=None)


def _factory(kind):
    if kind == "buff_ptr":
        from scripts.game_data.levelscript_buff_ptr_param_native import current_buff_ptr_params
        return current_buff_ptr_params
    if kind == "camera_shake":
        from scripts.game_data.levelscript_camera_shake_param_native import current_camera_shake_params
        return current_camera_shake_params
    if kind == "entity_list":
        from scripts.game_data.levelscript_entity_list_param_native import current_entity_list_params
        return current_entity_list_params
    raise ValueError(f"levelscript-parameter-batch:unknown-kind:{kind}")


class _ParamBatch:
    def __init__(self, game_root, strings, native_scope, progress):
        self.root = Path(game_root).resolve()
        self.strings = strings
        self.native_scope = native_scope
        self.progress = progress
        self.active = True
        self.stack = ExitStack()
        self.operations = {}
        self.requests = {}

    def acquire(self, kind):
        self.requests[kind] = self.requests.get(kind, 0) + 1
        if kind not in self.operations:
            if self.progress:
                self.progress(f"opening {kind} parameter operation")
            # These independent public operations authenticate themselves. An
            # outer node cache cannot replace either of their bookend proofs.
            with _suspend_native_validation():
                operation = self.stack.enter_context(_factory(kind)(
                    game_root=self.root, strings=self.strings))
            self.operations[kind] = operation
        return self.operations[kind]

    def statistics(self):
        return {kind: dict(requests=count, opened=int(kind in self.operations))
                for kind, count in sorted(self.requests.items())}


def selected_batch_param(kind, *, game_root, strings):
    """Return a prepared operation only to this batch's selected decoder."""
    batch = _CURRENT.get()
    if (batch is None or not batch.active or batch.native_scope.closed
            or _NATIVE_SCOPE.get() is not batch.native_scope
            or game_root is None or strings is not batch.strings
            or Path(game_root).resolve() != batch.root):
        return None
    return batch.acquire(kind)


@contextmanager
def batch_param_operations(*, game_root, strings, native_scope, progress=None):
    batch = _ParamBatch(game_root, strings, native_scope, progress)
    token = _CURRENT.set(batch)
    try:
        yield batch
    finally:
        batch.active = False
        _CURRENT.reset(token)
        try:
            if batch.operations and progress:
                progress("checking parameter operation exit proofs")
        finally:
            with _suspend_native_validation():
                batch.stack.close()
