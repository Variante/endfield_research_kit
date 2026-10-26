"""Refresh only FBX comparison keys in an existing broad Assets publication."""
from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path, PurePosixPath

from scripts.common import path_id_export_base_stem, rel_path, write_json
from scripts.game_data.extraction.verify_export_freshness import Requirements, verify
from scripts.game_data.fbx_normalize import FBX_CONTENT_SCHEMA, FBX_VARIANT_SCHEMA, fbx_content_fingerprints
from scripts.game_data.unity_store import UnityObjectStore
from scripts.source_paths import ExportLayout


def _file_state(path: Path) -> tuple[int, int] | None:
    if not path.exists():
        return None
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


def _compare_file(task: tuple[str, str, str, str, int, str]) -> tuple[str, str, str]:
    export_root, stored_name, loose_path, stem, expected_size, expected_hash = task
    data = (UnityObjectStore.for_export(Path(export_root)).read_bytes("Animator", stored_name)
            if stored_name else Path(loose_path).read_bytes())
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != expected_size or expected_hash and digest != expected_hash:
        raise ValueError(f"FBX source changed: {stored_name or loose_path}")
    return digest, *fbx_content_fingerprints(data, stem)


def publish_fbx_content(*, root: Path, export_root: Path, asset_dir: Path, jobs: int = 4) -> dict:
    """Keep every other index field and sidecar, rejecting stale/concurrent input."""
    if jobs < 1:
        raise ValueError("FBX jobs must be positive")
    index_path = asset_dir / "index.json"
    before = index_path.read_bytes()
    payload = json.loads(before)
    if payload.get("mode") == "webui" or payload.get("root") != rel_path(export_root, root):
        raise ValueError("FBX refresh needs a broad Assets index for the selected export root")
    if verify(output_root=export_root, requirements=Requirements(unity=("Animator",))):
        raise ValueError("Animator export freshness failed; Assets index was not changed")

    layout = ExportLayout(export_root)
    store = UnityObjectStore.for_export(export_root) if layout.unity_store_path.is_file() else None
    stored = {row.name: row for row in store.rows("Animator")} if store else {}
    roots = {"Unity": layout.unity_dir, "Game": layout.game}
    watched = {path: _file_state(path) for path in (
        layout.unity_store_path, Path(str(layout.unity_store_path) + "-wal"), layout.extraction_provenance_path,
    )}
    tasks: list[tuple] = []
    task_indices: dict[tuple, int] = {}
    selected: list[tuple[dict, int]] = []
    for entry in payload["entries"]:
        reference = str(entry.get("r", ""))
        if entry.get("k") != "model" or not reference.lower().endswith(".fbx"):
            continue
        parts = PurePosixPath(reference).parts
        if len(parts) < 2 or parts[0] not in roots or any(p in ("..", ".") for p in parts) or "\\" in reference:
            raise ValueError(f"Unsupported FBX reference: {reference}")
        source = roots[parts[0]]
        if payload.get("sourceRoots", {}).get(parts[0]) != rel_path(source, root):
            raise ValueError(f"FBX source root changed: {parts[0]}")
        name = parts[-1]
        stem = path_id_export_base_stem(Path(name).stem) or Path(name).stem
        row = stored.get(name) if parts[:2] == ("Unity", "Animator") and len(parts) == 3 else None
        expected_hash = entry.get("h", "")
        if row:
            if row.size != entry["s"] or expected_hash and expected_hash != row.sha256:
                raise ValueError(f"Published FBX is stale: {reference}")
            task = (str(export_root), name, "", stem, row.size, row.sha256)
            key = (row.sha256, stem)
        else:
            path = source.joinpath(*parts[1:]).resolve()
            if not path.is_relative_to(source.resolve()):
                raise ValueError(f"FBX path escapes its source: {reference}")
            watched[path] = _file_state(path)
            task = (str(export_root), "", str(path), stem, entry["s"], expected_hash)
            key = (str(path), stem)
        if key not in task_indices:
            task_indices[key] = len(tasks)
            tasks.append(task)
        selected.append((entry, task_indices[key]))

    print(f"Comparing {len(selected)} FBX entries ({len(tasks)} distinct inputs, {jobs} workers)...", flush=True)
    if jobs == 1:
        results = list(map(_compare_file, tasks))
    else:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            results = []
            for result in pool.map(_compare_file, tasks, chunksize=8):
                results.append(result)
                if len(results) % 500 == 0:
                    print(f"FBX comparisons: {len(results)}/{len(tasks)}", flush=True)
    counts = Counter(results[index][1] for _, index in selected if results[index][1])
    for entry, index in selected:
        digest, fingerprint, variant = results[index]
        entry.pop("fc", None)
        entry.pop("fv", None)
        if fingerprint and counts[fingerprint] > 1:
            entry.update(fc=fingerprint, fv=variant, h=digest)
    if any(_file_state(path) != state for path, state in watched.items()):
        raise ValueError("FBX export changed during comparison; Assets index was not changed")
    if index_path.read_bytes() != before:
        raise ValueError("Assets publication changed during comparison; retry against the new index")
    payload["generated"] = int(time.time())
    payload["fbxContentSchema"] = FBX_CONTENT_SCHEMA
    payload["fbxVariantSchema"] = FBX_VARIANT_SCHEMA
    write_json(index_path, payload)
    report = {"schema": FBX_CONTENT_SCHEMA, "entries": len(selected), "inputs": len(tasks),
              "sharedGroups": sum(n > 1 for n in counts.values()),
              "groupedFiles": sum(n for n in counts.values() if n > 1),
              "unsupportedFiles": sum(not results[index][1] for _, index in selected)}
    print("FBX grouping refreshed:", report, flush=True)
    return report
