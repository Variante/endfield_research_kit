"""Project the authenticated current Buff corpus without another binary reader.

The canonical JsonData gate already replays each admitted root from byte zero
through EOF. This adapter consumes that admission only while its registry,
family report, parser/native inputs and exported logical bytes are still
current. Complete receipts pass through unchanged; unresolved sources remain
visible as projections, never as invented partial root decodes.
"""
from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from scripts.common import canonical_json_sha256
from scripts.game_data.memorypack import buff_selected_roots
from scripts.game_data.memorypack.corpus_gate import (
    _fingerprint, _snapshot_pinned_files, verify_current_report_inputs,
)
from scripts.webui.data_inspector.contract import source_descriptor
from scripts.webui.data_inspector.current_receipts import (
    DEFAULT_LEDGER, DEFAULT_SUMMARY, select_current_family_report,
)

_SOURCE = re.compile(r"^Data/Json/BuffData/[^/\\]+[.]json$")
_ROOT_RECEIPTS = (
    "rootNoPositiveReceipt", "rootPositiveDamageReceipt",
    "rootSingleCreateActionReceipt", "rootSelectedSourceReceipt",
    "rootSharedEventReceipt",
)
_BOUNDARY = (
    "Current canonical admission and authenticated logical bytes establish the "
    "stored root receipt only. Unresolved sources remain format-framed; source "
    "names do not establish ownership, and stored fields do not establish runtime "
    "execution, provider selection, or gameplay effects."
)


def _require(condition: bool, check: str, source: str = "BuffData") -> None:
    if not condition:
        raise ValueError(f"buff-data:{check}:{source}")


def _family_inputs(report: dict[str, Any], selection: dict[str, Any]) -> dict[str, Any]:
    """Refresh common provenance and every additional Buff fingerprint.

    The Buff report has additional child contracts, declaration assemblies and
    source closures beyond the generic corpus helper. Check each unique path
    once, refusing conflicting pins. Native inputs are joined to the selected
    registry pair and its sibling UnityPlayer, not a module-global game root.
    """
    checked = verify_current_report_inputs(
        report, expected_format="animestudio-buffdata-current-vfs-corpus", label="BuffData",
    )
    known = {}
    for rows in checked.values():
        for pin in rows if isinstance(rows, list) else []:
            if isinstance(pin, dict) and "path" in pin:
                known[str(Path(pin["path"]).resolve()).casefold()] = pin
    extra: dict[str, dict[str, Any]] = {}
    provenance = report["provenance"]
    for role, value in provenance.items():
        if not role.startswith("buff"):
            continue
        fingerprint_role = role.endswith("Sources") or role in (
            "buffFrontiersNative", "buffNamedSchema", "buffSelectedRootNativeAudit",
        ) or isinstance(value, dict) and {"path", "length", "sha256"} <= value.keys()
        if isinstance(value, list) and value:
            fingerprint_role = fingerprint_role or all(
                isinstance(pin, dict) and {"path", "length", "sha256"} <= pin.keys() for pin in value
            )
        if not fingerprint_role:
            continue
        rows = value if isinstance(value, list) else [value]
        _require(bool(rows) and all(isinstance(pin, dict) for pin in rows), "fingerprint-list", role)
        for pin in rows:
            _require(all(key in pin for key in ("path", "length", "sha256")), "fingerprint-shape", role)
            _require(isinstance(pin["path"], str) and bool(pin["path"]), "fingerprint-path", role)
            key = str(Path(pin["path"]).resolve()).casefold()
            prior = known.get(key) or extra.get(key)
            if prior is not None:
                _require((prior["length"], str(prior["sha256"]).upper())
                         == (pin["length"], str(pin["sha256"]).upper()), "conflicting-fingerprint", pin["path"])
            else:
                extra[key] = pin
    checked["buffAdditionalInputs"] = _snapshot_pinned_files(
        [extra[key] for key in sorted(extra)], label="BuffData additional inputs",
    ) if extra else []

    declared: dict[str, str] = {}
    def native_pins(value: Any) -> None:
        if isinstance(value, dict):
            pins = value.get("nativeInputs")
            if isinstance(pins, dict):
                for name, digest in pins.items():
                    _require(isinstance(digest, str) and re.fullmatch(r"[0-9a-fA-F]{64}", digest) is not None,
                             "native-pin-shape", name)
                    digest = digest.upper()
                    _require(name not in declared or declared[name] == digest, "native-pin-conflict", name)
                    declared[name] = digest
            for child in value.values():
                native_pins(child)
        elif isinstance(value, list):
            for child in value:
                native_pins(child)
    native_pins(provenance)
    selected = dict(selection["currentSourceReceipt"]["selectedNative"])
    _require({"GameAssembly.dll", "global-metadata.dat"} <= declared.keys(), "native-pair-missing")
    if "UnityPlayer.dll" in declared:
        path = Path(selected["GameAssembly.dll"]["path"]).parent / "UnityPlayer.dll"
        selected["UnityPlayer.dll"] = _fingerprint(path)
    _require(declared.keys() <= selected.keys(), "unresolved-native-input")
    for name, digest in declared.items():
        _require(selected[name]["sha256"].upper() == digest, "selected-native-mismatch", name)
    if "buffSelectedRootSources" in provenance:
        audit = provenance.get("buffSelectedRootNativeAudit")
        _require(isinstance(audit, dict) and isinstance(audit.get("path"), str),
                 "selected-root-audit-missing")
        names = ("GameAssembly.dll", "global-metadata.dat", "UnityPlayer.dll")
        _require(set(names) <= selected.keys(), "selected-root-native-paths-missing")
        # Saved fingerprints alone cannot detect a newly contributing dispatcher
        # contract. Re-enumerate the dependency set without hashing the same
        # installed binaries again; their bytes were already checked above.
        buff_selected_roots.assert_source_path_set(
            sources=provenance["buffSelectedRootSources"], audit_path=Path(audit["path"]),
            native_paths=[Path(selected[name]["path"]) for name in names],
        )
    checked["selectedNative"] = selected
    return checked


