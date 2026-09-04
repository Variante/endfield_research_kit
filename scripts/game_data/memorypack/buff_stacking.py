"""Current-build audit for the anonymous BuffData member-18 stacking shape.

The reader in :mod:`buff` proves record boundaries from byte anchors and EOF
consumption.  It intentionally leaves the bytes between those anchors opaque
and does not assign setter-order field names to them.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .buff import decode_buff_memorypack


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_buff_stacking_member18(
    census_path: Path,
    boundary_report_path: Path,
    boundary_ledger_path: Path,
    *,
    expected_input_set_sha256: str | None = None,
    expected_target_count: int | None = None,
) -> dict[str, Any]:
    census = json.loads(census_path.read_text(encoding="utf-8"))
    boundary = json.loads(boundary_report_path.read_text(encoding="utf-8"))
    input_set = str(boundary.get("inputSetSha256") or "").upper()
    if len(input_set) != 64:
        raise ValueError("boundary-report:missing-inputSetSha256")
    if expected_input_set_sha256 and input_set != expected_input_set_sha256.upper():
        raise ValueError(
            "boundary-report:inputSetSha256-mismatch "
            f"expected={expected_input_set_sha256.upper()} actual={input_set}"
        )

    sources = boundary.get("sourceFingerprints")
    if not isinstance(sources, list) or not sources:
        raise ValueError("boundary-report:missing-sourceFingerprints")
    for index, source in enumerate(sources):
        path = Path(str(source.get("path") or ""))
        expected_hash = str(source.get("sha256") or "").lower()
        if not path.is_file():
            raise ValueError(f"sourceFingerprints[{index}]:missing path={path}")
        actual_hash = _sha256_file(path)
        if actual_hash != expected_hash:
            raise ValueError(
                f"sourceFingerprints[{index}]:sha256-mismatch path={path} "
                f"expected={expected_hash} actual={actual_hash}"
            )

    metadata = census.get("inputs", {}).get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("census:missing-metadata-provenance")
    metadata_path = Path(str(metadata.get("path") or ""))
    metadata_hash = str(metadata.get("sha256") or "").lower()
    if not metadata_path.is_file() or _sha256_file(metadata_path) != metadata_hash:
        raise ValueError(f"census:metadata-provenance-mismatch path={metadata_path}")

    current_rows: dict[str, dict[str, Any]] = {}
    with gzip.open(boundary_ledger_path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            virtual_path = str(row.get("virtualPath") or "")
            if (
                row.get("boundaryStatus") == "boundary_verified"
                and "/BuffData/" in virtual_path
            ):
                if virtual_path in current_rows:
                    raise ValueError(f"boundary-ledger:duplicate path={virtual_path}")
                current_rows[virtual_path] = row

    census_rows = census.get("files")
    if not isinstance(census_rows, list):
        raise ValueError("census:missing-files")
    previous_paths = {str(row.get("virtualPath") or "") for row in census_rows}
    if "" in previous_paths or len(previous_paths) != len(census_rows):
        raise ValueError("census:missing-or-duplicate-virtualPath")
    current_paths = set(current_rows)

    changed_rows: list[dict[str, Any]] = []
    target_rows: list[dict[str, Any]] = []
    action_member_counts: Counter[str] = Counter()
    stack_effect_counts: Counter[str] = Counter()
    for row in census_rows:
        virtual_path = str(row["virtualPath"])
        current = current_rows.get(virtual_path)
        if current is None:
            continue
        payload_path = Path(str(row.get("exportPath") or ""))
        data = payload_path.read_bytes()
        old_md5 = hashlib.md5(data).hexdigest().upper()
        new_md5 = str(current.get("recomputedFileDataMd5") or "").upper()
        if old_md5 != new_md5 or len(data) != current.get("length"):
            changed_rows.append(
                {
                    "virtualPath": virtual_path,
                    "previousLength": len(data),
                    "currentLength": current.get("length"),
                    "previousMd5": old_md5,
                    "currentMd5": new_md5,
                }
            )
            continue

        decoded = decode_buff_memorypack(payload_path, data, len(data))
        post_id = decoded["decoded"]["postIdPrefix"]
        stacking = post_id.get("stackingSettings") or {}
        member_counts = stacking.get("effectActionMemberCountCounts") or {}
        member18_count = int(member_counts.get("18") or 0)
        if not member18_count:
            continue
        exact = post_id.get("status") == "parsed-through-exact-tail"
        target_rows.append(
            {
                "virtualPath": virtual_path,
                "status": "exact-to-eof" if exact else "failed",
                "stackEffectCount": stacking.get("stackEffectsCount"),
                "member18ActionCount": member18_count,
                "diagnostic": None if exact else post_id.get("tailParseError"),
            }
        )
        action_member_counts[str(member18_count)] += 1
        stack_effect_counts[str(stacking.get("stackEffectsCount"))] += 1

    if expected_target_count is not None and len(target_rows) != expected_target_count:
        raise ValueError(
            f"member18-target-count-mismatch expected={expected_target_count} "
            f"actual={len(target_rows)}"
        )
    failed = [row for row in target_rows if row["status"] != "exact-to-eof"]
    if failed:
        raise ValueError(
            f"member18-boundary-failure count={len(failed)} first={failed[0]}"
        )

    return {
        "schemaVersion": 1,
        "inputSetSha256": input_set,
        "metadataSha256": metadata_hash,
        "sourceFingerprintCount": len(sources),
        "logicalIdentityDiff": {
            "added": sorted(current_paths - previous_paths),
            "removed": sorted(previous_paths - current_paths),
            "changed": changed_rows,
        },
        "currentBuffDataCount": len(current_rows),
        "member18TargetCount": len(target_rows),
        "member18ExactToEofCount": len(target_rows) - len(failed),
        "member18ActionCountPerFile": dict(sorted(action_member_counts.items())),
        "stackEffectCountPerFile": dict(sorted(stack_effect_counts.items())),
        "rows": target_rows,
        "wholeBuffSchemaExact": False,
        "evidenceBoundary": (
            "current ledger identity plus anonymous member-18 action envelope: "
            "member count, discriminator, one-byte nested marker, bounded UTF-8 P_ anchor, "
            "fixed current-build extent, guard tail, and downstream exact EOF; interior bytes "
            "and semantic field ownership remain opaque"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("census", type=Path)
    parser.add_argument("boundary_report", type=Path)
    parser.add_argument("boundary_ledger", type=Path)
    parser.add_argument("--expected-input-set-sha256")
    parser.add_argument("--expected-target-count", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = audit_buff_stacking_member18(
        args.census,
        args.boundary_report,
        args.boundary_ledger,
        expected_input_set_sha256=args.expected_input_set_sha256,
        expected_target_count=args.expected_target_count,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
