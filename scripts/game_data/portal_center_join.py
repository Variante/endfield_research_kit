"""Join stored portal templates and LevelData overrides to verified runtime fields.

The report identifies authored destination vectors. Native claims prove the
conditional assignment and loading route, but this tool does not observe a
portal interaction or a live selected streaming center.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.dynamic_streaming_config_join import _fresh_export
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import field_defaults, native_enum_members, runtime_type_name
from scripts.game_data.leveldata_binary import frame_leveldata_named_prefix
from scripts.game_data.memorypack.interactive import decode_interactive_template_memorypack
from scripts.repo_paths import REPO_ROOT


FORMAT = "endfield.portal-center-join.v3"
PORTAL_TYPES = {
    "LoadingPortalComponentData": "LoadingPortal",
    "SeamlessPortalComponentData": "SeamlessPortal",
}
UNION_CONTRACT = CONTRACTS_DIR / "levelscript_union_tags.json"
RUNTIME_CONTRACT = CONTRACTS_DIR / "dynamic_visibility_runtime_claims.json"
DEFAULT_VFS_REPORT = REPO_ROOT / "reports/animestudio/vfs_understanding_latest.json"
DEFAULT_RUNTIME_REPORT = REPO_ROOT / "reports/animestudio/dynamic_visibility_runtime_claims_latest.json"
DEFAULT_EXPORT_SUMMARY = REPO_ROOT / "reports/export/export_full_summary.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/portal_center_join_latest.json"


class PortalCenterJoinError(ValueError):
    """A selected source, format, or identity relation is not proven."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _union_contract(path: Path, native_inputs: dict[str, str]) -> tuple[dict[str, dict[str, Any]], str]:
    raw = path.read_bytes()
    contract = json.loads(raw)
    if (contract.get("schema") != "endfield.levelscript-union-tags.v1"
            or contract.get("nativeInputs") != native_inputs):
        raise PortalCenterJoinError(f"{path}: union contract schema or native inputs differ")
    rows = contract.get("families", {}).get("BaseComponentData") or []
    selected = {row["name"]: row for row in rows if row.get("name") in PORTAL_TYPES}
    if set(selected) != set(PORTAL_TYPES) or any(row.get("memberCount") != 1 for row in selected.values()):
        raise PortalCenterJoinError(f"{path}: portal union identities differ")
    return selected, _sha(raw)


def _runtime_report(path: Path, native_inputs: dict[str, str]) -> str:
    contract, digest = read_reviewed_contract(
        RUNTIME_CONTRACT, schema="endfield.dynamic-visibility-runtime-claims.v16",
        label="dynamic_visibility_runtime", status="validated",
    )
    report = json.loads(path.read_bytes())
    methods = report.get("methods") or []
    symbols = {row.get("symbol") for row in methods}
    required = {
        "Entity.AssignLevelEntityData", "InteractiveRootComponent.OnLevelDataAssigned",
        "LogicComponentWithDynamicProperty.AssignData",
        "LogicComponentWithDynamicProperty.InitSelf",
        "EntityManager._CreateInLevelClientInteractiveInfo",
        "LevelData.TryGetInteractiveInLevelData",
        "InteractiveInfo.InitFromLevelData",
        "BaseEntityData.SetupInLevelData",
        "EntityNode._SpawnEntity",
        "EntityNode.get_dependencyGroupId", "EntityNode.SetInAoi",
        "EntityNode.SetAoiState", "EntityNode._LaunchSpawnPipeline",
        "EntityNode.SwitchToNextPipelineState",
        "GridProcessor._TryDoSetInAoi", "NodeGrid._AddToForceLoadNodes",
        "NodeGrid.TickUpdateGridRange", "NodeGrid.OnNodeSkipAoiCheck",
        "ObjectContainer.SpawnEntity", "ObjectContainer.LoadEntity",
    } | {
        f"{kind}PortalComponentData.get_interactiveComponentType"
        for kind in ("Loading", "Seamless")
    } | {
        f"{kind}PortalComponentData.ApplyProperties"
        for kind in ("Loading", "Seamless")
    } | {
        f"{kind}PortalComponentData.<ApplyProperties>b__{suffix}_1"
        for kind, suffix in (("Loading", 30), ("Seamless", 26))
    } | {
        f"{kind}PortalComponent.OnInitDone"
        for kind in ("Loading", "Seamless")
    }
    if (report.get("format") != "endfield.dynamic-visibility-runtime-claims-audit.v3"
            or report.get("status") != "validated" or report.get("failures")
            or report.get("nativeInputs") != native_inputs
            or report.get("contractSha256") != digest
            or symbols != set(contract["methods"])
            or len(methods) != len(contract["methods"])
            or not required <= symbols):
        raise PortalCenterJoinError(f"{path}: runtime claim report provenance differs")
    return digest


