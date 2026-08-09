#!/usr/bin/env python3
"""Recover Timeline-embedded Story presentation from general runtime shape.

The audit discovers serialized text-carrying PlayableAsset families from the
installed IL2CPP metadata, validates their common CreatePlayable/localization
call chain in the installed GameAssembly, and then scans exported Timeline
objects by exact PathID references. It contains no Story-key, mission, dialog,
Timeline, CAB, or PathID allowlist.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools" / "endfield-il2cpp"
for import_root in (ROOT, ROOT / "scripts"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))
DEFAULT_GAMEASSEMBLY = Path(r"D:\Program Files\Endfield Game\GameAssembly.dll")
DEFAULT_METADATA = (
    Path(r"D:\Program Files\Endfield Game\Endfield_Data")
    / "il2cpp_data" / "Metadata" / "global-metadata.dat"
)
DEFAULT_STORY_ROOT = ROOT / "webui" / "data" / "lang" / "CN" / "conv"
DEFAULT_JSON = (
    ROOT / "reports" / "story" / "recovery"
    / "timeline_embedded_story_runtime_audit.json"
)
DEFAULT_MD = DEFAULT_JSON.with_suffix(".md")


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def resolved_targets(row: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (str(target.get("type") or ""), str(target.get("method") or ""))
        for call in row.get("directCalls") or []
        for target in call.get("resolved") or []
    }


def validation_failure(
    gate: str,
    expected: Any,
    actual: Any,
    source: str,
) -> dict[str, Any]:
    return {
        "validator": "timeline_embedded_story_runtime",
        "gate": gate,
        "sourceFile": source,
        "expected": expected,
        "actual": actual,
    }


def analyze_runtime_contract(
    catalog: dict[str, Any],
    body_map: dict[str, Any],
) -> dict[str, Any]:
    """Find all text PlayableAsset families by fields/methods/call shape."""
    body_rows = body_map.get("bodyTargets") or []
    body_by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in body_rows:
        body_by_key[(str(row.get("type") or ""), str(row.get("method") or ""))].append(row)

    candidates = []
    for row in catalog.get("matchedTypes") or []:
        full_name = str(row.get("fullName") or "")
        if not full_name.endswith("PlayableAsset"):
            continue
        fields = sorted({
            str(field.get("name") or "")
            for field in row.get("fields") or []
            if re.fullmatch(r"_textId(?:_\d+)?", str(field.get("name") or ""))
        })
        methods = {str(method.get("name") or "") for method in row.get("methods") or []}
        if fields and {"CreatePlayable", "_GetText"}.issubset(methods):
            candidates.append((row, fields))

    failures: list[dict[str, Any]] = []
    families: list[dict[str, Any]] = []
    if not candidates:
        failures.append(validation_failure(
            "structural_type_discovery",
            "one_or_more PlayableAsset types with _textId field(s), CreatePlayable, and _GetText",
            0,
            "global-metadata.dat",
        ))

    for type_row, text_fields in sorted(candidates, key=lambda item: item[0]["fullName"]):
        full_name = str(type_row["fullName"])
        create_rows = body_by_key.get((full_name, "CreatePlayable"), [])
        get_text_rows = body_by_key.get((full_name, "_GetText"), [])
        if len(create_rows) != 1 or create_rows[0].get("mappingStatus") != "mapped":
            failures.append(validation_failure(
                "create_playable_body",
                "one mapped CreatePlayable",
                len([row for row in create_rows if row.get("mappingStatus") == "mapped"]),
                full_name,
            ))
            continue
        if len(get_text_rows) != 1 or get_text_rows[0].get("mappingStatus") != "mapped":
            failures.append(validation_failure(
                "localization_body",
                "one mapped _GetText",
                len([row for row in get_text_rows if row.get("mappingStatus") == "mapped"]),
                full_name,
            ))
            continue

        create_targets = resolved_targets(create_rows[0])
        get_text_targets = resolved_targets(get_text_rows[0])
        init_targets = sorted(
            f"{type_name}::{method}"
            for type_name, method in create_targets
            if type_name.endswith("Behaviour")
            and method.startswith("Init")
        )
        localization_targets = {
            ("Beyond.I18n.I18nUtils", "TryGetText"),
            ("Beyond.Gameplay.GameplayUIUtils", "ResolveOriginalText"),
        }
        if not init_targets:
            failures.append(validation_failure(
                "playable_behaviour_initialization",
                "CreatePlayable -> Behaviour::Init*",
                sorted(f"{a}::{b}" for a, b in create_targets),
                full_name,
            ))
            continue
        missing_localization = sorted(
            f"{a}::{b}" for a, b in localization_targets - get_text_targets
        )
        if missing_localization:
            failures.append(validation_failure(
                "localized_text_resolution",
                sorted(f"{a}::{b}" for a, b in localization_targets),
                sorted(f"{a}::{b}" for a, b in get_text_targets),
                full_name,
            ))
            continue

        families.append({
            "type": full_name,
            "serializedAssetType": full_name.rsplit(".", 1)[-1],
            "textIdFields": text_fields,
            "createPlayable": {
                "methodIndex": create_rows[0].get("methodIndex"),
                "va": create_rows[0].get("methodPointerVa"),
                "behaviourInitializers": init_targets,
            },
            "localizedTextResolver": {
                "methodIndex": get_text_rows[0].get("methodIndex"),
                "va": get_text_rows[0].get("methodPointerVa"),
                "calls": sorted(f"{a}::{b}" for a, b in localization_targets),
            },
        })

    return {
        "validation": {
            "status": "validated" if families and not failures else "failed",
            "failures": failures,
        },
        "families": families,
    }


def story_line_index(story_root: Path) -> tuple[dict[str, str], dict[str, Any]]:
    owners: dict[str, set[str]] = defaultdict(set)
    files = sorted(story_root.glob("*.json"))
    failures: list[dict[str, Any]] = []
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(validation_failure(
                "story_bundle_json", "valid JSON", str(exc), repo_path(path)
            ))
            continue
        key = str(payload.get("key") or "") if isinstance(payload, dict) else ""
        if not key:
            failures.append(validation_failure(
                "story_bundle_key", "non-empty key", key, repo_path(path)
            ))
            continue
        for line in payload.get("lines") or []:
            line_id = str(line.get("id") or "") if isinstance(line, dict) else ""
            if line_id:
                owners[line_id].add(key)
    ambiguous = {
        line_id: sorted(values) for line_id, values in owners.items()
        if len(values) != 1
    }
    index = {
        line_id: next(iter(values))
        for line_id, values in owners.items()
        if len(values) == 1
    }
    return index, {
        "status": "validated" if files and not failures else "failed",
        "sourceRoot": repo_path(story_root),
        "storyFiles": len(files),
        "lineIds": len(index),
        "excludedAmbiguousLineIds": len(ambiguous),
        "ambiguousLineOwners": ambiguous,
        "failures": failures,
        "evidenceBoundary": (
            "Generated Story bundles provide only the exact emitted line-to-Story-key join; "
            "runtime and containment evidence comes from installed binary and serialized Unity data."
        ),
    }


def original_file_record(path_value: str, role: str) -> dict[str, Any]:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    meta = payload.get("$animestudio") or {}
    return {
        "role": role,
        "path": repo_path(path),
        # Unity PathIDs are signed 64-bit values and exceed JavaScript's safe
        # integer range. Publish their exact decimal spelling, never a JSON
        # number that the static WebUI would silently round.
        "pathId": str(meta["pathId"]) if isinstance(meta.get("pathId"), int) else meta.get("pathId"),
        "sourceFile": meta.get("sourceFile"),
        "sourceOriginalPath": meta.get("sourceOriginalPath"),
        "sourceOffset": meta.get("sourceOffset"),
        "byteSize": meta.get("byteSize"),
        "rawDataSha256": meta.get("rawDataSha256"),
        "exportedJsonSha256": sha256_path(path),
    }


def enrich_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched = []
    for row in rows:
        related = [
            original_file_record(str(row[field]), role)
            for field, role in (
                ("assetPath", "text_playable_asset"),
                ("trackPath", "timeline_track"),
                ("rootPath", "timeline_actor_root"),
            )
        ]
        compact = dict(row)
        for field_name in ("assetPathId", "trackPathId", "rootPathId"):
            if isinstance(compact.get(field_name), int):
                compact[field_name] = str(compact[field_name])
        compact["runtimePresentation"] = True
        compact["missionOwnership"] = False
        compact["questActivation"] = False
        compact["branchSelection"] = False
        compact["relatedOriginalFiles"] = related
        enriched.append(compact)
    return enriched


def local_order_edges(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(
            row.get("sourceFile"), row.get("timeline"), row.get("trackPathId"),
            row.get("clipOptionIndex"),
        )].append(row)
    edges: dict[tuple[Any, ...], dict[str, Any]] = {}
    for group_key, group_rows in groups.items():
        ordered = sorted(group_rows, key=lambda row: (
            float(row.get("clipStart") or 0), int(row.get("clipIndex") or 0),
            str(row.get("textId") or ""),
        ))
        for left, right in zip(ordered, ordered[1:]):
            if left.get("key") == right.get("key"):
                continue
            left_end = float(left.get("clipStart") or 0) + float(left.get("clipDuration") or 0)
            right_start = float(right.get("clipStart") or 0)
            if left_end > right_start:
                continue
            identity = (left.get("key"), right.get("key"), *group_key)
            edges[identity] = {
                "from": left.get("key"),
                "to": right.get("key"),
                "timeline": left.get("timeline"),
                "sourceFile": left.get("sourceFile"),
                "trackPathId": left.get("trackPathId"),
                "optionIndex": left.get("clipOptionIndex"),
                "fromClipStart": left.get("clipStart"),
                "fromClipDuration": left.get("clipDuration"),
                "toClipStart": right.get("clipStart"),
                "evidence": "exact_non_overlapping_serialized_clip_time",
                "scope": "same_timeline_track_option_lane",
                "missionOrder": False,
            }
    return sorted(edges.values(), key=lambda row: (
        str(row["timeline"]), float(row["fromClipStart"] or 0), str(row["from"])
    ))


def mapper_args(
    args: argparse.Namespace,
    metadata_path: Path,
    catalog_path: Path,
) -> SimpleNamespace:
    return SimpleNamespace(
        gameassembly=args.gameassembly,
        metadata=metadata_path,
        catalog=catalog_path,
        code_registration=args.code_registration,
        include_generic_instantiations=False,
        metadata_registration="",
        head_bytes=32,
        max_scan_bytes=0x6000,
        arg_context_window=96,
        body_summary_method_regex=r".*",
        body_summary_max_instructions=500,
        include_unresolved_calls=True,
    )


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    if not args.gameassembly.is_file() or not args.metadata.is_file():
        raise RuntimeError(
            "validator=timeline_embedded_story_runtime failed: gate=installed_sources "
            f"expected=GameAssembly+metadata actual={args.gameassembly},{args.metadata}"
        )
    catalog_module = load_module(
        "endfield_timeline_text_catalog",
        TOOLS / "catalog_option_flow_metadata.py",
    )
    mapper = load_module(
        "endfield_timeline_text_mapper",
        TOOLS / "map_body_targets_to_gameassembly.py",
    )
    metadata = catalog_module.Metadata(args.metadata)
    catalog = catalog_module.build_catalog(
        metadata,
        re.compile(r"PlayableAsset$"),
        re.compile(r"(?!)"),
        re.compile(r"^(?:CreatePlayable|_GetText)$"),
        re.compile(r"PlayableAsset$"),
        re.compile(r"Beyond", re.IGNORECASE),
        only_focus=False,
        include_all_members=True,
        body_context=0,
    )
    with tempfile.TemporaryDirectory(prefix="endfield-timeline-text-") as temp:
        catalog_path = Path(temp) / "catalog.json"
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
        body_map = mapper.build_report(mapper_args(args, args.metadata, catalog_path))
    contract = analyze_runtime_contract(catalog, body_map)
    if contract["validation"]["status"] != "validated":
        failure = (contract["validation"]["failures"] or [{}])[0]
        raise RuntimeError(
            "timeline embedded Story runtime validation failed: "
            f"validator={failure.get('validator')}; gate={failure.get('gate')}; "
            f"source={failure.get('sourceFile')}; expected={failure.get('expected')!r}; "
            f"actual={failure.get('actual')!r}"
        )

    line_index, line_validation = story_line_index(args.story_root)
    if line_validation["status"] != "validated":
        failure = (line_validation["failures"] or [{}])[0]
        raise RuntimeError(
            "timeline embedded Story line index validation failed: "
            f"validator={failure.get('validator')}; gate={failure.get('gate')}; "
            f"source={failure.get('sourceFile')}; expected={failure.get('expected')!r}; "
            f"actual={failure.get('actual')!r}"
        )

    try:
        from scripts.story_builder.timeline_recovery import (
            recover_timeline_text_attachments,
        )
    except ModuleNotFoundError:
        from story_builder.timeline_recovery import recover_timeline_text_attachments
    families = tuple(
        str(row["serializedAssetType"]) for row in contract["families"]
    )
    rows = enrich_rows(recover_timeline_text_attachments(
        line_id_to_story_key=line_index,
        playable_asset_type_names=families,
    ))
    edges = local_order_edges(rows)
    return {
        "schemaVersion": "timelineEmbeddedStoryRuntimeAudit.v1",
        "source": {
            "gameAssembly": str(args.gameassembly),
            "gameAssemblySha256": sha256_path(args.gameassembly),
            "metadata": str(args.metadata),
            "metadataSha256": sha256_path(args.metadata),
            "codeRegistration": body_map.get("codeRegistration"),
        },
        "validation": {
            "status": "validated",
            "runtimeContract": contract["validation"],
            "storyLineIndex": line_validation,
        },
        "runtimeContract": contract,
        "counts": {
            "runtimeCarrierFamilies": len(contract["families"]),
            "serializedClipRows": len(rows),
            "uniqueStoryKeys": len({row["key"] for row in rows}),
            "timelines": len({row["timeline"] for row in rows}),
            "localOrderEdges": len(edges),
            "missionOwnershipEdges": 0,
            "branchSelectionEdges": 0,
        },
        "rows": rows,
        "localOrderEdges": edges,
        "evidenceBoundary": {
            "runtimePresentation": True,
            "serializedTimelineContainment": True,
            "sameTrackNonOverlappingClipOrder": True,
            "missionOwnership": False,
            "questActivation": False,
            "branchSelection": False,
            "crossTimelineOrder": False,
            "ocrOrManualOverrideUsed": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    lines = [
        "# Timeline-Embedded Story Runtime Audit",
        "",
        f"- status: `{report['validation']['status']}`",
        f"- runtime carrier families: `{counts['runtimeCarrierFamilies']}`",
        f"- exact serialized clip rows: `{counts['serializedClipRows']}`",
        f"- unique Story keys: `{counts['uniqueStoryKeys']}`",
        f"- Timeline roots: `{counts['timelines']}`",
        f"- proven same-track local-order edges: `{counts['localOrderEdges']}`",
        f"- GameAssembly SHA-256: `{report['source']['gameAssemblySha256']}`",
        f"- metadata SHA-256: `{report['source']['metadataSha256']}`",
        "",
        "## General Runtime Contract",
        "",
    ]
    for family in report["runtimeContract"]["families"]:
        lines.append(
            f"- `{family['type']}` fields "
            f"{', '.join(f'`{value}`' for value in family['textIdFields'])}; "
            f"CreatePlayable `{family['createPlayable']['va']}` -> "
            f"{', '.join(f'`{value}`' for value in family['createPlayable']['behaviourInitializers'])}"
        )
    lines.extend([
        "",
        "## Evidence Boundary",
        "",
        "The installed binary proves that these serialized text fields are resolved and "
        "passed into live Timeline behaviours. Exact PathID links prove the playable, "
        "clip, track, and Actor root. Non-overlapping clip times prove only local order "
        "inside one track and option lane. They do not prove the owning mission/quest, "
        "which branch is selected, or any order across Timeline roots. OCR and manual "
        "overrides are not used.",
        "",
        "## Recovered Rows",
        "",
    ])
    for row in report["rows"]:
        lines.append(
            f"- `{row['key']}` / `{row['textId']}` in `{row['timeline']}` at "
            f"`{row['clipStart']}`s for `{row['clipDuration']}`s; "
            f"dialog `{row.get('dialogKey') or 'unresolved'}`; CAB `{row['sourceFile']}`"
        )
    lines.append("")
    return "\n".join(lines)


def build_default_report() -> dict[str, Any]:
    """Build the canonical current-install audit for pipeline integration."""
    return build_report(SimpleNamespace(
        gameassembly=DEFAULT_GAMEASSEMBLY,
        metadata=DEFAULT_METADATA,
        story_root=DEFAULT_STORY_ROOT,
        code_registration="0x18b9217d0",
    ))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAMEASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--story-root", type=Path, default=DEFAULT_STORY_ROOT)
    parser.add_argument("--code-registration", default="0x18b9217d0")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(render_markdown(report), encoding="utf-8")
    counts = report["counts"]
    print(
        "Timeline embedded Story runtime audit: "
        f"{counts['uniqueStoryKeys']} Story keys, "
        f"{counts['serializedClipRows']} clips, "
        f"{counts['localOrderEdges']} local-order edges -> {args.json}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
