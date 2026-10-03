"""Publish only authenticated Buff action spans, never a whole BuffData decode.

The optional ``buff-action-receipts`` Data-page dataset projects the eight
reviewed action wrapper fields from the current v7 receipt report at
their byte spans in exported BuffData files. ``load_receipt_records``
publishes only when every check holds:

* the receipt report names the Buff VFS corpus report by its SHA256, and its
  source identity set and input set equal that report's;
* the corpus report is complete and publication-eligible, with no failed or
  ambiguous file;
* each reviewed tag's domain gate authenticates its own selected native layout
  and the receipt report agrees with that gate's declared input pins;
* every Buff source's exported logical bytes still match its recorded length
  and SHA256;
* each span is independently certified by the corpus and replayed by its selected
  codec; names, kinds, ranges and structural fields agree with that replay;
  nested spans may contain one another, crossing
  or duplicate spans are refused, and the report summary
  matches the recounted spans.

Any failure raises, and the builder marks the dataset unavailable without
cached records. Records are ``bounded_partial`` projections: nested values,
unlisted actions and the enclosing BuffData schema are not decoded here, and
a stored action is not evidence of runtime use. The default report paths are
under ``reports/animestudio/``; ``--buff-corpus-report`` and
``--buff-action-receipts-report`` override them.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from scripts.common import canonical_json_sha256, resolve_installed_native_inputs
from scripts.game_data.memorypack.buff_action_receipts import (
    certified_action_spans, replay_action_receipt, validate_selected_native,
)
from scripts.webui.data_inspector.contract import source_descriptor


_SOURCE = re.compile(r"^Data/Json/BuffData/[^/\\]+[.]json$")
_HEX = re.compile(r"^[0-9A-Fa-f]{64}$")
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


def _native_current(
    inputs_by_tag: dict[str, Any],
) -> tuple[dict[int, dict[str, Any]], dict[str, str]]:
    """Revalidate every codec and compare report pins per selected route."""
    _assembly, metadata = resolve_installed_native_inputs()
    validations = validate_selected_native(metadata.resolve().parents[2])
    _require(isinstance(inputs_by_tag, dict)
             and set(inputs_by_tag) == {f"0x{tag:04X}" for tag in validations}, "native-tag-set")
    joined: dict[str, str] = {}
    for tag, validation in validations.items():
        reported = inputs_by_tag[f"0x{tag:04X}"]
        _require(isinstance(reported, dict)
                 and all(isinstance(value, str) and _HEX.fullmatch(value)
                         for value in reported.values()), "native-input-hash-shape")
        reported = {name: value.upper() for name, value in reported.items()}
        expected = {name: value.upper() for name, value in validation["nativeInputs"].items()}
        _require(reported == expected, f"native-input-disagreement:0x{tag:04X}")
        for name, value in expected.items():
            _require(name not in joined or joined[name] == value, "native-input-disagreement")
            joined[name] = value
    return validations, joined


def _source_rows(buff_report: dict[str, Any], export_root: Path) -> dict[str, dict[str, Any]]:
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
    result: dict[str, dict[str, Any]] = {}
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
                 and hashlib.sha256(data).hexdigest().upper() == digest.upper()
                 and hashlib.md5(data).hexdigest().upper()
                 == identity.get("recomputedFileDataMd5", "").upper(),
                 f"buff-source-bytes:{source}")
        result[source] = {"digest": digest.upper(), "row": row}
    return result


def _action_projection(
    action: dict[str, Any], source: str, digest: str, data: bytes,
    native_validations: dict[int, dict[str, Any]], certified_spans: list[dict[str, int]],
) -> dict[str, Any]:
    _require(isinstance(action, dict), f"action-shape:{source}")
    tag = action.get("tag")
    start, end = action.get("start"), action.get("end")
    fields = action.get("namedFields")
    _require(
        type(tag) is int and tag in native_validations
        and type(start) is int and type(end) is int
        and 0 <= start < end <= len(data)
        and action.get("source") == source
        and action.get("logicalSha256", "").upper() == digest
        and action.get("status") == "named-wrapper-exact-span"
        and action.get("wholeActionByteSpanExact") is True
        and action.get("recursiveNamedSchemaExact") is False
        and action.get("wholeBuffDataExact") is False
        and type(action.get("memberCount")) is int
        and 0 < action["memberCount"] < 250
        and isinstance(fields, list) and len(fields) == action["memberCount"],
        f"action-boundary:{source}:{tag}",
    )
    replayed = replay_action_receipt(
        data, source=source, logical_sha256=digest, start=start, end=end, tag=tag,
        native_validation=native_validations[tag], certified_spans=certified_spans,
    )
    for key in ("schema", "source", "logicalSha256", "status", "tag", "typeName",
                "memberCount", "start", "end", "namedFields", "nestedStructuralFields",
                "wholeActionByteSpanExact", "recursiveNamedSchemaExact", "wholeBuffDataExact"):
        _require(action.get(key) == replayed.get(key), f"action-replay-drift:{source}:{tag}:{key}")
    fields = replayed["namedFields"]
    projected_fields = []
    union_header = bytes([tag]) if tag < 250 else b"\xfa" + tag.to_bytes(2, "little")
    header = union_header + bytes([replayed["memberCount"]])
    _require(data[start:start + len(header)] == header,
             f"action-source-header:{source}:{tag}")
    cursor = start + len(header)
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
        "tag": tag, "typeName": replayed["typeName"],
        "startOffset": start, "endOffset": end,
        "memberCount": len(projected_fields),
        "namedFields": projected_fields,
        "nestedStructuralFields": replayed["nestedStructuralFields"],
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
        report.get("schema") == "endfield.buff-action-receipt-corpus.v7"
        and report.get("status") == "complete"
        and report.get("publicationEligible") is True
        and report.get("wholeBuffDataExact") is False
        and report.get("buffReportSha256") == hashlib.sha256(buff_raw).hexdigest().upper()
        and report.get("sourceIdentitySetSha256") == buff_report.get("identitySetSha256")
        and report.get("inputSetSha256") == buff_report.get("inputSetSha256")
        and Path(report.get("exportRoot", "")).resolve() == export_root,
        "receipt-report-provenance",
    )
    native_validations, native_inputs = _native_current(report.get("nativeInputsByTag") or {})
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
        digest = source_hashes[source]["digest"]
        _require(row.get("logicalSha256", "").upper() == digest,
                 f"receipt-source-hash:{source}")
        path = export_root / "game" / source.removeprefix("Data/")
        actions = row.get("actions")
        _require(isinstance(actions, list) and actions, f"receipt-actions:{source}")
        data = path.read_bytes()
        _require(hashlib.sha256(data).hexdigest().upper() == digest,
                 f"receipt-source-changed:{source}")
        corpus_row = source_hashes[source]["row"]
        candidates = [candidate for candidate in corpus_row.get("candidates", [])
                      if isinstance(candidate, dict) and candidate.get("readerAcceptedThroughEof") is True]
        _require(corpus_row.get("candidateCount") == 1 and len(candidates) == 1,
                 f"receipt-corpus-candidate:{source}")
        candidate = candidates[0]
        _require(all(isinstance(candidate.get(key), dict)
                     and candidate[key].get("status") == "supported-prefix"
                     for key in ("currentEventPrefix", "currentRootContinuation"))
                 and isinstance(candidate.get("namedSchemaReceipt"), dict),
                 f"receipt-corpus-action-frame:{source}")
        certified_spans = certified_action_spans(candidate, source=source, length=len(data))
        spans = [_action_projection(action, source, digest, data, native_validations, certified_spans)
                 for action in actions]
        intervals = sorted((span["startOffset"], span["endOffset"]) for span in spans)
        _require(len(set(intervals)) == len(intervals), f"receipt-duplicate-span:{source}")
        stack: list[tuple[int, int]] = []
        for start, end in sorted(intervals, key=lambda interval: (interval[0], -interval[1])):
            while stack and start >= stack[-1][1]:
                stack.pop()
            _require(not stack or (stack[-1][0] < start and end <= stack[-1][1]),
                     f"receipt-crossing-span:{source}")
            stack.append((start, end))
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
             and set(by_tag) == {f"0x{tag:04X}" for tag in native_validations}
             and all(by_tag[tag].get("actionSpans") == counts[tag]
                     and by_tag[tag].get("files") == files_by_tag[tag]
                     for tag in by_tag), "receipt-summary-drift")
    signature = {
        "receiptReportSha256": hashlib.sha256(receipt_raw).hexdigest().upper(),
        "buffReportSha256": hashlib.sha256(buff_raw).hexdigest().upper(),
        "sourceIdentitySetSha256": buff_report["identitySetSha256"],
        "inputSetSha256": buff_report["inputSetSha256"],
        "nativeInputs": native_inputs,
        "publisherRevision": 3,
    }
    return records, signature
