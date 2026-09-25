"""Pack a layout-v2 export root's loose Unity objects into game/Unity.sqlite (layout v3).

Layout v2 published every exported Unity object as a loose file under
``game/Unity/<Type>/``. Layout v3 keeps the object documents (``.json`` and
``.anim``) in one SQLite store (``scripts/game_data/unity_store.py``) and only
converted media as files. This command converts a v2 root in place:

1. mark the root as being written, so every reader refuses it meanwhile;
2. copy each object document into the store, byte-exact, with its SHA256;
3. verify every stored row by decompressing it and re-hashing;
4. delete the loose documents whose (size, mtime) match their row, then mark
   the root complete as v3.

An interrupted run resumes from its recorded phase. ``--unpack`` reverses it:
it restores the loose documents from the store (with their mtimes), removes the
store and marks the root v2 again.

    python -m scripts.game_data.extraction.pack_unity_store --export-root export_full_1d5d1 --dry-run
    python -m scripts.game_data.extraction.pack_unity_store --export-root export_full_1d5d1
    python -m scripts.game_data.extraction.pack_unity_store --export-root export_full_1d5d1 --unpack
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

if __package__ in {None, ""}:
    raise SystemExit("Run as: python -m scripts.game_data.extraction.pack_unity_store")

from scripts.game_data.unity_store import (
    UNREADABLE_META_KEY,
    UnityObjectStore,
    UnityObjectStoreWriter,
    UnityStoreError,
    is_store_file,
    verify_store,
)
from scripts.source_paths import (
    EXPORT_LAYOUT_SCHEMA,
    EXPORT_LAYOUT_SCHEMA_V2,
    EXPORT_LAYOUT_STATE_COMPLETE,
    ExportLayout,
    ExportLayoutError,
)

PHASE_PACK = "pack"
PHASE_DELETE = "delete"


class PackError(RuntimeError):
    pass


def loose_documents(layout: ExportLayout) -> dict[str, dict[str, Path]]:
    """``{type: {name: path}}`` of every loose object document under game/Unity."""
    found: dict[str, dict[str, Path]] = {}
    if not layout.unity_dir.is_dir():
        return found
    for type_entry in sorted(os.scandir(layout.unity_dir), key=lambda entry: entry.name):
        if not type_entry.is_dir():
            continue
        files = {
            entry.name: Path(entry.path)
            for entry in os.scandir(type_entry.path)
            if entry.is_file() and is_store_file(entry.name)
        }
        if files:
            found[type_entry.name] = files
    return found


def _progress(type_name: str, done: int, total: int) -> None:
    if done == total or done % 50000 < 2000:
        print(f"  {type_name}: {done}/{total}", flush=True)


def quarantine_dir(layout: ExportLayout) -> Path:
    """Where accepted-unreadable documents are moved: the work dir when it shares
    the export's volume (a move must stay a rename; the file cannot be read to
    copy), else beside the export root."""
    in_work = layout.work_dir / "unity_pack_quarantine"
    probe = layout.work_dir
    while not probe.exists():
        probe = probe.parent
    if os.stat(probe).st_dev == os.stat(layout.root).st_dev:
        return in_work
    return layout.root.parent / f"{layout.root.name}.unity_pack_quarantine"


def pack_documents(
    layout: ExportLayout,
    documents: dict[str, dict[str, Path]],
    *,
    jobs: int,
    accept_unreadable: bool = False,
) -> dict[str, dict[str, int]]:
    """Upsert every loose document into the store; rows of absent files are kept (resume-safe).

    Unreadable files do not stop the pass: every one is collected and written
    to the work dir. By default the pack then fails closed before anything is
    deleted. With ``accept_unreadable`` each such file is moved (renamed, not
    read) into the work dir's quarantine and listed in the store's
    ``unreadableAtPack`` meta row, so the loss is recorded rather than silent.
    """
    counts: dict[str, dict[str, int]] = {}
    with UnityObjectStoreWriter(layout.unity_store_path, jobs=jobs) as writer:
        for type_name, files in documents.items():
            counts[type_name] = writer.sync_type(type_name, files, remove_missing=False, progress=_progress, strict=False)
        unreadable = [
            {"type": type_name, "name": item.name, "path": item.path, "error": item.error}
            for type_name, item in writer.unreadable
        ]
        if unreadable and accept_unreadable:
            quarantine = quarantine_dir(layout)
            for row in unreadable:
                target = quarantine / row["type"] / row["name"]
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(row["path"], target)
                documents[row["type"]].pop(row["name"], None)
                row["quarantinedTo"] = str(target)
            recorded = json.loads(writer.get_meta(UNREADABLE_META_KEY) or "[]")
            writer.set_meta(UNREADABLE_META_KEY, json.dumps(recorded + unreadable, ensure_ascii=False))
            print(f"accepted {len(unreadable)} unreadable document(s) as lost; quarantined under {quarantine}")
            return counts
    if unreadable:
        listing = layout.work_dir / "unity_pack_unreadable.json"
        listing.parent.mkdir(parents=True, exist_ok=True)
        listing.write_text(json.dumps(unreadable, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        first = "; ".join(f"{row['type']}/{row['name']}: {row['error']}" for row in unreadable[:3])
        raise PackError(
            f"{len(unreadable)} loose document(s) could not be read (listed in {listing}); nothing was deleted "
            f"and the root stays mid-pack. First: {first}"
        )
    return counts


def delete_packed(layout: ExportLayout, documents: dict[str, dict[str, Path]]) -> int:
    """Delete loose documents whose row has the same (size, mtime); anything else aborts."""
    with UnityObjectStore(layout.unity_store_path) as store:
        return _delete_packed(layout, documents, store)


def _delete_packed(layout: ExportLayout, documents: dict[str, dict[str, Path]], store: UnityObjectStore) -> int:
    deleted = 0
    for type_name, files in documents.items():
        stamps = {row.name: (row.size, row.mtime_ns) for row in store.iter_rows(type_name)}
        unmatched = []
        for name, path in files.items():
            stat = path.stat()
            if stamps.get(name) != (stat.st_size, stat.st_mtime_ns):
                unmatched.append(name)
        if unmatched:
            raise PackError(f"{len(unmatched)} {type_name} file(s) differ from their stored row, e.g. {unmatched[:3]}; re-run the pack")
        for path in files.values():
            os.unlink(path)
            deleted += 1
        type_dir = layout.unity_type_dir(type_name)
        if type_dir.is_dir() and not any(os.scandir(type_dir)):
            type_dir.rmdir()
    return deleted


def pack(root: Path, *, jobs: int, accept_unreadable: bool = False) -> dict:
    layout = ExportLayout(root)
    marker = layout.read_marker()
    if marker is None:
        raise PackError(f"{root} has no layout marker; migrate it to v2 first")
    schema, state, phase = marker.get("schema"), marker.get("state"), marker.get("packPhase")
    if schema == EXPORT_LAYOUT_SCHEMA and state == EXPORT_LAYOUT_STATE_COMPLETE:
        leftovers = loose_documents(layout)
        if not leftovers:
            print(f"{root} is already layout v3")
            return {"alreadyPacked": True}
        raise PackError(f"{root} is v3 but still holds loose object documents in {sorted(leftovers)}")
    resuming = schema == EXPORT_LAYOUT_SCHEMA and phase in (PHASE_PACK, PHASE_DELETE)
    if not resuming:
        ExportLayout(root).require_schema(EXPORT_LAYOUT_SCHEMA_V2)
    started = time.time()
    documents = loose_documents(layout)
    total = sum(len(files) for files in documents.values())
    print(f"{total} loose object document(s) in {len(documents)} type(s)")
    report: dict = {"types": {name: len(files) for name, files in documents.items()}}
    if phase != PHASE_DELETE:
        layout.begin_write(upgrade_from_v2=True, packPhase=PHASE_PACK, packedFrom=EXPORT_LAYOUT_SCHEMA_V2)
        report["pack"] = pack_documents(layout, documents, jobs=jobs, accept_unreadable=accept_unreadable)
        print("verifying stored rows ...", flush=True)
        verification = verify_store(layout.unity_store_path, jobs=jobs)
        report["verify"] = verification
        if not verification["ok"]:
            raise PackError(f"store verification failed: {verification}")
        layout.begin_write(upgrade_from_v2=True, packPhase=PHASE_DELETE, packedFrom=EXPORT_LAYOUT_SCHEMA_V2)
    report["deleted"] = delete_packed(layout, documents)
    report["storeBytes"] = layout.unity_store_path.stat().st_size
    report["seconds"] = round(time.time() - started, 1)
    with UnityObjectStore(layout.unity_store_path) as store:
        rows = store.count()
    layout.finish_write(packedFrom=EXPORT_LAYOUT_SCHEMA_V2, packedAt=int(time.time()), unityStoreRows=rows)
    return report


def unpack(root: Path) -> dict:
    layout = ExportLayout(root)
    marker = layout.read_marker() or {}
    if marker.get("schema") != EXPORT_LAYOUT_SCHEMA:
        raise PackError(f"{root} is not a layout-v3 root (schema {marker.get('schema')!r})")
    UnityObjectStore.clear_cache()
    store = UnityObjectStore(layout.unity_store_path)
    layout.begin_write(unpacking=True)
    restored = 0
    for type_name in store.types():
        target = layout.unity_type_dir(type_name)
        target.mkdir(parents=True, exist_ok=True)
        for row, data in store.iter_documents(type_name):
            path = target / row.name
            if not (path.is_file() and path.stat().st_size == row.size):
                path.write_bytes(data)
            if row.mtime_ns:
                os.utime(path, ns=(row.mtime_ns, row.mtime_ns))
            restored += 1
    store.close()
    layout.unity_store_path.unlink()
    layout.finish_write(schema=EXPORT_LAYOUT_SCHEMA_V2, unpackedAt=int(time.time()))
    return {"restored": restored}


def dry_run(root: Path) -> dict:
    layout = ExportLayout(root)
    documents = loose_documents(layout)
    sizes = {name: sum(path.stat().st_size for path in files.values()) for name, files in documents.items()}
    return {
        "marker": layout.read_marker(),
        "types": {name: {"files": len(files), "bytes": sizes[name]} for name, files in documents.items()},
        "files": sum(len(files) for files in documents.values()),
        "bytes": sum(sizes.values()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=8, help="Parallel readers/compressors.")
    parser.add_argument(
        "--accept-unreadable",
        action="store_true",
        help="Accept documents the disk cannot read as lost: move them to the work dir's quarantine, "
        "record them in the store's unreadableAtPack meta row, and finish. Without it, any unreadable "
        "document stops the pack before anything is deleted.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Count what would be packed; change nothing.")
    mode.add_argument("--unpack", action="store_true", help="Restore loose documents and return the root to v2.")
    args = parser.parse_args(argv)
    try:
        if args.dry_run:
            report = dry_run(args.export_root)
        elif args.unpack:
            report = unpack(args.export_root)
        else:
            report = pack(args.export_root, jobs=args.jobs, accept_unreadable=args.accept_unreadable)
    except (PackError, UnityStoreError, ExportLayoutError) as exc:
        print(f"pack_unity_store: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
