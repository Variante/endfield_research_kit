"""Prepare installed-source evidence required by ordinary page builds.

This publishes no WebUI data. Receipts and their replay inputs belong to the
selected export. Existing receipts are admitted by their original validators;
cache metadata only avoids an unchanged VFS audit, never grants a schema claim.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import subprocess
import tempfile

from scripts.game_data import cooked_collision_corpus as collision
from scripts.game_data import jsondata_source_inventory as inventory
from scripts.game_data import unity_scene_corpus as scenes
from scripts.game_data.corpus_common import atomic_write_json, validate_provenance
from scripts.game_data.extraction.unity_overlay import iter_asset_map_rows
from scripts.source_paths import ExportLayout, configured_animestudio_cli


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def publish(path, value):
    atomic_write_json(path, value, sort_keys=True, skip_unchanged=True)


def run(command, **options):
    print("[build-evidence] " + subprocess.list2cmdline(list(map(str, command))), flush=True)
    subprocess.run(list(map(str, command)), check=True, **options)


def input_snapshot(game_root, cli):
    paths = {game_root.parent / "GameAssembly.dll", game_root.parent / "Endfield.exe",
             game_root / "app.info", game_root / "il2cpp_data/Metadata/global-metadata.dat",
             Path(__file__), cli}
    for assets in (game_root / "Persistent", game_root / "StreamingAssets"):
        paths.update(p for p in (assets / "VFS").rglob("*") if p.is_file())
    paths.update(p for p in cli.parent.rglob("*") if p.is_file())
    return [{"path": str(p.resolve()), "size": p.stat().st_size, "mtimeNs": p.stat().st_mtime_ns}
            for p in sorted(paths) if p.is_file()]


def audit_paths(layout):
    root = layout.evidence_dir / "animestudio"
    return root / "vfs_understanding_latest.json", root / "vfs_understanding_files_latest.jsonl.gz"


def validate_audit(summary_path, ledger_path, game_root, cli):
    summary = read_json(summary_path)
    for key, path in (("primaryAssets", game_root / "Persistent"),
                      ("fallbackAssets", game_root / "StreamingAssets")):
        if Path(summary[key]).resolve() != path.resolve():
            raise ValueError(f"VFS audit {key} differs from selected game root: {path}")
    if not summary.get("summary", {}).get("fullAuditPassed"):
        raise ValueError("VFS audit is not complete")
    with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
        header = json.loads(next(stream))
    failures, _ = validate_provenance(summary, header, ledger_path, summary["inputSetSha256"])
    if failures:
        raise ValueError(f"VFS audit provenance failed: {failures[:3]}")
    collision._verify_fingerprints(summary)
    if collision._path_key(cli) not in {collision._path_key(row["path"]) for row in summary["buildFingerprints"]}:
        raise ValueError("VFS audit does not name the selected AnimeStudio CLI")
    return summary


def ensure_audit(layout, game_root, cli):
    summary_path, ledger_path = audit_paths(layout)
    state_path = layout.evidence_dir / "animestudio/vfs_build_cache.json"
    before = input_snapshot(game_root, cli)
    try:
        if read_json(state_path) == before:
            summary = validate_audit(summary_path, ledger_path, game_root, cli)
            print("[build-evidence] VFS audit: current", flush=True)
            return summary
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        pass
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    run([cli, "vfs-audit", "--streaming-assets", game_root / "Persistent",
         "--fallback-assets", game_root / "StreamingAssets", "--summary-json", summary_path,
         "--ledger-jsonl-gz", ledger_path, "--report-md", summary_path.with_suffix(".md")])
    summary = validate_audit(summary_path, ledger_path, game_root, cli)
    if input_snapshot(game_root, cli) != before:
        raise ValueError("installed sources/exporter changed during VFS audit")
    publish(state_path, before)
    return summary


def ensure_jsondata(layout, summary):
    """Produce source identities, without requiring unrelated Buff/Skill grammar."""
    outer, ledger = audit_paths(layout)
    output = layout.evidence_dir / "animestudio/jsondata_source_current.json"
    rows = output.with_name("jsondata_source_files_current.jsonl.gz")
    try:
        saved = read_json(output)
        if (saved.get("format") == inventory.SOURCE_INVENTORY_FORMAT
                and saved.get("inputSetSha256") == summary["inputSetSha256"]
                and Path(saved["exportRoot"]).resolve() == layout.root.resolve()):
            inventory.verify_saved_inventory(saved, ledger_path=rows)
            print("[build-evidence] JsonData source inventory: current", flush=True)
            return
    except (OSError, ValueError, KeyError, TypeError):
        pass
    code = inventory.main(["--outer-summary", str(outer), "--outer-ledger", str(ledger),
        "--export-root", str(layout.root), "--expected-input-set-sha256", summary["inputSetSha256"],
        "--output-json", str(output), "--output-files", str(rows)])
    if code:
        raise ValueError("JsonData source inventory failed; see its bounded diagnostic above")


def bundle_slots(ledger):
    active, shadowed = set(), set()
    with gzip.open(ledger, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("recordType") != "file" or row.get("blockName") not in ("Bundle", "InitBundle"):
                continue
            if not row.get("physicalChunkPath"):
                continue
            key = (collision._path_key(row["physicalChunkPath"]), row["offset"])
            if row.get("status") == "shadowed_fallback":
                shadowed.add(key)
            elif row.get("status") == "verified" and row.get("boundaryStatus") == "boundary_verified":
                active.add(key)
    if not active:
        raise ValueError("current VFS audit has no authenticated Bundle slots")
    return active, shadowed


class ForeignMeshSource(ValueError):
    """An exported Mesh map names a different installation."""


def _mesh_rows(path, active, shadowed=(), *, vfs_roots=()):
    rows = []
    for row in iter_asset_map_rows(path):
        if row["Type"] != "Mesh":
            continue
        if vfs_roots and not any(Path(row["Source"]).resolve().is_relative_to(root) for root in vfs_roots):
            raise ForeignMeshSource(f"Mesh asset map does not describe the selected installed sources: {path}: {row['Source']}")
        slot = (collision._path_key(row["Source"]), row["Offset"])
        if slot not in active:
            if slot in shadowed:
                continue
            raise ValueError(f"Mesh asset map does not describe the selected installed sources: {path}: {slot}")
        rows.append(row)
    return rows


def _mesh_discovery(layout, game_root, cli, layer, active, input_set):
    """Discover current Mesh identities from the audit's exact physical CABs."""
    root = layout.evidence_dir / "assets/discovery" / layer
    root.mkdir(parents=True, exist_ok=True)
    physical_root = (game_root / layer).resolve()
    selection = [dict(Source=source, Offset=offset, PathID=0, Type="AssetBundle", Name="")
                 for source, offset in sorted(active) if Path(source).is_relative_to(physical_root)]
    if not selection:
        return []
    selection_path = root / "bundle_selection.json"
    publish(selection_path, selection)
    selection_sha = collision._digest(selection_path)
    producer_sha = collision._digest(Path(__file__))
    expected = dict(schema="endfield.collision-mesh-discovery.v3", inputSetSha256=input_set,
                    selectionSha256=selection_sha, producerSha256=producer_sha)
    state = root / "current.json"
    try:
        previous = read_json(state)
        candidate = Path(previous['path'])
        if (input_set and all(previous.get(key) == value for key, value in expected.items())
                and candidate.resolve().is_relative_to(root.resolve())
                and collision._digest(candidate) == previous['sha256']
                and Path(previous['log']).resolve().is_relative_to(root.resolve())
                and Path(previous['log']).stat().st_size == 0
                and collision._digest(Path(previous['log'])) == previous['logSha256']):
            rows = _mesh_rows(candidate, active)
            print(f"[build-evidence] collision Mesh discovery {layer}: current", flush=True)
            return rows
    except (OSError, ValueError, KeyError, TypeError):
        pass
    work = Path(tempfile.mkdtemp(prefix="maps-", dir=root)).resolve()
    log = work / "discovery.log"
    with log.open("wb") as stream:
        run([cli, physical_root, work, "--game", "ArknightsEndfield",
             "--map_op", "AssetMap", "--map_type", "JSON", "--map_name", layer, "--types", "Mesh",
             "--filter_data", selection_path, "--logger_flags", "Warning", "Error"],
            stdout=stream, stderr=subprocess.STDOUT)
    if log.stat().st_size:
        with log.open(encoding="utf-8", errors="replace") as stream:
            detail = stream.read(1200)
        raise ValueError(f"collision Mesh discovery diagnostics: {log}: {detail}")
    candidate = work / (layer + ".json")
    rows = _mesh_rows(candidate, active)
    if (collision._digest(selection_path) != selection_sha
            or collision._digest(Path(__file__)) != producer_sha):
        raise ValueError("collision Mesh discovery inputs changed during extraction")
    publish(state, {**expected, "path": str(candidate), "sha256": collision._digest(candidate),
                    "log": str(log), "logSha256": collision._digest(log)})
    return rows