def _registry_rows(ledger_path: Path) -> dict[str, dict[str, Any]]:
    result = {}
    with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            _require(isinstance(row, dict), "registry-row-shape")
            source = row.get("virtualPath", "")
            _require(isinstance(source, str), "registry-source-shape")
            if row.get("family") != "BuffData" and not source.startswith("Data/Json/BuffData/"):
                continue
            _require(row.get("family") == "BuffData" and _SOURCE.fullmatch(source) is not None
                     and source not in result, "registry-source", source)
            _require(row.get("exportRelativePath") == source.removeprefix("Data/Json/"),
                     "registry-export-path", source)
            _require(row.get("status") in ("schema_decoded", "format_framed"), "registry-status", source)
            result[source] = row
    _require(bool(result), "empty-registry-family")
    return result


def _record(row: dict[str, Any], registry: dict[str, Any], path: Path, export_root: Path) -> dict[str, Any]:
    source = registry["virtualPath"]
    exact = registry["status"] == "schema_decoded"
    _require((row.get("wholeSchemaExact") is True) == exact
             and (registry.get("detail", {}).get("wholeSchemaExact") is True) == exact,
             "admission-disagreement", source)
    receipts = [(key, row[key]) for key in _ROOT_RECEIPTS if row.get(key) is not None]
    base = {
        "id": path.relative_to(export_root).as_posix(), "title": path.stem,
        "status": registry["status"],
        "source": source_descriptor(path, export_root=export_root, media_type="application/octet-stream"),
        "tags": ["buff", "memorypack", registry["status"]],
        "evidenceBoundary": _BOUNDARY,
    }
    if exact:
        _require(len(receipts) == 1 and isinstance(receipts[0][1], dict), "root-receipt-count", source)
        kind, receipt = receipts[0]
        fields = receipt.get("fields")
        _require(receipt.get("source") == source and receipt.get("logicalSha256") == registry["logicalSha256"]
                 and receipt.get("wholeSchemaExact") is True and receipt.get("nativeStatus") == "validated"
                 and receipt.get("physicalEof") == receipt.get("bytesConsumed") == registry["length"]
                 and receipt.get("rootMemberCount") == 30 and isinstance(fields, list) and len(fields) == 30,
                 "root-receipt-join", source)
        _require(all(isinstance(field, dict) and isinstance(field.get("name"), str)
                     for field in fields), "root-field-names", source)
        names = [field["name"] for field in fields]
        return {**base, "summary": f"30 named root fields; cursor={registry['length']}; {kind}",
                "facts": {"canonicalStatus": registry["status"], "rootReceipt": kind,
                          "decodedFieldNames": names, "wholeSchemaExact": True},
                "searchTerms": names, "payloadKind": "reader", "payload": receipt}
    _require(not receipts, "unadmitted-root-receipt", source)
    return {**base, "summary": "Whole named Buff root unresolved; authenticated source and framing evidence available",
            "facts": {"canonicalStatus": registry["status"], "wholeSchemaExact": False},
            "payloadKind": "projection", "payload": {
                "canonicalStatus": registry["status"], "canonicalDetail": registry.get("detail"),
                "rootDiagnostic": row.get("rootSelectedSourceDiagnostic"),
                "wholeSchemaExact": False, "evidenceBoundary": _BOUNDARY,
            }}


