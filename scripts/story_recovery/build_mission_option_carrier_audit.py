#!/usr/bin/env python3
"""Build the current MissionOptionData carrier/instance audit.

This is an offline, rebuild-scoped audit. It verifies the pinned native method
bodies, scans every exported source surface that can preserve the managed type
or field names, and optionally streams installed Lua without launching the
game.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import (  # noqa: E402
    resolve_installed_game_data_root,
    sha256_file,
)

MAPPER_PATH = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
DEFAULT_GAME_ROOT = resolve_installed_game_data_root()
DEFAULT_GAME_ASSEMBLY = DEFAULT_GAME_ROOT.parent / "GameAssembly.dll"
DEFAULT_METADATA = DEFAULT_GAME_ROOT / "il2cpp_data" / "Metadata" / "global-metadata.dat"
DEFAULT_CLI = (
    ROOT
    / "tools"
    / "AnimeStudio"
    / "AnimeStudio.CLI"
    / "bin"
    / "Release"
    / "net9.0-windows"
    / "AnimeStudio.CLI.exe"
)
DEFAULT_JSON = ROOT / "reports" / "story" / "recovery" / "mission_option_carrier_audit.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "story" / "recovery" / "mission_option_carrier_audit.md"
EXPECTED_GAME_ASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)
EXPECTED_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)
SEARCH_TERMS = (b"MissionOptionData", b"callDialogId")
NATIVE_METHODS = {
    "MissionOptionData.get_optionHandlerType": {
        "token": "0x06003a25",
        "va": 0x1872AFD28,
        "bytes": 80,
        "sha256": "e59cb9b16bbf79f2dc73e37c651ec8d1bee4f12c219ddbb31c63c4194bfb7ed4",
        "fallbackPatchId": "0x442d",
    },
    "MissionOptionHandler.OnSelectWhenDialogEnd": {
        "token": "0x0600fa19",
        "va": 0x186E50F74,
        "bytes": 144,
        "sha256": "193af6ad72516d92d61ba55a958d215aea48e965044a9c195f9df91a168532d9",
        "fallbackPatchId": "0xc338",
    },
    "MissionOptionHandler.OnSelectWhenOptionEnd": {
        "token": "0x0600fa18",
        "va": 0x186E51004,
        "bytes": 144,
        "sha256": "08ab6fb67739b62cc795148f7d5705863924597fdae9478c4451114bc72d23b8",
        "fallbackPatchId": "0xc336",
    },
    "MissionOptionHandler._DoAction": {
        "token": "0x0600fa1a",
        "va": 0x186E510A4,
        "bytes": 252,
        "sha256": "ed1a5f11a3e0659fb0c16bc0ba42ce2792e86e146fb0cf6d2d85fa2f044b6e17",
        "fallbackPatchId": "0xc337",
    },
}


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module




def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path.resolve())


def scan_jsonl_indexes(paths: Iterable[Path]) -> dict[str, Any]:
    files = 0
    rows = 0
    byte_count = 0
    matches: list[dict[str, Any]] = []
    sources = []
    for path in paths:
        if not path.exists():
            continue
        files += 1
        size = path.stat().st_size
        byte_count += size
        sources.append({"path": repo_rel(path), "bytes": size})
        with path.open("rb") as handle:
            for line_number, line in enumerate(handle, start=1):
                rows += 1
                found = [
                    term.decode("ascii")
                    for term in SEARCH_TERMS
                    if term in line
                ]
                if found:
                    matches.append(
                        {
                            "path": repo_rel(path),
                            "line": line_number,
                            "terms": found,
                        }
                    )
    return {
        "sourceFiles": files,
        "rows": rows,
        "bytes": byte_count,
        "sources": sources,
        "matches": matches,
    }


def scan_text_assets(paths: Iterable[Path]) -> dict[str, Any]:
    files = 0
    script_bytes = 0
    decode_failures = []
    matches = []
    for root in paths:
        if not root.exists():
            continue
        for path in root.glob("*.json"):
            files += 1
            try:
                outer = json.loads(path.read_text(encoding="utf-8"))
                raw = base64.b64decode(str(outer.get("m_Script") or ""))
            except (OSError, ValueError) as exc:
                decode_failures.append({"path": repo_rel(path), "error": str(exc)})
                continue
            script_bytes += len(raw)
            found = [
                term.decode("ascii")
                for term in SEARCH_TERMS
                if term in raw
            ]
            if found:
                matches.append(
                    {
                        "path": repo_rel(path),
                        "assetName": outer.get("m_Name") or outer.get("Name"),
                        "terms": found,
                    }
                )
    return {
        "files": files,
        "decodedScriptBytes": script_bytes,
        "decodeFailures": decode_failures,
        "matches": matches,
    }


def scan_structured_json(paths: Iterable[Path]) -> dict[str, Any]:
    files = 0
    byte_count = 0
    matches = []
    for root in paths:
        if not root.exists():
            continue
        for path in root.rglob("*.json"):
            files += 1
            raw = path.read_bytes()
            byte_count += len(raw)
            found = [
                term.decode("ascii")
                for term in SEARCH_TERMS
                if term in raw
            ]
            if found:
                matches.append({"path": repo_rel(path), "terms": found})
    return {
        "files": files,
        "bytes": byte_count,
        "matches": matches,
    }


def scan_lua(cli: Path, game_root: Path) -> dict[str, Any]:
    command = [
        str(cli),
        "stream",
        "--streaming-assets",
        str(game_root / "Persistent"),
        "--fallback-assets",
        str(game_root / "StreamingAssets"),
        "--block-type",
        "lua",
        "--file-regex",
        ".*",
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    files = 0
    byte_count = 0
    matches = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        raw = base64.b64decode(str(payload.get("dataBase64") or ""))
        files += 1
        byte_count += len(raw)
        found = [
            term.decode("ascii")
            for term in SEARCH_TERMS
            if term in raw
        ]
        if found:
            matches.append(
                {
                    "blockType": payload.get("blockType"),
                    "fileName": payload.get("fileName"),
                    "terms": found,
                }
            )
    return {
        "files": files,
        "bytes": byte_count,
        "matches": matches,
        "stderr": result.stderr.strip(),
    }


def verify_native(game_assembly: Path) -> list[dict[str, Any]]:
    mapper = load_module("mission_option_audit_mapper", MAPPER_PATH)
    pe = mapper.PeImage(game_assembly)
    rows = []
    for name, expected in NATIVE_METHODS.items():
        raw = pe.bytes_at_va(expected["va"], expected["bytes"])
        actual_hash = hashlib.sha256(raw).hexdigest()
        if actual_hash != expected["sha256"]:
            raise RuntimeError(
                f"{name} body hash changed: expected {expected['sha256']}, got {actual_hash}"
            )
        rows.append(
            {
                "symbol": name,
                "token": expected["token"],
                "address": f"0x{expected['va']:x}",
                "bodyBytes": expected["bytes"],
                "bodySha256": actual_hash,
                "fallbackPatchId": expected["fallbackPatchId"],
            }
        )
    return rows


def render_markdown(payload: dict[str, Any]) -> str:
    sources = payload["authoredInstanceSearch"]
    return "\n".join(
        [
            "# MissionOptionData carrier audit",
            "",
            f"- GameAssembly SHA-256: `{payload['source']['gameAssemblySha256']}`",
            f"- Metadata SHA-256: `{payload['source']['metadataSha256']}`",
            f"- Exported MonoBehaviour rows searched: `{sources['monoBehaviourIndexes']['rows']}`",
            f"- Exported MonoBehaviour bytes searched: `{sources['monoBehaviourIndexes']['bytes']}`",
            f"- TextAsset payloads decoded: `{sources['textAssets']['files']}`",
            f"- TextAsset script bytes searched: `{sources['textAssets']['decodedScriptBytes']}`",
            f"- Structured JSON files searched: `{sources['structuredJson']['files']}`",
            f"- Installed Lua files searched: `{sources['installedLua']['files']}`",
            f"- Authored-instance matches: `{payload['summary']['authoredInstanceMatches']}`",
            f"- Story bindings added: `{payload['summary']['storyBindingsAdded']}`",
            "",
            "## Native result",
            "",
            "`MissionOptionData` contains `missionId` and `callDialogId`, but the "
            "current fallback does not use them as a bridge. "
            "`MissionOptionHandler._DoAction` checks non-empty `callDialogId` first, "
            "calls `DialogManager.StopAndPlayDialogById`, and jumps to the end. Only "
            "the empty-dialog branch checks `missionId` and calls "
            "`MissionSystem.AcceptMission`.",
            "",
            "The two fields are therefore mutually exclusive action alternatives in "
            "the current native path. Co-carriage alone proves neither mission-to-dialog "
            "causality nor Story ownership/order.",
            "",
            "## Current authored-data boundary",
            "",
            "No exact type/field occurrence exists in the complete exported "
            "MonoBehaviour object indexes, decoded TextAssets, structured JsonData "
            "roots, or installed VFS Lua corpus. The current installed 30-target IFix "
            "payload replaces none of the four audited methods.",
            "",
            "Reflection, dynamically constructed names, server-only construction, "
            "unexported object kinds, future IFix, and future builds remain outside "
            "this bounded result.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--skip-lua", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    game_hash = sha256_file(args.gameassembly)
    metadata_hash = sha256_file(args.metadata)
    if game_hash != EXPECTED_GAME_ASSEMBLY_SHA256:
        raise RuntimeError(
            f"GameAssembly hash changed: expected {EXPECTED_GAME_ASSEMBLY_SHA256}, got {game_hash}"
        )
    if metadata_hash != EXPECTED_METADATA_SHA256:
        raise RuntimeError(
            f"metadata hash changed: expected {EXPECTED_METADATA_SHA256}, got {metadata_hash}"
        )

    anime_root = ROOT / "export_full" / "recovered" / "AnimeStudio-cli"
    mono_indexes = [
        anime_root
        / source
        / "object_index"
        / "parts"
        / f"{source}_animestudio_json_by_type_MonoBehaviour.jsonl"
        for source in ("StreamingAssets", "Persistent")
    ]
    text_roots = [
        anime_root / source / "json_by_type" / "TextAsset"
        for source in ("StreamingAssets", "Persistent")
    ]
    structured_roots = [
        ROOT / "export_full" / "structured" / source / "Data" / "Json"
        for source in ("StreamingAssets", "Persistent")
    ]
    lua_result = (
        {
            "files": 0,
            "bytes": 0,
            "matches": [],
            "skipped": True,
        }
        if args.skip_lua
        else scan_lua(args.cli, args.game_root)
    )
    authored = {
        "monoBehaviourIndexes": scan_jsonl_indexes(mono_indexes),
        "textAssets": scan_text_assets(text_roots),
        "structuredJson": scan_structured_json(structured_roots),
        "installedLua": lua_result,
    }
    authored_matches = sum(
        len(result["matches"])
        for result in authored.values()
    )
    if authored_matches:
        raise RuntimeError(
            f"found {authored_matches} MissionOptionData authored-instance candidates; "
            "inspect before publishing the bounded-negative report"
        )

    ifix_path = ROOT / "reports" / "story" / "recovery" / "current_ifix_mission_graph_audit.json"
    ifix = json.loads(ifix_path.read_text(encoding="utf-8"))
    relevant_names = (
        "MissionOptionData",
        "MissionOptionHandler",
        "DialogUtils::AddOptionData",
        "DialogManager::AddOptionData",
    )
    ifix_matches = [
        row
        for row in ifix.get("fixedMethods", [])
        if any(name in str(row.get("signature") or "") for name in relevant_names)
    ]
    if ifix_matches:
        raise RuntimeError(
            "current IFix now replaces a MissionOption path; inspect before publishing"
        )

    payload = {
        "schemaVersion": 1,
        "source": {
            "gameAssembly": str(args.gameassembly.resolve()),
            "gameAssemblySha256": game_hash,
            "metadata": str(args.metadata.resolve()),
            "metadataSha256": metadata_hash,
        },
        "managedCarrier": {
            "type": "Beyond.Gameplay.MissionOptionData",
            "typeToken": "0x02000986",
            "baseType": "Beyond.Gameplay.DialogTreeOptionBase",
            "fields": [
                {"name": "missionId", "token": "0x04003bcd", "type": "string", "offset": "0x68"},
                {"name": "callDialogId", "token": "0x04003bce", "type": "string", "offset": "0x70"},
            ],
            "handlerType": {
                "enum": "Beyond.Gameplay.DialogEnums+OptionHandlerType",
                "value": 3,
                "name": "Mission",
            },
            "exactTypedConsumer": "Beyond.Gameplay.Core.MissionOptionHandler._DoAction",
        },
        "nativeMethods": verify_native(args.gameassembly),
        "nativeControlFlow": {
            "callDialogBranch": {
                "condition": "callDialogId is non-empty",
                "call": "DialogManager.StopAndPlayDialogById(callDialogId)",
                "callAddress": "0x186e1a67c",
                "effect": "jumps to method end after playback call",
            },
            "missionBranch": {
                "condition": "callDialogId is empty and missionId is non-empty",
                "call": "MissionSystem.AcceptMission(missionId)",
                "callAddress": "0x1873b7b48",
            },
            "finding": (
                "callDialogId and missionId are mutually exclusive action alternatives "
                "in the current native fallback; co-carriage does not create a "
                "mission-to-dialog edge"
            ),
        },
        "wholeBinaryDirectCallCensus": {
            "MissionOptionData::.ctor": 0,
            "MissionOptionData::get_optionHandlerType": 0,
            "MissionOptionHandler::_DoAction": 2,
            "MissionOptionHandler::_DoActionCallers": [
                "MissionOptionHandler.OnSelectWhenDialogEnd",
                "MissionOptionHandler.OnSelectWhenOptionEnd",
            ],
            "DialogUtils::AddOptionData": 2,
            "DialogUtils::AddOptionDataCallers": [
                "NpcProxy._RefreshExOption",
                "NpcProxy._RefreshExOption",
            ],
            "DialogManager::AddOptionData": 0,
            "boundary": (
                "Complete E8 rel32 census over GameAssembly .text/il2cpp sections; "
                "virtual, delegate, reflection, XLua, and IFix dispatch are not direct calls."
            ),
        },
        "authoredInstanceSearch": authored,
        "installedPatch": {
            "source": ifix["source"]["label"],
            "sha256": ifix["source"]["patchSha256"],
            "signatureTargetCount": ifix["format"]["fixedMethodCount"],
            "relevantMethodMatches": ifix_matches,
        },
        "summary": {
            "authoredInstanceMatches": authored_matches,
            "storyBindingsAdded": 0,
            "classification": "schema_only_current_export_absent",
            "confidence": "native_proven_bounded",
        },
        "boundary": (
            "Reflection, dynamically constructed names, server-only construction, "
            "unexported object kinds, future IFix, and future builds remain possible. "
            "The current fields must not be promoted to Story ownership or order."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "report": repo_rel(args.out),
                "monoBehaviourRows": authored["monoBehaviourIndexes"]["rows"],
                "textAssets": authored["textAssets"]["files"],
                "structuredJsonFiles": authored["structuredJson"]["files"],
                "luaFiles": authored["installedLua"]["files"],
                "authoredInstanceMatches": authored_matches,
                "storyBindingsAdded": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