def mesh_selection(layout, game_root, cli, active, shadowed, *, input_set=None):
    selected = {}
    vfs_roots = tuple((game_root / layer / "VFS").resolve() for layer in ("StreamingAssets", "Persistent"))
    for layer in ("StreamingAssets", "Persistent"):
        existing = sorted(layout.asset_map_dir(layer).glob("*.json"))
        rows = []
        current = bool(existing)
        for path in existing:
            # A foreign installation is a configuration error, not a request to
            # silently replace its sources with whichever local game is present.
            try:
                rows.extend(_mesh_rows(path, active, shadowed, vfs_roots=vfs_roots))
            except ForeignMeshSource:
                raise
            except ValueError as error:
                print(f"[build-evidence] collision Mesh discovery {layer}: exported map is not current; using audited discovery ({error})", flush=True)
                current = False
                break
        if not current:
            rows = _mesh_discovery(layout, game_root, cli, layer, active, input_set)
        for row in rows:
            slot = (collision._path_key(row["Source"]), row["Offset"])
            key = (*slot, row["PathID"])
            selected[key] = {**row, "Source": str(Path(row["Source"]).resolve())}
    if not selected:
        raise ValueError("current asset maps contain no authenticated Mesh identities")
    return [selected[key] for key in sorted(selected)]


