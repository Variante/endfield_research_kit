"""Replay the selected BuffData compact stacking branch against a completed gate.

The source report is a complete authenticated VFS corpus gate. This follow-on
receipt rechecks its unique accepted EOF candidate and logical SHA/length
against each exported file before applying the selected native child contract.
The following tag array has separate native ownership; timeline interiors stay
structural where the existing reader uses an opaque endpoint search.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.game_data.memorypack.buff import (
    buff_post_id_result_is_exact_tail,
    decode_buff_post_id_prefix_at,
    find_buff_timeline_actions_body_end,
    read_buff_trigger_interval_bool_tail_exact,
)
from scripts.game_data.memorypack.buff_stacking_compact_native import (
    CONTRACT_PATH,
    decode_stacking_settings_compact,
    validate_current_native_contract,
)


FORMAT = "animestudio-buffdata-current-vfs-corpus"
PREFIX = "Data/Json/BuffData/"


def _read_report_rows(path: Path, *, expected_input_set_sha256: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Stream the pretty-printed corpus rows without loading its large body."""
    header: dict[str, Any] = {}
    selected: dict[str, Any] = {}
    digest = hashlib.sha256()
    in_files = False
    current = bytearray()
    closed = False
    with path.open("rb") as stream:
        for raw in stream:
            digest.update(raw)
            line = raw.decode("utf-8")
            if not in_files:
                if line.startswith('  "files": ['):
                    in_files = True
                    continue
                if line.startswith("  ") and not line.startswith("    ") and ":" in line:
                    name, value = line.strip().split(":", 1)
                    if name.strip('"') in {"format", "schemaVersion", "inputSetSha256", "status", "publicationEligible"}:
                        header[name.strip('"')] = json.loads(value.strip().rstrip(","))
                continue
            if line.startswith("  ]") and not current:
                in_files = False
                closed = True
                continue
            if closed:
                continue
            if line.startswith("    {") and not current:
                current.extend(raw)
            elif current:
                current.extend(raw)
            if current and (line.rstrip("\r\n") == "    }," or line.rstrip("\r\n") == "    }"):
                row = json.loads(current.rstrip().rstrip(b","))
                current.clear()
                identity = row.get("identity") or {}
                source = identity.get("virtualPath")
                if not isinstance(source, str) or not source.startswith(PREFIX) or "/" in source[len(PREFIX):]:
                    raise ValueError(f"buff-stacking-corpus:invalid-identity={source!r}")
                if source in selected:
                    raise ValueError(f"buff-stacking-corpus:duplicate-identity={source}")
                if (identity.get("status") != "verified"
                        or identity.get("boundaryStatus") != "boundary_verified"
                        or identity.get("inputSetSha256") != expected_input_set_sha256
                        or row.get("coverageStatus") != "unique"
                        or row.get("namedOuterFrameStatus") != "named_exact_frame"):
                    raise ValueError(f"buff-stacking-corpus:source-gate={source}")
                accepted = [candidate for candidate in row.get("candidates", [])
                            if candidate.get("readerAcceptedThroughEof")]
                if len(accepted) != 1 or int(accepted[0]["readerEndOffset"], 0) != identity["length"]:
                    raise ValueError(f"buff-stacking-corpus:accepted-eof-candidate={source}")
                selected[source] = {
                    "length": identity["length"], "sha256": row["logicalSha256"],
                    "anchor": accepted[0]["anchorOffset"],
                }
    if current or not closed or not selected:
        raise ValueError(f"buff-stacking-corpus:incomplete-report={path}")
    if (header.get("format") != FORMAT or header.get("schemaVersion") != 1
            or header.get("inputSetSha256") != expected_input_set_sha256
            or header.get("status") != "complete" or header.get("publicationEligible") is not True):
        raise ValueError(f"buff-stacking-corpus:report-gate={header!r}")
    header["reportSha256"] = digest.hexdigest().upper()
    return header, selected


def _after_stacking(data: bytes, offset: int) -> dict[str, Any]:
    """Follow the separate raw GameplayTag array and structural timeline tail."""
    if offset + 4 > len(data):
        raise ValueError(f"tagsAfterTriggerExtendBuffAction:truncated-count={offset}")
    tag_count = struct.unpack_from("<i", data, offset)[0]
    if not -1 <= tag_count <= 256:
        raise ValueError(f"tagsAfterTriggerExtendBuffAction:count={tag_count}; offset={offset}")
    tag_end = offset + 4 + max(tag_count, 0) * 4
    if tag_end + 4 > len(data):
        raise ValueError(f"tagsAfterTriggerExtendBuffAction:truncated-items={offset}")
    tag_ids = [struct.unpack_from("<I", data, offset + 4 + i * 4)[0]
               for i in range(max(tag_count, 0))]
    timeline_count = struct.unpack_from("<i", data, tag_end)[0]
    if not -1 <= timeline_count <= 256:
        raise ValueError(f"timelineActions:count={timeline_count}; offset={tag_end}")
    timeline_start = tag_end + 4
    if timeline_count > 0:
        trigger_at, pattern = find_buff_timeline_actions_body_end(
            data, timeline_start, timeline_count
        )
        timeline_status = "opaque-structural-endpoint"
    else:
        trigger_at, pattern = timeline_start, None
        timeline_status = "empty-or-null"
    _trigger, _time_dilation, _wait_first, end = read_buff_trigger_interval_bool_tail_exact(
        data, trigger_at
    )
    if end != len(data):
        raise ValueError(f"tail:expected-eof={len(data)} actual={end}")
    return {
        "tagCount": tag_count, "tagIdsRaw": tag_ids,
        "tagRange": [offset, tag_end], "timelineCount": timeline_count,
        "timelineBodyStatus": timeline_status,
        "timelineBodyRange": [timeline_start, trigger_at],
        "timelineEndpointPattern": pattern,
        "triggerIntervalOffset": trigger_at,
    }


