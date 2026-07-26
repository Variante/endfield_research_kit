#!/usr/bin/env python3
"""Census direct managed mission/quest identity co-carriers.

This audit scans every installed managed type for a direct field pair between:

* mission/quest identity; and
* a LevelScript/scene identity or a Story playback identity.

The exact candidates are then classified against already decoded authored and
native behavior.  The point is to keep the recovery queue honest: a direct
managed carrier must not remain "possibly unexplored" after its current
consumer semantics have already been bounded.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from common import md_escape, write_report_json, write_text_if_changed  # noqa: E402


CATALOG_PATH = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
DEFAULT_GAME_ROOT = Path(r"D:\Program Files\Endfield Game\Endfield_Data")
DEFAULT_GAME_ASSEMBLY = DEFAULT_GAME_ROOT.parent / "GameAssembly.dll"
DEFAULT_METADATA = DEFAULT_GAME_ROOT / "il2cpp_data" / "Metadata" / "global-metadata.dat"
DEFAULT_GAMEPLAY_CONFIG = (
    ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Data"
    / "Json"
    / "GameplayConfig"
)
DEFAULT_MISSION_OPTION_AUDIT = (
    ROOT / "reports" / "story" / "recovery" / "mission_option_carrier_audit.json"
)
DEFAULT_IFIX_AUDIT = (
    ROOT / "reports" / "story" / "recovery" / "current_ifix_mission_graph_audit.json"
)
DEFAULT_OUT = (
    ROOT / "reports" / "story" / "recovery" / "managed_identity_carrier_census.json"
)
DEFAULT_MARKDOWN = (
    ROOT / "reports" / "story" / "recovery" / "managed_identity_carrier_census.md"
)

EXPECTED_GAME_ASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)
EXPECTED_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)
EXPECTED_IFIX_SHA256 = (
    "737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21"
)

OWNER_NAMES = {
    "missionid",
    "dungeonmissionid",
    "runtimemissionid",
    "questid",
}
RUNTIME_NAMES = {
    "levelscriptid",
    "bindscriptid",
    "scriptid",
    "sceneid",
    "scenename",
    "scenenumid",
}
STORY_NAMES = {
    "dialogid",
    "calldialogid",
    "radioid",
    "radioidinteractlocked",
    "cutsceneid",
    "storyid",
    "performid",
    "narrativeid",
    "remotecommid",
    "blackid",
    "snsid",
}

EXPECTED_CANDIDATES = {
    "Beyond.Gameplay.CommonTrackingPointInfoBase": {
        "owner": ["missionId"],
        "runtime": ["sceneId"],
        "story": [],
    },
    "Beyond.Gameplay.Core.FocusModeInstanceData": {
        "owner": ["missionId"],
        "runtime": [],
        "story": ["radioIdInteractLocked"],
    },
    "Beyond.Gameplay.Core.NpcRuntimeProxyExData": {
        "owner": ["missionId"],
        "runtime": [],
        "story": ["dialogId"],
    },
    "Beyond.Gameplay.Core.SubGameInstanceData": {
        "owner": ["dungeonMissionId"],
        "runtime": ["bindScriptId"],
        "story": [],
    },
    "Beyond.Gameplay.MissionOptionData": {
        "owner": ["missionId"],
        "runtime": [],
        "story": ["callDialogId"],
    },
    "Beyond.Gameplay.TeleportParam": {
        "owner": ["missionId"],
        "runtime": ["levelScriptId"],
        "story": ["performId"],
    },
    "Beyond.Gameplay.TrackingInfoBase": {
        "owner": ["m_runtimeMissionId"],
        "runtime": ["sceneId"],
        "story": [],
    },
    "Beyond.IdPickerAttribute+StringIdType": {
        "owner": ["MissionId"],
        "runtime": [],
        "story": ["DialogId", "RadioId", "RemoteCommId"],
    },
    "Beyond.PropertyKeys": {
        "owner": ["MISSION_ID", "QUEST_ID"],
        "runtime": ["LEVEL_SCRIPT_ID", "SCENE_ID", "SCRIPT_ID"],
        "story": ["CUTSCENE_ID", "DIALOG_ID", "PERFORM_ID", "RADIO_ID"],
    },
    "Proto.CS_MISSION_CLIENT_TRIGGER_DONE": {
        "owner": ["missionId_"],
        "runtime": ["sceneName_"],
        "story": [],
    },
}

EXPECTED_AUTHORED_COUNTS = {
    "focusModeRows": 14,
    "focusModeMissionRadioRows": 13,
    "focusModeUniqueRadios": 10,
    "npcProxyExRows": 2630,
    "npcProxyExMissionDialogRows": 453,
    "subGameRows": 469,
    "subGameMissionScriptRows": 20,
    "missionOptionAuthoredMatches": 0,
}

CLASSIFICATIONS = {
    "Beyond.Gameplay.CommonTrackingPointInfoBase": {
        "status": "closed_tracking_ui_context",
        "finding": (
            "missionId and sceneId belong to a map/HUD tracking point. "
            "_UpdateVisible reads sceneId to compare system maps and does not read "
            "missionId or call Story playback."
        ),
    },
    "Beyond.Gameplay.Core.FocusModeInstanceData": {
        "status": "recovered_non_owning_story_context",
        "finding": (
            "Thirteen authored rows directly pair a mission with the radio played "
            "when focus-mode interaction is locked. Mission Pipeline already emits "
            "these as context, not quest transition or chronology."
        ),
    },
    "Beyond.Gameplay.Core.NpcRuntimeProxyExData": {
        "status": "recovered_mission_shell_story_context",
        "finding": (
            "Authored rows pair a mission and dialog, but native consumers select "
            "dialogId from server-chosen proxy state and read missionId separately "
            "for mission-conflict handling. Mission Pipeline keeps the pair on the "
            "mission shell and derives no cross-row order."
        ),
    },
    "Beyond.Gameplay.Core.SubGameInstanceData": {
        "status": "recovered_runtime_shell_without_story",
        "finding": (
            "Twenty rows pair dungeonMissionId and bindScriptId. The proven native "
            "consumer uses bindScriptId for WorldChallenge cleanup; the pair supplies "
            "a SubGame runtime shell but no quest or Story playback edge."
        ),
    },
    "Beyond.Gameplay.MissionOptionData": {
        "status": "closed_mutually_exclusive_actions",
        "finding": (
            "missionId and callDialogId select mutually exclusive native action "
            "branches, and the current authored-instance census is empty."
        ),
    },
    "Beyond.Gameplay.TeleportParam": {
        "status": "closed_unpopulated_unused_mission_field",
        "finding": (
            "Current producers do not co-populate missionId and levelScriptId, and "
            "audited loading consumers never read missionId."
        ),
    },
    "Beyond.Gameplay.TrackingInfoBase": {
        "status": "closed_tracking_ui_context",
        "finding": (
            "ActivateTrackUnit passes its mission id to "
            "CommonTrackingSystem.AddMissionTrack, which writes it into a tracking "
            "point and allocates a tracker key. Deactivation removes that tracker. "
            "No Story playback consumer is present."
        ),
    },
    "Beyond.IdPickerAttribute+StringIdType": {
        "status": "not_a_carrier_enum",
        "finding": (
            "These are editor id-picker enum alternatives, not fields co-resident "
            "on a serialized or runtime object."
        ),
    },
    "Beyond.PropertyKeys": {
        "status": "not_a_carrier_static_key_catalog",
        "finding": (
            "These are independent global property-key constants. Their presence on "
            "one static type does not co-carry values on an authored object."
        ),
    },
    "Proto.CS_MISSION_CLIENT_TRIGGER_DONE": {
        "status": "closed_inactive_current_fallback_sender",
        "finding": (
            "The schema pairs missionId and sceneName, but the current fallback has "
            "no gameplay constructor/sender; the installed IFix does not add one."
        ),
    },
}

TRACKING_NATIVE_EVIDENCE = [
    {
        "symbol": "CommonTrackingPointInfoBase._UpdateVisible",
        "token": "0x0600403b",
        "address": "0x183482bb0",
        "finding": (
            "Reads sceneId at object offset +0x30, maps it through "
            "GameUtil.GetSystemMapIdByLevelId, compares the current level's system "
            "map, and never reads missionId at +0x20."
        ),
    },
    {
        "symbol": "CommonTrackingPointInfoBase.CalTrackingData",
        "token": "0x0600403c",
        "address": "0x183482860",
        "finding": (
            "Computes the HUD/map tracking position and then calls _UpdateVisible; "
            "it has no Story playback call."
        ),
    },
    {
        "symbol": "CommonTrackingSystem.AddMissionTrack",
        "token": "0x0600407e",
        "address": "0x184792ac0",
        "finding": (
            "Writes the supplied missionId to CommonTrackingPointInfoBase +0x20, "
            "allocates the tracking key at +0x18, and registers tracking maps."
        ),
    },
    {
        "symbol": "TrackingInfoBase.ActivateTrackUnit",
        "token": "0x06004c8a",
        "address": "0x184792960",
        "finding": (
            "Passes missionId to CommonTrackingSystem.AddMissionTrack and stores the "
            "returned tracker key; this is UI/navigation tracking activation."
        ),
    },
    {
        "symbol": "TrackingInfoBase.DeactivateTrackUnit",
        "token": "0x06004c8b",
        "address": "0x187375114",
        "finding": (
            "Calls CommonTrackingSystem.RemoveMissionTrack with the stored key and "
            "clears it."
        ),
    },
]


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def normalize_field_name(name: str) -> str:
    backing = re.fullmatch(r"<(.+)>k__BackingField", name)
    if backing:
        name = backing.group(1)
    name = name.strip("_")
    name = re.sub(r"^(?:m|s)_", "", name, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]", "", name.casefold())


def scan_metadata(path: Path) -> dict[str, Any]:
    catalog = load_module("managed_identity_carrier_catalog", CATALOG_PATH)
    metadata = catalog.Metadata(path)
    candidates: list[dict[str, Any]] = []
    for type_def in metadata.types:
        fields = metadata.fields_for(type_def)
        if not fields:
            continue
        field_rows = [
            {
                "name": metadata.string(field.name_index),
                "normalized": normalize_field_name(
                    metadata.string(field.name_index)
                ),
                "token": f"0x{field.token:08x}",
            }
            for field in fields
            if metadata.string(field.name_index) != "value__"
            and not metadata.string(field.name_index).endswith("FieldNumber")
        ]
        owner = [row for row in field_rows if row["normalized"] in OWNER_NAMES]
        runtime = [row for row in field_rows if row["normalized"] in RUNTIME_NAMES]
        story = [row for row in field_rows if row["normalized"] in STORY_NAMES]
        if not owner or not (runtime or story):
            continue
        full_name = metadata.type_full_name(type_def)
        classification = CLASSIFICATIONS.get(full_name, {})
        candidates.append(
            {
                "type": full_name,
                "image": metadata.image_name_by_type_index.get(type_def.index, ""),
                "typeToken": f"0x{type_def.token:08x}",
                "ownerFields": owner,
                "runtimeFields": runtime,
                "storyFields": story,
                "status": classification.get("status", "unreviewed"),
                "finding": classification.get("finding", ""),
            }
        )
    candidates.sort(key=lambda row: row["type"])
    return {
        "metadataVersion": metadata.version,
        "typeCount": len(metadata.types),
        "fieldCount": len(metadata.fields),
        "candidateCount": len(candidates),
        "objectCandidateCount": sum(
            row["status"] not in {
                "not_a_carrier_enum",
                "not_a_carrier_static_key_catalog",
            }
            for row in candidates
        ),
        "unreviewedCandidateCount": sum(
            row["status"] == "unreviewed" for row in candidates
        ),
        "candidates": candidates,
    }


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_bytes())
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def scan_authored(
    gameplay_config: Path,
    mission_option_audit: Path,
) -> dict[str, Any]:
    focus = load_json(gameplay_config / "FocusModeInstanceTable.json")
    focus_rows = focus.get("dataTable") or {}
    npc = load_json(gameplay_config / "NpcProxyExDataTable.json")
    npc_groups = npc.get("data") or {}
    npc_rows = [
        row
        for rows in npc_groups.values()
        for row in (rows or [])
        if isinstance(row, dict)
    ]
    subgame = load_json(gameplay_config / "SubGameInstanceDataTable.json")
    subgame_rows = subgame.get("dataTable") or {}
    option = load_json(mission_option_audit)
    return {
        "focusModeRows": len(focus_rows),
        "focusModeMissionRadioRows": sum(
            bool(row.get("missionId") and row.get("radioIdInteractLocked"))
            for row in focus_rows.values()
        ),
        "focusModeUniqueRadios": len(
            {
                str(row.get("radioIdInteractLocked"))
                for row in focus_rows.values()
                if row.get("radioIdInteractLocked")
            }
        ),
        "npcProxyExRows": len(npc_rows),
        "npcProxyExMissionDialogRows": sum(
            bool(row.get("missionId") and row.get("dialogId"))
            for row in npc_rows
        ),
        "subGameRows": len(subgame_rows),
        "subGameMissionScriptRows": sum(
            bool(row.get("dungeonMissionId") and row.get("bindScriptId"))
            for row in subgame_rows.values()
        ),
        "missionOptionAuthoredMatches": int(
            ((option.get("authoredInstanceSearch") or {}).get("matches") or 0)
        ),
    }


def scan_ifix(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    source = payload.get("source") or {}
    fixed = payload.get("fixedMethods") or []
    terms = (
        "CommonTrackingPointInfoBase",
        "CommonTrackingSystem",
        "TrackingInfoBase",
        "FocusModeInstanceData",
        "NpcRuntimeProxyExData",
        "SubGameInstanceData",
        "MissionOptionData",
        "TeleportParam",
        "CS_MISSION_CLIENT_TRIGGER_DONE",
    )
    relevant = [
        row
        for row in fixed
        if any(
            term.casefold() in str(row.get("signature") or "").casefold()
            for term in terms
        )
    ]
    return {
        "patchSha256": str(source.get("patchSha256") or "").casefold(),
        "fixedMethodCount": len(fixed),
        "relevantFixedMethods": relevant,
    }


def candidate_shape(report: dict[str, Any]) -> dict[str, dict[str, list[str]]]:
    return {
        row["type"]: {
            "owner": sorted(field["name"] for field in row["ownerFields"]),
            "runtime": sorted(field["name"] for field in row["runtimeFields"]),
            "story": sorted(field["name"] for field in row["storyFields"]),
        }
        for row in report["metadataCensus"]["candidates"]
    }


def validate_expected(report: dict[str, Any], *, allow_drift: bool) -> list[str]:
    errors: list[str] = []
    source = report["source"]
    if source["gameAssemblySha256"] != EXPECTED_GAME_ASSEMBLY_SHA256:
        errors.append("GameAssembly SHA256 changed")
    if source["metadataSha256"] != EXPECTED_METADATA_SHA256:
        errors.append("global-metadata SHA256 changed")
    if source["ifixSha256"] != EXPECTED_IFIX_SHA256:
        errors.append("Gameplay IFix SHA256 changed")
    if candidate_shape(report) != EXPECTED_CANDIDATES:
        errors.append("direct managed identity candidate set changed")
    if report["authoredCounts"] != EXPECTED_AUTHORED_COUNTS:
        errors.append("authored carrier counts changed")
    if report["metadataCensus"]["unreviewedCandidateCount"] != 0:
        errors.append("unreviewed direct managed identity candidate found")
    if report["installedIfix"]["relevantFixedMethods"]:
        errors.append("installed IFix now replaces a reviewed carrier method")
    if errors and not allow_drift:
        raise RuntimeError("; ".join(errors))
    return errors


def render_markdown(report: dict[str, Any]) -> str:
    census = report["metadataCensus"]
    authored = report["authoredCounts"]
    lines = [
        "# Managed identity carrier census",
        "",
        f"- Classification: `{report['classification']}`",
        f"- Direct candidate types: `{census['candidateCount']}`",
        f"- Runtime/serialized object candidates: `{census['objectCandidateCount']}`",
        f"- Unreviewed candidates: `{census['unreviewedCandidateCount']}`",
        f"- New Story bindings: `{report['storyBindingsAdded']}`",
        f"- New mission-order edges: `{report['missionOrderEdgesAdded']}`",
        "",
        "## Candidate verdicts",
        "",
        "| type | direct fields | status |",
        "|---|---|---|",
    ]
    for row in census["candidates"]:
        fields = [
            *[field["name"] for field in row["ownerFields"]],
            *[field["name"] for field in row["runtimeFields"]],
            *[field["name"] for field in row["storyFields"]],
        ]
        lines.append(
            f"| `{md_escape(row['type'])}` | "
            f"{', '.join(f'`{md_escape(field)}`' for field in fields)} | "
            f"`{md_escape(row['status'])}` |"
        )
        lines.append(f"|  | {md_escape(row['finding'])} |  |")
    lines.extend(
        [
            "",
            "## Authored rows already admitted by their proper evidence class",
            "",
            f"- FocusMode: `{authored['focusModeMissionRadioRows']}` mission/radio rows, `{authored['focusModeUniqueRadios']}` unique radios.",
            f"- NpcProxyEx: `{authored['npcProxyExMissionDialogRows']}` mission/dialog rows.",
            f"- SubGame: `{authored['subGameMissionScriptRows']}` mission/bound-script rows.",
            f"- MissionOption: `{authored['missionOptionAuthoredMatches']}` current authored instances.",
            "",
            "## Newly closed tracking pair",
            "",
        ]
    )
    for row in report["trackingNativeEvidence"]:
        lines.append(
            f"- `{md_escape(row['symbol'])}` `{row['token']}` @ "
            f"`{row['address']}`: {md_escape(row['finding'])}"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["finding"],
            "",
            report["coverage"],
            "",
        ]
    )
    if report["validationWarnings"]:
        lines.extend(
            [
                "## Drift warnings",
                "",
                *[f"- {md_escape(item)}" for item in report["validationWarnings"]],
                "",
            ]
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument(
        "--gameplay-config",
        type=Path,
        default=DEFAULT_GAMEPLAY_CONFIG,
    )
    parser.add_argument(
        "--mission-option-audit",
        type=Path,
        default=DEFAULT_MISSION_OPTION_AUDIT,
    )
    parser.add_argument("--ifix", type=Path, default=DEFAULT_IFIX_AUDIT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument(
        "--allow-drift",
        action="store_true",
        help="write warnings instead of failing on current-build drift",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for path in (
        args.gameassembly,
        args.metadata,
        args.gameplay_config,
        args.mission_option_audit,
        args.ifix,
    ):
        if not path.exists():
            raise FileNotFoundError(path)

    installed_ifix = scan_ifix(args.ifix)
    report: dict[str, Any] = {
        "schemaVersion": 1,
        "source": {
            "gameAssembly": str(args.gameassembly.resolve()),
            "gameAssemblySha256": sha256_file(args.gameassembly),
            "metadata": str(args.metadata.resolve()),
            "metadataSha256": sha256_file(args.metadata),
            "gameplayConfig": repo_rel(args.gameplay_config),
            "missionOptionAudit": repo_rel(args.mission_option_audit),
            "ifixAudit": repo_rel(args.ifix),
            "ifixSha256": installed_ifix["patchSha256"],
        },
        "metadataCensus": scan_metadata(args.metadata),
        "authoredCounts": scan_authored(
            args.gameplay_config,
            args.mission_option_audit,
        ),
        "trackingNativeEvidence": TRACKING_NATIVE_EVIDENCE,
        "installedIfix": installed_ifix,
        "classification": "all_direct_managed_identity_carriers_reviewed",
        "storyBindingsAdded": 0,
        "missionOrderEdgesAdded": 0,
        "finding": (
            "The current installed metadata contains no unreviewed direct managed "
            "mission/quest identity co-carrier. Productive FocusMode, NpcProxyEx, "
            "and SubGame pairs are already represented by their bounded context or "
            "runtime-shell evidence. MissionOption, TeleportParam, the inactive "
            "mission/scene packet, and both tracking types add no new Story ownership "
            "or order edge. The two broad apparent pairs are an editor enum and a "
            "static key catalog, not value carriers."
        ),
        "coverage": (
            "Covers direct named fields on all 63,987 current managed types, exact "
            "current authored counts for FocusMode/NpcProxyEx/SubGame/MissionOption, "
            "the installed GameAssembly tracking consumers, and the complete "
            "30-target Gameplay IFix list. Nested object graphs, indirect/reflection/"
            "XLua construction, opaque server-only state, unexported asset kinds, "
            "future patches, and future builds remain outside the bound."
        ),
        "validationWarnings": [],
    }
    report["validationWarnings"] = validate_expected(
        report,
        allow_drift=args.allow_drift,
    )
    write_report_json(args.out, report)
    write_text_if_changed(args.markdown, render_markdown(report))
    print(
        "managed identity carrier census: "
        f"{report['metadataCensus']['candidateCount']} direct types, "
        f"{report['metadataCensus']['unreviewedCandidateCount']} unreviewed, "
        "0 new Story bindings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
