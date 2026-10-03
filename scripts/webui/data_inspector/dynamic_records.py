"""Publish authenticated stored DynamicStreaming components, without extracting."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import resolve_installed_game_data_root, resolve_installed_native_inputs
from scripts.game_data.dynamic_scalar_components_native import (
    decode_authenticated_main, validate_native_layout,
)
from scripts.game_data.dynamic_stream_area_corpus import (
    DEFAULT_CLI, DEFAULT_LEDGER, DEFAULT_OUTER, MAIN_NAME_RE, load_current_inputs,
)
from scripts.game_data.dynamic_root_comp_native import (
    decode_authenticated_root_components, load_current_template_asset,
    validate_native_layout as validate_root_layout,
)
from scripts.webui.data_inspector.contract import source_descriptor


def main_raw_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.bytes") if MAIN_NAME_RE.search(path.as_posix()))


def _raw_path(export_root: Path, virtual_path: str) -> Path:
    normalized = virtual_path.replace("\\", "/")
    if not normalized.startswith("Data/DynamicStreaming/"):
        raise ValueError(f"unexpected DynamicStreaming source: {virtual_path}")
    path = export_root / "raw" / normalized.removeprefix("Data/")
    path.resolve().relative_to((export_root / "raw/DynamicStreaming").resolve())
    return path


def _attach_authored_owners(components: list[dict[str, Any]], references: list[dict[str, Any]],
                           fields: dict[str, int]) -> int:
    """Join only the same grid, proved vector field and stored element index."""
    indexed: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
    for reference in references:
        key = (reference["gridOrdinal"], reference["fieldIndex"], reference["componentOrdinal"])
        indexed.setdefault(key, []).append(reference)
    owned = 0
    for component in components:
        matches = indexed.get((component["gridOrdinal"], fields[component["name"]], component["ordinal"]), [])
        if any(reference["component"] != component["name"]
               or reference["gridUniqueId"] != component["uniqueId"] for reference in matches):
            raise ValueError("authored root association differs from the selected component field/grid")
        component["authoredOwners"] = [{**reference["authoredOwner"],
                                       "directoryOrdinal": reference["directoryOrdinal"]} for reference in matches]
        owned += bool(matches)
    return owned


def dynamic_main_records(export_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Recheck native inputs, the current roster and every raw byte join before reuse."""
    gameassembly, metadata = resolve_installed_native_inputs()
    layout, main, digests, native_inputs = validate_native_layout(gameassembly, metadata)
    outer = json.loads(DEFAULT_OUTER.read_text(encoding="utf-8"))
    _, sources, provenance = load_current_inputs(
        DEFAULT_OUTER, DEFAULT_LEDGER, DEFAULT_CLI, str(outer.get("inputSetSha256") or ""),
        file_name_re=MAIN_NAME_RE, selection_label="fb_main_*.bytes",
    )
    # Authored ownership needs its own native route and a fresh template asset.
    # A refused owner gate retains only independently proved scalar fields.
    owner_context = None
    owner_signature: dict[str, Any]
    try:
        root_layout, index_layout, root_main, enums, entities, root_digests, root_inputs = validate_root_layout(gameassembly, metadata)
        templates, template_receipt = load_current_template_asset(
            root_layout["templateLookup"], game_root=resolve_installed_game_data_root(),
            export_root=export_root, entity_enum=entities, data_enum=enums,
        )
        owner_context = (root_layout, index_layout, root_main, enums, entities, templates)
        owner_signature = {"status": "validated", "nativeInputs": root_inputs,
                           **root_digests, "template": template_receipt}
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        owner_signature = {"status": "unavailable", "diagnostic": f"{type(exc).__name__}: {str(exc)[:1000]}"}
    fields = {row["name"]: int(row["gridFieldIndex"]) for row in layout["records"]} if owner_context else {}
    records, byte_receipts = [], []
    for source in sources:
        virtual_path = source["path"]
        path = _raw_path(export_root, virtual_path)
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest().upper()
        components = decode_authenticated_main(data, layout=layout, main=main, source=source)
        references: list[dict[str, Any]] = []
        owned = 0
        if owner_context:
            root_layout, index_layout, root_main, enums, entities, templates = owner_context
            references = decode_authenticated_root_components(
                data, layout=root_layout, index_layout=index_layout, main_layout=root_main,
                enum_by_id=enums, entity_enum=entities, templates=templates, source=source,
            )
            owned = _attach_authored_owners(components, references, fields)
        by_type: dict[str, int] = {}
        keys = set()
        for component in components:
            name = component["name"]
            by_type[name] = by_type.get(name, 0) + 1
            for reference in component.get("stringReferences", {}).values():
                if reference.get("status") == "resolved":
                    keys.add(reference["text"])
        byte_receipts.append({"path": virtual_path, "bytes": len(data), "sha256": sha})
        relative = path.relative_to(export_root).as_posix()
        records.append({
            "id": relative, "title": path.stem,
            "source": source_descriptor(path, export_root=export_root, media_type="application/octet-stream"),
            "status": "bounded_partial", "tags": ["world", "dynamic-streaming", "bounded_partial"],
            "summary": f"{len(components)} stored components; authored mission keys={len(keys)}",
            "searchTerms": sorted({*by_type, *keys, *(reference["authoredOwner"]["entityTypeName"] for reference in references)}),
            "facts": {"componentCount": len(components), "byType": by_type, "authoredMissionKeyCount": len(keys),
                      "authoredOwnedComponentCount": owned, "authoredRootReferenceCount": len(references)},
            "payloadKind": "reader",
            "payload": {
                "schemaStatus": "bounded_partial", "components": components,
                "componentLayouts": [row["name"] for row in layout["records"]],
                "authoredRootReferences": references,
                "authoredRootAssociationGate": owner_signature,
                "evidenceBoundary": {"storedComponentFields": "exact", "missionConditionString": "direct",
                                     "authoredRootOwnership": "direct" if owner_context else "unresolved",
                                     "runtimeEntityOwnership": "unresolved", "conditionEvaluation": "unresolved"},
            },
        })
    return records, {
        "nativeStatus": "validated", "nativeInputs": native_inputs, **digests,
        "currentCorpus": provenance, "authenticatedFiles": byte_receipts,
        "authoredRootAssociations": owner_signature,
    }
