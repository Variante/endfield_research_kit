"""Fail-closed provenance for a selected process's audited JSON contract opens.

The caller freezes ordinary contract files before importing consumers, installs
this CPython hook and verifies its probe. Every observed read is authenticated
before it opens and all consumed pins are rechecked at completion. Unopened
contracts are not declared unused by another process or unaudited native I/O.
Input failures remain latched when a consumer catches the raised exception.
This is a provenance observer, not a security boundary. Native binaries, Python
sources, VFS inputs and non-contract reports still need their own gates.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Callable, Mapping


class ContractReadScopeError(ValueError):
    """A watched input is unknown, writable, linked or changed."""


class ContractReadScope:
    probe_event = 'endfield.contract-read-scope.probe'

    def __init__(self, root: Path, frozen: Mapping[str, dict],
                 verify: Callable[[dict], None]):
        if not isinstance(frozen, Mapping) or not callable(verify):
            raise ContractReadScopeError('contract-read-scope.input: frozen pins and verifier required')
        self.root = self._key(root)
        self.prefix = self.root + os.sep
        self.verify = verify
        self.frozen = {}
        for path, pin in frozen.items():
            key = self._key(path)
            if (not key.startswith(self.prefix) or not key.endswith('.json')
                    or key in self.frozen or not isinstance(pin, dict)
                    or self._key(pin.get('path', '')) != key):
                raise ContractReadScopeError(f'contract-read-scope.freeze: invalid or duplicate pin {path!r}')
            self.frozen[key] = dict(pin)
        self.observed = {}
        self.probe_count = 0
        self.open_count = 0
        self.active = True
        self._local = threading.local()
        self._lock = threading.RLock()
        self._failure_lock = threading.Lock()
        self.first_failure = None
        self.failure_count = 0

    @staticmethod
    def _key(path) -> str:
        if not isinstance(path, (str, bytes, os.PathLike)):
            raise ContractReadScopeError('contract-read-scope.path: filesystem path required')
        return os.path.normcase(os.path.abspath(os.fsdecode(path)))

    def _verify(self, pin):
        previous = getattr(self._local, 'verifying', False)
        self._local.verifying = True
        try:
            self.verify(pin)
        finally:
            self._local.verifying = previous

    def _remember_failure(self, error):
        # A different thread can reject an open while the verifier holds the
        # pin lock. The failure latch must not wait for that verifier's lock.
        with self._failure_lock:
            self.failure_count += 1
            if self.first_failure is None:
                self.first_failure = {'type': type(error).__name__, 'detail': str(error)[:5000]}

    def _raise_prior_failure(self):
        with self._failure_lock:
            failure = None if self.first_failure is None else dict(self.first_failure)
        if failure is not None:
            raise ContractReadScopeError('contract-read-scope.prior-input-failure: ' + failure['detail'])

    def __call__(self, event, args):
        if not self.active or getattr(self._local, 'verifying', False):
            return
        if event == self.probe_event:
            if len(args) == 1 and args[0] is self:
                self.probe_count += 1
            return
        if event != 'open':
            return
        try:
            self._observe_open(args)
        except Exception as error:
            self._remember_failure(error)
            raise

    def _observe_open(self, args):
        if len(args) != 3:
            raise ContractReadScopeError('contract-read-scope.event: complete open arguments required')
        path, mode, flags = args
        if isinstance(path, int):
            return  # A descriptor is not assigned a guessed path.
        key = self._key(path)
        if not key.startswith(self.prefix) or not key.endswith('.json'):
            return
        if (type(flags) is not int or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
                or mode is not None and (not isinstance(mode, str) or any(c in mode for c in 'wax+'))):
            raise ContractReadScopeError(f'contract-read-scope.read-only: writable or unsupported open {key}')
        if key not in self.frozen:
            raise ContractReadScopeError(f'contract-read-scope.unfrozen: contract opened after freeze {key}')
        if self._key(Path(key).resolve()) != key:
            raise ContractReadScopeError(f'contract-read-scope.link: linked contract path {key}')
        with self._lock:
            self._verify(self.frozen[key])
            self.observed[key] = self.frozen[key]
            self.open_count += 1

    def check_consumed(self):
        if not self.active or self.probe_count < 1:
            raise ContractReadScopeError('contract-read-scope.installation: active observed hook probe required')
        with self._lock:
            self._raise_prior_failure()
            for key in sorted(self.observed):
                try:
                    self._verify(self.observed[key])
                except Exception as error:
                    self._remember_failure(error)
                    raise
            self._raise_prior_failure()

    def close(self):
        """Disable this observer; a CPython audit hook itself is not removable."""
        self.active = False

    def summary(self):
        return {'scope':'Current CPython audited JSON contract opens only',
            'probeObserved':self.probe_count > 0,'active':self.active,
            'frozenContracts':len(self.frozen),'observedContractOpens':self.open_count,
            'consumedContracts':len(self.observed),
            'consumedPins':[self.observed[key] for key in sorted(self.observed)],
            'failureLatched':self.first_failure is not None,
            'observedInputFailures':self.failure_count,
            'firstInputFailure':None if self.first_failure is None else dict(self.first_failure),
            'unopenedContractsProvedUnusedByOtherProcessesOrNativeIO':False,
            'nativeOrParserOrVfsGatesReplaced':False}