def load_buff_root_records(
    export_root: Path, *, summary_path: Path = DEFAULT_SUMMARY, ledger_path: Path = DEFAULT_LEDGER,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load every current Buff source, failing closed before dataset cache reuse."""
    export_root = export_root.resolve()
    report_path, selection = select_current_family_report(
        "BuffData", export_root, summary_path=summary_path, ledger_path=ledger_path,
    )
    raw = report_path.read_bytes()
    pin = selection["familyReport"]
    _require(len(raw) == pin["length"] and hashlib.sha256(raw).hexdigest().upper() == pin["sha256"].upper(),
             "family-report-byte-join", str(report_path))
    report = json.loads(raw)
    current = _family_inputs(report, selection)
    canonical = _registry_rows(ledger_path)
    rows = report.get("files")
    _require(isinstance(rows, list), "family-files")
    summary = report.get("summary", {})
    _require(summary.get("filesSelected") == summary.get("filesUnique") == len(rows)
             and summary.get("filesFailed") == summary.get("filesAmbiguous") == 0, "family-completeness")
    identities = [{"identity": row.get("identity"), "logicalSha256": row.get("logicalSha256")} for row in rows]
    _require(canonical_json_sha256(identities) == report.get("identitySetSha256"), "family-identity-set")
    _require(report.get("inputSetSha256") == selection["currentSourceReceipt"]["inputSetSha256"], "input-set-join")
    root = export_root / "game/Json/BuffData"
    exported = {"Data/" + path.relative_to(export_root / "game").as_posix() for path in root.rglob("*.json")}
    _require(exported == canonical.keys(), "exported-source-set")
    records, source_pins, seen = [], [], set()
    for row in rows:
        identity = row.get("identity", {})
        source = identity.get("fileName")
        _require(source in canonical and source not in seen, "family-source", str(source))
        seen.add(source)
        expected = canonical[source]
        _require(identity.get("virtualPath") == source and identity.get("status") == "verified"
                 and identity.get("boundaryStatus") == "boundary_verified"
                 and identity.get("inputSetSha256") == report["inputSetSha256"]
                 and identity.get("length") == identity.get("actualBytesRead") == expected["length"]
                 and row.get("logicalSha256") == expected["logicalSha256"], "family-source-join", source)
        path = export_root / "game" / source.removeprefix("Data/")
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest().upper()
        md5 = hashlib.md5(data).hexdigest().upper()
        _require(len(data) == expected["length"] and sha == expected["logicalSha256"].upper()
                 and md5 == expected["logicalMd5"].upper() == identity.get("recomputedFileDataMd5", "").upper(),
                 "exported-source-bytes", source)
        source_pins.append({"source": source, "length": len(data), "sha256": sha})
        records.append(_record(row, expected, path, export_root))
    _require(seen == canonical.keys(), "family-registry-source-set")
    counts = Counter(record["status"] for record in records)
    _require(counts["schema_decoded"] == summary.get("filesWholeSchemaExact"), "family-exact-count")
    after_path, after_selection = select_current_family_report(
        "BuffData", export_root, summary_path=summary_path, ledger_path=ledger_path,
    )
    _require(after_path == report_path and after_selection == selection, "registry-drift-during-publication")
    _require(_family_inputs(report, after_selection) == current, "family-input-drift-during-publication")
    return records, {"currentBuffReceiptSelection": selection, "currentFamilyInputs": current,
                     "exportedLogicalSources": source_pins, "statusCounts": dict(sorted(counts.items())),
                     "evidenceBoundary": _BOUNDARY}
