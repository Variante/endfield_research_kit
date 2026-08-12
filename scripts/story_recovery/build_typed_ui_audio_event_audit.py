#!/usr/bin/env python3
"""Audit typed UI/activity table Events and their current Lua consumers."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_audio import TYPED_UI_TABLE_WWISE_EVENT_FIELDS  # noqa: E402
from build_audio_semantics import audio_hash_generator_compute  # noqa: E402


LUA_CONSUMER_CHECKS = {
    "uiAnimationOpenEvent": {
        "Data/LuaScripts/UI/Panels/ActivityStaminaDiscount/ActivityStaminaDiscountCtrl.lua": (
            "bgStateData.audioOnOpen", "SetAudioOnOpen(audioOnOpen)",
        ),
    },
    "activityPushPopupBgmEvent": {
        "Data/LuaScripts/UI/Panels/ActivityPushPopup/ActivityPushPopupCtrl.lua": (
            "pushCfg.bgm", "AudioManager.PostEvent(pushCfg.bgm)",
        ),
    },
    "activityCenterBgmEvent": {
        "Data/LuaScripts/Phase/ActivityCenter/PhaseActivityCenter.lua": (
            "activityData.bgm", "AudioManager.PostEvent(activityData.bgm)",
        ),
    },
    "uiVideoAudioEvent": {
        "Data/LuaScripts/UI/Widgets/VideoPlayer.lua": (
            "VideoPlayer.PlayAudio", "AudioAdapter.PostEvent(audioKey)",
            "AudioAdapter.SeekOnEvent(self.m_videoAudioKey",
        ),
        "Data/LuaScripts/UI/Panels/GachaPoolVideo/GachaPoolVideoCtrl.lua": (
            "cfg.videoAudioKey", "videoPlayer:PlayAudio(self.m_info.videoAudioKey)",
        ),
        "Data/LuaScripts/UI/Panels/ActivitySkipChapter1/ActivitySkipChapter1Ctrl.lua": (
            "cfg.videoAudioKey", "videoPlayer:PlayAudio(self.m_info.videoAudioKey)",
        ),
    },
    "domainRegionSwitchEvent": {
        "Data/LuaScripts/UI/Panels/SettlementSwitchRegionPopup/SettlementSwitchRegionPopupCtrl.lua": (
            "domainData.audKeySwitchRegionPopup",
            "AudioManager.PostEvent(domainData.audKeySwitchRegionPopup)",
        ),
    },
    "domainUpgradeAnimationEvent": {
        "Data/LuaScripts/UI/Panels/DomainUpgrade/DomainUpgradeCtrl.lua": (
            "audKeyUpToastNotLevelUpEnhance", "audKeyUpToastLevelUpPreEnhance",
            "audKeyUpToastLevelUpMoment", "audKeyUpToastLevelUpAfterEnhance",
            "AudioAdapter.PostEvent(audKey)",
        ),
    },
}

SNS_VOICE_LUA_CONSUMER_CHECKS = {
    "Data/LuaScripts/UI/Widgets/SNSDialogContentCoreCell.lua": (
        '[SNSDialogContentType.Voice] = "Voice"',
        "ContentType2WidgetName[contentType]",
    ),
    "Data/LuaScripts/UI/Widgets/SNSContentVoice.lua": (
        "local voiceId = contentParam.Count > 0 and contentParam[0] or \"\"",
        "AudioAdapter.PostEvent(voiceId)",
        "AudioAdapter.StopByPlayingId(self.m_voiceHandleId)",
    ),
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_report(
    audio_index: dict[str, Any],
    *,
    lua_root: Path,
    metadata_catalog: dict[str, Any] | None = None,
    native_catalog: dict[str, Any] | None = None,
    metadata_path: Path | None = None,
    gameassembly_path: Path | None = None,
) -> dict[str, Any]:
    inventory: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in audio_index.get("wwiseEventInventory") or []:
        if isinstance(row, dict) and isinstance(row.get("eventHash"), int):
            inventory[int(row["eventHash"]) & 0xFFFFFFFF].append(row)
    prior_names = {
        int(row["eventHash"]) & 0xFFFFFFFF
        for row in audio_index.get("eventEvidence") or []
        if isinstance(row, dict) and isinstance(row.get("eventHash"), int)
        and not str(row.get("eventId") or "").startswith("hashed-event:0x")
    }
    allowed = {
        (table, field): spec[0]
        for table, fields in TYPED_UI_TABLE_WWISE_EVENT_FIELDS.items()
        for field, spec in fields.items()
    }
    errors: list[str] = []
    aliases: list[dict[str, Any]] = []
    seen: dict[int, str] = {}
    route_counts: Counter[str] = Counter()
    field_counts: Counter[str] = Counter()
    relation_counts: Counter[str] = Counter()
    packages: Counter[str] = Counter()
    for raw in audio_index.get("typedUiTableWwiseEventAliases") or []:
        if not isinstance(raw, dict):
            continue
        row = dict(raw)
        try:
            event_hash = int(row.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            errors.append(f"invalid alias identity: {row!r}")
            continue
        name = str(row.get("name") or "").strip()
        if audio_hash_generator_compute(name) != event_hash:
            errors.append(f"name hash mismatch for {name}: 0x{event_hash:08x}")
        if event_hash not in inventory:
            errors.append(f"Wwise Event missing for {name}: 0x{event_hash:08x}")
        if event_hash in seen and seen[event_hash].casefold() != name.casefold():
            errors.append(f"alias collision for 0x{event_hash:08x}: {seen[event_hash]} / {name}")
        seen[event_hash] = name
        for usage in row.get("usages") or []:
            if not isinstance(usage, dict):
                continue
            key = (str(usage.get("table") or ""), str(usage.get("field") or ""))
            route = str(usage.get("routeKind") or "")
            if key not in allowed:
                errors.append(f"unapproved field for {name}: {key[0]}.{key[1]}")
            elif allowed[key] != route:
                errors.append(f"route mismatch for {name}: {route} != {allowed[key]}")
            route_counts[route] += 1
            field_counts[f"{key[0]}.{key[1]}"] += int(usage.get("occurrenceCount") or 0)
        event_rows = inventory.get(event_hash, [])
        media_ids = {media for item in event_rows for media in item.get("mediaIds") or []}
        action_operations = []
        for item in event_rows:
            for action in item.get("actionEvidence") or []:
                if not isinstance(action, dict):
                    continue
                operation = str(action.get("operation") or "")
                try:
                    operation_type = int(action.get("actionType")) & 0xFF00
                except (TypeError, ValueError):
                    operation_type = -1
                if operation_type == 0x1200:
                    operation = "setState"
                elif operation_type == 0x1400:
                    operation = "resetGameParameter"
                if operation:
                    action_operations.append(operation)
        control_only = bool(action_operations) and all(
            operation in {"setState", "resetGameParameter"}
            for operation in action_operations
        )
        relation = "decodedMedia" if media_ids else "controlOnly" if control_only else "noDecodedMedia"
        relation_counts[relation] += 1
        bank_packages = sorted({
            PurePosixPath(str(item.get("bank") or "").replace("\\", "/")).name
            for item in event_rows if item.get("bank")
        })
        for package in bank_packages:
            packages[package] += 1
        row["bankPackages"] = bank_packages
        row["decodedMediaCount"] = len(media_ids)
        row["audioLibraryRelation"] = relation
        row["wasPreviouslyNamed"] = event_hash in prior_names
        row["aliasSource"] = "typedUiTableWwiseEventAliases"
        aliases.append(row)

    typed_ui_alias_count = len(aliases)
    for raw in audio_index.get("snsVoiceWwiseEventAliases") or []:
        if not isinstance(raw, dict):
            continue
        row = dict(raw)
        try:
            event_hash = int(row.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            errors.append(f"invalid SNS Voice alias identity: {row!r}")
            continue
        name = str(row.get("name") or "").strip()
        if audio_hash_generator_compute(name) != event_hash:
            errors.append(f"SNS Voice name hash mismatch for {name}: 0x{event_hash:08x}")
        if event_hash not in inventory:
            errors.append(f"SNS Voice Wwise Event missing for {name}: 0x{event_hash:08x}")
        if event_hash in seen and seen[event_hash].casefold() != name.casefold():
            errors.append(f"SNS Voice alias collision for 0x{event_hash:08x}: {seen[event_hash]} / {name}")
        seen[event_hash] = name
        for usage in row.get("usages") or []:
            if not isinstance(usage, dict):
                continue
            if usage.get("table") != "SNSDialogTable.json":
                errors.append(f"SNS Voice unexpected table for {name}: {usage.get('table')}")
            if usage.get("contentType") != 5 or usage.get("contentTypeName") != "Voice":
                errors.append(f"SNS Voice content type mismatch for {name}: {usage.get('contentType')}")
            if usage.get("contentParamIndex") != 0:
                errors.append(f"SNS Voice parameter index mismatch for {name}: {usage.get('contentParamIndex')}")
        event_rows = inventory.get(event_hash, [])
        media_ids = {media for item in event_rows for media in item.get("mediaIds") or []}
        relation = "decodedMedia" if media_ids else "noDecodedMedia"
        relation_counts[relation] += 1
        bank_packages = sorted({
            PurePosixPath(str(item.get("bank") or "").replace("\\", "/")).name
            for item in event_rows if item.get("bank")
        })
        for package in bank_packages:
            packages[package] += 1
        row["bankPackages"] = bank_packages
        row["decodedMediaCount"] = len(media_ids)
        row["audioLibraryRelation"] = relation
        row["wasPreviouslyNamed"] = event_hash in prior_names
        row["aliasSource"] = "snsVoiceWwiseEventAliases"
        aliases.append(row)

    checked_routes = set(route_counts)
    for route in sorted(checked_routes):
        for rel, needles in LUA_CONSUMER_CHECKS.get(route, {}).items():
            path = lua_root / Path(rel)
            if not path.is_file():
                errors.append(f"Lua consumer missing for {route}: {rel}")
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for needle in needles:
                if needle not in text:
                    errors.append(f"Lua consumer evidence missing for {route}: {rel}: {needle}")
    if len(aliases) > typed_ui_alias_count:
        for rel, needles in SNS_VOICE_LUA_CONSUMER_CHECKS.items():
            path = lua_root / Path(rel)
            if not path.is_file():
                errors.append(f"SNS Voice Lua consumer missing: {rel}")
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for needle in needles:
                if needle not in text:
                    errors.append(f"SNS Voice Lua evidence missing: {rel}: {needle}")

    provenance: dict[str, Any] = {
        "audioIndexSchemaVersion": audio_index.get("eventEvidenceSchemaVersion"),
        "luaRoot": str(lua_root),
    }
    if metadata_catalog:
        provenance["metadataCatalog"] = {
            "metadata": metadata_catalog.get("metadata"),
            "matchedTypeCount": (metadata_catalog.get("summary") or {}).get("matchedTypeCount"),
        }
    if native_catalog:
        mapped = [row for row in native_catalog.get("bodyTargets") or [] if row.get("mappingStatus") == "mapped"]
        provenance["nativeCatalog"] = {
            "mappedBodyTargets": len(mapped),
            "totalBodyTargets": len(native_catalog.get("bodyTargets") or []),
            "codeRegistration": native_catalog.get("codeRegistration"),
        }
    for label, path in (("globalMetadata", metadata_path), ("gameAssembly", gameassembly_path)):
        if path is not None and path.is_file():
            provenance[label] = {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
    summary = {
        "wwiseEventObjectOccurrences": sum(len(rows) for rows in inventory.values()),
        "wwiseEventObjectHashes": len(inventory),
        "typedUiTableWwiseEventAliases": typed_ui_alias_count,
        "snsVoiceWwiseEventAliases": len(aliases) - typed_ui_alias_count,
        "newlyRecoveredEventNames": sum(not row["wasPreviouslyNamed"] for row in aliases),
        "previouslyNamedAliases": sum(bool(row["wasPreviouslyNamed"]) for row in aliases),
        "routeKinds": dict(sorted(route_counts.items())),
        "fieldOccurrences": dict(sorted(field_counts.items())),
        "audioLibraryRelations": dict(sorted(relation_counts.items())),
        "bankPackages": dict(sorted(packages.items())),
        "validationErrors": len(errors),
    }
    return {
        "schemaVersion": 1,
        "summary": summary,
        "provenance": provenance,
        "evidenceBoundary": [
            "Only metadata-typed table getters with an exact current decrypted-Lua path to PostEvent/PlayAudio/SetAudioOnOpen are admitted.",
            "SNS aliases additionally require metadata enum Voice=5, contentParam[0], the Voice widget mapping, and its exact PostEvent/StopByPlayingId consumer.",
            "Each string must hash exactly to a current type-4 Wwise Event id; unrelated table strings and hash collisions remain excluded.",
            "VideoPlayer proves PostEvent plus playing-id stop and seek synchronization, but the selected video/pool and live execution remain unobserved.",
            "Static Lua callsites prove authored conditional placement, not that the branch ran or the media was audible.",
        ],
        "validationErrors": errors,
        "aliases": aliases,
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Typed UI/activity audio Event audit", "",
        f"- complete Wwise Event inventory: `{summary['wwiseEventObjectOccurrences']:,}` occurrences / `{summary['wwiseEventObjectHashes']:,}` unique hashes",
        f"- exact typed table/Lua consumer aliases: `{summary['typedUiTableWwiseEventAliases']:,}`",
        f"- exact SNS Voice-node/Lua aliases: `{summary['snsVoiceWwiseEventAliases']:,}`",
        f"- newly recovered Event names: `{summary['newlyRecoveredEventNames']:,}`",
        f"- validation errors: `{summary['validationErrors']}`", "",
        "## Routes", "",
    ]
    lines.extend(f"- `{name}`: `{count:,}` Events" for name, count in summary["routeKinds"].items())
    lines.extend(["", "## Audio-library relations", ""])
    lines.extend(f"- `{name}`: `{count:,}` Events" for name, count in summary["audioLibraryRelations"].items())
    lines.extend(["", "## Evidence boundary", ""])
    lines.extend(f"- {value}" for value in report["evidenceBoundary"])
    lines.extend(["", "## Aliases", ""])
    for row in report["aliases"]:
        lines.append(
            f"- `{row['eventHashHex']}` -> `{row['name']}`; "
            f"audio-library relation `{row['audioLibraryRelation']}`; "
            f"decoded media `{row['decodedMediaCount']}`"
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, default=ROOT / "export_full")
    parser.add_argument("--language", default="CN")
    parser.add_argument("--lua-root", type=Path, default=ROOT / "scratch/reverse_engineering/audio_event_string_hash_scan/lua_consumers/Persistent/Lua")
    parser.add_argument("--metadata-catalog", type=Path, default=ROOT / "scratch/reverse_engineering/audio_event_string_hash_scan/ui_activity_audio_metadata.json")
    parser.add_argument("--native-catalog", type=Path, default=ROOT / "scratch/reverse_engineering/audio_event_string_hash_scan/ui_activity_audio_consumers_gameassembly.json")
    parser.add_argument("--game-root", type=Path, default=Path(r"D:\Program Files\Endfield Game\Endfield_Data"))
    parser.add_argument("--out", type=Path, default=ROOT / "reports/story/recovery/audio/typed_ui_audio_event_audit.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "reports/story/recovery/audio/typed_ui_audio_event_audit.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        load_json(args.export_root / "structured/Audio" / args.language.upper() / "index.json"),
        lua_root=args.lua_root,
        metadata_catalog=load_json(args.metadata_catalog) if args.metadata_catalog.is_file() else None,
        native_catalog=load_json(args.native_catalog) if args.native_catalog.is_file() else None,
        metadata_path=args.game_root / "il2cpp_data/Metadata/global-metadata.dat",
        gameassembly_path=args.game_root.parent / "GameAssembly.dll",
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(report), encoding="utf-8")
    summary = report["summary"]
    total_aliases = summary["typedUiTableWwiseEventAliases"] + summary["snsVoiceWwiseEventAliases"]
    print(f"Typed UI/SNS audio Event audit: aliases={total_aliases:,}, newNames={summary['newlyRecoveredEventNames']:,}, errors={summary['validationErrors']}")
    return 1 if summary["validationErrors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