def _vfs_report(
    path: Path, expected_input_set_sha256: str, native_inputs: dict[str, str],
    gameassembly: Path, metadata: Path,
) -> str:
    raw = path.read_bytes()
    report = json.loads(raw)
    fingerprints = {Path(row["path"]).name: row for row in report.get("buildFingerprints") or []}
    assembly_row = fingerprints.get("GameAssembly.dll") or {}
    metadata_row = fingerprints.get("global-metadata.dat") or {}
    if (report.get("format") != "animestudio-vfs-boundary-audit"
            or report.get("schemaVersion") != 1
            or report.get("inputSetSha256", "").upper() != expected_input_set_sha256.upper()
            or not report.get("summary", {}).get("fullAuditPassed")
            or assembly_row.get("sha256", "").upper() != native_inputs["gameAssemblySha256"]
            or metadata_row.get("sha256", "").upper() != native_inputs["metadataSha256"]
            or Path(assembly_row.get("path", "")).resolve() != gameassembly.resolve()
            or Path(metadata_row.get("path", "")).resolve() != metadata.resolve()):
        raise PortalCenterJoinError(f"{path}: VFS audit/input-set/build provenance differs")
    return _sha(raw)


def _finite_vector(values: list[Any], label: str) -> list[float]:
    if len(values) != 3 or any(not isinstance(value, (int, float)) for value in values):
        raise PortalCenterJoinError(f"{label}: expected three numeric coordinates")
    vector = [float(value) for value in values]
    if not all(math.isfinite(value) for value in vector):
        raise PortalCenterJoinError(f"{label}: nonfinite coordinate")
    return vector


def _unsigned_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+", value) or int(value) > 0xFFFFFFFFFFFFFFFF:
        raise PortalCenterJoinError(f"{label}: expected decimal UInt64")
    return value


def _stored_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise PortalCenterJoinError(f"{label}: expected Boolean")
    return value


def _param_vector(value: dict[str, Any], label: str) -> list[float]:
    array = value.get("valueArray") or {}
    atoms = array.get("values") or []
    if value.get("typeRaw") != 11 or array.get("status") != "present" or array.get("count") != 3 or len(atoms) != 3:
        raise PortalCenterJoinError(f"{label}: expected ParamValue Vector3 type 11 with three atoms")
    vector = []
    for atom in atoms:
        bits = atom.get("valueBit64")
        if (type(bits) is not int or not -(1 << 31) <= bits < (1 << 31)
                or atom.get("valueString") is not None):
            raise PortalCenterJoinError(f"{label}: Vector3 atom is not a signed low-32-bit float")
        vector.append(struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0])
    return _finite_vector(vector, label)


def _param_string(value: dict[str, Any], label: str) -> str:
    array = value.get("valueArray") or {}
    atoms = array.get("values") or []
    if (value.get("typeRaw") != 7 or array.get("status") != "present"
            or array.get("count") != 1 or len(atoms) != 1
            or not isinstance(atoms[0].get("valueString"), str)):
        raise PortalCenterJoinError(f"{label}: expected one ParamValue string type 7")
    return atoms[0]["valueString"]


def _portal_hierarchy(image: Any) -> dict[str, str]:
    expected = {
        "Beyond.Gameplay.LoadingPortalComponentData": "Beyond.Gameplay.Core.InteractiveCoreComponentData",
        "Beyond.Gameplay.SeamlessPortalComponentData": "Beyond.Gameplay.Core.InteractiveCoreComponentData",
        "Beyond.Gameplay.LoadingPortalComponent": "Beyond.Gameplay.Core.InteractiveLogicBaseComponent",
        "Beyond.Gameplay.SeamlessPortalComponent": "Beyond.Gameplay.Core.InteractiveLogicBaseComponent",
        "Beyond.Gameplay.Core.InteractiveCoreComponentData": "Beyond.Gameplay.Core.DynamicPropertyComponentData",
        "Beyond.Gameplay.Core.InteractiveLogicBaseComponent": "Beyond.Gameplay.Core.InteractiveCoreComponent",
        "Beyond.Gameplay.Core.InteractiveCoreComponent": (
            "Beyond.Gameplay.Core.LogicComponentWithDynamicProperty`1"
            "<Beyond.Gameplay.Core.InteractiveCoreComponentData>"
        ),
    }
    types = {image.metadata.type_full_name(owner): owner for owner in image.metadata.types}
    table_va = int(image.registration["types"], 16)
    actual: dict[str, str] = {}
    for name, parent in expected.items():
        owner = types.get(name)
        if owner is None or not 0 <= owner.parent_index < int(image.registration["typesCount"]):
            raise PortalCenterJoinError(f"selected native hierarchy lacks {name}")
        pointer = image.pe.u64_at_va(table_va + owner.parent_index * 8)
        actual[name] = runtime_type_name(image.pe, image.metadata, pointer)
        if actual[name] != parent:
            raise PortalCenterJoinError(f"selected native parent differs: {name}: {actual[name]}")
    return actual


