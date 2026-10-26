"""Data-page views of the maintained exact/bounded LevelScript owner frame.

The adapter publishes the reader's result unchanged. Native input drift makes
this dataset unavailable before record decoding or cache reuse; bounded owner
frames and all-refusal diagnostics remain visible, without runtime claims.
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.levelscript_binary import (
    LevelScriptTopLevelFramingError,
    frame_levelscript_named,
)
from scripts.game_data.levelscript_union_tags import contract_native_inputs
from scripts.game_data.string_pool import export_string_pool
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data.spawner_records_native import check_spawner_records_native_inputs
from scripts.game_data.serialization_roots_native import check_root_native_inputs
from scripts.game_data.leveldata_function_area_native import check_function_area_native_inputs
from scripts.game_data.leveldata_airwalls_native import check_airwall_native_inputs
from scripts.repo_paths import REPO_ROOT
from scripts.webui.data_inspector.contract import source_descriptor
from scripts.webui.data_inspector.levelscript_native_inputs import selected_child_native_signature


_HASH = re.compile(r"^[0-9A-Fa-f]{64}$")


def reader_dependency_signature(
    *, source_root: Path | None = None, contracts_root: Path | None = None,
) -> dict[str, Any]:
    """Current LevelScript reader/layout/native-contract bytes for cache reuse.

    This is a generated cache input, not a native evidence gate or a digest pin.
    Production shares the canonical complete raw-package/helper snapshot.
    Explicit source-root overrides retain the bounded family fixture scope.
    This only invalidates a page cache: it never admits a stored schema receipt.
    Collect each source once per snapshot, including shared helpers and layouts.
    """
    root = source_root if source_root is not None else REPO_ROOT / "scripts/game_data"
    contracts = contracts_root if contracts_root is not None else CONTRACTS_DIR
    lane = root / "codecs/levelscript"
    paths = {root / "levelscript_binary.py"}
    paths.update(root.glob("levelscript*.py"))
    paths.update(lane.rglob("*.py"))
    paths.update(lane.rglob("*.json"))
    paths.update(contracts.glob("levelscript*.json"))
    if source_root is None:
        return snapshot_complete_reader_inputs()
    return {"algorithm": "current-family-source-length-sha256",
            "files": [_fingerprint(path) for path in sorted(paths)]}


def selected_native_signature(*, family: str = "LevelScript") -> tuple[dict[str, Any], str]:
    """Gate the selected build against the reader's reviewed union-tag inputs."""
    expected = contract_native_inputs()
    signature: dict[str, Any] = {"unionTagNativeInputs": expected, "family": family}
    if any(_HASH.fullmatch(str(expected.get(key) or "")) is None
           for key in ("gameAssemblySha256", "metadataSha256")):
        signature["nativeStatus"] = "unavailable"
        return signature, f"{family} union-tag contract native inputs missing or invalid"
    try:
        gate = check_installed_native_inputs(
            expected["gameAssemblySha256"], expected["metadataSha256"],
        )
    except (OSError, ValueError, RuntimeError) as exc:
        signature["nativeStatus"] = "unavailable"
        return signature, f"{family} native inputs: {type(exc).__name__}: {str(exc)[:500]}"
    signature.update({
        "gameAssemblySha256": gate.gameassembly_sha256,
        "metadataSha256": gate.metadata_sha256,
        "nativeStatus": gate.status,
    })
    source_gates = []
    if family in {"LevelScript", "LevelData"}:
        source_gates.append(("rootSourceGate", "root source", check_root_native_inputs))
    if family == "LevelData":
        source_gates.extend((("airWallGate", "air-wall source", check_airwall_native_inputs),
                             ("functionAreaGate", "FunctionArea source", check_function_area_native_inputs)))
    if family == "SpawnerConfig":
        source_gates.append(("spawnerSourceGate", "native", check_spawner_records_native_inputs))
    if gate.validated:
        for key, label, select in source_gates:
            try:
                source = select()
                signature[key] = {"status":source.status, "detail":source.detail}
            except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
                signature[key] = {"status":"unavailable", "detail":str(exc)[:500]}
            if signature[key]["status"] != "validated":
                signature["nativeStatus"] = signature[key]["status"]
                return signature, f"{family} {label} {signature[key]['status']}: {signature[key]['detail']}"
        if family in {"LevelScript", "LevelScriptTemplateData", "LevelData", "SpawnerConfig"}:
            try:
                signature["readerDependencies"] = reader_dependency_signature()
            except (OSError, ValueError) as exc:
                signature["nativeStatus"] = "unavailable"
                return signature, f"{family} reader dependencies: {str(exc)[:500]}"
    if gate.validated and family in {"LevelScript", "LevelScriptTemplateData"}:
        child_gate = selected_child_native_signature({
            "GameAssembly.dll": gate.gameassembly_sha256,
            "global-metadata.dat": gate.metadata_sha256,
        })
        signature["childNativeGate"] = child_gate
        if child_gate["status"] != "validated":
            signature["nativeStatus"] = child_gate["status"]
            return signature, f"{family} native {child_gate['status']}: {child_gate['detail']}"
    return signature, "" if gate.validated else f"{family} native {gate.status}: {gate.detail or gate.status}"


