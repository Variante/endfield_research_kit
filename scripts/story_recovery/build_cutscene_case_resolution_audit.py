#!/usr/bin/env python3
"""Prove whether a case-mismatched Lua cutscene ID can resolve natively.

This is a build-scoped, fail-closed audit.  It follows the exact installed
GameAssembly call chain from GameAction playback to StringPathHash lookup and
combines it with the maintained Lua consumer and IFix audits.  The reviewed
instruction landmarks are pinned to one metadata/GameAssembly fingerprint;
after a game update the script refuses to carry the conclusion forward until
the native chain is reviewed again.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MAPPER_PATH = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
DEFAULT_GAME_ROOT = Path(os.environ.get("ENDFIELD_GAME_ROOT", r"D:\Program Files\Endfield Game"))
DEFAULT_GAMEASSEMBLY = DEFAULT_GAME_ROOT / "GameAssembly.dll"
DEFAULT_METADATA = (
    DEFAULT_GAME_ROOT
    / "Endfield_Data"
    / "il2cpp_data"
    / "Metadata"
    / "global-metadata.dat"
)
DEFAULT_LUA_AUDIT = ROOT / "reports" / "mission_order" / "lua_consumer_reference_audit.json"
DEFAULT_IFIX_AUDIT = ROOT / "reports" / "story" / "recovery" / "current_ifix_mission_graph_audit.json"
DEFAULT_OUT = ROOT / "reports" / "story" / "recovery" / "cutscene_case_resolution_audit.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "story" / "recovery" / "cutscene_case_resolution_audit.md"

REVIEWED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
REVIEWED_GAMEASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
REVIEWED_IFIX_SHA256 = "737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21"

LUA_LITERAL = "Cutscene_e0m0_1"
CANONICAL_STORY_KEY = "cutscene_e0m0_1"

# Current-build method definitions and reviewed executable entry points.
METHODS: dict[str, dict[str, Any]] = {
    "gameAction": {
        "index": 32855,
        "type": "Beyond.Gameplay.Actions.GameAction",
        "method": "PlayCutsceneAndGetHandle",
        "token": "0x06008058",
        "va": 0x1875E6AAC,
    },
    "playCutscene": {
        "index": 61163,
        "type": "Beyond.Gameplay.Core.CutsceneManager",
        "method": "PlayCutscene",
        "token": "0x0600eeec",
        "va": 0x186DB94CC,
    },
    "checkCanPlay": {
        "index": 61164,
        "type": "Beyond.Gameplay.Core.CutsceneManager",
        "method": "CheckCanPlay",
        "token": "0x0600eeed",
        "va": 0x186DB8A94,
    },
    "genderedId": {
        "index": 6530,
        "type": "Beyond.Gameplay.NarrativeUtils",
        "method": "GetGenderedCutsceneId",
        "token": "0x06001983",
        "va": 0x1835FD630,
    },
    "getCinematicData": {
        "index": 60787,
        "type": "Beyond.Gameplay.Core.CinematicTimelineManagerBase",
        "method": "TryGetCinematicData",
        "token": "0x0600ed74",
        "va": 0x1848511C0,
        "generic": True,
    },
    "loadByName": {
        "index": 60785,
        "type": "Beyond.Gameplay.Core.CinematicTimelineManagerBase",
        "method": "_TryLoadCutsceneDataByName",
        "token": "0x0600ed72",
        "va": 0x184495B60,
    },
    "cachedTryLoad": {
        "index": 296332,
        "type": "Beyond.Resource.CachedPathAssetLoader",
        "method": "TryLoad",
        "token": "0x06000f27",
        "va": 0x18304BB40,
        "generic": True,
    },
    "cachedTypedTryLoad": {
        "index": 296335,
        "type": "Beyond.Resource.CachedPathAssetLoader",
        "method": "TryLoad",
        "token": "0x06000f2a",
        "va": 0x18304BBD0,
    },
    "stringPathHashCtor": {
        "index": 296749,
        "type": "Beyond.Resource.StringPathHash",
        "method": ".ctor",
        "token": "0x060010c8",
        "va": 0x1868C15BC,
    },
}

RAW_STRING_HASH_VA = 0x182F75F50

CALL_EDGES = (
    ("gameAction", "playCutscene"),
    ("playCutscene", "checkCanPlay"),
    ("checkCanPlay", "genderedId"),
    ("checkCanPlay", "getCinematicData"),
    ("getCinematicData", "loadByName"),
    ("loadByName", "cachedTryLoad"),
    ("cachedTryLoad", "cachedTypedTryLoad"),
)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_mapper() -> Any:
    spec = importlib.util.spec_from_file_location("endfield_cutscene_case_mapper", MAPPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load IL2CPP mapper: {MAPPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def method_pointer(
    row: dict[str, Any],
    *,
    pointers_by_image: dict[str, list[int]],
    ranges: dict[str, dict[str, int]],
    generic_index: dict[int, list[dict[str, Any]]],
) -> tuple[int, str, list[dict[str, Any]]]:
    method_index = int(row["methodIndex"])
    image = str(row.get("image") or "")
    if not image:
        image = next(
            (
                name
                for name, image_range in ranges.items()
                if int(image_range["methodStart"]) <= method_index
                < int(image_range["methodEnd"])
            ),
            "",
        )
    if not image:
        raise RuntimeError(f"unable to resolve codegen image for method {method_index}")
    image_range = ranges[image]
    pointer = pointers_by_image[image][method_index - image_range["methodStart"]]
    if pointer:
        return pointer, "codegen_module", []
    candidates = load_mapper_once().generic_body_candidates(
        generic_index, int(row["methodIndex"])
    )
    if len(candidates) != 1:
        raise RuntimeError(
            f"{row['type']}.{row['method']} has {len(candidates)} generic body candidates"
        )
    return (
        int(candidates[0]["methodPointerVa"], 16),
        "generic_method_pointer",
        list(candidates[0].get("instantiations") or []),
    )


_MAPPER: Any | None = None


def load_mapper_once() -> Any:
    global _MAPPER
    if _MAPPER is None:
        _MAPPER = load_mapper()
    return _MAPPER


def decoded_text(mapper: Any, pe: Any, va: int, size: int) -> list[str]:
    return [
        str(row.get("text") or "")
        for row in mapper.decode_x64_subset(pe.bytes_at_va(va, size), va, stop_offset=size)
    ]


def call_targets(mapper: Any, pe: Any, va: int, size: int) -> list[int]:
    targets: list[int] = []
    for text in decoded_text(mapper, pe, va, size):
        match = re.fullmatch(r"call 0x([0-9a-f]+)", text)
        if match:
            targets.append(int(match.group(1), 16))
    return targets


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    for path in (args.gameassembly, args.metadata, args.lua_audit, args.ifix_audit):
        if not path.is_file():
            raise FileNotFoundError(path)

    metadata_sha = sha256_path(args.metadata)
    gameassembly_sha = sha256_path(args.gameassembly)
    if metadata_sha != REVIEWED_METADATA_SHA256:
        raise RuntimeError(
            "metadata fingerprint changed; review the native cutscene resolver before "
            f"updating the pinned hash ({metadata_sha})"
        )
    if gameassembly_sha != REVIEWED_GAMEASSEMBLY_SHA256:
        raise RuntimeError(
            "GameAssembly fingerprint changed; review the native cutscene resolver before "
            f"updating the pinned hash ({gameassembly_sha})"
        )

    lua_audit = load_json(args.lua_audit)
    lua_rows = [
        row
        for row in (lua_audit.get("gameActionAudit") or {}).get("storyPlaybackCalls") or []
        if row.get("resolvedLiteral") == LUA_LITERAL
        and row.get("canonicalStoryKey") == CANONICAL_STORY_KEY
    ]
    if len(lua_rows) != 1 or lua_rows[0].get("registryStatus") != "case_mismatch_registry_match":
        raise RuntimeError("expected one exact Lua case-mismatch playback row")

    ifix_audit = load_json(args.ifix_audit)
    ifix_sha = str((ifix_audit.get("source") or {}).get("patchSha256") or "").lower()
    if ifix_sha != REVIEWED_IFIX_SHA256:
        raise RuntimeError(
            "IFix fingerprint changed; rebuild and review the current IFix audit before "
            "carrying forward the case-resolution conclusion"
        )

    mapper = load_mapper_once()
    catalog_module = mapper.load_catalog_module()
    md = catalog_module.Metadata(args.metadata)
    pe = mapper.PeImage(args.gameassembly)
    code_registration = mapper.DEFAULT_CODE_REGISTRATION
    metadata_registration = mapper.DEFAULT_METADATA_REGISTRATION
    modules = mapper.parse_codegen_modules(pe, code_registration)
    ranges = mapper.image_method_ranges(md)
    pointers_by_image, method_by_pointer = mapper.build_pointer_indexes(pe, md, modules, ranges)
    generic_index = mapper.build_generic_method_index(
        pe, md, code_registration, metadata_registration
    )
    for pointer, rows in generic_index.items():
        method_by_pointer.setdefault(pointer, rows)

    method_rows: dict[str, dict[str, Any]] = {}
    for label, expected in METHODS.items():
        row = mapper.method_signature(md, int(expected["index"]))
        for field in ("type", "method", "token"):
            if row.get(field) != expected[field]:
                raise RuntimeError(
                    f"{label} metadata drift: expected {field}={expected[field]!r}, "
                    f"found {row.get(field)!r}"
                )
        pointer, pointer_source, specs = method_pointer(
            row,
            pointers_by_image=pointers_by_image,
            ranges=ranges,
            generic_index=generic_index,
        )
        if pointer != int(expected["va"]):
            raise RuntimeError(
                f"{label} entry point drift: expected 0x{int(expected['va']):x}, "
                f"found 0x{pointer:x}"
            )
        method_rows[label] = {
            **row,
            "entryPoint": f"0x{pointer:x}",
            "pointerSource": pointer_source,
            "methodSpecs": specs,
        }

    all_pointers = sorted({
        pointer
        for pointers in pointers_by_image.values()
        for pointer in pointers
        if pointer
    } | set(generic_index))
    call_evidence: list[dict[str, Any]] = []
    for caller_label, callee_label in CALL_EDGES:
        caller_va = int(METHODS[caller_label]["va"])
        callee_va = int(METHODS[callee_label]["va"])
        size, next_pointer = mapper.estimate_scan_size(caller_va, all_pointers, 8192)
        targets = call_targets(mapper, pe, caller_va, size)
        if callee_va not in targets:
            raise RuntimeError(f"missing reviewed edge {caller_label} -> {callee_label}")
        call_evidence.append({
            "caller": caller_label,
            "callee": callee_label,
            "callerEntryPoint": f"0x{caller_va:x}",
            "calleeEntryPoint": f"0x{callee_va:x}",
            "scanBytes": size,
            "nextEntryPoint": f"0x{next_pointer:x}" if next_pointer else None,
        })

    gender_text = decoded_text(mapper, pe, METHODS["genderedId"]["va"], 0x140)
    gender_landmarks = {
        "originalIdSaved": "mov rdi, rcx" in gender_text,
        "originalIdPassedIntoGenderCandidate": "mov rdx, rdi" in gender_text,
        "originalIdReturnedOnFallback": "mov rax, rdi" in gender_text,
        "caseConversionCalls": [
            row
            for row in gender_text
            if any(term in row.lower() for term in ("tolower", "toupper", "ordinalignorecase"))
        ],
    }
    if not all((
        gender_landmarks["originalIdSaved"],
        gender_landmarks["originalIdPassedIntoGenderCandidate"],
        gender_landmarks["originalIdReturnedOnFallback"],
    )) or gender_landmarks["caseConversionCalls"]:
        raise RuntimeError("GetGenderedCutsceneId instruction landmarks changed")

    hash_ctor_targets = call_targets(
        mapper, pe, METHODS["stringPathHashCtor"]["va"], 0x58
    )
    typed_loader_targets = call_targets(
        mapper, pe, METHODS["cachedTypedTryLoad"]["va"], 0x170
    )
    if RAW_STRING_HASH_VA not in hash_ctor_targets:
        raise RuntimeError("StringPathHash(string) no longer calls the reviewed raw-string hash")
    if RAW_STRING_HASH_VA not in typed_loader_targets:
        raise RuntimeError("CachedPathAssetLoader.TryLoad no longer hashes its input path directly")

    hash_text = decoded_text(mapper, pe, RAW_STRING_HASH_VA, 0x160)
    hash_landmarks = {
        "originalStringSaved": "mov rbx, rcx" in hash_text,
        "originalStringPassedToHash": "mov rcx, rbx" in hash_text,
        "hashResultReturned": "mov rax, rdi" in hash_text,
        "caseConversionCalls": [
            row
            for row in hash_text
            if any(term in row.lower() for term in ("tolower", "toupper", "ordinalignorecase"))
        ],
    }
    if not all((
        hash_landmarks["originalStringSaved"],
        hash_landmarks["originalStringPassedToHash"],
        hash_landmarks["hashResultReturned"],
    )) or hash_landmarks["caseConversionCalls"]:
        raise RuntimeError("StringPathHash instruction landmarks changed")

    protected_signatures = {
        f"{row['type']}::{row['method']}"
        for row in method_rows.values()
    }
    ifix_hits = [
        row
        for row in ifix_audit.get("fixedMethods") or []
        if any(str(row.get("signature") or "").startswith(prefix) for prefix in protected_signatures)
    ]
    if ifix_hits:
        raise RuntimeError("current IFix replaces one or more reviewed resolver methods")

    return {
        "schemaVersion": 1,
        "source": {
            "gameAssembly": str(args.gameassembly),
            "gameAssemblyBytes": args.gameassembly.stat().st_size,
            "gameAssemblySha256": gameassembly_sha,
            "metadata": str(args.metadata),
            "metadataBytes": args.metadata.stat().st_size,
            "metadataSha256": metadata_sha,
            "luaAudit": str(args.lua_audit),
            "ifixAudit": str(args.ifix_audit),
            "ifixPatchSha256": ifix_sha,
        },
        "luaPlayback": lua_rows[0],
        "canonicalRegistryKey": CANONICAL_STORY_KEY,
        "methodChain": method_rows,
        "callEvidence": call_evidence,
        "instructionEvidence": {
            "getGenderedCutsceneId": gender_landmarks,
            "stringPathHashStringConstructor": {
                "entryPoint": f"0x{METHODS['stringPathHashCtor']['va']:x}",
                "rawStringHashEntryPoint": f"0x{RAW_STRING_HASH_VA:x}",
                "directCallConfirmed": True,
            },
            "cachedPathAssetLoaderTypedTryLoad": {
                "entryPoint": f"0x{METHODS['cachedTypedTryLoad']['va']:x}",
                "rawStringHashEntryPoint": f"0x{RAW_STRING_HASH_VA:x}",
                "directCallConfirmed": True,
            },
            "rawStringHash": {
                "entryPoint": f"0x{RAW_STRING_HASH_VA:x}",
                **hash_landmarks,
            },
        },
        "ifixBoundary": {
            "fixedMethodCount": len(ifix_audit.get("fixedMethods") or []),
            "reviewedResolverMatches": ifix_hits,
        },
        "conclusion": {
            "caseResolution": "case_sensitive",
            "luaLiteral": LUA_LITERAL,
            "canonicalStoryKey": CANONICAL_STORY_KEY,
            "literalResolvesToCanonicalKey": False,
            "graphAction": "reject_case_mismatch_no_playback_binding",
            "ownershipAction": "none",
            "reason": (
                "The original Lua spelling is preserved through gender selection and "
                "resource-path construction, then converted directly to StringPathHash "
                "without case folding. The mismatched spelling therefore cannot prove "
                "playback of the lowercase registry key in this build."
            ),
        },
        "boundary": (
            "This rejects one playback edge for the reviewed installed build. It does not "
            "infer mission ownership, and it must be rerun and reviewed after any binary, "
            "metadata, Lua-audit, or IFix fingerprint changes."
        ),
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    source = report["source"]
    conclusion = report["conclusion"]
    lines = [
        "# Cutscene case-resolution audit",
        "",
        f"- Lua literal: `{conclusion['luaLiteral']}`",
        f"- Canonical Story key: `{conclusion['canonicalStoryKey']}`",
        f"- Native case resolution: **{conclusion['caseResolution']}**",
        f"- Playback binding: **{conclusion['graphAction']}**",
        f"- Mission ownership: **{conclusion['ownershipAction']}**",
        "",
        "## Build scope",
        "",
        f"- GameAssembly SHA-256: `{source['gameAssemblySha256']}`",
        f"- Metadata SHA-256: `{source['metadataSha256']}`",
        f"- IFix patch SHA-256: `{source['ifixPatchSha256']}`",
        "",
        "## Proven native chain",
        "",
    ]
    for edge in report["callEvidence"]:
        caller = report["methodChain"][edge["caller"]]
        callee = report["methodChain"][edge["callee"]]
        lines.append(
            f"- `{caller['type']}.{caller['method']}` `{edge['callerEntryPoint']}` "
            f"calls `{callee['type']}.{callee['method']}` `{edge['calleeEntryPoint']}`."
        )
    lines.extend([
        "",
        "The final typed loader converts the constructed path directly through "
        "`StringPathHash(string)`. The reviewed hash path receives and hashes the "
        "original string; neither it nor `GetGenderedCutsceneId` performs case folding.",
        "",
        "## Conclusion",
        "",
        conclusion["reason"],
        "",
        report["boundary"],
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAMEASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--lua-audit", type=Path, default=DEFAULT_LUA_AUDIT)
    parser.add_argument("--ifix-audit", type=Path, default=DEFAULT_IFIX_AUDIT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(args.markdown, report)
    print(f"case resolution: {report['conclusion']['caseResolution']}")
    print(f"graph action: {report['conclusion']['graphAction']}")
    print(f"wrote JSON: {args.out}")
    print(f"wrote Markdown: {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
