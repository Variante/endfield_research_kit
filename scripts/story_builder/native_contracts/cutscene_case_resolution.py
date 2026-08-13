"""Validate the reviewed case-sensitive cutscene lookup contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from common import (
        NATIVE_EVIDENCE_MISSING,
        NATIVE_EVIDENCE_MISMATCHED,
        NATIVE_EVIDENCE_VALIDATED,
        check_installed_native_inputs,
    )
except ImportError:  # pragma: no cover - package import identity
    from scripts.common import (
        NATIVE_EVIDENCE_MISSING,
        NATIVE_EVIDENCE_MISMATCHED,
        NATIVE_EVIDENCE_VALIDATED,
        check_installed_native_inputs,
    )


SCHEMA = "cutsceneCaseResolutionNativeContract.v1"
AUDIT_SCHEMA = "cutsceneCaseResolutionNativeContractAudit.v1"
DEFAULT_CONTRACT = Path(__file__).with_name("cutscene_case_resolution.json")
DEFAULT_IFIX_AUDIT = (
    Path(__file__).resolve().parents[3]
    / "reports" / "story" / "recovery" / "current_ifix_mission_graph_audit.json"
)
GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)
IFIX_PATCH_SHA256 = (
    "737134081E06371F13C073988547E887037FCCF2F57E1052BE35DD255D27BC21"
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
    ifix_audit_path: Path = DEFAULT_IFIX_AUDIT,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    """Return the exact rejection rule only while every source gate matches."""

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
        ("graph_action", "reject_case_mismatch_no_playback_binding", conclusion.get("graphAction")),
        ("ownership_action", "none", conclusion.get("ownershipAction")),
    )
    for gate, expected, actual in exact_gates:
        if actual != expected:
            reject(gate, expected, actual)
    for label, expected in RESOLVER_METHODS.items():
        actual = resolver.get(label)
        if actual != list(expected):
            reject(f"resolver_{label}", list(expected), actual)

    ifix_path = Path(ifix_audit_path)
    ifix, _ifix_raw, ifix_error = _read_json(ifix_path)
    if ifix_error:
        reject(
            "read_valid_ifix_audit",
            {"readableJsonObject": True},
            ifix_error,
            _source_file(ifix_path),
        )
    else:
        ifix_sha = str((ifix.get("source") or {}).get("patchSha256") or "").upper()
        if ifix_sha != IFIX_PATCH_SHA256:
            reject(
                "ifix_source_hash",
                IFIX_PATCH_SHA256,
                ifix_sha or "<missing>",
                _source_file(ifix_path),
            )
        ifix_metadata_sha = str(
            (ifix.get("source") or {}).get("metadataSha256") or ""
        ).upper()
        if ifix_metadata_sha != METADATA_SHA256:
            reject(
                "ifix_metadata_hash",
                METADATA_SHA256,
                ifix_metadata_sha or "<missing>",
                _source_file(ifix_path),
            )
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
        ifix_hits = [
            row
            for row in ifix.get("fixedMethods") or []
            if isinstance(row, dict)
            and any(
                str(row.get("signature") or "").startswith(prefix)
                for prefix in prefixes
            )
        ]
        if ifix_hits:
            reject(
                "ifix_resolver_matches",
                [],
                [str(row.get("signature") or "") for row in ifix_hits[:10]],
                _source_file(ifix_path),
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

    source_sha256 = hashlib.sha256(raw).hexdigest().upper() if raw else ""
    status = NATIVE_EVIDENCE_VALIDATED
    if failures:
        status = (
            native.status
            if native.status != NATIVE_EVIDENCE_VALIDATED
            else NATIVE_EVIDENCE_MISSING
            if error or ifix_error
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
    "DEFAULT_IFIX_AUDIT",
    "GAMEASSEMBLY_SHA256",
    "IFIX_PATCH_SHA256",
    "MATCH_FIELDS",
    "METADATA_SHA256",
    "RESOLVER_METHODS",
    "SCHEMA",
    "load_cutscene_case_resolution_contract",
    "matches_reviewed_lua_playback",
]