def _properties(entry: dict[str, Any], label: str) -> dict[str, dict[str, Any]]:
    prop_map = entry.get("properties") or {}
    values = prop_map.get("values") or []
    if prop_map.get("status") != "present" or prop_map.get("count") != len(values):
        raise PortalCenterJoinError(f"{label}: component property map is incomplete")
    properties: dict[str, dict[str, Any]] = {}
    for row in values:
        key = row.get("key")
        if not isinstance(key, str) or key in properties:
            raise PortalCenterJoinError(f"{label}: duplicate or unnamed property {key!r}")
        properties[key] = row["value"]
    return properties


def _templates(
    root: Path, union_rows: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], int]:
    directory = root / "game/Json/Interactive/InteractiveData"
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise PortalCenterJoinError(f"{directory}: no InteractiveData templates")
    templates: dict[str, dict[str, Any]] = {}
    for path in paths:
        raw = path.read_bytes()
        result = decode_interactive_template_memorypack(path, raw, len(raw))
        if result is None:
            raise PortalCenterJoinError(f"{path}: InteractiveData template is unrecognized")
        decoded = result["decoded"]
        if not decoded.get("exactLength") or decoded.get("componentParseError"):
            raise PortalCenterJoinError(f"{path}: InteractiveData template does not close to EOF")
        rows = [*decoded.get("componentListPrefixRows", []),
                *decoded.get("componentListParsedPayloadRows", [])]
        portal = [row for row in rows if row.get("type") in PORTAL_TYPES]
        if not portal:
            continue
        if len(rows) != decoded.get("componentListCount") or len(portal) != 1:
            raise PortalCenterJoinError(f"{path}: portal template does not close to physical EOF")
        component = portal[0]
        kind = component["type"]
        union = union_rows[kind]
        if (component.get("tag") != f"0x{union['tag']:04x}"
                or component.get("memberCount") != union["memberCount"]):
            raise PortalCenterJoinError(f"{path}: portal component union identity differs")
        maps = [row for row in decoded.get("componentPropertyMapComponents", [])
                if row.get("type") == kind]
        if len(maps) != 1 or maps[0].get("bodyShape") != "singlePropertyMap":
            raise PortalCenterJoinError(f"{path}: portal property map is not exact")
        sample = {row["key"]: row for row in maps[0].get("sampleProperties", [])}
        position = sample.get("tp_position") or {}
        level = sample.get("tp_level_id") or {}
        if (position.get("valueType") != 11 or position.get("valueCount") != 3
                or level.get("valueType") != 7 or level.get("valueCount") != 1):
            raise PortalCenterJoinError(f"{path}: portal default properties differ")
        name = decoded.get("name")
        if not isinstance(name, str) or name in templates:
            raise PortalCenterJoinError(f"{path}: duplicate or missing template name {name!r}")
        templates[name] = {
            "name": name,
            "componentType": kind,
            "unionTag": component["tag"],
            "defaultDestinationLevelId": (level["values"][0].get("stringTail") or ""),
            "defaultDestinationPosition": _finite_vector(position["preview"], f"{path}:tp_position"),
            "source": path.relative_to(root).as_posix(),
            "sourceSha256": _sha(raw),
        }
    if set(row["componentType"] for row in templates.values()) != set(PORTAL_TYPES):
        raise PortalCenterJoinError(f"{directory}: expected both portal component families")
    return templates, len(paths)


