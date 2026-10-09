"""Archive bounded exported source bytes before mission observation.

This preserves stored export identities only. It neither extracts game data nor
authenticates those exports against the installed native client.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.repo_paths import REPO_ROOT

TABLE_PREFIXES = ("SNS", "Dialog", "Mission", "Quest", "ChapterMission", "InteractiveMission", "AudioDialog",
                  "Activity", "Dungeon", "Level", "Map", "Npc", "Snapshot", "KiteStation")
TEXT_TABLES = {"TextTable.json", "TextVoIdTable.json", "I18nTextTable_CN.json"}
IDENTITY_TIME_TABLES = {"TimeRangeTable.json"}
ALL_JSON_FAMILIES = ("MissionRuntimeAsset", "LevelData", "LevelScriptData", "LevelScriptTemplateData", "LevelConfig")
SHARED_JSON = ("game/Json/GameplayConfig/NpcProxyExDataTable.json",
               "game/Json/GameplayConfig/DialogIdTable.json")
MAX_FILES = 16384
MAX_COPY_FILE_BYTES = 32 * 1024 * 1024
MAX_COPY_BYTES = 128 * 1024 * 1024
MAX_IDENTITY_BYTES = 256 * 1024 * 1024


class SourceArchiveError(ValueError):
    """Source selection or archive publication cannot be completed safely."""


def select_sources(export_root: Path, mission: str, *, profile: str = "mission") -> tuple[list[tuple[Path, str]], list[str]]:
    if profile not in {"mission", "buff"} or (profile == "buff" and mission != "all"):
        raise SourceArchiveError("mission_source_archive: expected mission or buff; buff requires --mission all")
    if profile == "buff":
        provenance = export_root / "meta/extraction/provenance.json"
        sources = sorted((export_root / "game/Json/BuffData").glob("*.json"))
        if not provenance.is_file() or not sources:
            raise SourceArchiveError("mission_source_archive: buff requires export provenance and nonempty game/Json/BuffData")
        selected = [(provenance, "exportProvenance"), *((path, "buffData") for path in sources)]
        skills = sorted((export_root / "game/Json/SkillData").glob("*.json"))
        selected.extend((path, "skillData") for path in skills)
        selected.extend((path, "buffIdentityTable") for path in sorted((export_root / "game/Table").glob("Buff*.json")))
        if len(selected) > MAX_FILES:
            raise SourceArchiveError(f"mission_source_archive: selected {len(selected)} files exceeds {MAX_FILES}")
        return selected, ([] if skills else ["No available SkillData source bytes; skill source joins remain unresolved."])
    if not re.fullmatch(r"[a-z0-9_]{1,80}", mission):
        raise SourceArchiveError("mission_source_archive: invalid mission ID")
    required = [(export_root / "meta/extraction/provenance.json", "exportProvenance")]
    if mission == "all":
        mains = sorted(path for path in (export_root / "game/Json/MissionRuntimeAsset").glob("*.json")
                       if not path.stem.endswith("_meta"))
        if not mains:
            raise SourceArchiveError("mission_source_archive: no mission definitions in selected export")
        for path in mains:
            required.extend(((path, "mission"), (path.with_stem(path.stem + "_meta"), "missionMeta")))
    else:
        required.extend(((export_root / f"game/Json/MissionRuntimeAsset/{mission}.json", "mission"),
                         (export_root / f"game/Json/MissionRuntimeAsset/{mission}_meta.json", "missionMeta")))
    missing = [str(path) for path, _ in required if not path.is_file()]
    if missing:
        raise SourceArchiveError(f"mission_source_archive: missing required exported sources: {missing!r}")
    selected = {path: role for path, role in required}
    # Underscores are source-name separators. Reject a1m150 when focus is a1m15.
    match = re.compile(rf"(?<![a-z0-9]){re.escape(mission)}(?![a-z0-9])", re.IGNORECASE)
    for path in (export_root / "game/Json").rglob("*.json"):
        family = path.relative_to(export_root / "game/Json").parts[0]
        if (mission == "all" and family in ALL_JSON_FAMILIES) or (mission != "all" and match.search(path.stem)):
            relative = path.relative_to(export_root).as_posix()
            role = {"LevelData": "levelData", "LevelScriptData": "levelScriptData",
                    "LevelScriptTemplateData": "levelScriptTemplateData", "LevelConfig": "levelConfig"}.get(family, "missionNamedJson")
            selected.setdefault(path, role)
    for relative in SHARED_JSON:
        path = export_root / relative
        if path.is_file():
            selected[path] = "sharedSemanticJson"
    for path in (export_root / "game/Table").glob("*.json"):
        if path.stem.startswith(TABLE_PREFIXES) or path.name in TEXT_TABLES | IDENTITY_TIME_TABLES:
            selected[path] = "sharedSemanticTable"
    if len(selected) > MAX_FILES:
        raise SourceArchiveError(f"mission_source_archive: selected {len(selected)} files exceeds {MAX_FILES}")
    gaps = []
    if mission == "all":
        for family in ALL_JSON_FAMILIES:
            if not any(path.is_relative_to(export_root / "game/Json" / family) for path in selected):
                gaps.append(f"No available source bytes for selected family: game/Json/{family}")
    if not any(role == "levelData" for role in selected.values()):
        gaps.append("No selected LevelData source was present.")
    for table in ("SNSDialogTable.json", "SNSDialogOptionTable.json", "DialogTextTable.json", "DialogOptionTable.json", "TextTable.json", "I18nTextTable_CN.json"):
        if export_root / f"game/Table/{table}" not in selected:
            gaps.append(f"Expected semantic table missing: game/Table/{table}")
    for relative in (*SHARED_JSON, *(f"game/Table/{name}" for name in sorted(IDENTITY_TIME_TABLES))):
        if export_root / relative not in selected:
            gaps.append(f"Expected identity/context source missing: {relative}")
    # Preserve identity/provenance and mission definitions before optional tables
    # or script files can consume a copy budget.
    priority = {"exportProvenance": 0, "mission": 1, "missionMeta": 2}
    return sorted(selected.items(), key=lambda item: (priority.get(item[1], 3), item[0].relative_to(export_root).as_posix())), gaps


def archive(export_root: Path, output_dir: Path, mission: str, *, profile: str = "mission") -> dict[str, Any]:
    export_root, output_dir = Path(export_root).resolve(), Path(output_dir).resolve()
    if not any(output_dir.is_relative_to((REPO_ROOT / folder).resolve()) for folder in ("reports", "scratch", "tmp")):
        raise SourceArchiveError("mission_source_archive: output must be under reports/, scratch/, or tmp/")
    if output_dir == export_root or output_dir.is_relative_to(export_root):
        raise SourceArchiveError("mission_source_archive: output must be outside the selected export")
    if output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir())):
        raise SourceArchiveError("mission_source_archive: output directory must be new or empty")
    selected, gaps = select_sources(export_root, mission, profile=profile)
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory: dict[str, Any] = {"schema": "endfield.mission-source-archive.v1", "focusMission": mission,
        "archivedAt": datetime.now(timezone.utc).isoformat(), "exportRoot": str(export_root),
        "evidenceBoundary": "structuralOnly", "nativeValidated": False,
        "identityBoundary": "Copied exported bytes and their SHA256 identities only; export provenance is retained verbatim and is not a current-native validation result.",
        "selectionScope": "allMissions" if mission == "all" else "focusedMission",
        "selection": ("All available MissionRuntimeAsset, LevelData, LevelScriptData, LevelScriptTemplateData and LevelConfig JSON bytes; shared NPC/activity/dungeon/mission/dialog/snapshot/entrust identity/time tables and CN localization."
                      if mission == "all" else "Mission-delimited JSON filenames, required mission/meta/provenance, and bounded shared semantic tables including CN localization."),
        "budgets": {"maxFiles": MAX_FILES, "maxCopyFileBytes": MAX_COPY_FILE_BYTES,
                    "maxCopyBytes": MAX_COPY_BYTES, "maxIdentityBytes": MAX_IDENTITY_BYTES},
        "files": [], "gaps": gaps, "copiedFiles": 0, "copiedBytes": 0, "identityBytes": 0,
        "unarchivedScope": ("Unity.sqlite objects, other JSON families, media and non-CN localization are outside this bounded archive. Referenced sources outside the selected families remain unresolved."
                            if mission == "all" else "Other missions, indirect template dependencies, Unity.sqlite objects, media, and non-CN localization are outside this bounded archive.")}
    if profile == "buff":
        inventory.update(selectionScope="buffData", selection="All exported BuffData and available SkillData JSON bytes and Buff identity tables, with export provenance retained verbatim.",
                         unarchivedScope="Character/ability/entity definitions, other JSON families, Unity objects and media are not archived. Referenced sources outside BuffData and SkillData remain unresolved.")
    try:
        for path, role in selected:
            if not path.resolve().is_relative_to(export_root):
                raise SourceArchiveError(f"mission_source_archive: source escaped export root: {path}")
            stat = path.stat()
            relative = path.relative_to(export_root).as_posix()
            row: dict[str, Any] = {"sourceRelativePath": relative, "originalPath": str(path),
                "role": role, "bytes": stat.st_size, "sourceMtimeNs": stat.st_mtime_ns,
                "sha256": None, "copied": False, "nativeValidated": False}
            inventory["files"].append(row)
            if inventory["identityBytes"] + stat.st_size > MAX_IDENTITY_BYTES:
                row["status"] = "identityBudgetExceeded"
                inventory["gaps"].append(f"Source identity budget exceeded: {relative}")
                continue
            copy = stat.st_size <= MAX_COPY_FILE_BYTES and inventory["copiedBytes"] + stat.st_size <= MAX_COPY_BYTES
            destination = output_dir / "files" / relative
            if copy:
                destination.parent.mkdir(parents=True, exist_ok=True)
            digest, length = hashlib.sha256(), 0
            # Hash exactly the bytes copied, using one read of the selected file.
            with path.open("rb") as source:
                target = destination.open("xb") if copy else None
                try:
                    while block := source.read(1024 * 1024):
                        length += len(block)
                        if inventory["identityBytes"] + length > MAX_IDENTITY_BYTES or length > stat.st_size:
                            raise SourceArchiveError(f"mission_source_archive: source grew or identity budget changed while reading: {relative}")
                        digest.update(block)
                        if target is not None:
                            target.write(block)
                finally:
                    if target is not None:
                        target.close()
            final_stat = path.stat()
            if length != stat.st_size or (stat.st_size, stat.st_mtime_ns) != (final_stat.st_size, final_stat.st_mtime_ns):
                raise SourceArchiveError(f"mission_source_archive: source changed while reading: {relative}")
            row.update(sha256=digest.hexdigest(), copied=copy, status="copied" if copy else "identityOnlyCopyBudgetExceeded")
            inventory["identityBytes"] += length
            if copy:
                row["archivedRelativePath"] = destination.relative_to(output_dir).as_posix()
                inventory["copiedFiles"] += 1
                inventory["copiedBytes"] += length
            else:
                inventory["gaps"].append(f"Copy budget exceeded; SHA256 identity only: {relative}")
        inventory["selectionComplete"] = all(row["copied"] for row in inventory["files"])
        inventory["status"] = "archived"
    except (OSError, SourceArchiveError) as exc:
        inventory["status"] = "failed"
        inventory["failure"] = str(exc)
        (output_dir / "inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise
    (output_dir / "inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return inventory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mission", default="all", help="All available mission sources by default; supply a mission key for a smaller snapshot.")
    parser.add_argument("--profile", choices=("mission", "buff"), default="mission", help="Buff selects BuffData and available SkillData source bytes without requiring mission definitions.")
    parser.add_argument("--export-root", type=Path, default=REPO_ROOT / "export_full")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = archive(args.export_root, args.output_dir, args.mission, profile=args.profile)
    except (OSError, SourceArchiveError) as exc:
        print(f"[mission_trace_source_archive] failed: {exc}")
        return 1
    print(f"[mission_trace_source_archive] archived: {result['copiedFiles']} files, {result['copiedBytes']} bytes; {len(result['gaps'])} gaps; native validation not claimed")
    if args.mission == "all" and not result["selectionComplete"]:
        print("[mission_trace_source_archive] incomplete source selection: source copy budgets exceeded; preserve the inventory and review the source archive bounds")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
