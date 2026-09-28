"""Audit the current BundleManifest dependency graph against Unity CAB externals.

The BundleManifest and CABMap are independent outputs. This gate first
authenticates the manifest, its selected-build native field interpretation, the
full VFS ledger, and both CABMaps' selected source positions. It then projects
each CAB dependency through the selected Bundle span containing that CAB. A
projection is a stored-graph relation, not a runtime load or object ownership.
Dependencies without a selected CAB stay unresolved rather than being guessed.

What the current corpus establishes (stored container relationships only, no
Unity object ownership or load order): every projected external CAB target is
present in the manifest's ``directDependencies``, with a small named residual
of manifest-only edges; the reverse list is exactly the direct graph's
inverse; and ``dependencies`` is exactly its transitive closure. The selected
native Bundle proxy loaders both call
``RuntimeManifestBinary.TryGetBundleDirectDeps`` and read a loop element
before recursing (checked in the manifest-native contract), so the
manifest-only residual belongs to a list the loader can consume; its
authoring cause is unproved.

The same relation explains most AssetMap path/physical-Bundle disagreements:
the physical Bundle is in the path's listed Bundle's ``directDependencies``,
with the reciprocal reverse entry. That is a verified Bundle-list relation,
not proof that the mapped object belongs to, or loads through, either Bundle.

Join mechanics worth not re-deriving: every manifest list is sorted by Bundle
index and duplicate-free, while CAB externals keep their own order, so the
comparison is a multiset containment and never a sequence equality. One
selected Bundle holds both a main CAB and a ``.sharedAssets`` CAB, and both
are checked. A CAB's source root, chunk and offset must first land inside an
authenticated VFS Bundle span; stale AssetMap source chunks cannot supply
field ownership, and the StreamingAssets AssetMap needs selection per source
*and* offset because per-file overlay replacement leaves gaps inside chunks
that also hold verified files. Unselected external names are excluded from
the projection and counted separately.

Inputs: the dumped ``manifest.hgmmap``, the VFS audit summary and ledger with
its ``inputSetSha256``, ``--cabmap-dir export_full/meta/cab_map``, and the
explicit ``--gameassembly``/``--metadata`` pair. The conventional ``--out``
is ``reports/animestudio/bundle_cab_dependency_corpus_latest.json``.
"""

from __future__ import annotations

import argparse
import bisect
from collections import Counter, defaultdict, deque
import gzip
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

from scripts.game_data.bundle_manifest import parse_decompressed_bundle_manifest
from scripts.game_data.bundle_manifest_corpus import MANIFEST_PATH, _record, inspect as inspect_manifest
from scripts.game_data.bundle_manifest_native import audit_bundle_manifest_native
from scripts.game_data.cabmap import MAXIMUM_CABS_PER_LOGICAL_FILE, CabEntry, parse_cabmap


SCHEMA = "endfield.bundle-cab-dependency-corpus.v1"
PREFIX = "Data/Bundles/Windows/"
MAP_NAMES = {
    "Persistent": "endfield_persistent_assets.bin",
    "StreamingAssets": "endfield_streamingassets_assets.bin",
}


def _require(condition: bool, check: str) -> None:
    if not condition:
        raise ValueError(f"bundle-cab-dependency:{check}")