def _instances(
    root: Path, templates: dict[str, dict[str, Any]], enum_ids: dict[str, int],
) -> tuple[list[dict[str, Any]], int, int]:
    directory = root / "game/Json/LevelData"
    paths = sorted(directory.rglob("*.json"))
    if not paths:
        raise PortalCenterJoinError(f"{directory}: no LevelData files")
    needles = {name: name.encode("utf-8") for name in templates}
    result: list[dict[str, Any]] = []
    matched_files = 0
    for path in paths:
        raw = path.read_bytes()
        if not any(needle in raw for needle in needles.values()):
            continue
        frame = frame_leveldata_named_prefix(raw)
        if (frame.get("status") != "exact_named_schema"
                or frame.get("bytesConsumed") != len(raw)):
            raise PortalCenterJoinError(f"{path}: selected portal LevelData is not framed to EOF")
        interactives = frame.get("fields", {}).get("interactives") or {}
        values = interactives.get("values") or []
        if interactives.get("count") != len(values):
            raise PortalCenterJoinError(f"{path}: interactive collection count differs")
        found_in_file = 0
        for interactive in values:
            name = interactive.get("entityDataIdKey")
            if name not in templates:
                continue
            found_in_file += 1
            template = templates[name]
            component_key = enum_ids[PORTAL_TYPES[template["componentType"]]]
            components = interactive.get("componentProperties") or {}
            entries = components.get("entries") or []
            if components.get("status") != "present" or components.get("count") != len(entries):
                raise PortalCenterJoinError(f"{path}:{name}: incomplete component override map")
            matches = [entry for entry in entries if entry.get("componentTypeRaw") == component_key]
            if len(matches) > 1:
                raise PortalCenterJoinError(f"{path}:{name}: duplicate portal component overrides")
            override = None
            if matches:
                properties = _properties(matches[0], f"{path}:{name}")
                if "tp_position" not in properties or "tp_level_id" not in properties:
                    raise PortalCenterJoinError(f"{path}:{name}: portal override has no destination pair")
                override = {
                    "destinationLevelId": _param_string(properties["tp_level_id"], f"{path}:{name}:tp_level_id"),
                    "destinationPosition": _param_vector(properties["tp_position"], f"{path}:{name}:tp_position"),
                }
            source_position = interactive.get("position") or {}
            force_load = _stored_bool(
                interactive.get("forceLoad"), f"{path}:{name}:forceLoad",
            )
            result.append({
                "template": name,
                "componentType": template["componentType"],
                "componentTypeRaw": component_key,
                "levelLogicId": interactive.get("levelLogicId"),
                "dependencyGroupId": _unsigned_id(
                    interactive.get("dependencyGroupId"), f"{path}:{name}:dependencyGroupId",
                ),
                "forceLoad": force_load,
                "sourcePosition": _finite_vector(
                    [source_position.get(axis) for axis in ("x", "y", "z")],
                    f"{path}:{name}:sourcePosition",
                ),
                "instanceOverride": override,
                "source": path.relative_to(root).as_posix(),
                "sourceSha256": _sha(raw),
            })
        if found_in_file:
            matched_files += 1
        else:
            raise PortalCenterJoinError(f"{path}: portal template name found without an interactive instance")
    if not result:
        raise PortalCenterJoinError(f"{directory}: no portal instances in selected LevelData corpus")
    return result, len(paths), matched_files


