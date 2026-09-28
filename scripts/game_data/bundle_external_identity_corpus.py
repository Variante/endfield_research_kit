"""Join selected CAB externals to independently serialized Resources identities.

The Bundle/CAB exception gate authenticates the current VFS, CABMap, manifest,
and native consumer first.  This gate then checks a complete object index from
the same installed StreamingAssets tree and the standalone Unity ``Resources``
files.  A matching filename, external slot, and target PathID is an authored
serialized-object identity; it does not prove Unity executed a resolver.
"""

from __future__ import annotations

import argparse
import bisect
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.game_data.bundle_cab_dependency_corpus import _norm, _selected_spans
from scripts.game_data.bundle_cab_exceptions import inspect as inspect_exceptions
from scripts.game_data.cabmap import parse_cabmap
from scripts.game_data.extraction.export_full_from_game import (
    collect_source_sizes, load_animestudio_object_index_summary,
)
from scripts.game_data.unity_serialized_identity import (
    object_name, parse_no_type_tree_v22,
)


SCHEMA = "endfield.bundle-external-serialized-identity.v1"
EXAMPLE_CAP = 12


def _require(condition: bool, check: str) -> None:
    if not condition:
        raise ValueError(f"bundle-external-identity:{check}")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _resource_inventory(resources_root: Path) -> dict[str, dict[str, Any]]:
    _require(resources_root.is_dir(), "resources-root")
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(resources_root.iterdir()):
        _require(path.is_file(), f"non-file-resource:{path.name}")
        data = path.read_bytes()
        parsed = parse_no_type_tree_v22(data)
        _require(path.name not in result, f"duplicate-resource:{path.name}")
        result[path.name] = {
            "path": str(path), "length": len(data), "sha256": _sha256(data),
            "unityVersion": parsed.unity_version, "platform": parsed.platform,
            "objectCount": len(parsed.objects),
            "objects": {item.path_id: item for item in parsed.objects},
            "data": data,
        }
    _require(bool(result), "no-resource-files")
    return result


