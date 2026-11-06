"""Bounded LevelScript decoding with fresh input bookends.

This operation only shares successful child-native proofs. It grants no owner
EOF or source-receipt authority: the supplied reader retains every refusal.
No decoded result escapes until the native pair, UnityPlayer, complete reader
sources, StringPool and selected LevelScript file roster pass the exit checks.
"""
from __future__ import annotations

from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
import time

from scripts.common import check_installed_native_inputs
from scripts.game_data.levelscript_reader_inputs import (
    reader_input_changes, snapshot_complete_reader_inputs, snapshot_string_pool_inputs,
)
from scripts.game_data.levelscript_union_tags import contract_native_inputs
from scripts.game_data.memorypack.operation_native_validation import (
    _native_validation_scope, _suspend_native_validation,
)
from scripts.game_data.string_pool import export_string_pool
from scripts.game_data.memorypack.levelscript_param_batch import batch_param_operations


class LevelScriptDecodeBatchError(ValueError):
    def __init__(self, gate, source, expected, actual):
        self.diagnostic = dict(validator="levelscriptDecodeBatch", gate=gate,
                               source=str(source), expected=expected, actual=actual)
        super().__init__(json.dumps(self.diagnostic, ensure_ascii=False, sort_keys=True))


def _native_inputs(game_root):
    assembly = game_root.parent / "GameAssembly.dll"
    metadata = game_root / "il2cpp_data/Metadata/global-metadata.dat"
    pins = contract_native_inputs()
    gate = check_installed_native_inputs(
        pins["gameAssemblySha256"], pins["metadataSha256"],
        gameassembly=assembly, metadata=metadata,
    )
    if gate.status != "validated":
        raise LevelScriptDecodeBatchError("selected-native-inputs", game_root,
                                         pins, dict(status=gate.status, detail=gate.detail))
    # Measure current bytes, including the third binary used by child proofs.
    measured = {}
    for name, path in (
        ("GameAssembly.dll", assembly), ("global-metadata.dat", metadata),
        ("UnityPlayer.dll", assembly.parent / "UnityPlayer.dll"),
    ):
        with path.open("rb") as stream:
            measured[name] = hashlib.file_digest(stream, "sha256").hexdigest().upper()
    expected = {"GameAssembly.dll": pins["gameAssemblySha256"],
                "global-metadata.dat": pins["metadataSha256"]}
    if any(measured[name] != digest.upper() for name, digest in expected.items()):
        raise LevelScriptDecodeBatchError("selected-native-byte-join", game_root, expected, measured)
    return measured


def _row(path, raw):
    return dict(path=path.as_posix(), length=len(raw),
                sha256=hashlib.sha256(raw).hexdigest().upper())


def _sources(root, recursive=True):
    return {"files": [_row(path, path.read_bytes())
                      for path in sorted(root.rglob("*.json") if recursive else root.glob("*.json")) if path.is_file()]}


def _unchanged(gate, source, before, after):
    if before != after:
        changes = reader_input_changes(before, after)
        raise LevelScriptDecodeBatchError(gate, source, "unchanged complete input set", changes)


def decode_levelscript_batch(source_root, decode, *, game_root, progress=None,
                            json_root=None, recursive=True, operation=None):
    """Return ``(records, audit)`` after decoding the current family's files.

    ``decode(path, raw, strings, game_root)`` may preserve bounded/error rows;
    it must not publish them. All paths and native selection are explicit.
    A level-directory caller supplies its family's Json root and can select
    only immediate files; entry and exit use exactly the same source roster.
    An optional source operation enters and exits inside these bookends, so
    its final native/source checks cannot run after the batch's exit proof.
    """
    root = Path(source_root).resolve()
    pool_root = Path(json_root).resolve() if json_root is not None else root.parent
    selected = Path(game_root).resolve()
    if not root.is_dir():
        raise LevelScriptDecodeBatchError("source-root", root, "existing directory", "missing")
    started = time.monotonic()
    # Independent/nested operations must never inherit an earlier proof.
    with _suspend_native_validation():
        try:
            reader_before = snapshot_complete_reader_inputs()
            native_before = _native_inputs(selected)
            source_before = _sources(root, recursive)
            pool_before = snapshot_string_pool_inputs(pool_root)
            strings = export_string_pool(pool_root)
            records = []
            total = len(source_before["files"])
            last_progress = started
            if progress:
                progress(f"decode {total} files; selected inputs checked")
            with _native_validation_scope(
                gameassembly=selected.parent / "GameAssembly.dll",
                metadata=selected / "il2cpp_data/Metadata/global-metadata.dat",
                native_inputs=native_before, reader_inputs=reader_before,
            ) as scope, batch_param_operations(
                game_root=selected, strings=strings, native_scope=scope, progress=progress,
            ) as params:
                with (nullcontext() if operation is None else operation):
                    for index, source in enumerate(source_before["files"], 1):
                        path = Path(source["path"])
                        raw = path.read_bytes()
                        actual = _row(path, raw)
                        if source != actual:
                            raise LevelScriptDecodeBatchError("source-read-drift", path, source, actual)
                        records.append(decode(path, raw, strings, selected))
                        now = time.monotonic()
                        if progress and (index == total or now - last_progress >= 15):
                            progress(f"decoded {index}/{total}: {path.relative_to(root)} ({now-started:.1f}s)")
                            last_progress = now
            if progress:
                progress("checking input drift before returning decoded records")
            _unchanged("reader-input-drift", root, reader_before, snapshot_complete_reader_inputs())
            _unchanged("source-input-drift", root, source_before, _sources(root, recursive))
            _unchanged("string-pool-drift", pool_root / "StringPool", pool_before,
                       snapshot_string_pool_inputs(pool_root))
            native_after = _native_inputs(selected)
            if native_before != native_after:
                raise LevelScriptDecodeBatchError("native-input-drift", selected,
                                                 native_before, native_after)
            reuse = scope.statistics()
            reuse["entryExitBookendsPassed"] = True
            return records, dict(sourceCount=total, nativeValidationReuse=reuse,
                                 paramOperationReuse=params.statistics())
        except OSError as error:
            raise LevelScriptDecodeBatchError("input-read", error.filename or root,
                                             "readable current input", str(error)[:1000]) from error