def audit(
    *, gameassembly: Path, metadata: Path, game_root: Path, export_root: Path,
    export_summary: Path, runtime_report: Path, vfs_report: Path,
    expected_input_set_sha256: str,
) -> dict[str, Any]:
    union_raw = json.loads(UNION_CONTRACT.read_bytes())
    native_inputs = union_raw.get("nativeInputs") or {}
    gate = check_installed_native_inputs(
        native_inputs["gameAssemblySha256"], native_inputs["metadataSha256"],
        gameassembly=gameassembly, metadata=metadata,
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise PortalCenterJoinError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    selected = {"gameAssemblySha256": gate.gameassembly_sha256.upper(),
                "metadataSha256": gate.metadata_sha256.upper()}
    unions, union_digest = _union_contract(UNION_CONTRACT, selected)
    runtime_digest = _runtime_report(runtime_report, selected)
    vfs_digest = _vfs_report(
        vfs_report, expected_input_set_sha256, selected, gameassembly, metadata,
    )
    _freshness, export_summary_digest = _fresh_export(
        game_root=game_root, export_root=export_root, export_summary=export_summary,
        gameassembly=gameassembly, metadata=metadata,
    )
    image = open_native_image(gameassembly, metadata)
    hierarchy = _portal_hierarchy(image)
    members = native_enum_members(
        image.metadata, field_defaults(image.metadata), image.pe, image.registration,
        "Beyond.Gameplay.InteractiveComponentType",
    )
    enum_ids = {row["name"]: row["id"] for row in members}
    if any(name not in enum_ids for name in PORTAL_TYPES.values()):
        raise PortalCenterJoinError("selected InteractiveComponentType enum lacks a portal component")
    if len({enum_ids[name] for name in PORTAL_TYPES.values()}) != len(PORTAL_TYPES):
        raise PortalCenterJoinError("selected portal enum IDs alias")
    templates, template_files = _templates(export_root, unions)
    instances, level_files, matched_files = _instances(export_root, templates, enum_ids)
    return {
        "format": FORMAT,
        "status": "validated",
        "inputSetSha256": expected_input_set_sha256.upper(),
        "nativeInputs": selected,
        "sourceProvenance": {
            "unionContractSha256": union_digest,
            "runtimeContractSha256": runtime_digest,
            "runtimeReportSha256": _sha(runtime_report.read_bytes()),
            "vfsReportSha256": vfs_digest,
            "exportSummarySha256": export_summary_digest,
        },
        "portalComponentEnum": {name: enum_ids[name] for name in PORTAL_TYPES.values()},
        "nativeHierarchy": hierarchy,
        "corpus": {
            "interactiveTemplateFiles": template_files,
            "portalTemplates": len(templates),
            "levelDataFiles": level_files,
            "matchedLevelDataFiles": matched_files,
            "portalInstances": len(instances),
            "instancesWithDestinationOverride": sum(row["instanceOverride"] is not None for row in instances),
            "instancesWithoutDependencyGroup": sum(row["dependencyGroupId"] == "0" for row in instances),
            "forceLoadInstances": sum(row["forceLoad"] for row in instances),
        },
        "templates": sorted(templates.values(), key=lambda row: row["name"]),
        "instances": instances,
        "evidenceBoundary": {
            "exact": "Selected template and LevelData records close to physical EOF; component tags and enum keys match selected native inputs. Each placed portal's unsigned dependencyGroupId and authored forceLoad flag are preserved separately from its destination override.",
            "direct": "Selected native getters match each portal data class to the enum key in LevelData. The logic-ID interactive lookup passes the selected LevelInteractiveData into InteractiveInfo and BaseEntityData. The node dependency-group getter reads that level object's stored ID; for zero, SetInAoi has a direct state route that maps true to the selected Intrested enum member. GridProcessor and NodeGrid methods call an unnamed native AOI setter with the same checked group lookup and state mapping; the grid processor passes its named node and AOI flag, and the force-load route passes true. SetAoiState can launch the node pipeline, which has a spawn branch passing level data through ObjectContainer to the ordinary allocator before component pre-initialization. The portal class hierarchy selects the dynamic-property component family; its shared body creates a component blackboard from template properties. The interactive root enumerates the LevelData component override map and loads selected property rows into a component blackboard; ApplyProperties binds tp_position to the component's tpPosition field.",
            "conditional": "If an observed portal node receives an AOI entry update, its readiness guard and the spawn pipeline branch succeed, and the selected unpatched data application and portal interaction branches execute, the stored override vector can reach the level-loading and streaming-center path.",
            "unresolved": "No live AOI update, node spawn, component value, portal interaction, selected scene, or actual dealer center is observed. The stored forceLoad flag is not by itself proof of the runtime skip-AOI flag. The generic data application uses a shared System.Object code pointer and an unnamed dispatch helper.",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, default=REPO_ROOT / "export_full")
    parser.add_argument("--export-summary", type=Path, default=DEFAULT_EXPORT_SUMMARY)
    parser.add_argument("--runtime-report", type=Path, default=DEFAULT_RUNTIME_REPORT)
    parser.add_argument("--vfs-report", type=Path, default=DEFAULT_VFS_REPORT)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        report = audit(
            gameassembly=args.gameassembly, metadata=args.metadata,
            game_root=args.game_root, export_root=args.export_root,
            export_summary=args.export_summary, runtime_report=args.runtime_report,
            vfs_report=args.vfs_report,
            expected_input_set_sha256=args.expected_input_set_sha256,
        )
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        print(f"portal-center-join: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    corpus = report["corpus"]
    print(f"Portal center join passed: templates={corpus['portalTemplates']} "
          f"instances={corpus['portalInstances']} overrides={corpus['instancesWithDestinationOverride']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