def levelscript_record(path: Path, export_root: Path, *, game_root=None) -> dict[str, Any]:
    """Keep exact/bounded status, opaque ranges and refused-profile evidence."""
    relative = path.relative_to(export_root).as_posix()
    source = source_descriptor(path, export_root=export_root, media_type="application/octet-stream")
    base = {
        "id": relative, "title": path.stem, "source": source,
        "tags": ["level", "levelscript", "memorypack"],
    }
    try:
        decoded = frame_levelscript_named(path.read_bytes(), source=relative, strings=export_string_pool(export_root/'game'/'Json'), game_root=game_root)
    except (OSError, LevelScriptTopLevelFramingError, ValueError) as exc:
        record = {
            **base, "status": "decode_error", "summary": str(exc)[:1200],
            "tags": [*base["tags"], "decode_error"], "diagnostic": str(exc)[:1200],
        }
        diagnostics = getattr(exc, "diagnostics", None)
        if isinstance(diagnostics, list):
            record["facts"] = {"readerDiagnostics": diagnostics}
        return record
    return levelscript_record_from_detail(path, export_root, decoded)


def levelscript_record_from_detail(path: Path, export_root: Path, decoded: dict[str, Any]) -> dict[str, Any]:
    """Present an authenticated reader result unchanged, including source locators."""
    relative = path.relative_to(export_root).as_posix()
    base = {"id": relative, "title": path.stem,
            "source": source_descriptor(path, export_root=export_root, media_type="application/octet-stream"),
            "tags": ["level", "levelscript", "memorypack"]}
    status = str(decoded.get("schemaStatus") or decoded.get("status") or "bounded_partial")
    fields = decoded.get("fields") if isinstance(decoded.get("fields"), dict) else {}
    stop = decoded.get("stopField")
    open_field = decoded.get("openField")
    if stop is None and isinstance(open_field, dict):
        stop = open_field.get("name")
    facts = {
        "reader": decoded.get("reader"),
        "decodedFieldNames": list(fields),
        "serializedMemberCount": decoded.get("serializedMemberCount"),
        "bytesConsumed": decoded.get("bytesConsumed"),
        "stopField": stop,
        "readerRefusalCount": len(decoded.get("readerRefusals") or []),
    }
    parts = [f"named fields={len(fields)}"]
    if facts["bytesConsumed"] is not None:
        parts.append(f"cursor={facts['bytesConsumed']}")
    if stop is not None:
        parts.append(f"open={stop}")
    return {
        **base, "status": status, "summary": "; ".join(parts),
        "tags": [*base["tags"], status], "searchTerms": list(fields),
        "facts": facts, "payload": decoded, "payloadKind": "reader",
    }
