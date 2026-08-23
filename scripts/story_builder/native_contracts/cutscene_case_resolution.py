"""Validate the reviewed case-sensitive cutscene lookup contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

if __package__ == "scripts.story_builder.native_contracts":
    from ...common import (
        NATIVE_EVIDENCE_MISSING,
        NATIVE_EVIDENCE_MISMATCHED,
        NATIVE_EVIDENCE_VALIDATED,
        check_installed_native_inputs,
    )
elif __package__ == "story_builder.native_contracts":
    from common import (
        NATIVE_EVIDENCE_MISSING,
        NATIVE_EVIDENCE_MISMATCHED,
        NATIVE_EVIDENCE_VALIDATED,
        check_installed_native_inputs,
    )
else:  # pragma: no cover - invalid embedding identity
    raise ImportError(f"unsupported package identity: {__package__!r}")

from .ifix_patch import (
    DEFAULT_CONTRACT as DEFAULT_IFIX_CONTRACT,
    PATCH_SHA256 as IFIX_PATCH_SHA256,
    fixed_method_prefix_matches,
    load_ifix_patch_contract,
)


SCHEMA = "cutsceneCaseResolutionNativeContract.v2"
AUDIT_SCHEMA = "cutsceneCaseResolutionNativeContractAudit.v2"
DEFAULT_CONTRACT = Path(__file__).with_name("cutscene_case_resolution.json")
GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)
RESOLVER_METHODS = {
    "gameAction": ("0x06008058", "0x1875e6aac"),
    "playCutscene": ("0x0600eeec", "0x186db94cc"),
    "checkCanPlay": ("0x0600eeed", "0x186db8a94"),
    "getGenderedCutsceneId": ("0x06001983", "0x1835fd630"),
    "tryGetCinematicData": ("0x0600ed74", "0x1848511c0"),
    "tryLoadCutsceneDataByName": ("0x0600ed72", "0x184495b60"),
    "cachedPathTryLoad": ("0x06000f27", "0x18304bb40"),
    "cachedPathTypedTryLoad": ("0x06000f2a", "0x18304bbd0"),
    "stringPathHashConstructor": ("0x060010c8", "0x1868c15bc"),
}
MATCH_FIELDS = (
    "module",
    "sourceSha256",
    "line",
    "method",
    "resolvedLiteral",
    "canonicalStoryKey",
    "registryStatus",
)


def _source_file(path: Path) -> str:
    root = Path(__file__).resolve().parents[3]
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _read_json(path: Path) -> tuple[dict[str, Any], bytes, str | None]:
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return {}, b"", str(error)[:400]
    if not isinstance(payload, dict):
        return {}, raw, f"expected object, found {type(payload).__name__}"
    return payload, raw, None


def load_cutscene_case_resolution_contract(
    contract_path: Path = DEFAULT_CONTRACT,
    *,
    ifix_contract_path: Path = DEFAULT_IFIX_CONTRACT,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    """Validate the pinned runtime fact and offline association policy."""

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
    sources = contract.get("sources") if isinstance(contract.get("sources"), dict) else {}
    playback = (
        contract.get("luaPlayback")
        if isinstance(contract.get("luaPlayback"), dict)
        else {}
    )
    resolver = contract.get("resolver") if isinstance(contract.get("resolver"), dict) else {}
    conclusion = (
        contract.get("conclusion")
        if isinstance(contract.get("conclusion"), dict)
        else {}
    )
    association = (
        contract.get("recoveryAssociationPolicy")
        if isinstance(contract.get("recoveryAssociationPolicy"), dict)
        else {}
    )
    bridge = (
        contract.get("genderSelectBridge")
        if isinstance(contract.get("genderSelectBridge"), dict)
        else {}
    )
    bridge_script = bridge.get("levelScript") or {}
    exact_gates = (
        ("schema", SCHEMA, contract.get("schema")),
        ("status", "validated", contract.get("status")),
        ("gameassembly_sha256", GAMEASSEMBLY_SHA256, sources.get("gameAssemblySha256")),
        ("metadata_sha256", METADATA_SHA256, sources.get("metadataSha256")),
        ("ifix_patch_sha256", IFIX_PATCH_SHA256, sources.get("ifixPatchSha256")),
        ("lua_module", "Phase/GenderSelect/PhaseGenderSelect.lua", playback.get("module")),
        ("lua_source_sha256", "A56B82797427F179D4F21E6C28989BE8AB8CCFAEDAC1B06D2BD5D286E243E368", playback.get("sourceSha256")),
        ("lua_line", 75, playback.get("line")),
        ("lua_method", "PlayCutsceneAndGetHandle", playback.get("method")),
        ("lua_literal", "Cutscene_e0m0_1", playback.get("resolvedLiteral")),
        ("canonical_story_key", "cutscene_e0m0_1", playback.get("canonicalStoryKey")),
        ("registry_status", "case_mismatch_registry_match", playback.get("registryStatus")),
        ("raw_string_hash", "0x182f75f50", resolver.get("rawStringHashEntryPoint")),
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
        ("gender_select_action_type", "Beyond.Gameplay.Actions.StartGenderSelect", bridge.get("actionType")),
        ("gender_select_action_token", "0x02001768", bridge.get("actionTypeToken")),
        ("gender_select_level", "indie_dg002", bridge_script.get("levelId")),
        ("gender_select_script", 8700020000, bridge_script.get("scriptId")),
        ("gender_select_header", 12, bridge_script.get("headerLocalId")),
        ("gender_select_trigger_slot", 80001, bridge_script.get("triggerSlotId")),
        ("gender_select_switch", 13, bridge_script.get("switchLocalId")),
        ("gender_select_switch_case", 0, bridge_script.get("switchCase")),
        ("gender_select_action", 16, bridge_script.get("actionLocalId")),
        ("gender_select_action_offset", 310, bridge_script.get("actionRecordOffset")),
        ("gender_select_story", "cutscene_e0m0_1", bridge.get("storyKey")),
        ("gender_select_conditional", True, bridge.get("conditionalPlayback")),
        ("gender_select_ownership", False, bridge.get("suppliesMissionOrQuestOwnership")),
    )
    for gate, expected, actual in exact_gates:
        if actual != expected:
            reject(gate, expected, actual)
    for label, expected in RESOLVER_METHODS.items():
        actual = resolver.get(label)
        if actual != list(expected):
            reject(f"resolver_{label}", list(expected), actual)

    ifix_audit = load_ifix_patch_contract(
        ifix_contract_path,
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if ifix_audit.get("status") != NATIVE_EVIDENCE_VALIDATED:
        reject(
            "ifix_contract_status",
            {"status": NATIVE_EVIDENCE_VALIDATED},
            {
                "status": ifix_audit.get("status"),
                "validationFailures": ifix_audit.get("validationFailures") or [],
            },
            str(ifix_audit.get("sourceFile") or _source_file(ifix_contract_path)),
        )
    else:
        prefixes = resolver.get("protectedMethodPrefixes") or []
        if (
            not isinstance(prefixes, list)
            or not prefixes
            or any(not isinstance(value, str) or not value for value in prefixes)
        ):
            reject(
                "protected_method_prefixes",
                {"nonemptyStrings": True},
                prefixes,
            )
            prefixes = []
        ifix_hits = fixed_method_prefix_matches(ifix_audit, prefixes)
        if ifix_hits:
            reject(
                "ifix_resolver_matches",
                [],
                ifix_hits[:10],
                str(ifix_audit.get("sourceFile") or _source_file(ifix_contract_path)),
            )

    native = check_installed_native_inputs(
        GAMEASSEMBLY_SHA256,
        METADATA_SHA256,
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
    try:
        image = Path(gameassembly_path).read_bytes() if gameassembly_path else b""
    except OSError as error:
        image = b""
        reject("read_gameassembly", True, str(error)[:400])
    bridge_methods = {
        "execute": ("0x06008b48", "0x18765b560"),
        "gameAction": ("0x0600800c", "0x1875eda48"),
    } if gameassembly_path else {}
    for method_name, identity in bridge_methods.items():
        method = bridge.get(method_name) or {}
        actual_identity = (method.get("token"), method.get("virtualAddress"))
        if actual_identity != identity:
            reject(f"gender_select_{method_name}_identity", identity, actual_identity)
            continue
        offset, size = method.get("fileOffset"), method.get("bodySize")
        if not isinstance(offset, int) or not isinstance(size, int) or size <= 0:
            reject(f"gender_select_{method_name}_range", {"offset": "int", "size": ">0"}, method)
            continue
        body = image[offset:offset + size]
        actual_hash = hashlib.sha256(body).hexdigest().upper()
        expected_hash = str(method.get("bodySha256") or "").upper()
        if len(body) != size or actual_hash != expected_hash:
            reject(f"gender_select_{method_name}_body", expected_hash, actual_hash)

    bridge_calls = (
        ("execute", "gameActionCallOffset", "gameActionCallBytes", "0x1875eda48"),
        ("gameAction", "messageDispatchCallOffset", "messageDispatchCallBytes", "0x183194740"),
    ) if gameassembly_path else ()
    for method_name, offset_key, bytes_key, target in bridge_calls:
        method = bridge.get(method_name) or {}
        offset = method.get("fileOffset")
        call_offset = method.get(offset_key)
        expected_bytes = bytes.fromhex(str(method.get(bytes_key) or ""))
        if not isinstance(offset, int) or not isinstance(call_offset, int):
            reject(f"gender_select_{method_name}_call_range", True, method)
            continue
        actual_bytes = image[offset + call_offset:offset + call_offset + 5]
        if actual_bytes != expected_bytes or actual_bytes[:1] != b"\xe8":
            reject(f"gender_select_{method_name}_call_bytes", expected_bytes.hex(), actual_bytes.hex())
            continue
        method_va = int(str(method.get("virtualAddress")), 16)
        relative = int.from_bytes(actual_bytes[1:], "little", signed=True)
        actual_target = method_va + call_offset + 5 + relative
        if actual_target != int(target, 16):
            reject(f"gender_select_{method_name}_call_target", target, hex(actual_target))

    script_path = Path(__file__).resolve().parents[3] / str(bridge_script.get("sourceFile") or "")
    try:
        script_hash = hashlib.sha256(script_path.read_bytes()).hexdigest().upper()
    except OSError as error:
        script_hash = str(error)[:400]
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


__all__ = [
    "AUDIT_SCHEMA",
    "DEFAULT_CONTRACT",
    "DEFAULT_IFIX_CONTRACT",
    "GAMEASSEMBLY_SHA256",
    "IFIX_PATCH_SHA256",
    "MATCH_FIELDS",
    "METADATA_SHA256",
    "RESOLVER_METHODS",
    "SCHEMA",
    "load_cutscene_case_resolution_contract",
    "matches_reviewed_lua_playback",
]