def ensure_collision(layout, game_root, cli, summary):
    outer, ledger = audit_paths(layout)
    root = layout.evidence_dir / "assets"
    root.mkdir(parents=True, exist_ok=True)
    active, shadowed = bundle_slots(ledger)
    selection = mesh_selection(layout, game_root, cli, active, shadowed, input_set=summary['inputSetSha256'])
    selection_path = root / "collision_mesh_selection.json"
    publish(selection_path, selection)
    receipt = root / "cooked_collision_current_latest.json"
    try:
        saved = collision.validate_receipt(receipt)
        if (saved["inputSetSha256"] != summary["inputSetSha256"]
                or read_json(Path(saved["selection"]["path"])) != selection):
            raise ValueError("collision selection/input set changed")
        print("[build-evidence] cooked collision: current", flush=True)
    except (OSError, ValueError, KeyError, TypeError):
        report = collision.audit_selection(selection_path=selection_path, summary_path=outer,
            ledger_path=ledger, expected_input_set=summary["inputSetSha256"], cli=cli,
            work_root=root / "collision_evidence", evidence_root=layout.evidence_dir)
        if report["status"] != "complete":
            publish(receipt.with_suffix(".failed.json"), report)
            raise ValueError(f"collision extraction failed: {report['failures'][:3]}")
        publish(receipt, report)
    scene_selection = [dict(Source=source, Offset=offset, PathID=0, Type="AssetBundle", Name="")
                       for source, offset in sorted(active)]
    scene_path = root / "collision_scene_selection.json"
    publish(scene_path, scene_selection)
    scene_receipt = root / "collision_scene_current.json"
    try:
        saved = scenes.validate_receipt(scene_receipt)
        if (saved["inputSetSha256"] != summary["inputSetSha256"]
                or read_json(Path(saved["selection"]["path"])) != scene_selection):
            raise ValueError("scene selection/input set changed")
        print("[build-evidence] collision authored sources: current", flush=True)
    except (OSError, ValueError, KeyError, TypeError):
        report = scenes.audit_selection(selection_path=scene_path, summary_path=outer, ledger_path=ledger,
            expected_input_set=summary["inputSetSha256"], work_root=root / "collision_ownership", cli=cli)
        if report["status"] != "complete":
            publish(scene_receipt.with_suffix(".failed.json"), report)
            raise ValueError(f"collision scene extraction failed: {report['failures'][:3]}")
        publish(scene_receipt, report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--animestudio", type=Path, default=configured_animestudio_cli())
    parser.add_argument("--family", choices=("jsondata-source", "jsondata-classified", "collision", "vfs"), action="append", required=True)
    args = parser.parse_args(argv)
    try:
        layout = ExportLayout(args.export_root.resolve()).require()
        game_root, cli = args.game_root.resolve(), args.animestudio.resolve()
        families = set(args.family)
        if "jsondata-classified" in families:
            if not layout.game.is_dir():
                raise ValueError(f"selected export has no game directory: {layout.game}; cannot build Data from missing inputs")
            families.add("jsondata-source")
        if "jsondata-source" in families and not layout.json_dir.is_dir():
            # Required JsonData is rejected by the wrapper's freshness guard.
            # Optional page inputs must remain optional on a partial export.
            print(f"[build-evidence] JsonData source inventory: no exported input at {layout.json_dir}", flush=True)
            families.remove("jsondata-source")
            families.discard("jsondata-classified")
        if not families:
            return 0
        if not cli.is_file():
            raise ValueError(f"selected AnimeStudio CLI is missing: {cli}")
        if "jsondata-classified" in families:
            from scripts.game_data.extraction.jsondata_evidence import require_current_family_native
            require_current_family_native(game_root)
        summary = ensure_audit(layout, game_root, cli)
        if "jsondata-source" in families:
            ensure_jsondata(layout, summary)
        if "jsondata-classified" in families:
            from scripts.game_data.extraction.jsondata_evidence import prepare
            prepare(layout, game_root, cli, summary)
        if "collision" in families:
            ensure_collision(layout, game_root, cli, summary)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f"[build-evidence] failed: {error}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