def _indexed_pointers(
    object_index: Path, external_names: set[str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    needles = tuple(name.encode("utf-8") for name in external_names)
    pointers: list[dict[str, Any]] = []
    stats: Counter[str] = Counter()
    with gzip.open(object_index, "rb") as stream:
        for line_number, raw in enumerate(stream, 1):
            stats["objectsScanned"] += 1
            if not any(needle in raw for needle in needles):
                continue
            row = json.loads(raw)
            source = row.get("object") or {}
            for pointer in row.get("pptrs", []):
                expected = pointer.get("expected") or {}
                name = expected.get("serializedFile")
                if name not in external_names:
                    continue
                stats["candidatePointers"] += 1
                _require(pointer.get("status") == "external_not_exported" and not pointer.get("target"),
                         f"unexpected-exporter-resolution:{line_number}")
                _require(isinstance(pointer.get("fileId"), int) and pointer["fileId"] > 0,
                         f"pointer-file-id:{line_number}")
                _require(isinstance(pointer.get("pathId"), int) and pointer["pathId"] != 0,
                         f"pointer-path-id:{line_number}")
                _require(isinstance(source.get("source"), str)
                         and isinstance(source.get("sourceOffset"), int)
                         and isinstance(source.get("serializedFile"), str),
                         f"pointer-source:{line_number}")
                pointers.append({
                    "externalName": name,
                    "externalPath": expected.get("externalPath"),
                    "fileId": pointer["fileId"],
                    "pathId": pointer["pathId"],
                    "field": pointer.get("path"),
                    "source": source,
                    "sourceType": row.get("type"),
                    "sourceName": row.get("name"),
                })
    return pointers, dict(stats)


def _selected_pointer_rows(
    pointers: list[dict[str, Any]], outer_summary: dict[str, Any],
    outer_ledger: Path, input_set: str, cabmap_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    chunks, _selected_names = _selected_spans(outer_ledger, input_set)
    starts = {chunk: [span[0] for span in spans] for chunk, spans in chunks.items()}
    base, entries = parse_cabmap(cabmap_path.read_bytes())
    _require(_norm(base) == _norm(outer_summary["fallbackAssets"]), "streaming-cabmap-root")
    cabs = {entry.cab: entry for entry in entries}
    _require(len(cabs) == len(entries), "duplicate-streaming-cab")
    selected: list[dict[str, Any]] = []
    excluded: Counter[str] = Counter()
    for pointer in pointers:
        source = pointer["source"]
        cab = source["serializedFile"]
        entry = cabs.get(cab)
        _require(entry is not None, f"source-cab-absent:{cab}")
        _require(_norm(entry.path) == _norm(source["source"])
                 and entry.offset == source["sourceOffset"],
                 f"source-cab-position:{cab}")
        file_id = pointer["fileId"]
        _require(file_id <= len(entry.dependencies)
                 and entry.dependencies[file_id - 1] == pointer["externalName"],
                 f"external-slot:{cab}:{file_id}")
        chunk = _norm(Path(base) / entry.path)
        spans = chunks.get(chunk, ())
        index = bisect.bisect_right(starts.get(chunk, ()), entry.offset) - 1
        if index < 0 or entry.offset >= spans[index][1]:
            excluded["notSelectedVfsSpan"] += 1
            continue
        selected.append({**pointer, "selectedBundle": spans[index][2]})
    return selected, dict(excluded)


def _project_resource_identity(
    pointers: list[dict[str, Any]], resources: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    for pointer in pointers:
        name = pointer["externalName"]
        external_path = pointer["externalPath"]
        _require(isinstance(external_path, str), f"external-path:{name}")
        _require(external_path.replace("\\", "/").split("/")[-1] == name,
                 f"external-path-basename:{name}")
        matches = [file_name for file_name, file in resources.items()
                   if pointer["pathId"] in file["objects"]]
        exact = resources.get(name)
        candidate = exact["objects"].get(pointer["pathId"]) if exact else None
        row = {**pointer, "resourcesContainingPathId": sorted(matches),
               "exactNameResourceObject": None}
        if candidate:
            _require(matches == [name], f"ambiguous-resource-object:{name}:{pointer['pathId']}")
            object_row: dict[str, Any] = {
                "classId": candidate.class_id,
                "byteStart": candidate.byte_start,
                "byteSize": candidate.byte_size,
            }
            if candidate.class_id == 43:
                object_row["name"] = object_name(exact["data"], candidate)
            row["exactNameResourceObject"] = object_row
        projected.append(row)
    return projected


def inspect(
    *, manifest: Path, outer_summary: Path, outer_ledger: Path,
    cabmap_dir: Path, expected_input_set_sha256: str,
    gameassembly: Path, metadata: Path,
    export_root: Path, resources_root: Path,
) -> dict[str, Any]:
    core = inspect_exceptions(
        manifest=manifest, outer_summary=outer_summary, outer_ledger=outer_ledger,
        cabmap_dir=cabmap_dir, expected_input_set_sha256=expected_input_set_sha256,
        gameassembly=gameassembly, metadata=metadata,
    )
    result: dict[str, Any] = {
        "schema": SCHEMA, "status": "mismatched", "detail": core.get("detail", ""),
        "expectedInputSetSha256": expected_input_set_sha256.upper(),
    }
    if core.get("status") != "complete":
        return result
    try:
        summary = json.loads(outer_summary.read_text(encoding="utf-8"))
        game_root = Path(summary["fallbackAssets"]).parent
        expected_source = collect_source_sizes(game_root, ("StreamingAssets",))["StreamingAssets"]
        object_index_summary = load_animestudio_object_index_summary(
            export_root, "StreamingAssets", expected_source_fingerprint=expected_source,
        )
        _require(isinstance(object_index_summary, dict)
                 and object_index_summary.get("complete") is True,
                 f"object-index:{(object_index_summary or {}).get('errors')}")
        object_index_path = export_root / "meta/StreamingAssets/object_index/objects.jsonl.gz"
        resources = _resource_inventory(resources_root)
        for candidate in core["resourceFileCandidates"]:
            if candidate["status"] != "exact-name-file":
                continue
            resource = resources.get(candidate["externalName"])
            _require(resource is not None and resource["sha256"] == candidate["sha256"]
                     and resource["length"] == candidate["length"],
                     f"exception-resource-changed:{candidate['externalName']}")
        unknown = {row["externalName"] for row in core["unresolvedExternals"]}
        pointers, index_stats = _indexed_pointers(object_index_path, unknown)
        _require(index_stats["objectsScanned"] ==
                 object_index_summary["counts"]["objects"] +
                 object_index_summary["counts"]["monoScripts"],
                 "object-index-record-count")
        selected, excluded = _selected_pointer_rows(
            pointers, summary, outer_ledger, core["inputSetSha256"],
            cabmap_dir / "endfield_streamingassets_assets.bin",
        )
        projected = _project_resource_identity(selected, resources)
        external_rows = []
        for external in core["unresolvedExternals"]:
            name = external["externalName"]
            rows = [row for row in projected if row["externalName"] == name]
            exact = [row for row in rows if row["exactNameResourceObject"] is not None]
            external_rows.append({
                "externalName": name,
                "selectedCabExternalReferences": external["references"],
                "selectedIndexedPointers": len(rows),
                "distinctIndexedTargetPathIds": len({row["pathId"] for row in rows}),
                "exactNameResourceObjectMatches": len(exact),
                "anyResourceObjectMatches": sum(bool(row["resourcesContainingPathId"]) for row in rows),
                "pointerFields": dict(sorted(Counter(row["field"] for row in rows).items())),
                "examples": rows[:EXAMPLE_CAP],
                "examplesTruncated": len(rows) > EXAMPLE_CAP,
            })
        resource_rows = [{key: file[key] for key in ("path", "length", "sha256", "unityVersion", "platform", "objectCount")}
                         for file in resources.values()]
        result.update(
            status="complete", detail="", inputSetSha256=core["inputSetSha256"],
            inputs={**core["inputs"],
                    "objectIndex": {
                        "summary": str(export_root / "meta/StreamingAssets/object_index/summary.json"),
                        "sourceFingerprint": expected_source["fingerprint"],
                        "objectsSha256": object_index_summary["outputs"]["objects"]["sha256"],
                    }},
            resources=resource_rows,
            objectIndexScan=index_stats,
            objectIndexUnselected=excluded,
            externalIdentities=external_rows,
            evidenceBoundary={
                "exact": "The current VFS/CAB exception gate, CAB external slot, complete source-fingerprint-matched object index, and strict standalone Resources metadata parser independently agree on named serialized identities and PathIDs.",
                "conditional": "An exact-name resource object at the PPtr PathID is a serialized target candidate. The object index exports only its selected MonoBehaviour and PlayableDirector classes, so its absent pointers are not evidence about other classes.",
                "unresolved": "No live or selected native Unity resolver execution binds Library/unity default resources to the installed Resources path. CAB-shaped externals without a selected CABMap source remain unresolved; absence of their observed PathIDs from installed Resources rules out only those observed pointers.",
            },
        )
    except (OSError, ValueError, KeyError, IndexError, TypeError, UnicodeError, gzip.BadGzipFile) as error:
        result["detail"] = str(error)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--outer-summary", type=Path, required=True)
    parser.add_argument("--outer-ledger", type=Path, required=True)
    parser.add_argument("--cabmap-dir", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--resources-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = inspect(
        manifest=args.manifest, outer_summary=args.outer_summary,
        outer_ledger=args.outer_ledger, cabmap_dir=args.cabmap_dir,
        expected_input_set_sha256=args.expected_input_set_sha256,
        gameassembly=args.gameassembly, metadata=args.metadata,
        export_root=args.export_root, resources_root=args.resources_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Bundle external serialized identity: {report['status']}")
    if report["status"] != "complete":
        print(f"  {report['detail']}")
        return 1
    for row in report["externalIdentities"]:
        print(f"  {row['externalName']}: {row['selectedIndexedPointers']} selected indexed PPtrs, "
              f"{row['exactNameResourceObjectMatches']} exact-name Resource object matches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
