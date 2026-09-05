"""Source-bound ordered Init/Streaming witnesses, never runtime receipts."""
from __future__ import annotations

import hashlib
from typing import Any

from scripts.game_data import streaming as fmt


IDENTITY_FIELDS = (
    "virtualPath", "physicalChunkPath", "physicalChunkSource", "metadataProvenance",
    "overlayState", "offset", "length", "packedSha256",
)
ORDERED_FIELDS = ("rowCount", "field3VectorSha256", "field4VectorSha256")
WITNESS_FIELDS = ORDERED_FIELDS + ("rowField0ValuesSha256", "field3DuplicateCount")


def _equal(source: str, field: str, expected: Any, actual: Any) -> None:
    if expected != actual:
        raise ValueError(f"{source}: pair {field}: expected {expected!r}, actual {actual!r}")


def _sha(value: Any, source: str, field: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789ABCDEF" for c in value):
        raise ValueError(f"{source}: pair {field}: expected uppercase SHA256, actual {value!r}")


def index_ordered_pairs(report: dict[str, Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    """Index a source-hash-gated root report; the caller owns that input gate."""
    summary = report["layer3"]["pairedRootIdentities"]
    _equal("root-report", "status", "exact-ordered-witness-matches", summary.get("status"))
    pairs = summary.get("pairs")
    if not isinstance(pairs, list):
        raise ValueError("root-report: pair inventory: expected list, actual non-list")
    for name in ("candidatePairCount", "matchedPairCount", "mismatchedPairCount", "unpairedFileCount"):
        if type(summary.get(name)) is not int or summary[name] < 0:
            raise ValueError(f"root-report: pair {name}: expected nonnegative integer, actual {summary.get(name)!r}")
    for name in ("candidatePairCount", "matchedPairCount"):
        _equal("root-report", name, len(pairs), summary.get(name))
    for name in ("mismatchedPairCount", "unpairedFileCount"):
        _equal("root-report", name, 0, summary.get(name))
    _equal("root-report", "unpairedFiles", [], summary.get("unpairedFiles"))
    index = {}
    for pair in pairs:
        left, right = pair["init"], pair["streaming"]
        source = right["virtualPath"]
        _equal(source, "status", "exact-ordered-witness-match", pair.get("status"))
        _equal(source, "differences", [], pair.get("differences"))
        parent, _, leaf = source.rpartition("/")
        if not leaf.startswith("StreamingChunkData_") or not leaf.endswith(".bytes"):
            raise ValueError(f"{source}: pair leaf: expected StreamingChunkData_*.bytes")
        _equal(source, "Init leaf", parent + "/InitChunkData_" + leaf[len("StreamingChunkData_"):], left["virtualPath"])
        for name in ORDERED_FIELDS:
            _equal(source, name, left["witness"][name], right["witness"][name])
        for side in ("init", "streaming"):
            record = pair[side]
            for name in IDENTITY_FIELDS:
                if name not in record:
                    raise ValueError(f"{source}: pair {side}.{name}: expected present, actual absent")
            _sha(record["packedSha256"], source, f"{side}.packedSha256")
            witness = record["witness"]
            for field in WITNESS_FIELDS:
                if field not in witness:
                    raise ValueError(f"{source}: pair witness.{field}: expected present, actual absent")
            if type(witness["rowCount"]) is not int or witness["rowCount"] < 0:
                raise ValueError(f"{source}: pair rowCount: expected nonnegative integer, actual {witness['rowCount']!r}")
            for field in ORDERED_FIELDS[1:]:
                _sha(witness[field], source, f"{side}.{field}")
            _sha(witness["rowField0ValuesSha256"], source, f"{side}.rowField0ValuesSha256")
            if type(witness["field3DuplicateCount"]) is not int or not 0 <= witness["field3DuplicateCount"] <= witness["rowCount"]:
                raise ValueError(f"{source}: pair field3DuplicateCount: expected bounded integer, actual {witness['field3DuplicateCount']!r}")
            path = record["virtualPath"]
            if path in index:
                raise ValueError(f"{path}: pair identity: expected unique, actual duplicate")
            index[path] = (side, pair)
    return index


def bind_current_pair(
    *, pair_index: dict[str, tuple[str, dict[str, Any]]], identity: dict[str, Any],
    decoded: bytes, parsed: dict[str, Any], root_report_sha256: str,
) -> dict[str, Any]:
    """Recheck this side; publication additionally requires the full source-set gate.

    Init's marker and Streaming's marker agree by complete ordered vector
    equality. An old runtime key can still retain a different historical marker.
    """
    source = identity["virtualPath"]
    if source not in pair_index:
        raise ValueError(f"{source}: pair identity: expected authenticated mate, actual absent")
    side, pair = pair_index[source]
    record = pair[side]
    for name in IDENTITY_FIELDS:
        expected, actual = record[name], identity.get(name)
        if name == "physicalChunkPath":
            expected = str(expected).replace("\\", "/").casefold()
            actual = str(actual).replace("\\", "/").casefold()
        _equal(source, name, expected, actual)
    witness = parsed["anonymousParallelSubgraph"]["orderedRootWitness"]
    for name, expected in record["witness"].items():
        _equal(source, f"current witness.{name}", expected, witness.get(name))
    table = fmt._table_layout(decoded, fmt._u32(decoded, 0))
    vectors = {}
    for field, width in ((3, 4), (4, 1), (5, 4)):
        start, count, end = fmt._bounded_vector(decoded, table, field, width, f"pair field{field}")
        _equal(source, f"field{field} count", witness["rowCount"], count)
        if field != 5:
            _equal(source, f"field{field} bytes", witness[f"field{field}VectorSha256"],
                   hashlib.sha256(decoded[start:end]).hexdigest().upper())
        vectors[field] = start
    _sha(root_report_sha256, source, "rootReportSha256")
    return {
        "schema": "endfield.streaming-ordered-pair-context.v1",
        "source": source, "side": side, "rootReportSha256": root_report_sha256,
        "decodedSha256": hashlib.sha256(decoded).hexdigest().upper(),
        "sourcePair": {name: {field: pair[name][field] for field in IDENTITY_FIELDS}
                       for name in ("init", "streaming")},
        "orderedWitness": {field: witness[field] for field in ORDERED_FIELDS},
        "markerVectorStart": vectors[4], "rowVectorStart": vectors[5],
        "publicationCondition": "staged until complete corpus source-identity and start/end gates pass",
        "runtimeCondition": "new-key compatibility only; existing-key history/default overrides/runtime receipt unresolved",
    }


def bind_pair_row(data: bytes, row: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Tie a freshly parsed directory row to its exact serialized ordinal."""
    source = context["source"]
    _equal(source, "context schema", "endfield.streaming-ordered-pair-context.v1", context.get("schema"))
    _equal(source, "context side", "streaming", context.get("side"))
    _equal(source, "decoded SHA256", context.get("decodedSha256"), hashlib.sha256(data).hexdigest().upper())
    _equal(source, "directory root marker", 2, row.get("rootMarker"))
    ordinal, count = row.get("outerRowIndex"), context["orderedWitness"]["rowCount"]
    if type(ordinal) is not int or type(count) is not int or not 0 <= ordinal < count:
        raise ValueError(f"{source}: pair ordinal: expected integer in [0,{count}), actual {ordinal!r}")
    for name, width in (("markerVectorStart", 1), ("rowVectorStart", 4)):
        start = context.get(name)
        if type(start) is not int or start < 0 or start > len(data) - 4 - count * width:
            raise ValueError(f"{source}: pair {name}: expected bounded count/vector span, actual {start!r} for count {count}")
    marker_offset = context["markerVectorStart"] + 4 + ordinal
    _equal(source, "marker offset", marker_offset, row.get("rootMarkerOffset"))
    _equal(source, f"marker byte at {marker_offset}", 2, data[marker_offset])
    slot = context["rowVectorStart"] + 4 + ordinal * 4
    relative = fmt._u32(data, slot)
    if relative == 0 or slot + relative > len(data) - 4:
        raise ValueError(f"{source}: pair row slot {slot}: expected positive bounded uoffset, actual {relative}")
    _equal(source, "row table offset", slot + relative, row.get("outerRowOffset"))
    return {"outerRowIndex": ordinal, "rootMarkerOffset": marker_offset,
            "outerRowOffset": slot + relative, "rootReportSha256": context["rootReportSha256"],
            "classification": "conditional-new-key-native-read-window-compatibility",
            "runtimeReceipt": "unresolved"}
