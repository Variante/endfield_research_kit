"""Share checks and native proofs across one ``export.bat`` run.

``scripts.webui.export`` opens a run folder under ``webui/data/_build`` and
names it in ``ENDFIELD_EXPORT_RUN`` for every child process. Within that run:

- the complete reader-code snapshot is taken once at the start and once at
  the end; every check in between reuses the start snapshot, and a changed
  reader fails the run at its end;
- the installed game is assumed not to change while the run is going, so a
  pure native proof (its result depends only on the selected native inputs,
  the reader code and its contracts) is derived once and reused by every
  later step, page and process of the same run.

Outside a run (direct ``python -m`` builds, tests) nothing is shared and
every caller keeps its own per-call checks. The run folder is deleted when
the run ends; no proof outlives the run that derived it.

This module imports neither script line, so both can use it.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import shutil
import threading
import time
from contextlib import contextmanager
from pathlib import Path, PurePath
from typing import Any, Callable

ENV = "ENDFIELD_EXPORT_RUN"
SCHEMA = "endfield.export-run.v1"
_RUN_FILE = "run.json"
_MEMORY: dict[tuple[str, str], bytes] = {}
_RUN_STATE: dict[str, Any] = {"dir": None, "reader": None}


def run_dir() -> Path | None:
    """Return the active run folder, or None outside an ``export.bat`` run."""
    value = os.environ.get(ENV)
    if not value:
        return None
    folder = Path(value)
    if _RUN_STATE["dir"] != folder:
        if not (folder / _RUN_FILE).is_file():
            return None
        _RUN_STATE.update(dir=folder, reader=None)
        _MEMORY.clear()
    return folder


def _load_run(folder: Path) -> dict[str, Any]:
    run = json.loads((folder / _RUN_FILE).read_text(encoding="utf-8"))
    if run.get("schema") != SCHEMA:
        raise ValueError(f"export-run:schema-mismatch:{run.get('schema')}")
    return run


def reader_snapshot() -> dict[str, Any] | None:
    """Return a private copy of the run's start reader snapshot, if in a run."""
    folder = run_dir()
    if folder is None:
        return None
    blob = _RUN_STATE["reader"]
    if blob is None:
        blob = _RUN_STATE["reader"] = pickle.dumps(_load_run(folder)["readerInputs"],
                                                   protocol=pickle.HIGHEST_PROTOCOL)
    return pickle.loads(blob)


def _plain(value: Any) -> Any:
    if isinstance(value, PurePath):
        return {"path": Path(value).resolve().as_posix()}
    if isinstance(value, dict):
        return {"dict": [[_plain(k), _plain(v)] for k, v in value.items()]}
    if isinstance(value, (list, tuple)):
        return {type(value).__name__: [_plain(item) for item in value]}
    if isinstance(value, (set, frozenset)):
        return {"set": sorted((_plain(item) for item in value), key=repr)}
    if isinstance(value, float):
        return {"float": value.hex()}
    if isinstance(value, bytes):
        return {"bytes": value.hex()}
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"export-run:unsupported-key-type:{type(value).__name__}")


def proof_key(*parts: Any) -> str | None:
    """A stable digest for literal call arguments, or None when unsupported."""
    try:
        text = json.dumps(_plain(list(parts)), sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError, OSError):
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_proof(family: str, key: str | None, compute: Callable[[], Any], *,
              keep: Callable[[Any], bool] = lambda result: True) -> Any:
    """Derive a pure proof once per run and hand every caller its own copy.

    Outside a run, or for an unsupported key, ``compute`` simply runs. Only a
    result accepted by ``keep`` and pickle-able is shared; an exception is
    never shared.
    """
    folder = run_dir()
    if folder is None or key is None:
        return compute()
    slot = (family, key)
    blob = _MEMORY.get(slot)
    path = folder / "proofs" / family / f"{key}.pickle"
    if blob is None:
        try:
            blob = path.read_bytes()
        except OSError:
            blob = None
        if blob is not None:
            _MEMORY[slot] = blob
    if blob is not None:
        return pickle.loads(blob)
    result = compute()
    if not keep(result):
        return result
    try:
        blob = pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:
        return result
    _MEMORY[slot] = blob
    path.parent.mkdir(parents=True, exist_ok=True)
    # Threads of one process can derive the same proof at once, so the
    # partial name carries the thread too. When another writer already
    # published the proof, Windows may refuse the replace while that file is
    # open; the published copy holds the same pure result, so keep it.
    partial = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.part")
    partial.write_bytes(blob)
    try:
        os.replace(partial, path)
    except PermissionError:
        partial.unlink(missing_ok=True)
        if not path.is_file():
            raise
    return pickle.loads(blob)


@contextmanager
def export_run(root: Path, *, reader_snapshot_fresh: Callable[[], dict],
               reader_changes: Callable[[dict, dict], dict]):
    """Open a run folder for the duration of one export run.

    The reader snapshot is taken at entry and again at exit; a difference
    raises RuntimeError after the run so its published output is reported
    as built against changed reader code.
    """
    if os.environ.get(ENV):
        yield Path(os.environ[ENV])
        return
    folder = Path(root) / f"{time.strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
    folder.mkdir(parents=True, exist_ok=False)
    try:
        before = reader_snapshot_fresh()
        (folder / _RUN_FILE).write_text(json.dumps({"schema": SCHEMA, "readerInputs": before}),
                                        encoding="utf-8")
        os.environ[ENV] = str(folder)
        try:
            yield folder
        finally:
            os.environ.pop(ENV, None)
            _RUN_STATE.update(dir=None, reader=None)
            _MEMORY.clear()
        after = reader_snapshot_fresh()
        if after != before:
            changes = reader_changes(before, after)
            first = next(iter(changes.get("changes", [])), {})
            raise RuntimeError(
                "reader code changed during the export run; its output was built against "
                f"changed readers (changedFiles={changes.get('changedFiles')}, "
                f"first={first.get('path')}, change={first.get('change')})")
    finally:
        shutil.rmtree(folder, ignore_errors=True)
