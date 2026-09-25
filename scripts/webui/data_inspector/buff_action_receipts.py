"""Publish only authenticated Buff action spans, never a whole BuffData decode."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from scripts.common import canonical_json_sha256, check_installed_native_inputs, sha256_file_upper
from scripts.webui.data_inspector.contract import source_descriptor


_SOURCE = re.compile(r"^Data/Json/BuffData/[^/\\]+[.]json$")
_HEX = re.compile(r"^[0-9A-Fa-f]{64}$")
_MEMBERS = {0x0092: 19, 0x00B4: 13}
_BOUNDARY = (
    "Authenticated BuffData logical bytes and selected native contracts establish only "
    "the listed action spans and their wrapper field names. Nested fields remain "
    "structural, other actions are not listed, and the enclosing BuffData schema "
    "is not a complete named decode. Stored actions do not establish runtime use."
)


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(f"buff-action-receipts:{reason}")


def _read(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    value = json.loads(raw)
    _require(isinstance(value, dict), "report-shape")
    return raw, value


def _native_current(inputs_by_tag: dict[str, Any]) -> dict[str, str]:
    _require(set(inputs_by_tag) == {"0x0092", "0x00B4"}, "native-tag-set")
    values = list(inputs_by_tag.values())
    expected = values[0]
    _require(all(value == expected for value in values), "native-input-disagreement")
    _require(isinstance(expected, dict) and set(expected) == {
        "GameAssembly.dll", "global-metadata.dat", "UnityPlayer.dll",
    }, "native-input-shape")
    _require(all(isinstance(value, str) and _HEX.fullmatch(value)
                 for value in expected.values()), "native-input-hash-shape")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
    )
    _require(gate.validated, f"native-{gate.status}: {gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    _require(unityplayer.is_file(), "native-UnityPlayer-missing")
    _require(sha256_file_upper(unityplayer) == expected["UnityPlayer.dll"].upper(),
             "native-UnityPlayer-mismatch")
    return {key: value.upper() for key, value in expected.items()}


def _source_rows(buff_report: dict[str, Any], export_root: Path) -> dict[str, str]:
    rows = buff_report.get("files")
    summary = buff_report.get("summary") or {}
    _require(
        buff_report.get("format") == "animestudio-buffdata-current-vfs-corpus"
        and buff_report.get("status") == "complete"
        and buff_report.get("publicationEligible") is True
        and buff_report.get("wholeSchemaExact") is False
        and isinstance(rows, list)
        and summary.get("filesSelected") == len(rows)
        and summary.get("filesUnique") == len(rows)
        and summary.get("filesFailed") == 0
        and summary.get("filesAmbiguous") == 0,
        "buff-corpus-not-complete",
    )
    identity_rows = [
        {"identity": row.get("identity"), "logicalSha256": row.get("logicalSha256")}
        for row in rows
    ]
    _require(canonical_json_sha256(identity_rows) == buff_report.get("identitySetSha256"),
             "buff-identity-set-drift")
    result: dict[str, str] = {}
    for row in rows:
        identity = row.get("identity") or {}
        source = identity.get("fileName")
        digest = row.get("logicalSha256")
        _require(
            isinstance(source, str) and _SOURCE.fullmatch(source) is not None
            and source not in result and identity.get("virtualPath") == source
            and identity.get("status") == "verified"
            and identity.get("boundaryStatus") == "boundary_verified"
            and identity.get("inputSetSha256", "").upper()
            == buff_report.get("inputSetSha256", "").upper()
            and type(identity.get("length")) is int
            and identity.get("actualBytesRead") == identity["length"]
            and isinstance(digest, str) and _HEX.fullmatch(digest) is not None,
            f"buff-source-identity:{source}",
        )
        path = export_root / "game" / source.removeprefix("Data/")
        data = path.read_bytes()
        _require(len(data) == identity["length"]
                 and hashlib.sha256(data).hexdigest().upper() == digest.upper(),
                 f"buff-source-bytes:{source}")
        result[source] = digest.upper()
    return result


def _action_projection(action: dict[str, Any], source: str, digest: str,
                       source_length: int) -> dict[str, Any]:
    tag = action.get("tag")
    start, end = action.get("start"), action.get("end")
    fields = action.get("namedFields")
    _require(
        type(tag) is int and tag in _MEMBERS
        and type(start) is int and type(end) is int
        and 0 <= start < end <= source_length
        and action.get("source") == source
        and action.get("logicalSha256", "").upper() == digest
        and action.get("status") == "named-wrapper-exact-span"
        and action.get("wholeActionByteSpanExact") is True
        and action.get("recursiveNamedSchemaExact") is False
        and action.get("wholeBuffDataExact") is False
        and action.get("memberCount") == _MEMBERS[tag]
        and isinstance(action.get("typeName"), str) and action["typeName"]
        and isinstance(fields, list) and len(fields) == _MEMBERS[tag],
        f"action-boundary:{source}:{tag}",
    )
    projected_fields = []
    cursor = start + 2  # one-byte union tag followed by the wrapper header byte
    for field in fields:
        _require(
            isinstance(field, dict)
            and isinstance(field.get("fieldName"), str) and field["fieldName"]
            and isinstance(field.get("kind"), str) and field["kind"]
            and type(field.get("start")) is int and type(field.get("end")) is int
            and field["start"] == cursor and cursor < field["end"] <= end,
            f"action-field-range:{source}:{tag}",
        )
        projected_fields.append({
            "fieldName": field["fieldName"], "kind": field["kind"],
            "startOffset": cursor, "endOffset": field["end"],
        })
        cursor = field["end"]
    _require(cursor == end, f"action-field-end:{source}:{tag}")
    return {
        "tag": tag, "typeName": action["typeName"],
        "startOffset": start, "endOffset": end,
        "memberCount": len(projected_fields),
        "namedFields": projected_fields,
        "nestedStructuralFields": action.get("nestedStructuralFields") or [],
        "wholeActionByteSpanExact": True,
        "recursiveNamedSchemaExact": False,
        "wholeBuffDataExact": False,
    }


def load_receipt_records(
    receipt_path: Path, buff_report_path: Path, export_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Recheck the selected report, corpus, native inputs and every export identity."""
    export_root = export_root.resolve()
    receipt_raw, report = _read(receipt_path)
    buff_raw, buff_report = _read(buff_report_path)
    _require(
        report.get("schema") == "endfield.buff-action-receipt-corpus.v1"
        and report.get("status") == "complete"
        and report.get("publicationEligible") is True
        and report.get("wholeBuffDataExact") is False
        and report.get("buffReportSha256") == hashlib.sha256(buff_raw).hexdigest().upper()
        and report.get("sourceIdentitySetSha256") == buff_report.get("identitySetSha256")
        and report.get("inputSetSha256") == buff_report.get("inputSetSha256")
        and Path(report.get("exportRoot", "")).resolve() == export_root,
        "receipt-report-provenance",
    )
    native_inputs = _native_current(report.get("nativeInputsByTag") or {})
    source_hashes = _source_rows(buff_report, export_root)
    rows = report.get("files")
    _require(isinstance(rows, list), "receipt-file-list")
    records = []
    seen: set[str] = set()
    counts: Counter[str] = Counter()
    files_by_tag: Counter[str] = Counter()
    for row in rows:
        source = row.get("source") if isinstance(row, dict) else None
        _require(isinstance(source, str) and source in source_hashes and source not in seen,
                 f"receipt-source:{source}")
        seen.add(source)
        digest = source_hashes[source]
        _require(row.get("logicalSha256", "").upper() == digest,
                 f"receipt-source-hash:{source}")
        path = export_root / "game" / source.removeprefix("Data/")
        actions = row.get("actions")
        _require(isinstance(actions, list) and actions, f"receipt-actions:{source}")
        spans = [_action_projection(action, source, digest, path.stat().st_size)
                 for action in actions]
        intervals = sorted((span["startOffset"], span["endOffset"]) for span in spans)
        _require(all(left[1] <= right[0] for left, right in zip(intervals, intervals[1:])),
                 f"receipt-overlap:{source}")
        for tag in {span["tag"] for span in spans}:
            files_by_tag[f"0x{tag:04X}"] += 1
        for span in spans:
            counts[f"0x{span['tag']:04X}"] += 1
        terms = sorted({span["typeName"] for span in spans})
        records.append({
            "id": path.relative_to(export_root).as_posix(),
            "title": path.stem,
            "status": "bounded_partial",
            "summary": f"{len(spans)} verified action span(s); enclosing BuffData remains partial",
            "tags": ["gameplay", "buffdata", "memorypack", "action-spans"],
            "searchTerms": terms,
            "source": source_descriptor(path, export_root=export_root,
                                        media_type="application/octet-stream"),
            "facts": {
                "verifiedActionSpanCount": len(spans),
                "wholeBuffDataExact": False,
                "recursiveNamedSchemaExact": False,
                "evidenceBoundary": _BOUNDARY,
            },
            "payload": {"actionReceipts": spans},
            "payloadKind": "projection",
        })
    summary = report.get("summary") or {}
    by_tag = summary.get("byTag") or {}
    _require(summary.get("filesWithNamedActionReceipts") == len(records)
             and set(by_tag) == {"0x0092", "0x00B4"}
             and all(by_tag[tag].get("actionSpans") == counts[tag]
                     and by_tag[tag].get("files") == files_by_tag[tag]
                     for tag in by_tag), "receipt-summary-drift")
    signature = {
        "receiptReportSha256": hashlib.sha256(receipt_raw).hexdigest().upper(),
        "buffReportSha256": hashlib.sha256(buff_raw).hexdigest().upper(),
        "sourceIdentitySetSha256": buff_report["identitySetSha256"],
        "inputSetSha256": buff_report["inputSetSha256"],
        "nativeInputs": native_inputs,
        "publisherRevision": 1,
    }
    return records, signature
