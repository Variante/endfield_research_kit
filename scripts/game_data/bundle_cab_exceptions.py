"""Explain the bounded residuals of the current Bundle/CAB dependency join.

The complete dependency corpus gate runs first. This audit then locates each
unselected CAB external at its selected referring Bundle and checks for an
exact-name installed Resources file. A same-name file is a candidate, not a
proved Unity runtime resolution. It also records manifest AssetInfo paths for
the few Bundles on either side of a manifest-only edge.

Current reading: the manifest-only residual's sources are dialog timeline
prefabs with manifest AssetInfo paths, while the common target has no
AssetInfo row and no matching CAB external. The common unselected external is
the ``unity default resources`` literal, which matches an installed
serialized file and a UnityPlayer string (identity is settled by
``bundle_external_identity_corpus``). A second, CAB-shaped external name has
no selected CABMap source and no exact-name installed Resources file.

It takes the same inputs as ``bundle_cab_dependency_corpus``; the
conventional ``--out`` is
``reports/animestudio/bundle_cab_exceptions_latest.json``.
"""

from __future__ import annotations

import argparse
import bisect
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

from scripts.game_data.bundle_cab_dependency_corpus import (
    MAP_NAMES, _manifest_dependency_lists, _norm, _selected_spans, audit,
)
from scripts.game_data.bundle_manifest import parse_decompressed_bundle_manifest
from scripts.game_data.cabmap import parse_cabmap
from scripts.game_data.contracts import CONTRACTS_DIR


SCHEMA = "endfield.bundle-cab-exceptions.v1"
CONTRACT = CONTRACTS_DIR / "bundle_manifest_native.json"
EXAMPLE_CAP = 40


