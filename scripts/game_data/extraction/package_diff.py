"""Plan a client-update refresh before anything is decoded.

Compares the installed client against the client an export was made from, using
only VFS metadata, and predicts which files of that export the refresh will
replace. Nothing is extracted and nothing under the export root is written.

Old side: the export's certified VFS audit ledger
(``meta/evidence/animestudio/vfs_understanding_files_latest.jsonl.gz``) and the
build fingerprints in its summary. New side: ``AnimeStudio.CLI vfs-index`` over
the installed Persistent/StreamingAssets overlay (seconds, metadata only).
Logical files are keyed ``<block>/<virtual path>`` and compared on declared
FileDataMd5, length and encryption. Rows the old audit marked
``shadowed_fallback`` are StreamingAssets copies hidden by Persistent and are
not part of the effective client.

Evidence tiers of the prediction:

- ``exact``: one VFS file is one exported file (Table, JsonData, LipSync, Lua,
  Video, Terrain, and the byte-for-byte ``raw/`` families). Its old output path
  is derived with the exporter's own path rules and checked to exist.
- ``candidate``: a changed bundle names the CABs and PathIDs it held (CAB map
  and asset map spans joined to the old ledger's chunk/offset), hence the Unity
  media files and ``Unity.sqlite`` rows it produced. A changed bundle may still
  decode to identical bytes, and an unchanged bundle whose dependency changed
  may decode differently, so only a post-extraction comparison is final.
- ``relocated``: an update that rewrites a chunk moves bundles whose bytes did
  not change to a new chunk path or offset. Exported Unity documents record
  their source location (``sourceOriginalPath``/``sourceOffset`` and the
  ``*Source*`` fields of resolved references), so the CABs of a relocated
  bundle, and the CABs that depend on them, are predicted to change in those
  location fields only. Verification holds them to exactly that.
- ``container``: audio packages decode to many files; the package is named and
  the decoded files are settled after extraction.

``--self-check`` predicts outputs for every old exact-tier file and reports
predictions that do not exist, which validates the path rules against the
current export without a client update.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

if __package__ in {None, ""}:
    raise SystemExit("Run this maintained entry point as: python -m scripts.game_data.extraction.package_diff")

from scripts.common import ROOT
from scripts.game_data.cabmap import parse_cabmap
from scripts.source_paths import (
    ExportLayout,
    ExportLayoutError,
    configured_animestudio_cli,
    game_relative_path,
    packed_game_dir,
    raw_relative_path,
)

SCHEMA = "endfield.package-diff.v1"
LEDGER_RELATIVE = Path("animestudio/vfs_understanding_files_latest.jsonl.gz")
AUDIT_SUMMARY_RELATIVE = Path("animestudio/vfs_understanding_latest.json")
DEFAULT_GAME_ROOT = Path(os.environ.get("ENDFIELD_GAME_ROOT") or r"D:\Program Files\Endfield Game\Endfield_Data")
DEFAULT_REPORT = ROOT / "reports" / "updates" / "package_diff_latest.json"
LAYERS = (("Persistent", "persistent"), ("StreamingAssets", "streamingassets"))
BUNDLE_BLOCKS = frozenset({"Bundle", "InitBundle"})
COMPARED_FIELDS = ("md5", "length", "encrypted")
PATH_ID_RE = re.compile(r"_p([0-9A-Fa-f]{16})(?=\.)")


class PackageDiffError(RuntimeError):
    pass


def _norm(path: str | Path) -> str:
    return os.path.normcase(os.path.normpath(str(path)))


# -- old and new inventories -------------------------------------------------

def load_old_ledger(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    header: dict[str, Any] = {}
    shadowed = 0
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                kind = row.get("recordType")
                if kind == "audit_header":
                    header = {"inputSetSha256": row.get("inputSetSha256")}
                if kind != "file":
                    continue
                if row.get("status") == "shadowed_fallback":
                    shadowed += 1
                    continue
                key = f"{row['blockName']}/{str(row['virtualPath']).lstrip('/')}"
                if key in rows:
                    raise PackageDiffError(f"duplicate effective logical file in old ledger: {key}")
                rows[key] = {
                    "block": row["blockName"],
                    "path": row["virtualPath"],
                    "md5": str(row.get("declaredFileDataMd5DisplayHex") or "").upper(),
                    "length": int(row["length"]),
                    "encrypted": bool(row.get("encrypted")),
                    "chunk": row.get("physicalChunkPath"),
                    "offset": int(row.get("offset") or 0),
                }
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise PackageDiffError(f"unreadable old VFS ledger {path}: {exc}") from exc
    if not rows:
        raise PackageDiffError(f"old VFS ledger has no file rows: {path}")
    header["shadowedFallbackRows"] = shadowed
    return rows, header


def scan_installed(cli: Path, game_root: Path, work: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    output = work / "vfs_index_all.jsonl"
    command = [str(cli), "vfs-index", "--jsonl", "-s", str(game_root / "Persistent"),
               "--fallback-assets", str(game_root / "StreamingAssets"), "-o", str(output)]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        raise PackageDiffError(f"vfs-index failed ({completed.returncode}): {completed.stderr.strip()[-2000:]}")
    rows: dict[str, dict[str, Any]] = {}
    chunk_ids: dict[str, str] = {}
    chunks: dict[str, str] = {}
    summary: dict[str, Any] | None = None
    with output.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("recordType") == "summary":
                summary = row
            if row.get("recordType") == "chunk" and row.get("exists", True):
                chunks.setdefault(str(row["chunkId"]), str(row["absolutePath"]))
            if row.get("recordType") != "file":
                continue
            key = f"{row['blockName']}/{str(row['fileName']).lstrip('/')}"
            if key in rows:
                raise PackageDiffError(f"duplicate logical file in installed index: {key}")
            rows[key] = {
                "block": row["blockName"],
                "path": row["fileName"],
                "md5": str(row.get("fileDataMd5") or "").upper(),
                "length": int(row["length"]),
                "encrypted": bool(row.get("encrypted")),
                "offset": int(row.get("offset") or 0),
            }
            chunk_ids[key] = str(row.get("chunkId") or "")
    for key, chunk_id in chunk_ids.items():
        rows[key]["chunk"] = chunks.get(chunk_id)
    if summary is None or int(summary.get("fileCount") or -1) != len(rows):
        raise PackageDiffError(f"installed VFS index is incomplete: summary={summary}, rows={len(rows)}")
    return rows, summary


def _location(row: dict[str, Any]) -> tuple[str, int] | None:
    return (_norm(row["chunk"]), row["offset"]) if row.get("chunk") else None


def classify(old: dict[str, dict[str, Any]], new: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """Added, deleted and modified logical files, plus ``relocated``: same bytes, new chunk or offset."""
    common = old.keys() & new.keys()
    modified = {k for k in common if any(old[k][f] != new[k][f] for f in COMPARED_FIELDS)}
    return {
        "added": sorted(new.keys() - old.keys()),
        "deleted": sorted(old.keys() - new.keys()),
        "modified": sorted(modified),
        "relocated": sorted(k for k in common - modified
                            if _location(old[k]) and _location(new[k]) and _location(old[k]) != _location(new[k])),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def compare_build_files(audit_summary: Path, game_root: Path) -> list[dict[str, Any]]:
    """Client binaries the old VFS audit fingerprinted (the exporter binary excluded)."""
    try:
        recorded = json.loads(audit_summary.read_text(encoding="utf-8")).get("buildFingerprints") or []
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageDiffError(f"unreadable VFS audit summary {audit_summary}: {exc}") from exc
    install = game_root.parent
    rows = []
    for item in recorded:
        old_path = Path(str(item.get("path") or ""))
        if old_path.name.lower() == "animestudio.cli.exe":
            continue
        # Re-root the recorded path onto the selected install by its tail.
        parts = [part.lower() for part in old_path.parts]
        if "endfield_data" in parts:
            current = game_root.joinpath(*old_path.parts[parts.index("endfield_data") + 1:])
        else:
            current = install / old_path.name
        row = {"file": old_path.name, "oldSha256": str(item.get("sha256") or "").upper(),
               "path": str(current)}
        row["newSha256"] = sha256_file(current) if current.is_file() else None
        row["changed"] = row["newSha256"] != row["oldSha256"]
        rows.append(row)
    return rows


# -- predicting old outputs ---------------------------------------------------

def exact_output(block: str, virtual_path: str) -> tuple[str, str] | None:
    """(kind, export-relative path) of the single file a VFS file exports to."""
    path = str(virtual_path).replace("\\", "/").lstrip("/")
    if block == "Table":
        return "file", f"game/Table/{PurePosixPath(path).stem}.json"
    if block == "Lua":
        name = path
        while name.endswith(".lua.enc"):
            name = name[: -len(".enc")]
        if not name.endswith(".lua"):
            name += ".lua"
        return "file", f"game/{game_relative_path('Lua/' + name)}"
    try:
        relative = game_relative_path(path)
    except ExportLayoutError:
        relative = None
    if relative is not None:
        if block in {"Video", "AuditVideo"} and relative.suffix.lower() == ".usm":
            relative = relative.with_suffix(".mp4")
        if packed_game_dir(str(relative)):
            return "store", f"game/GameFiles.sqlite:{relative}"
        return "file", f"game/{relative}"
    try:
        return "file", f"raw/{raw_relative_path(path)}"
    except ExportLayoutError:
        return None


class BundleOutputs:
    """Old Unity outputs of bundle spans, joined through the old CAB and asset maps.

    Each CAB occupies its chunk from its offset up to the next CAB's offset, and
    an asset map row belongs to the CAB whose range holds its offset. A CAB that
    lists a changed CAB among its (transitive) dependencies is reported apart:
    its bytes did not change, but its converted outputs may.
    """

    def __init__(self, layout: ExportLayout) -> None:
        self.layout = layout
        starts: dict[str, list[tuple[int, str]]] = defaultdict(list)
        self.dependencies: dict[str, tuple[str, ...]] = {}
        for _layer, name in LAYERS:
            path = layout.cab_map_dir / f"endfield_{name}_assets.bin"
            if not path.is_file():
                raise PackageDiffError(f"missing old CAB map: {path}")
            base, entries = parse_cabmap(path.read_bytes())
            for entry in entries:
                starts[_norm(Path(base) / entry.path)].append((entry.offset, entry.cab))
                self.dependencies[entry.cab] = tuple(entry.dependencies)
        self.starts = {chunk: sorted(rows) for chunk, rows in starts.items()}
        self.assets: dict[str, set[tuple[str, str]]] = defaultdict(set)
        for layer, name in LAYERS:
            path = layout.asset_map_dir(layer) / f"endfield_{name}_assets.json"
            if not path.is_file():
                raise PackageDiffError(f"missing old asset map: {path}")
            for entry in json.loads(path.read_text(encoding="utf-8"))["AssetEntries"]:
                cab = self._cab_at(_norm(entry["Source"]), int(entry.get("Offset") or 0))
                if cab is not None:
                    path_id = f"{int(entry['PathID']) & ((1 << 64) - 1):016X}"
                    self.assets[cab].add((entry["Type"], path_id))

    def _cab_at(self, chunk: str, offset: int) -> str | None:
        rows = self.starts.get(chunk)
        if not rows:
            return None
        low, high = 0, len(rows)
        while low < high:
            middle = (low + high) // 2
            if rows[middle][0] <= offset:
                low = middle + 1
            else:
                high = middle
        return rows[low - 1][1] if low else None

    def owned(self, spans: Iterable[dict[str, Any]]) -> set[str]:
        cabs: set[str] = set()
        for span in spans:
            start = span["offset"]
            end = start + span["length"]
            cabs.update(cab for offset, cab in self.starts.get(_norm(span["chunk"]), ()) if start <= offset < end)
        return cabs

    def dependents(self, changed: set[str]) -> set[str]:
        reverse: dict[str, set[str]] = defaultdict(set)
        for cab, dependencies in self.dependencies.items():
            for dependency in dependencies:
                reverse[dependency].add(cab)
        found: set[str] = set()
        pending = list(changed)
        while pending:
            for cab in reverse.get(pending.pop(), ()):
                if cab not in changed and cab not in found:
                    found.add(cab)
                    pending.append(cab)
        return found

    def path_ids(self, cabs: set[str]) -> dict[str, set[str]]:
        result: dict[str, set[str]] = defaultdict(set)
        for cab in cabs:
            for type_name, path_id in self.assets.get(cab, ()):
                result[type_name].add(path_id)
        return result

    def media_files(self, path_ids: dict[str, set[str]]) -> set[str]:
        """Converted media named by PathID; a PathID shared across CABs over-reports."""
        files: set[str] = set()
        for type_name, wanted in sorted(path_ids.items()):
            folder = self.layout.unity_type_dir(type_name)
            if not wanted or not folder.is_dir():
                continue
            for item in folder.rglob("*"):
                match = PATH_ID_RE.search(item.name)
                if match and match.group(1).upper() in wanted and item.is_file():
                    files.add(item.relative_to(self.layout.root).as_posix())
        return files

    def store_rows(self, cabs: set[str], path_ids: dict[str, set[str]]) -> set[tuple[str, str]]:
        """``(type, name)`` keys of the Unity store rows these CABs produced."""
        store = self.layout.unity_store_path
        if not store.is_file() or not cabs:
            return set()
        connection = sqlite3.connect(f"file:{store.as_posix()}?mode=ro", uri=True)
        try:
            connection.execute("create temp table wanted_cab (cab text primary key)")
            connection.executemany("insert or ignore into wanted_cab values (?)", ((c,) for c in cabs))
            rows = set(connection.execute(
                "select type, name from objects where source_file in (select cab from wanted_cab)"))
            # Rows the store keeps without a container are matched by PathID only.
            connection.execute("create temp table wanted_id (id integer primary key)")
            ids = {int(pid, 16) - (1 << 64) if int(pid, 16) >= 1 << 63 else int(pid, 16)
                   for values in path_ids.values() for pid in values}
            connection.executemany("insert or ignore into wanted_id values (?)", ((i,) for i in ids))
            rows.update(connection.execute(
                "select type, name from objects where source_file is null "
                "and path_id in (select id from wanted_id)"))
            return rows
        finally:
            connection.close()


def predict(layout: ExportLayout, old: dict[str, dict[str, Any]], changes: dict[str, list[str]]) -> dict[str, Any]:
    """Full predicted sets of old outputs a refresh replaces, by evidence tier.

    Files are export-relative POSIX paths. Store entries use the store's own
    ``"<type>/<name>"`` row key, which for GameFiles is the game/-relative path.
    """
    replaced = [old[key] for key in changes["modified"] + changes["deleted"]]
    outputs: BundleOutputs | None = None
    result: dict[str, Any] = {
        "exactFiles": set(), "gameFileStoreEntries": set(), "predictedButAbsent": set(),
        "audioPackages": set(), "unmappedFiles": set(), "bundles": set(),
        "unityMediaFiles": set(), "unityStoreRows": set(),
        "dependentMediaFiles": set(), "dependentStoreRows": set(),
        "cabs": set(), "dependentCabs": set(),
        "relocatedBundles": set(), "relocatedCabs": set(),
        "relocatedMediaFiles": set(), "relocatedStoreRows": set(),
    }
    spans: list[dict[str, Any]] = []
    for row in replaced:
        name = f"{row['block']}/{row['path']}"
        if row["block"] in BUNDLE_BLOCKS:
            spans.append(row)
            result["bundles"].add(name)
            continue
        if "Audio" in row["block"]:
            result["audioPackages"].add(name)
            continue
        target = exact_output(row["block"], row["path"])
        if target is None:
            result["unmappedFiles"].add(name)
        elif target[0] == "store":
            result["gameFileStoreEntries"].add(target[1].split(":", 1)[1].replace("\\", "/"))
        elif (layout.root / target[1]).is_file():
            result["exactFiles"].add(target[1])
        else:
            result["predictedButAbsent"].add(target[1])
    if spans:
        outputs = BundleOutputs(layout)
        cabs = outputs.owned(spans)
        dependents = outputs.dependents(cabs)
        for tier, tier_cabs in (("", cabs), ("dependent", dependents)):
            path_ids = outputs.path_ids(tier_cabs)
            media = outputs.media_files(path_ids)
            rows = {f"{type_name}/{name}" for type_name, name in outputs.store_rows(tier_cabs, path_ids)}
            if tier:
                result["dependentCabs"], result["dependentMediaFiles"], result["dependentStoreRows"] = tier_cabs, media, rows
            else:
                result["cabs"], result["unityMediaFiles"], result["unityStoreRows"] = tier_cabs, media, rows
        result["dependentMediaFiles"] -= result["unityMediaFiles"]
        result["dependentStoreRows"] -= result["unityStoreRows"]
    moved = [old[key] for key in changes.get("relocated", ()) if old[key]["block"] in BUNDLE_BLOCKS]
    if moved:
        outputs = outputs if spans else BundleOutputs(layout)
        result["relocatedBundles"] = {f"{row['block']}/{row['path']}" for row in moved}
        moved_cabs = outputs.owned(moved)
        # A referencing document records its target's location too.
        moved_cabs |= outputs.dependents(moved_cabs)
        moved_cabs -= result["cabs"] | result["dependentCabs"]
        path_ids = outputs.path_ids(moved_cabs)
        result["relocatedCabs"] = moved_cabs
        result["relocatedMediaFiles"] = (outputs.media_files(path_ids)
                                         - result["unityMediaFiles"] - result["dependentMediaFiles"])
        result["relocatedStoreRows"] = ({f"{t}/{n}" for t, n in outputs.store_rows(moved_cabs, path_ids)}
                                        - result["unityStoreRows"] - result["dependentStoreRows"])
    return result


def summarize_prediction(prediction: dict[str, Any], sample_limit: int) -> dict[str, Any]:
    return {key: {"count": len(values), "sample": sorted(values)[:sample_limit]}
            for key, values in prediction.items()}


def prediction_payload(prediction: dict[str, Any]) -> dict[str, list[str]]:
    return {key: sorted(values) for key, values in prediction.items()}


def self_check(layout: ExportLayout, old: dict[str, dict[str, Any]], sample_limit: int) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    missing: dict[str, list[str]] = defaultdict(list)
    store_paths: dict[str, set[str]] = defaultdict(set)
    for row in old.values():
        if row["block"] in BUNDLE_BLOCKS or "Audio" in row["block"]:
            continue
        target = exact_output(row["block"], row["path"])
        if target is None:
            counts[f"{row['block']}:unmapped"] += 1
        elif target[0] == "store":
            counts[f"{row['block']}:store"] += 1
            store_paths[row["block"]].add(target[1].split(":", 1)[1])
        elif (layout.root / target[1]).is_file():
            counts[f"{row['block']}:present"] += 1
        else:
            counts[f"{row['block']}:absent"] += 1
            if len(missing[row["block"]]) < sample_limit:
                missing[row["block"]].append(target[1])
    return {"counts": dict(sorted(counts.items())), "absentSample": dict(missing)}


# -- CLI ----------------------------------------------------------------------

def run(args: argparse.Namespace) -> dict[str, Any]:
    layout = ExportLayout(args.export_root).require()
    old, header = load_old_ledger(layout.evidence_dir / LEDGER_RELATIVE)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "exportRoot": str(layout.root),
        "gameRoot": str(args.game_root),
        "oldLedger": {"files": len(old), **header},
    }
    if args.self_check:
        report["selfCheck"] = self_check(layout, old, args.sample_limit)
        return report
    with tempfile.TemporaryDirectory(prefix="package_diff_") as work:
        new, summary = scan_installed(args.animestudio, args.game_root, Path(work))
    changes = classify(old, new)
    build = compare_build_files(layout.evidence_dir / AUDIT_SUMMARY_RELATIVE, args.game_root)
    by_block: dict[str, Counter[str]] = defaultdict(Counter)
    for kind, keys in changes.items():
        for key in keys:
            by_block[key.split("/", 1)[0]][kind] += 1
    report.update({
        "installed": {"files": len(new), "missingChunks": summary.get("missingChunkCount")},
        "buildFiles": build,
        "totals": {kind: len(keys) for kind, keys in changes.items()},
        "byBlock": {block: dict(counter) for block, counter in sorted(by_block.items())},
        "changes": {kind: keys[: args.sample_limit] for kind, keys in changes.items()},
        "upToDate": not any(changes.values()) and not any(row["changed"] for row in build),
    })
    prediction = predict(layout, old, changes)
    report["replacedOutputs"] = summarize_prediction(prediction, args.sample_limit)
    if getattr(args, "keep_prediction", False):
        report["_prediction"] = prediction
    return report


def print_summary(report: dict[str, Any]) -> None:
    if "selfCheck" in report:
        print(json.dumps(report["selfCheck"], indent=2))
        return
    totals = report["totals"]
    print(f"installed client vs {report['exportRoot']}: "
          f"{totals['added']} added, {totals['modified']} modified, {totals['deleted']} deleted VFS files, "
          f"{totals.get('relocated', 0)} moved to a new chunk location")
    for row in report["buildFiles"]:
        if row["changed"]:
            print(f"  client binary changed: {row['file']}")
    for block, counts in report["byBlock"].items():
        print(f"  {block}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    outputs = report["replacedOutputs"]
    count = lambda key: outputs[key]["count"]  # noqa: E731
    print(f"old outputs predicted to change: {count('exactFiles')} exact files, "
          f"{count('gameFileStoreEntries')} GameFiles.sqlite entries, "
          f"{count('bundles')} bundles, {count('audioPackages')} audio packages")
    if count("bundles"):
        print(f"  bundles -> {count('cabs')} CABs, {count('unityMediaFiles')} Unity media files, "
              f"{count('unityStoreRows')} Unity.sqlite rows; through dependencies "
              f"{count('dependentCabs')} CABs, {count('dependentMediaFiles')} media files, "
              f"{count('dependentStoreRows')} rows")
    if count("relocatedBundles"):
        print(f"  {count('relocatedBundles')} unchanged bundles moved -> {count('relocatedCabs')} CABs, "
              f"{count('relocatedMediaFiles')} media files, {count('relocatedStoreRows')} rows "
              f"may change in their recorded source location only")
    for key in ("predictedButAbsent", "unmappedFiles"):
        if outputs[key]["count"]:
            print(f"  WARNING {key}: {outputs[key]['count']} (see report)")
    print("export is up to date with the installed client" if report["upToDate"]
          else "installed client differs from the export")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--export-root", type=Path, default=ExportLayout.configured().root)
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT,
                        help="installed Endfield_Data directory")
    parser.add_argument("--animestudio", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--sample-limit", type=int, default=200)
    parser.add_argument("--self-check", action="store_true",
                        help="predict every old exact-tier output and report absent predictions")
    args = parser.parse_args(argv)
    args.animestudio = args.animestudio or configured_animestudio_cli()
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = run(args)
    except (PackageDiffError, ExportLayoutError) as exc:
        print(f"package diff failed: {exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print_summary(report)
    print(f"report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