def audit_compact_branch(
    corpus_path: Path, export_root: Path, *, expected_input_set_sha256: str
) -> dict[str, Any]:
    expected = expected_input_set_sha256.upper()
    native = validate_current_native_contract()
    if native.get("status") != "validated":
        raise ValueError(f"buff-stacking-corpus:native={native.get('status')} {native.get('detail','')}")
    header, selected = _read_report_rows(corpus_path, expected_input_set_sha256=expected)
    export_paths = {PREFIX + path.name for path in export_root.glob("*.json")}
    if set(selected) != export_paths:
        raise ValueError(f"buff-stacking-corpus:export-identity-set added={len(export_paths-set(selected))} "
                         f"missing={len(set(selected)-export_paths)}")
    counts: Counter[str] = Counter()
    rows = []
    for source in sorted(selected):
        expected_row = selected[source]
        path = export_root / source[len(PREFIX):]
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest().upper()
        if len(data) != expected_row["length"] or digest != expected_row["sha256"]:
            raise ValueError(f"buff-stacking-corpus:logical-sha-or-length={source}")
        stem = path.stem
        marker = len(stem.encode("utf-8")).to_bytes(4, "little") + stem.encode("utf-8")
        accepted = []
        scan = 1
        while (anchor := data.find(marker, scan)) >= 0:
            decoded = decode_buff_post_id_prefix_at(data, stem, anchor)
            if (buff_post_id_result_is_exact_tail(decoded)
                    and int(decoded["endOffset"], 0) == len(data)):
                accepted.append((anchor, decoded))
            scan = anchor + 1
        if len(accepted) != 1 or accepted[0][0] != expected_row["anchor"]:
            raise ValueError(f"buff-stacking-corpus:accepted-candidate-drift={source} "
                             f"expected={expected_row['anchor']} actual={[row[0] for row in accepted]}")
        anchor, old = accepted[0]
        old_stacking = old["stackingSettings"]
        child = decode_stacking_settings_compact(
            data, int(old_stacking["offset"], 0), native_validation=native
        )
        tail = _after_stacking(data, child["consumedEnd"])
        tag_at = int(old["tagsAfterTriggerExtendBuffAction"]["offset"], 0)
        if child["consumedEnd"] != tag_at or tail["tagRange"][0] != tag_at:
            raise ValueError(f"buff-stacking-corpus:child-tag-join={source}; "
                             f"childEnd={child['consumedEnd']} tagStart={tag_at}")
        counts["files"] += 1
        counts["key." + child["stackingKeyBranch"]] += 1
        counts["stackEffects.positive" if child["stackEffectsCount"] else "stackEffects.zero"] += 1
        counts["tags.positive" if tail["tagCount"] > 0 else "tags.emptyOrNull"] += 1
        counts["timeline.positive" if tail["timelineCount"] > 0 else "timeline.emptyOrNull"] += 1
        rows.append({
            "source": source, "logicalSha256": digest, "physicalEof": len(data),
            "acceptedAnchor": anchor, "stackingStart": child["startOffset"],
            "stackingEnd": child["consumedEnd"], "tagStart": tag_at,
            "stackingKeyBranch": child["stackingKeyBranch"],
            "stackingKeyRange": child["stackingKeyRange"],
            "stackingTypeRange": child["stackingTypeRange"],
            "stackEffectsBodyStatus": child["stackEffectsBodyStatus"],
            "tagCount": tail["tagCount"], "tagRange": tail["tagRange"],
            "timelineCount": tail["timelineCount"],
            "timelineBodyStatus": tail["timelineBodyStatus"],
            "triggerIntervalOffset": tail["triggerIntervalOffset"],
            "reachedEof": True,
        })
    return {
        "schema": "endfield.buff-stacking-compact-corpus-receipt.v1",
        "status": "complete", "publicationEligible": True,
        "inputSetSha256": expected,
        "sourceReport": {"path": str(corpus_path), "sha256": header["reportSha256"]},
        "nativeContract": {"path": str(CONTRACT_PATH),
                           "sha256": hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest().upper(),
                           "status": native["status"]},
        "counts": dict(sorted(counts.items())), "rows": rows,
        "wholeBuffSchemaExact": False,
        "evidenceBoundary": {
            "exact": "Each exported logical file matches the complete VFS gate's SHA256 and length; one independently accepted EOF candidate is replayed. The selected native source names the compact stacking child cursor and the following raw GameplayTag array; every corrected tail rejoins physical EOF.",
            "structuralOnly": "Positive stackEffects and timelineActions bodies retain their opaque or structural endpoint status. No runtime stacking or action behavior follows from stored bytes.",
            "unresolved": "The whole BuffData recursive naming proof and alternate native builds remain open."
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-report", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = audit_compact_branch(
        args.corpus_report, args.export_root,
        expected_input_set_sha256=args.expected_input_set_sha256,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "counts": result["counts"],
                      "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
