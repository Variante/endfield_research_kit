"""Pack an older export root's loose small files into its SQLite stores (layout v4).

Layout v2 published every file loose. Layout v3 moved the exported Unity object
documents (``.json``, ``.anim``) into ``game/Unity.sqlite``
(``scripts/game_data/unity_store.py``). Layout v4 also moves every file under
``PACKED_GAME_DIRS`` (``scripts/source_paths.py``) into ``game/GameFiles.sqlite``
(``scripts/game_data/game_file_store.py``). This command converts a v2 or v3
root in place:

1. mark the root as being written, so every reader refuses it meanwhile;
2. copy each loose document into its store, byte-exact, with its SHA256;
3. verify every stored row of both stores by decompressing and re-hashing;
4. delete the loose files whose (size, mtime) match their row, then mark the
   root complete as v4.

An interrupted run resumes from its recorded phase. A file the disk cannot
read stops the pack before anything is deleted, with every such file listed in
the work dir; ``--accept-unreadable`` is the explicit decision to record them
as lost (moved to a quarantine, listed in the store's ``unreadableAtPack`` meta
row) and finish. ``--unpack`` reverses a pack: it restores every loose file
from both stores (with their mtimes), removes the stores and marks the root v2.

    python -m scripts.game_data.extraction.pack_export_stores --export-root export_full_1d5d1 --dry-run
    python -m scripts.game_data.extraction.pack_export_stores --export-root export_full_1d5d1
    python -m scripts.game_data.extraction.pack_export_stores --export-root export_full_1d5d1 --unpack
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

if __package__ in {None, ""}:
    raise SystemExit("Run as: python -m scripts.game_data.extraction.pack_export_stores")

from scripts.game_data.game_file_store import (
    GameFileStore,
    GameFileStoreWriter,
    loose_packed_files,
    verify_game_file_store,
)
from scripts.game_data.unity_store import (
    UNREADABLE_META_KEY,
    UnityObjectStore,
    UnityObjectStoreWriter,
    UnityStoreError,
    is_store_file,
    verify_store,
)
from scripts.source_paths import (
    EXPORT_LAYOUT_PACKABLE_SCHEMAS,
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


def _progress(group: str, done: int, total: int) -> None:
    if done == total or done % 50000 < 2000:
        print(f"  {group}: {done}/{total}", flush=True)


def quarantine_dir(layout: ExportLayout) -> Path:
    """Where accepted-unreadable files are moved: the work dir when it shares
    the export's volume (a move must stay a rename; the file cannot be read to
    copy), else beside the export root."""
    in_work = layout.work_dir / "unity_pack_quarantine"
    probe = layout.work_dir
    while not probe.exists():
        probe = probe.parent
    if os.stat(probe).st_dev == os.stat(layout.root).st_dev:
        return in_work
    return layout.root.parent / f"{layout.root.name}.unity_pack_quarantine"


def _settle_unreadable(
    layout: ExportLayout,
    groups: dict[str, dict[str, Path]],
    unreadable: list[dict[str, str]],
    writer: UnityObjectStoreWriter | GameFileStoreWriter,
    *,
    store_label: str,
    accept_unreadable: bool,
) -> None:
    """Quarantine and record accepted losses, or fail closed with the full list."""
    if not unreadable:
        return
    if accept_unreadable:
        quarantine = quarantine_dir(layout)
        for row in unreadable:
            target = quarantine / row["group"] / row["name"]
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(row["path"], target)
            groups[row["group"]].pop(row["name"], None)
            row["quarantinedTo"] = str(target)
        recorded = json.loads(writer.get_meta(UNREADABLE_META_KEY) or "[]")
        writer.set_meta(UNREADABLE_META_KEY, json.dumps(recorded + unreadable, ensure_ascii=False))
        print(f"accepted {len(unreadable)} unreadable {store_label} file(s) as lost; quarantined under {quarantine}")
        return
    listing = layout.work_dir / f"pack_unreadable_{store_label}.json"
    listing.parent.mkdir(parents=True, exist_ok=True)
    listing.write_text(json.dumps(unreadable, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    first = "; ".join(f"{row['group']}/{row['name']}: {row['error']}" for row in unreadable[:3])
    raise PackError(
        f"{len(unreadable)} loose {store_label} file(s) could not be read (listed in {listing}); nothing was "
        f"deleted and the root stays mid-pack. First: {first}"
    )


def pack_documents(
    layout: ExportLayout,
    documents: dict[str, dict[str, Path]],
    *,
    jobs: int,
    accept_unreadable: bool = False,
) -> dict[str, dict[str, int]]:
    """Upsert every loose Unity document into its store; rows of absent files are kept (resume-safe)."""
    counts: dict[str, dict[str, int]] = {}
    with UnityObjectStoreWriter(layout.unity_store_path, jobs=jobs) as writer:
        for type_name, files in documents.items():
            counts[type_name] = writer.sync_type(type_name, files, remove_missing=False, progress=_progress, strict=False)
        unreadable = [
            {"group": type_name, "name": item.name, "path": item.path, "error": item.error}
            for type_name, item in writer.unreadable
        ]
        _settle_unreadable(layout, documents, unreadable, writer, store_label="unity", accept_unreadable=accept_unreadable)
    return counts


def pack_game_files(
    layout: ExportLayout,
    files_by_folder: dict[str, dict[str, Path]],
    *,
    jobs: int,
    accept_unreadable: bool = False,
) -> dict[str, dict[str, int]]:
    """Upsert every loose file under a packed folder into the game-file store (resume-safe)."""
    counts: dict[str, dict[str, int]] = {}
    with GameFileStoreWriter(layout.game_file_store_path, jobs=jobs) as writer:
        for folder, files in files_by_folder.items():
            counts[folder] = writer.sync_folder(folder, files, remove_missing=False, progress=_progress, strict=False)
        unreadable = []
        for row in writer.unreadable:
            folder = _folder_of(row["path"], files_by_folder)
            unreadable.append({"group": folder, "name": row["path"][len(folder) + 1:], "path": row["file"], "error": row["error"]})
        _settle_unreadable(layout, files_by_folder, unreadable, writer, store_label="game_files", accept_unreadable=accept_unreadable)
    return counts


def _folder_of(game_path: str, files_by_folder: dict[str, dict[str, Path]]) -> str:
    for folder in files_by_folder:
        if game_path.startswith(folder + "/"):
            return folder
    raise PackError(f"{game_path} is under no packed folder")


def _delete_matching(groups: dict[str, dict[str, Path]], stamps_of, label: str) -> int:
    deleted = 0
    for group, files in groups.items():
        stamps = stamps_of(group)
        unmatched = []
        for name, path in files.items():
            stat = path.stat()
            if stamps.get(name) != (stat.st_size, stat.st_mtime_ns):
                unmatched.append(name)
        if unmatched:
            raise PackError(f"{len(unmatched)} {label} {group} file(s) differ from their stored row, e.g. {unmatched[:3]}; re-run the pack")
        for path in files.values():
            os.unlink(path)
            deleted += 1
    return deleted


def _remove_empty_dirs(base: Path) -> None:
    if not base.is_dir():
        return
    for dirpath, _dirnames, _filenames in os.walk(base, topdown=False):
        if not os.listdir(dirpath):
            os.rmdir(dirpath)


def delete_packed(
    layout: ExportLayout,
    documents: dict[str, dict[str, Path]],
    game_files: dict[str, dict[str, Path]],
) -> int:
    """Delete loose files whose row has the same (size, mtime); anything else aborts."""
    deleted = 0
    if documents:
        with UnityObjectStore(layout.unity_store_path) as store:
            deleted += _delete_matching(
                documents, lambda group: {row.name: (row.size, row.mtime_ns) for row in store.iter_rows(group)}, "Unity"
            )
        for type_name in documents:
            type_dir = layout.unity_type_dir(type_name)
            if type_dir.is_dir() and not any(os.scandir(type_dir)):
                type_dir.rmdir()
    if game_files:
        with GameFileStore(layout.game_file_store_path) as store:
            def stamps(folder: str) -> dict[str, tuple[int, int]]:
                return {row.path[len(folder) + 1:]: (row.size, row.mtime_ns) for row in store.iter_rows(folder)}

            deleted += _delete_matching(game_files, stamps, "packed")
        for folder in game_files:
            _remove_empty_dirs(layout.game.joinpath(*folder.split("/")))
    return deleted


def pack(root: Path, *, jobs: int, accept_unreadable: bool = False) -> dict:
    layout = ExportLayout(root)
    marker = layout.read_marker()
    if marker is None:
        raise PackError(f"{root} has no layout marker; migrate it to v2 first")
    schema, state, phase = marker.get("schema"), marker.get("state"), marker.get("packPhase")
    if schema == EXPORT_LAYOUT_SCHEMA and state == EXPORT_LAYOUT_STATE_COMPLETE:
        leftovers = sorted(loose_documents(layout)) + sorted(loose_packed_files(layout))
        if not leftovers:
            print(f"{root} is already layout v4")
            return {"alreadyPacked": True}
        raise PackError(f"{root} is v4 but still holds loose files in {leftovers}")
    resuming = schema == EXPORT_LAYOUT_SCHEMA and phase in (PHASE_PACK, PHASE_DELETE)
    packed_from = marker.get("packedFrom") if resuming else schema
    if not resuming:
        if schema not in EXPORT_LAYOUT_PACKABLE_SCHEMAS or state != EXPORT_LAYOUT_STATE_COMPLETE:
            raise PackError(f"{root} is not a complete v2 or v3 root (found {(schema, state)!r})")
    started = time.time()
    documents = loose_documents(layout)
    game_files = loose_packed_files(layout)
    print(
        f"{sum(len(v) for v in documents.values())} loose Unity document(s) in {len(documents)} type(s); "
        f"{sum(len(v) for v in game_files.values())} loose file(s) in {len(game_files)} packed folder(s)"
    )
    report: dict = {
        "unityTypes": {name: len(files) for name, files in documents.items()},
        "packedFolders": {name: len(files) for name, files in game_files.items()},
    }
    if phase != PHASE_DELETE:
        layout.begin_write(upgrade=True, packPhase=PHASE_PACK, packedFrom=packed_from)
        if documents:
            report["unity"] = pack_documents(layout, documents, jobs=jobs, accept_unreadable=accept_unreadable)
        if game_files:
            report["gameFiles"] = pack_game_files(layout, game_files, jobs=jobs, accept_unreadable=accept_unreadable)
        print("verifying stored rows ...", flush=True)
        report["verify"] = {}
        for label, path, verify in (
            ("unity", layout.unity_store_path, verify_store),
            ("gameFiles", layout.game_file_store_path, verify_game_file_store),
        ):
            if path.is_file():
                verification = verify(path, jobs=jobs)
                report["verify"][label] = verification
                if not verification["ok"]:
                    raise PackError(f"{label} store verification failed: {verification}")
        layout.begin_write(upgrade=True, packPhase=PHASE_DELETE, packedFrom=packed_from)
    report["deleted"] = delete_packed(layout, documents, game_files)
    report["seconds"] = round(time.time() - started, 1)
    fields: dict = {"packedFrom": packed_from, "packedAt": int(time.time())}
    if layout.unity_store_path.is_file():
        with UnityObjectStore(layout.unity_store_path) as store:
            fields["unityStoreRows"] = store.count()
    if layout.game_file_store_path.is_file():
        with GameFileStore(layout.game_file_store_path) as store:
            fields["gameFileStoreRows"] = store.count()
    layout.finish_write(**fields)
    return report


def unpack(root: Path) -> dict:
    layout = ExportLayout(root)
    marker = layout.read_marker() or {}
    if marker.get("schema") != EXPORT_LAYOUT_SCHEMA:
        raise PackError(f"{root} is not a layout-v4 root (schema {marker.get('schema')!r})")
    UnityObjectStore.clear_cache()
    GameFileStore.clear_cache()
    layout.begin_write(unpacking=True)
    restored = 0
    if layout.unity_store_path.is_file():
        with UnityObjectStore(layout.unity_store_path) as store:
            for type_name in store.types():
                target = layout.unity_type_dir(type_name)
                target.mkdir(parents=True, exist_ok=True)
                for row, data in store.iter_documents(type_name):
                    restored += _restore(target / row.name, data, row.size, row.mtime_ns)
        layout.unity_store_path.unlink()
    if layout.game_file_store_path.is_file():
        with GameFileStore(layout.game_file_store_path) as store:
            for folder in store.folders():
                for row, data in store.iter_files(folder):
                    target = layout.game.joinpath(*row.path.split("/"))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    restored += _restore(target, data, row.size, row.mtime_ns)
        layout.game_file_store_path.unlink()
    layout.finish_write(schema=EXPORT_LAYOUT_SCHEMA_V2, unpackedAt=int(time.time()))
    return {"restored": restored}


def _restore(path: Path, data: bytes, size: int, mtime_ns: int) -> int:
    if not (path.is_file() and path.stat().st_size == size):
        path.write_bytes(data)
    if mtime_ns:
        os.utime(path, ns=(mtime_ns, mtime_ns))
    return 1


def dry_run(root: Path) -> dict:
    layout = ExportLayout(root)

    def summarize(groups: dict[str, dict[str, Path]]) -> dict:
        return {name: {"files": len(files), "bytes": sum(p.stat().st_size for p in files.values())} for name, files in groups.items()}

    unity = summarize(loose_documents(layout))
    game_files = summarize(loose_packed_files(layout))
    return {
        "marker": layout.read_marker(),
        "unityTypes": unity,
        "packedFolders": game_files,
        "files": sum(v["files"] for v in (*unity.values(), *game_files.values())),
        "bytes": sum(v["bytes"] for v in (*unity.values(), *game_files.values())),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=8, help="Parallel readers/compressors.")
    parser.add_argument(
        "--accept-unreadable",
        action="store_true",
        help="Accept files the disk cannot read as lost: move them to the work dir's quarantine, "
        "record them in their store's unreadableAtPack meta row, and finish. Without it, any unreadable "
        "file stops the pack before anything is deleted.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Count what would be packed; change nothing.")
    mode.add_argument("--unpack", action="store_true", help="Restore every loose file and return the root to v2.")
    args = parser.parse_args(argv)
    try:
        if args.dry_run:
            report = dry_run(args.export_root)
        elif args.unpack:
            report = unpack(args.export_root)
        else:
            report = pack(args.export_root, jobs=args.jobs, accept_unreadable=args.accept_unreadable)
    except (PackError, UnityStoreError, ExportLayoutError) as exc:
        print(f"pack_export_stores: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