def _norm(path: str | Path) -> str:
    return str(path).replace("\\", "/").casefold()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _selected_spans(ledger: Path, input_set: str) -> tuple[
    dict[str, list[tuple[int, int, str]]], dict[str, str]
]:
    chunks: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    names: dict[str, str] = {}
    with gzip.open(ledger, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            _require(row.get("inputSetSha256", "").upper() == input_set,
                     f"ledger-input-set:{line_number}")
            if row.get("recordType") != "file" or row.get("blockName") not in {"Bundle", "InitBundle"}:
                continue
            if row.get("status") != "verified" or row.get("boundaryStatus") != "boundary_verified":
                continue
            name = row["fileName"]
            _require(name.startswith(PREFIX) and name not in names, f"selected-name:{name}")
            root = _norm(row["physicalChunkRoot"])
            chunk = _norm(row["physicalChunkPath"])
            _require(chunk.startswith(root + "/"), f"selected-root:{name}")
            start = row["offset"]
            end = start + row["length"]
            _require(0 <= start < end, f"selected-span:{name}")
            chunks[chunk].append((start, end, name))
            names[name] = row["blockName"]
    for chunk, records in chunks.items():
        records.sort()
        for left, right in zip(records, records[1:]):
            _require(left[1] <= right[0], f"overlapping-selected-spans:{chunk}")
    return chunks, names


def _manifest_dependency_lists(raw: bytes) -> tuple[
    list[str], list[list[tuple[int, ...]]], dict[str, int]
]:
    import brotli

    decoded = brotli.decompress(raw)
    parsed = parse_decompressed_bundle_manifest(decoded)
    table = parsed.tables[2]
    region = parsed.variable_region
    payload = memoryview(decoded)[region.payload_offset:region.footer_offset]
    names: list[str] = []
    dependency_lists: list[list[tuple[int, ...]]] = []
    shape = Counter()
    for index in range(table.row_count):
        words = struct.unpack_from("<12I", decoded, table.offset + index * 48)
        offset = words[1]
        suffix, _raw_record, end = _record(payload, offset)
        next_offset = (
            struct.unpack_from("<I", decoded, table.offset + (index + 1) * 48 + 4)[0]
            if index + 1 < table.row_count else region.opaque_suffix_offset
        )
        _require(end == next_offset, f"indexed-record-end:{index}")
        name = PREFIX + suffix
        _require(not names or name > names[-1], f"indexed-name-order:{index}")
        names.append(name)
        cursor = offset + 4 + len(suffix.encode("utf-16-le")) + 2
        row_lists: list[tuple[int, ...]] = []
        for ordinal in range(3):
            count = struct.unpack_from("<I", payload, cursor)[0]
            cursor += 4
            _require(count <= (end - cursor - 2) // 4, f"dependency-bounds:{index}:{ordinal}")
            values = struct.unpack_from("<" + "I" * count, payload, cursor) if count else ()
            cursor += 4 * count + 2
            _require(values == tuple(sorted(set(values))), f"dependency-order:{index}:{ordinal}")
            _require(all(value < table.row_count for value in values),
                     f"dependency-index:{index}:{ordinal}")
            row_lists.append(values)
            shape[f"list{ordinal}Rows"] += 1
            shape[f"list{ordinal}Edges"] += count
        _require(cursor == end, f"dependency-record-end:{index}")
        dependency_lists.append(row_lists)
    return names, dependency_lists, dict(shape)


def _validate_manifest_graph(rows: list[list[tuple[int, ...]]]) -> dict[str, Any]:
    """Check reverse edges and the full transitive dependency closure."""

    count = len(rows)
    reverse = [row[1] for row in rows]
    direct = [row[2] for row in rows]
    incoming: list[list[int]] = [[] for _ in range(count)]
    for index, targets in enumerate(direct):
        for target in targets:
            _require(target < count, f"direct-target:{index}:{target}")
            incoming[target].append(index)
    for index, expected in enumerate(reverse):
        _require(tuple(incoming[index]) == expected, f"direct-reverse:{index}")
    remaining = [len(targets) for targets in direct]
    queue = deque(index for index, value in enumerate(remaining) if value == 0)
    closures: list[set[int] | None] = [None] * count
    processed = 0
    while queue:
        index = queue.popleft()
        closure: set[int] = set()
        for target in direct[index]:
            target_closure = closures[target]
            _require(target_closure is not None, f"dependency-order:{index}:{target}")
            closure.add(target)
            closure.update(target_closure)
        _require(tuple(sorted(closure)) == rows[index][0], f"transitive-closure:{index}")
        closures[index] = closure
        processed += 1
        for parent in incoming[index]:
            remaining[parent] -= 1
            if remaining[parent] == 0:
                queue.append(parent)
    _require(processed == count, f"dependency-cycle:{processed}/{count}")
    return {
        "acyclic": True,
        "directReverseExact": True,
        "dependenciesAreExactTransitiveClosure": True,
        "directEdges": sum(len(targets) for targets in direct),
        "reverseEdges": sum(len(targets) for targets in reverse),
        "closureEdges": sum(len(row[0]) for row in rows),
    }


def _project_dependencies(
    names: list[str], direct_lists: list[tuple[int, ...]],
    selected: dict[str, list[tuple[str, CabEntry]]], cab_target: dict[str, str],
) -> dict[str, Any]:
    outcomes = Counter()
    unknown = Counter()
    mismatches: list[dict[str, Any]] = []
    for index, name in enumerate(names):
        entries = selected[name]
        expected = Counter(names[value] for value in direct_lists[index])
        bundle_match = True
        for root, entry in entries:
            projected: Counter[str] = Counter()
            projected_order: list[str] = []
            raw_unknown: list[str] = []
            for dependency in entry.dependencies:
                target = cab_target.get(dependency)
                if target is None:
                    unknown[dependency] += 1
                    raw_unknown.append(dependency)
                else:
                    projected[target] += 1
                    projected_order.append(target)
            if not (projected - expected):
                outcomes["cabRecordsProjectedSubsetOfManifest"] += 1
            else:
                outcomes["cabRecordsWithCabOnlyDependency"] += 1
            if raw_unknown:
                outcomes["cabRecordsWithUnresolvedExternal"] += 1
            if projected == expected:
                outcomes["cabRecordsMatchingManifestProjection"] += 1
            else:
                bundle_match = False
                outcomes["cabRecordsDifferingFromManifestProjection"] += 1
                mismatches.append({
                    "bundle": name, "sourceRoot": root, "cab": entry.cab,
                    "manifestOnly": sorted((expected - projected).elements()),
                    "cabOnly": sorted((projected - expected).elements()),
                    "unresolvedExternal": raw_unknown,
                })
            if not raw_unknown and projected == expected:
                outcomes["cabRecordsExactSelectedTargetMultiset"] += 1
            if not raw_unknown and projected_order == [names[v] for v in direct_lists[index]]:
                # Descriptive only: the manifest order is by Bundle index,
                # while the CABMap preserves the Unity externals order.
                outcomes["cabRecordsSameOrder"] += 1
        outcomes["bundlesMatchingEveryCabProjection" if bundle_match else "bundlesWithProjectionDifference"] += 1
        if len(entries) > 1:
            outcomes["bundlesWithMultipleCabs"] += 1
    return {
        "outcomes": dict(outcomes),
        "unresolvedExternalNames": dict(unknown),
        "mismatches": mismatches,
        "evidenceBoundary": {
            "exact": "For selected VFS spans, every CABMap entry is placed by its own source root, chunk and offset; each selected CAB name maps to one Bundle logical path. The authenticated native contract names the manifest's third list directDependencies.",
            "conditional": "A CAB external with a selected CAB target is projected to that target's Bundle path and compared as a multiset. Unselected CAB names are excluded from the projected relation and counted separately.",
            "unresolved": "A manifest dependency absent from Unity CAB externals is a stored-graph difference; the audit does not infer why it was authored or which runtime loader follows it. CABMap source positions do not independently verify Unity object ownership.",
        },
    }


def audit(
    *, manifest: Path, outer_summary: Path, outer_ledger: Path,
    cabmap_dir: Path, expected_input_set_sha256: str,
    gameassembly: Path, metadata: Path,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": SCHEMA, "status": "mismatched", "detail": "",
        "expectedInputSetSha256": expected_input_set_sha256.upper(),
    }
    try:
        summary = json.loads(outer_summary.read_text(encoding="utf-8"))
        input_set = str(summary.get("inputSetSha256", "")).upper()
        _require(input_set == expected_input_set_sha256.upper(), "input-set-sha256")
        _require(summary.get("summary", {}).get("fullAuditPassed") is True,
                 "outer-full-audit")
        outer_join = inspect_manifest(
            manifest, outer_summary, outer_ledger, expected_input_set_sha256
        )
        _require(outer_join["status"] == "validated", "manifest-outer-join")
        native = audit_bundle_manifest_native(
            manifest=manifest, gameassembly=gameassembly, metadata=metadata
        )
        _require(native["status"] == "validated",
                 f"native:{native['status']}:{native.get('detail','')}")
        chunks, selected_names = _selected_spans(outer_ledger, input_set)
        names, lists, list_shape = _manifest_dependency_lists(manifest.read_bytes())
        _require(set(names) == set(selected_names), "manifest-selected-name-set")
        graph = _validate_manifest_graph(lists)
        direct_lists = [row[2] for row in lists]
        del lists
        starts = {chunk: [span[0] for span in records] for chunk, records in chunks.items()}
        selected: dict[str, list[tuple[str, CabEntry]]] = defaultdict(list)
        cab_target: dict[str, str] = {}
        map_sources: dict[str, Any] = {}
        placement = Counter()
        for root, file_name in MAP_NAMES.items():
            map_path = cabmap_dir / file_name
            base, entries = parse_cabmap(map_path.read_bytes())
            expected_base = (summary["primaryAssets"] if root == "Persistent"
                             else summary["fallbackAssets"])
            _require(_norm(base) == _norm(expected_base), f"cabmap-root:{root}")
            _require(len(entries) == len({entry.cab for entry in entries}),
                     f"cabmap-duplicate-cab:{root}")
            map_sources[root] = {
                "path": str(map_path), "sha256": _sha256(map_path),
                "baseFolder": base, "entries": len(entries),
            }
            for entry in entries:
                chunk = _norm(Path(base) / entry.path)
                records = chunks.get(chunk)
                if records is None:
                    placement[f"{root}:chunkNotSelected"] += 1
                    continue
                at = bisect.bisect_right(starts[chunk], entry.offset) - 1
                if at < 0 or entry.offset >= records[at][1]:
                    placement[f"{root}:offsetNotSelected"] += 1
                    continue
                bundle = records[at][2]
                prior = cab_target.setdefault(entry.cab, bundle)
                _require(prior == bundle, f"selected-cab-ambiguous:{entry.cab}")
                selected[bundle].append((root, entry))
                placement[f"{root}:selected"] += 1
        _require(set(selected) == set(names), "cabmap-selected-bundle-set")
        _require(all(1 <= len(entries) <= MAXIMUM_CABS_PER_LOGICAL_FILE
                     for entries in selected.values()), "cabmap-per-bundle-cap")
        relation = _project_dependencies(names, direct_lists, selected, cab_target)
        report.update(
            status="complete", inputSetSha256=input_set,
            inputs={
                "manifest": {"path": str(manifest), "sha256": _sha256(manifest)},
                "outerSummary": {"path": str(outer_summary), "sha256": _sha256(outer_summary)},
                "outerLedger": {"path": str(outer_ledger), "sha256": _sha256(outer_ledger)},
                "nativeContractSha256": native["contractSha256"],
                "gameAssemblySha256": native["nativeInputs"]["gameAssemblySha256"],
                "globalMetadataSha256": native["nativeInputs"]["globalMetadataSha256"],
                "cabMaps": map_sources,
            },
            manifest={"bundleRows": len(names), "dependencyListShape": list_shape,
                      "graph": graph},
            cabMapPlacement={"selectedBundleFiles": len(selected),
                             "selectedCabNames": len(cab_target), "outcomes": dict(placement)},
            dependencyRelation=relation,
        )
    except (OSError, ValueError, KeyError, IndexError, struct.error, UnicodeError) as error:
        report["detail"] = str(error)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--outer-summary", type=Path, required=True)
    parser.add_argument("--outer-ledger", type=Path, required=True)
    parser.add_argument("--cabmap-dir", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(
        manifest=args.manifest, outer_summary=args.outer_summary,
        outer_ledger=args.outer_ledger, cabmap_dir=args.cabmap_dir,
        expected_input_set_sha256=args.expected_input_set_sha256,
        gameassembly=args.gameassembly, metadata=args.metadata,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Bundle/CAB dependency corpus: {result['status']}")
    if result["status"] != "complete":
        print(f"  {result['detail']}")
        return 1
    relation = result["dependencyRelation"]["outcomes"]
    print(f"  {result['manifest']['bundleRows']} Bundles; "
          f"{relation.get('bundlesMatchingEveryCabProjection', 0)} projected matches; "
          f"{relation.get('bundlesWithProjectionDifference', 0)} differences")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
