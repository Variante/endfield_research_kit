"""Validate and regenerate the reviewed case-sensitive cutscene lookup contract.

The contract proves that the GenderSelect phase's ``Cutscene_e0m0_1`` literal
reaches a case-sensitive cutscene lookup: no method in the resolver chain
converts case, so the literal does not resolve to the canonical
``cutscene_e0m0_1`` key at runtime. It also records the exact LevelScript
bridge that starts that phase (StartGenderSelect.Execute ->
GameAction.StartGenderSelect -> EventManager.SendGlobal).

Only names survive a client update. ``--regenerate`` re-resolves every method
by type, name and parameter names (through the generic-instantiation table
where a method has no direct body), recounts case conversion across the
resolver bodies, rebuilds the bridge's body hashes and call bytes, and
re-verifies the LevelScript record against the configured export.

Run as: python -m scripts.game_data.cutscene_case_resolution_native --regenerate [--write]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import (
    NATIVE_EVIDENCE_MISSING,
    NATIVE_EVIDENCE_MISMATCHED,
    NATIVE_EVIDENCE_VALIDATED,
    check_installed_native_inputs,
)
from scripts.common import read_json_object_bytes as _read_json
from scripts.common import repo_path as _source_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.ifix_patch_native import (
    DEFAULT_CONTRACT as DEFAULT_IFIX_CONTRACT,
    fixed_method_prefix_matches,
    load_ifix_patch_contract,
)
from scripts.source_paths import ExportLayout


SCHEMA = "cutsceneCaseResolutionNativeContract.v4"
AUDIT_SCHEMA = "cutsceneCaseResolutionNativeContractAudit.v2"
DEFAULT_CONTRACT = CONTRACTS_DIR / "cutscene_case_resolution.json"
#: The lookup chain, named by type, method and parameter names.
RESOLVER_SPECS = {
    "gameAction": ("Beyond.Gameplay.Actions.GameAction", "PlayCutsceneAndGetHandle", None),
    "playCutscene": (
        "Beyond.Gameplay.Core.CutsceneManager", "PlayCutscene",
        ("key", "afterFinish", "existingInteractives", "existingEnemies",
         "existingSceneObjects", "playParam", "queueItemHandle"),
    ),
    "checkCanPlay": ("Beyond.Gameplay.Core.CutsceneManager", "CheckCanPlay", ("key", "cutsceneData")),
    "getGenderedCutsceneId": ("Beyond.Gameplay.NarrativeUtils", "GetGenderedCutsceneId", None),
    "tryGetCinematicData": ("Beyond.Gameplay.Core.CinematicTimelineManagerBase", "TryGetCinematicData", None),
    "tryLoadCutsceneDataByName": (
        "Beyond.Gameplay.Core.CinematicTimelineManagerBase", "_TryLoadCutsceneDataByName", None,
    ),
    "cachedPathTryLoad": ("Beyond.Resource.CachedPathAssetLoader", "TryLoad", ("path", "asset")),
    "cachedPathTypedTryLoad": ("Beyond.Resource.CachedPathAssetLoader", "TryLoad", ("path", "type", "handle")),
    "stringPathHashConstructor": ("Beyond.Resource.StringPathHash", ".ctor", ("str",)),
}
CASE_CONVERSION_METHODS = frozenset({"ToLower", "ToUpper", "ToLowerInvariant", "ToUpperInvariant"})
BRIDGE_ACTION_TYPE = "Beyond.Gameplay.Actions.StartGenderSelect"
BRIDGE_GAME_ACTION = ("Beyond.Gameplay.Actions.GameAction", "StartGenderSelect")
BRIDGE_DISPATCH = ("Beyond.EventManager", "SendGlobal")
BRIDGE_ACTION_NAME = "StartGenderSelect"
MATCH_FIELDS = (
    "module",
    "sourceSha256",
    "line",
    "method",
    "resolvedLiteral",
    "canonicalStoryKey",
    "registryStatus",
)


def load_cutscene_case_resolution_contract(
    contract_path: Path = DEFAULT_CONTRACT,
    *,
    ifix_contract_path: Path = DEFAULT_IFIX_CONTRACT,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
    export_root: Path | None = None,
) -> dict[str, Any]:
    """Validate the reviewed runtime fact and offline association policy.

    ``export_root`` selects the export whose game/ tree holds the recorded
    LevelScript; it defaults to the configured export root.
    """

    path = Path(contract_path)
    source_file = _source_file(path)
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any, source: str = source_file) -> None:
        failures.append({
            "validator": "cutsceneCaseResolutionNativeContract",
            "gate": gate,
            "sourceFile": source,
            "expected": expected,
            "actual": actual,
        })

    contract, raw, error = _read_json(path)
    if error:
        reject("read_valid_contract", {"readableJsonObject": True}, error)

    def section(name: str) -> dict[str, Any]:
        value = contract.get(name)
        return value if isinstance(value, dict) else {}

    sources = section("sources")
    playback = section("luaPlayback")
    resolver = section("resolver")
    conclusion = section("conclusion")
    association = section("recoveryAssociationPolicy")
    bridge = section("genderSelectBridge")
    bridge_script = bridge.get("levelScript") or {}
    exact_gates = (
        ("schema", SCHEMA, contract.get("schema")),
        ("status", "validated", contract.get("status")),
        ("lua_module", "Phase/GenderSelect/PhaseGenderSelect.lua", playback.get("module")),
        ("lua_method", "PlayCutsceneAndGetHandle", playback.get("method")),
        ("lua_literal", "Cutscene_e0m0_1", playback.get("resolvedLiteral")),
        ("canonical_story_key", "cutscene_e0m0_1", playback.get("canonicalStoryKey")),
        ("registry_status", "case_mismatch_registry_match", playback.get("registryStatus")),
        ("case_conversion_calls", 0, resolver.get("caseConversionCalls")),
        ("ifix_resolver_matches", 0, resolver.get("ifixResolverMatches")),
        ("case_resolution", "case_sensitive", conclusion.get("caseResolution")),
        ("literal_resolution", False, conclusion.get("literalResolvesToCanonicalKey")),
        ("graph_action", "record_native_case_mismatch", conclusion.get("graphAction")),
        ("ownership_action", "none", conclusion.get("ownershipAction")),
        ("association_comparison", "ascii_case_insensitive", association.get("comparison")),
        ("association_unique_key", True, association.get("requiresUniqueCanonicalStoryKey")),
        ("association_result", True, association.get("literalAssociatesToCanonicalKey")),
        ("association_graph_action", "associate_casefolded_playback_reference", association.get("graphAction")),
        ("association_ownership", False, association.get("suppliesMissionOrQuestOwnership")),
        ("association_spatial", False, association.get("suppliesSpatialEvidence")),
        ("gender_select_bridge_status", "validated", bridge.get("status")),
        ("gender_select_action_type", BRIDGE_ACTION_TYPE, bridge.get("actionType")),
        ("gender_select_action", BRIDGE_ACTION_NAME, bridge_script.get("actionName")),
        ("gender_select_story", "cutscene_e0m0_1", bridge.get("storyKey")),
        ("gender_select_conditional", True, bridge.get("conditionalPlayback")),
        ("gender_select_ownership", False, bridge.get("suppliesMissionOrQuestOwnership")),
    )
    for gate, expected, actual in exact_gates:
        if actual != expected:
            reject(gate, expected, actual)
    for label in RESOLVER_SPECS:
        row = resolver.get(label) or {}
        if not (isinstance(row, dict) and row.get("token") and row.get("va")):
            reject(f"resolver_{label}", {"token": "recorded", "va": "recorded"}, row)
    if not resolver.get("rawStringHashEntryPoints"):
        reject("raw_string_hash_entry_points", "recorded", resolver.get("rawStringHashEntryPoints"))

    ifix_audit = load_ifix_patch_contract(
        ifix_contract_path,
        gameassembly=gameassembly,
        metadata=metadata,
    )
    ifix_source = _source_file(ifix_contract_path)
    if ifix_audit.get("status") != NATIVE_EVIDENCE_VALIDATED:
        reject(
            "ifix_contract_status",
            {"status": NATIVE_EVIDENCE_VALIDATED},
            {
                "status": ifix_audit.get("status"),
                "validationFailures": ifix_audit.get("validationFailures") or [],
            },
            str(ifix_audit.get("sourceFile") or ifix_source),
        )
    else:
        installed_patch = str((ifix_audit.get("source") or {}).get("patchSha256") or "").upper()
        if str(sources.get("ifixPatchSha256") or "").upper() != installed_patch:
            reject("ifix_patch_sha256", installed_patch, sources.get("ifixPatchSha256"))
        prefixes = resolver.get("protectedMethodPrefixes") or []
        if (
            not isinstance(prefixes, list)
            or not prefixes
            or any(not isinstance(value, str) or not value for value in prefixes)
        ):
            reject("protected_method_prefixes", {"nonemptyStrings": True}, prefixes)
            prefixes = []
        ifix_hits = fixed_method_prefix_matches(ifix_audit, prefixes)
        if ifix_hits:
            reject("ifix_resolver_matches", [], ifix_hits[:10], str(ifix_audit.get("sourceFile") or ifix_source))

    native = check_installed_native_inputs(
        str(sources.get("gameAssemblySha256") or ""),
        str(sources.get("metadataSha256") or ""),
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        reject(
            "installed_native_inputs",
            {"status": NATIVE_EVIDENCE_VALIDATED},
            {"status": native.status, "detail": native.detail},
        )
    gameassembly_path = getattr(native, "gameassembly", None)
    image = b""
    if native.status == NATIVE_EVIDENCE_VALIDATED and gameassembly_path:
        try:
            image = Path(gameassembly_path).read_bytes()
        except OSError as read_error:
            reject("read_gameassembly", True, str(read_error)[:400])

    # The bridge bodies and their calls are checked against the binary: a
    # changed body or call target fails even on the recorded build.
    if image:
        for method_name, offset_key, bytes_key, target_key in (
            ("execute", "gameActionCallOffset", "gameActionCallBytes", None),
            ("gameAction", "messageDispatchCallOffset", "messageDispatchCallBytes", "messageDispatchTarget"),
        ):
            method = bridge.get(method_name) or {}
            offset, size = method.get("fileOffset"), method.get("bodySize")
            if not isinstance(offset, int) or not isinstance(size, int) or size <= 0:
                reject(f"gender_select_{method_name}_range", {"offset": "int", "size": ">0"}, method)
                continue
            body = image[offset:offset + size]
            actual_hash = hashlib.sha256(body).hexdigest().upper()
            if len(body) != size or actual_hash != str(method.get("bodySha256") or "").upper():
                reject(f"gender_select_{method_name}_body", method.get("bodySha256"), actual_hash)
                continue
            call_offset = method.get(offset_key)
            expected_bytes = bytes.fromhex(str(method.get(bytes_key) or ""))
            actual_bytes = body[call_offset:call_offset + 5] if isinstance(call_offset, int) else b""
            if actual_bytes != expected_bytes or actual_bytes[:1] != b"\xe8":
                reject(f"gender_select_{method_name}_call_bytes", expected_bytes.hex(), actual_bytes.hex())
                continue
            target = (
                (bridge.get("gameAction") or {}).get("virtualAddress")
                if target_key is None else method.get(target_key)
            )
            method_va = int(str(method.get("virtualAddress")), 16)
            actual_target = method_va + call_offset + 5 + struct.unpack_from("<i", actual_bytes, 1)[0]
            if not target or actual_target != int(str(target), 16):
                reject(f"gender_select_{method_name}_call_target", target, hex(actual_target))

    # sourceFile is relative to the export root (layout v2), so the gate reads
    # the configured export rather than a fixed export_full folder.
    script_root = Path(export_root) if export_root is not None else ExportLayout.configured().root
    script_path = script_root / str(bridge_script.get("sourceFile") or "")
    try:
        script_hash = hashlib.sha256(script_path.read_bytes()).hexdigest().upper()
    except OSError as read_error:
        script_hash = str(read_error)[:400]
    if script_hash != bridge_script.get("sourceSha256"):
        reject("gender_select_levelscript_sha256", bridge_script.get("sourceSha256"), script_hash)

    source_sha256 = hashlib.sha256(raw).hexdigest().upper() if raw else ""
    status = NATIVE_EVIDENCE_VALIDATED
    if failures:
        status = (
            native.status
            if native.status != NATIVE_EVIDENCE_VALIDATED
            else NATIVE_EVIDENCE_MISSING
            if error or ifix_audit.get("status") == NATIVE_EVIDENCE_MISSING
            else NATIVE_EVIDENCE_MISMATCHED
        )
    return {
        "schema": AUDIT_SCHEMA,
        "status": status,
        "sourceFile": source_file,
        "sourceSha256": source_sha256,
        "nativeContract": contract if not failures else {},
        "matchFields": MATCH_FIELDS,
        "validationFailures": failures,
        "usesOcrOrManualOrder": False,
    }


def matches_reviewed_lua_playback(
    row: dict[str, Any],
    audit: dict[str, Any],
) -> bool:
    """Whether ``row`` is the one exact playback covered by the contract."""

    if audit.get("status") != NATIVE_EVIDENCE_VALIDATED:
        return False
    contract = audit.get("nativeContract") or {}
    expected = contract.get("luaPlayback") or {}
    for field in MATCH_FIELDS:
        actual_value = row.get(field)
        expected_value = expected.get(field)
        if field == "sourceSha256":
            actual_value = str(actual_value or "").casefold()
            expected_value = str(expected_value or "").casefold()
        if actual_value != expected_value:
            return False
    return True


# -- regeneration ----------------------------------------------------------------


def regenerate(contract: dict[str, Any], *, export_root: Path | None = None) -> tuple[dict[str, Any], list[str]]:
    """Re-derive every build-specific row from names; return (contract, refusals)."""
    from scripts.game_data import levelscript_binary
    from scripts.game_data import levelscript_union_tags
    from scripts.game_data.il2cpp import protocol as il2cpp
    from scripts.game_data.il2cpp.native_image import METADATA_HELPER_PATH, open_native_image

    gate = check_installed_native_inputs()
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return contract, [f"installed_native_inputs:{gate.status}:{gate.detail}"]
    image = open_native_image(gate.gameassembly, gate.metadata)
    mapper, pe, metadata = image.mapper, image.pe, image.metadata
    helper = il2cpp.load_metadata_helper(METADATA_HELPER_PATH)
    modules = mapper.parse_codegen_modules(pe, image.code_registration)
    ranges = mapper.image_method_ranges(metadata)
    _pointers, method_by_pointer = mapper.build_pointer_indexes(pe, metadata, modules, ranges)
    generic = mapper.build_generic_method_index(
        pe, metadata, image.code_registration, image.metadata_registration
    )
    names_by_pointer = {**{p: rows for p, rows in generic.items()}, **method_by_pointer}
    extents = mapper.pdata_function_extents(pe)
    sorted_pointers = sorted(names_by_pointer)
    refused: list[str] = []

    types = {metadata.type_full_name(t): t for t in metadata.types}

    def body_extent(pointer: int) -> int:
        if pointer in extents:
            return extents[pointer] - pointer
        size, _next = mapper.estimate_scan_size(pointer, sorted_pointers, 0x4000)
        return size

    def resolve(type_name: str, method_name: str, parameters: tuple[str, ...] | None) -> dict[str, Any]:
        type_def = types.get(type_name)
        if type_def is None:
            raise LookupError(f"type-missing:{type_name}")
        candidates = []
        for method in metadata.methods_for(type_def):
            info = helper.method_row(metadata, method)
            if info.get("name") != method_name:
                continue
            names = tuple(row.get("name") for row in info.get("parameterDetails") or [])
            if parameters is not None and names != parameters:
                continue
            candidates.append((method, info, names))
        if len(candidates) != 1:
            raise LookupError(f"{type_name}.{method_name}:{len(candidates)} overloads")
        method, info, names = candidates[0]
        pointers = sorted(
            pointer for pointer, rows in names_by_pointer.items()
            if any(row.get("methodIndex") == method.index for row in rows)
        )
        if len(pointers) != 1:
            raise LookupError(f"{type_name}.{method_name}:{len(pointers)} bodies")
        return {
            "type": type_name, "method": method_name, "parameters": list(names),
            "token": info.get("token"), "va": f"0x{pointers[0]:x}",
            "pointer": pointers[0], "size": body_extent(pointers[0]),
        }

    def direct_calls(pointer: int, size: int) -> list[tuple[int, int]]:
        data = pe.bytes_at_va(pointer, size)
        return [
            (offset, pointer + offset + 5 + struct.unpack_from("<i", data, offset + 1)[0])
            for offset in range(len(data) - 5) if data[offset] == 0xE8
        ]

    def callee_names(target: int) -> set[tuple[str, str]]:
        named = {(row.get("type"), row.get("method")) for row in names_by_pointer.get(target, [])}
        if named or target not in extents or extents[target] - target > mapper.MAX_UNNAMED_HELPER_BYTES:
            return named
        return {
            (row.get("type"), row.get("method"))
            for _offset, inner in direct_calls(target, extents[target] - target)
            for row in names_by_pointer.get(inner, [])
        }

    resolver: dict[str, Any] = {}
    case_conversions: list[str] = []
    unnamed_by_body: list[set[int]] = []
    try:
        for label, (type_name, method_name, parameters) in RESOLVER_SPECS.items():
            row = resolve(type_name, method_name, parameters)
            body_calls = direct_calls(row["pointer"], row["size"])
            unnamed_by_body.append({t for _o, t in body_calls if not names_by_pointer.get(t)})
            for _offset, target in body_calls:
                for callee_type, callee_method in callee_names(target):
                    if callee_method in CASE_CONVERSION_METHODS:
                        case_conversions.append(f"{label}->{callee_type}.{callee_method}")
            resolver[label] = {key: row[key] for key in ("type", "method", "parameters", "token", "va")}
        ctor = resolve(*RESOLVER_SPECS["stringPathHashConstructor"])
    except LookupError as error:
        return contract, [f"identity:{error}"]
    # Unnamed callees most resolver bodies share are IL2CPP runtime helpers
    # (metadata init, write barrier), not the constructor's own hash routine.
    shared_runtime = {
        target for target in set().union(*unnamed_by_body)
        if sum(target in calls for calls in unnamed_by_body) >= 2
    }
    raw_hash_calls = sorted({
        f"0x{target:x}" for _offset, target in direct_calls(ctor["pointer"], ctor["size"])
        if not names_by_pointer.get(target) and target not in shared_runtime
    })
    resolver.update({
        "rawStringHashEntryPoints": raw_hash_calls,
        "caseConversionCalls": len(case_conversions),
        "caseConversionSites": case_conversions,
        "protectedMethodPrefixes": sorted({
            f"{type_name}::{method_name}" for type_name, method_name, _p in RESOLVER_SPECS.values()
        }),
    })
    if case_conversions:
        refused.append(f"case-conversion:{case_conversions[:5]}")

    ifix_audit = load_ifix_patch_contract()
    if ifix_audit.get("status") != NATIVE_EVIDENCE_VALIDATED:
        return contract, [f"ifix_contract:{ifix_audit.get('status')}"]
    resolver["ifixResolverMatches"] = len(fixed_method_prefix_matches(ifix_audit, resolver["protectedMethodPrefixes"]))

    # -- the StartGenderSelect bridge --------------------------------------------
    old_bridge = dict(contract.get("genderSelectBridge") or {})
    try:
        execute = resolve(BRIDGE_ACTION_TYPE, "Execute", None)
        game_action = resolve(*BRIDGE_GAME_ACTION, None)
    except LookupError as error:
        return contract, [f"bridge-identity:{error}"]

    def bridge_body(row: dict[str, Any]) -> dict[str, Any]:
        size = row["size"]
        file_offset, _section, _rva = pe.file_offset_for_va(row["pointer"])
        body = pe.bytes_at_va(row["pointer"], size)
        return {
            "token": row["token"], "virtualAddress": row["va"],
            "fileOffset": file_offset, "bodySize": size,
            "bodySha256": hashlib.sha256(body).hexdigest().upper(),
        }

    execute_row = bridge_body(execute)
    calls = [(o, t) for o, t in direct_calls(execute["pointer"], execute["size"]) if t == game_action["pointer"]]
    if len(calls) != 1:
        refused.append(f"bridge-execute-call:{len(calls)} calls to GameAction.StartGenderSelect")
    else:
        offset = calls[0][0]
        execute_row.update({
            "gameActionCallOffset": offset,
            "gameActionCallBytes": pe.bytes_at_va(execute["pointer"] + offset, 5).hex().upper(),
        })
    game_action_row = bridge_body(game_action)
    dispatch = [
        (o, t) for o, t in direct_calls(game_action["pointer"], game_action["size"])
        if BRIDGE_DISPATCH in callee_names(t)
    ]
    if len(dispatch) != 1:
        refused.append(f"bridge-dispatch:{len(dispatch)} calls to EventManager.SendGlobal")
    else:
        offset, target = dispatch[0]
        game_action_row.update({
            "messageDispatchCallOffset": offset,
            "messageDispatchCallBytes": pe.bytes_at_va(game_action["pointer"] + offset, 5).hex().upper(),
            "messageDispatchTarget": f"0x{target:x}",
            "messageDispatch": ".".join(BRIDGE_DISPATCH),
        })

    # -- the LevelScript record, re-read from the configured export ---------------
    script = dict(old_bridge.get("levelScript") or {})
    root = Path(export_root) if export_root is not None else ExportLayout.configured().root
    script_path = root / str(script.get("sourceFile") or "")
    try:
        data = script_path.read_bytes()
    except OSError as error:
        return contract, [f"levelscript:{error}"]
    details = levelscript_binary.decode_levelscript_action_map_details(
        data, sample_record_limit=100000, max_hint_records=100000
    )
    records = {row.get("localId"): row for row in details.get("sampleRecords") or []}
    action_code = levelscript_union_tags.action(BRIDGE_ACTION_NAME)
    action = records.get(script.get("actionLocalId")) or {}
    header = records.get(script.get("headerLocalId")) or {}
    switch = records.get(script.get("switchLocalId")) or {}
    code = action_code[0] if isinstance(action_code, tuple) else action_code
    if int(str(action.get("code") or "-1"), 16) != code:
        refused.append(f"levelscript-action:{script.get('actionLocalId')} is {action.get('code')} not {BRIDGE_ACTION_NAME}")
    if header.get("payloadHint") != "ScriptEvent_OnLeaderEnterTriggerVolume":
        refused.append(f"levelscript-header:{header.get('payloadHint')}")
    if switch.get("payloadHint") != "actionbase-switch-int":
        refused.append(f"levelscript-switch:{switch.get('payloadHint')}")
    summary = levelscript_binary.decode_levelscript_binary_summary(data, int(script["scriptId"]))
    volumes = [
        row for row in (summary.get("triggerVolumesDetails") or {}).get("volumes") or []
        if row.get("slotId") == script.get("triggerSlotId") and row.get("triggerVolumeType") == "Leader"
    ]
    if len(volumes) != 1:
        refused.append(f"levelscript-trigger:{len(volumes)} Leader volumes at slot {script.get('triggerSlotId')}")
    script.update({
        "sourceSha256": hashlib.sha256(data).hexdigest().upper(),
        "actionRecordOffset": int(str(action.get("offset") or "0x0"), 16),
    })

    regenerated = dict(contract)
    regenerated.update({
        "schema": SCHEMA,
        "sources": {
            "gameAssemblySha256": gate.gameassembly_sha256.upper(),
            "metadataSha256": gate.metadata_sha256.upper(),
            "ifixPatchSha256": str((ifix_audit.get("source") or {}).get("patchSha256") or "").upper(),
        },
        "resolver": resolver,
        "genderSelectBridge": {
            **old_bridge,
            "actionTypeToken": f"0x{types[BRIDGE_ACTION_TYPE].token:08x}",
            "execute": execute_row,
            "gameAction": game_action_row,
            "levelScript": script,
        },
    })
    return regenerated, refused


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--regenerate", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if not args.regenerate:
        audit = load_cutscene_case_resolution_contract(args.contract)
        print(json.dumps({"status": audit["status"], "failures": audit["validationFailures"]}, indent=1))
        return 0 if audit["status"] == NATIVE_EVIDENCE_VALIDATED else 1
    contract = json.loads(args.contract.read_bytes())
    regenerated, refused = regenerate(contract)
    print(json.dumps({"refused": refused, "resolver": regenerated.get("resolver")}, indent=1))
    if refused:
        return 1
    if args.write:
        args.contract.write_bytes((json.dumps(regenerated, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    if not __package__:
        raise SystemExit("Run as: python -m scripts.game_data.cutscene_case_resolution_native")
    sys.exit(main())


__all__ = [
    "AUDIT_SCHEMA",
    "DEFAULT_CONTRACT",
    "DEFAULT_IFIX_CONTRACT",
    "MATCH_FIELDS",
    "RESOLVER_SPECS",
    "SCHEMA",
    "load_cutscene_case_resolution_contract",
    "matches_reviewed_lua_playback",
    "regenerate",
]