def _require(condition: bool, check: str) -> None:
    if not condition:
        raise ValueError(f"bundle-cab-exceptions:{check}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _resource_candidate(root: Path, external: str, unity_player_bytes: bytes) -> dict[str, Any]:
    row: dict[str, Any] = {"externalName": external, "status": "no-exact-name-file"}
    if not external or external in {".", ".."} or any(char in external for char in "/\\:"):
        row["status"] = "not-a-file-name"
        return row
    path = root / external
    if not path.is_file():
        return row
    data = path.read_bytes()
    row.update(status="exact-name-file", path=str(path), length=len(data),
               sha256=hashlib.sha256(data).hexdigest().upper())
    if len(data) >= 40:
        metadata_bytes = struct.unpack_from(">I", data, 20)[0]
        file_bytes = struct.unpack_from(">Q", data, 24)[0]
        data_offset = struct.unpack_from(">Q", data, 32)[0]
        row["serializedHeader"] = {
            "version": struct.unpack_from(">I", data, 8)[0],
            "metadataBytes": metadata_bytes,
            "fileBytes": file_bytes,
            "dataOffset": data_offset,
            "selfConsistent": file_bytes == len(data) and 0 < metadata_bytes < data_offset < len(data),
        }
    literal_offset = unity_player_bytes.find(external.encode("utf-8"))
    row["unityPlayerAsciiLiteralOffset"] = literal_offset if literal_offset >= 0 else None
    return row


def _unresolved_receipts(
    summary: dict[str, Any], ledger: Path, input_set: str,
    cabmap_dir: Path, unknown_names: dict[str, int],
) -> tuple[list[dict[str, Any]], dict[str, set[str]], dict[str, int]]:
    chunks, _names = _selected_spans(ledger, input_set)
    starts = {chunk: [span[0] for span in records] for chunk, records in chunks.items()}
    receipts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    totals: Counter[str] = Counter()
    source_bundles: dict[str, set[str]] = defaultdict(set)
    combinations: Counter[str] = Counter()
    for root, file_name in MAP_NAMES.items():
        map_path = cabmap_dir / file_name
        base, entries = parse_cabmap(map_path.read_bytes())
        expected_base = summary["primaryAssets"] if root == "Persistent" else summary["fallbackAssets"]
        _require(_norm(base) == _norm(expected_base), f"cabmap-root:{root}")
        for entry in entries:
            named = [(slot, external) for slot, external in enumerate(entry.dependencies)
                     if external in unknown_names]
            if not named:
                continue
            chunk = _norm(Path(base) / entry.path)
            spans = chunks.get(chunk)
            if not spans:
                continue
            index = bisect.bisect_right(starts[chunk], entry.offset) - 1
            if index < 0 or entry.offset >= spans[index][1]:
                continue
            bundle = spans[index][2]
            combinations[" + ".join(sorted(set(external for _, external in named)))] += 1
            for slot, external in named:
                source_bundles[external].add(bundle)
                totals[external] += 1
                if len(receipts[external]) < EXAMPLE_CAP:
                    receipts[external].append({
                        "bundle": bundle, "cab": entry.cab, "sourceRoot": root,
                        "cabMapPath": entry.path, "cabMapOffset": entry.offset,
                        "dependencySlot": slot,
                    })
    _require(dict(totals) == unknown_names, "unresolved-counts")
    rows = [{"externalName": external, "references": count,
             "selectedSourceExamples": receipts[external],
             "sourceExamplesTruncated": count > len(receipts[external])}
            for external, count in sorted(totals.items())]
    return rows, source_bundles, dict(combinations)


def _asset_info_receipts(manifest: Path, interesting: set[str]) -> dict[str, Any]:
    import brotli

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    spec = contract["assetInfoType"]
    header = spec["boxedValueHeaderBytes"]
    fields = {key: value - header for key, value in spec["fieldOffsets"].items()}
    decoded = brotli.decompress(manifest.read_bytes())
    parsed = parse_decompressed_bundle_manifest(decoded)
    names, _, _ = _manifest_dependency_lists(manifest.read_bytes())
    index_to_name = {index: name for index, name in enumerate(names) if name in interesting}
    _require(len(index_to_name) == len(interesting), "interesting-bundle-names")
    table = parsed.tables[0]
    _require(table.row_size == 32 and len(fields) >= 4, "asset-info-width")
    values_start = table.offset + table.row_count * 8
    payload = memoryview(decoded)[parsed.variable_region.payload_offset:parsed.variable_region.footer_offset]
    receipts: dict[str, dict[str, Any]] = {
        name: {"assetInfoRows": 0, "pathExamples": []} for name in interesting
    }
    for index in range(table.row_count):
        row = values_start + index * 24
        bundle_index = struct.unpack_from("<I", decoded, row + fields["bundleIndex"])[0]
        name = index_to_name.get(bundle_index)
        if name is None:
            continue
        result = receipts[name]
        result["assetInfoRows"] += 1
        if len(result["pathExamples"]) >= 4:
            continue
        pointer = struct.unpack_from("<I", decoded, row + fields["path"])[0]
        length = struct.unpack_from("<I", payload, pointer)[0]
        _require(pointer + 4 + length + 2 <= len(payload), f"asset-path-bounds:{index}")
        _require(payload[pointer+4+length:pointer+4+length+2].tobytes() == b"\0\0",
                 f"asset-path-terminator:{index}")
        path = brotli.decompress(payload[pointer+4:pointer+4+length]).decode("utf-16-le")
        result["pathExamples"].append({
            "path": path,
            "assetSize": struct.unpack_from("<i", decoded, row + fields["assetSize"])[0],
        })
    return dict(sorted(receipts.items()))


def inspect(
    *, manifest: Path, outer_summary: Path, outer_ledger: Path,
    cabmap_dir: Path, expected_input_set_sha256: str,
    gameassembly: Path, metadata: Path,
) -> dict[str, Any]:
    core = audit(
        manifest=manifest, outer_summary=outer_summary, outer_ledger=outer_ledger,
        cabmap_dir=cabmap_dir, expected_input_set_sha256=expected_input_set_sha256,
        gameassembly=gameassembly, metadata=metadata,
    )
    report: dict[str, Any] = {
        "schema": SCHEMA, "status": core["status"], "detail": core["detail"],
        "inputSetSha256": core.get("inputSetSha256"),
    }
    if core["status"] != "complete":
        return report
    try:
        summary = json.loads(outer_summary.read_text(encoding="utf-8"))
        unknown = core["dependencyRelation"]["unresolvedExternalNames"]
        unresolved, external_sources, combinations = _unresolved_receipts(
            summary, outer_ledger, core["inputSetSha256"], cabmap_dir, unknown,
        )
        mismatches = core["dependencyRelation"]["mismatches"]
        residual_bundles = {row["bundle"] for row in mismatches}
        residual_targets = {name for row in mismatches for name in row["manifestOnly"]}
        resource_root = Path(summary["primaryAssets"]).parent / "Resources"
        _require(resource_root.is_dir(), "resources-root")
        unity_player = gameassembly.with_name("UnityPlayer.dll")
        _require(_sha256(unity_player).upper() ==
                 json.loads(CONTRACT.read_text(encoding="utf-8"))["nativeInputs"]["unityPlayerSha256"].upper(),
                 "unity-player-hash")
        unity_player_bytes = unity_player.read_bytes()
        candidates = [_resource_candidate(resource_root, name, unity_player_bytes)
                      for name in sorted(unknown)]
        no_file_sources = sorted({bundle for row in candidates
                                  if row["status"] == "no-exact-name-file"
                                  for bundle in external_sources[row["externalName"]]})
        asset_info_bundles = residual_bundles | residual_targets | set(no_file_sources[:EXAMPLE_CAP])
        asset_info = _asset_info_receipts(manifest, asset_info_bundles)
        for key, path in (("manifest", manifest), ("outerSummary", outer_summary),
                          ("outerLedger", outer_ledger)):
            _require(_sha256(path) == core["inputs"][key]["sha256"], f"source-changed:{key}")
        for root, file_name in MAP_NAMES.items():
            _require(_sha256(cabmap_dir / file_name) ==
                     core["inputs"]["cabMaps"][root]["sha256"],
                     f"source-changed:cabmap:{root}")
        report.update(
            status="complete", detail="", inputs=core["inputs"],
            nativeRuntimeConsumers="validated by current bundle_manifest_native contract",
            manifestOnlyEdges=mismatches,
            manifestOnlySourceBundles=sorted(residual_bundles),
            manifestOnlyTargetBundles=sorted(residual_targets),
            unresolvedExternals=unresolved,
            unresolvedSelectedSourceBundles=len(set().union(*external_sources.values())),
            unresolvedSourceCombinations=combinations,
            resourceFileCandidates=candidates,
            assetInfoReceipts=asset_info,
            assetInfoSourceExamplesTruncated=len(no_file_sources) > EXAMPLE_CAP,
            evidenceBoundary={
                "direct": "The selected native sync and async Bundle loaders call TryGetBundleDirectDeps and recurse over returned entries. Manifest AssetInfo paths and CABMap source locations are from the complete authenticated corpus gate. An exact-name Resources file is an installed serialized-file candidate with its own SHA256 and self-consistent header.",
                "unresolved": "The four manifest-only edges have no CABMap external witness; the authoring producer of those edges and live branch execution are not observed. Exact Resources filename equality does not prove Unity's external-file binding. A CAB external with no selected CAB or exact Resources file has no resolved target.",
            },
        )
    except (OSError, ValueError, KeyError, IndexError, struct.error, UnicodeError) as error:
        report.update(status="mismatched", detail=str(error))
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
    result = inspect(
        manifest=args.manifest, outer_summary=args.outer_summary,
        outer_ledger=args.outer_ledger, cabmap_dir=args.cabmap_dir,
        expected_input_set_sha256=args.expected_input_set_sha256,
        gameassembly=args.gameassembly, metadata=args.metadata,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Bundle/CAB exceptions: {result['status']}")
    if result["status"] != "complete":
        print(f"  {result['detail']}")
        return 1
    print(f"  {len(result['manifestOnlyEdges'])} manifest-only edges; "
          f"{len(result['unresolvedExternals'])} unresolved external names")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
