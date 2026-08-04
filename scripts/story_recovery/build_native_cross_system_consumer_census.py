#!/usr/bin/env python3
"""Census direct native callers that consume multiple recovery subsystems.

The scan is intentionally corpus-driven.  It maps every current IL2CPP method
pointer, scans both executable GameAssembly sections for direct ``E8 rel32``
calls, and reports callers that cross MissionSystem, DynamicScene, LevelScript,
or Story API families.  No mission, quest, Story, scene, or object id is seeded.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import importlib.util
import json
import re
import struct
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
MAPPER_PATH = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
CATALOG_PATH = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
DEFAULT_GAME_ROOT = Path(r"D:\Program Files\Endfield Game\Endfield_Data")
DEFAULT_GAME_ASSEMBLY = DEFAULT_GAME_ROOT.parent / "GameAssembly.dll"
DEFAULT_METADATA = DEFAULT_GAME_ROOT / "il2cpp_data" / "Metadata" / "global-metadata.dat"
DEFAULT_JSON = ROOT / "reports" / "story" / "recovery" / "native_cross_system_consumer_census.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "story" / "recovery" / "native_cross_system_consumer_census.md"
EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
MAX_POINTER_ALIASES = 8
EXPECTED_CLASS_COUNTS = {
    "mission_state_controls_dynamic_component_availability": 4,
    "shared_trigger_geometry_adapter": 3,
    "global_level_load_synchronization": 1,
    "story_dynamic_scene_visual_context": 8,
    "mission_or_dialog_alternate_action_consumer": 1,
}
EXPECTED_DIRECT_CLOSURE = {
    "seedMethods": 4,
    "reachableMethods": 23,
    "directEdges": 30,
    "maximumDepth": 2,
    "levelScriptMethods": 0,
    "storyMethods": 0,
    "reviewedIndirectSites": 1,
    "unreviewedIndirectSites": 0,
}
EXPECTED_PENDING_FIELD = {
    "name": "m_pendingRefreshCompSet",
    "token": "0x0400e5f9",
    "offset": "0x48",
}


class AuditError(RuntimeError):
    """Raised when the build-locked census cannot be validated safely."""


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AuditError(f"cannot load required helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path.resolve())


def method_symbol(row: dict[str, Any]) -> str:
    return f"{row.get('type', '')}.{row.get('method', '')}"


def api_families(row: dict[str, Any]) -> set[str]:
    """Classify APIs by managed namespace/type semantics, never content ids."""
    type_name = str(row.get("type") or "")
    method_name = str(row.get("method") or "")
    result: set[str] = set()
    if type_name == "Beyond.Gameplay.MissionSystem":
        result.add("mission_system")
    if type_name.startswith("Beyond.Gameplay.Core.DynamicScene."):
        result.add("dynamic_scene")
    if "LevelScript" in type_name or "LevelScript" in method_name:
        result.add("level_script")
    if any(token in type_name or token in method_name for token in (
        "Dialog", "Radio", "Cinematic", "Cutscene",
    )):
        result.add("story")
    return result


def admissible_pointer_aliases(aliases: Iterable[dict[str, Any]]) -> bool:
    rows = list(aliases)
    families = {family for row in rows for family in api_families(row)}
    return (
        bool(rows)
        and len(rows) <= MAX_POINTER_ALIASES
        and len(families) <= 1
        and any(str(row.get("type") or "").startswith("Beyond.Gameplay") for row in rows)
    )


def classify_candidate(families: Iterable[str], target_symbols: Iterable[str]) -> str:
    """Classify a cross-family caller by API behavior; unknown shapes fail closed."""
    family_set = frozenset(families)
    symbols = tuple(target_symbols)
    joined = "\n".join(symbols)
    if family_set == {"dynamic_scene", "mission_system"}:
        if ("MissionSystem.GetMissionState" in joined or "MissionSystem.GetQuestState" in joined):
            return "mission_state_controls_dynamic_component_availability"
    elif family_set == {"dynamic_scene", "level_script"}:
        if "DynamicStreamingScene.WaitIdle" in joined and "LevelScriptManager." in joined:
            return "global_level_load_synchronization"
        geometry_tokens = (
            "get_position", "get_rotation", "get_scale", "get_shapeOffset",
            "get_shapeSize", "get_shapeType",
        )
        if symbols and all(any(token in symbol for token in geometry_tokens) for symbol in symbols):
            return "shared_trigger_geometry_adapter"
    elif family_set == {"dynamic_scene", "story"}:
        dynamic_visual = any(token in joined for token in (
            "SetOverrideEnable", "RemoveOverride", "RefreshEntity", "ReleaseEntity",
            "GetEntity", "get_entitySys", "get_view",
        ))
        story_visual = any(token in joined for token in (
            "Dialog", "Cinematic", "Decoration", "Actor", "HideSceneObject",
            "SceneRecover", "InteractiveVisibility",
        ))
        if dynamic_visual and story_visual:
            return "story_dynamic_scene_visual_context"
    elif family_set == {"mission_system", "story"}:
        if "MissionSystem.AcceptMission" in joined and "StopAndPlayDialogById" in joined:
            return "mission_or_dialog_alternate_action_consumer"
    return "unreviewed_cross_system_call_shape"


def validate_counts(rows: list[dict[str, Any]], source_file: str) -> list[dict[str, Any]]:
    actual = Counter(str(row.get("classification") or "") for row in rows)
    failures: list[dict[str, Any]] = []
    for classification, expected in EXPECTED_CLASS_COUNTS.items():
        observed = actual.get(classification, 0)
        if observed != expected:
            failures.append({
                "validator": "nativeCrossSystemConsumerCensus",
                "gate": "expectedClassificationCount",
                "classification": classification,
                "expected": expected,
                "actual": observed,
                "sourceFile": source_file,
            })
    unknown = actual.get("unreviewed_cross_system_call_shape", 0)
    if unknown:
        failures.append({
            "validator": "nativeCrossSystemConsumerCensus",
            "gate": "allCrossSystemCallShapesReviewed",
            "expected": 0,
            "actual": unknown,
            "sourceFile": source_file,
        })
    expected_total = sum(EXPECTED_CLASS_COUNTS.values())
    if len(rows) != expected_total:
        failures.append({
            "validator": "nativeCrossSystemConsumerCensus",
            "gate": "expectedCrossSystemCallerCount",
            "expected": expected_total,
            "actual": len(rows),
            "sourceFile": source_file,
        })
    return failures


def method_body(pe: Any, pointers: list[int], pointer: int) -> bytes:
    """Return a bounded native body using the next mapped method as its end."""
    index = bisect.bisect_right(pointers, pointer)
    end = pointers[index] if index < len(pointers) else pointer + 0x10000
    return pe.bytes_at_va(pointer, min(max(0, end - pointer), 0x10000))


def direct_gameplay_targets(
    pe: Any,
    pointers: list[int],
    methods_by_pointer: dict[int, list[dict[str, Any]]],
    pointer: int,
) -> set[int]:
    """Find unambiguous managed gameplay targets without seeding content ids."""
    data = method_body(pe, pointers, pointer)
    targets: set[int] = set()
    position = data.find(b"\xe8")
    while position >= 0:
        if position + 5 <= len(data):
            target = pointer + position + 5 + struct.unpack_from("<i", data, position + 1)[0]
            aliases = methods_by_pointer.get(target) or []
            if admissible_pointer_aliases(aliases) and any(
                str(row.get("type") or "").startswith("Beyond.Gameplay") for row in aliases
            ):
                targets.add(target)
        position = data.find(b"\xe8", position + 1)
    return targets


def build_direct_closure(
    pe: Any,
    pointers: list[int],
    methods_by_pointer: dict[int, list[dict[str, Any]]],
    seeds: Iterable[int],
) -> tuple[set[int], set[tuple[int, int]], dict[int, int]]:
    """Follow direct gameplay calls to a deterministic fixed point."""
    seed_set = set(seeds)
    seen = set(seed_set)
    depths = {pointer: 0 for pointer in seed_set}
    queue = deque(sorted(seed_set))
    edges: set[tuple[int, int]] = set()
    while queue:
        source = queue.popleft()
        for target in sorted(direct_gameplay_targets(pe, pointers, methods_by_pointer, source)):
            edges.add((source, target))
            if target not in seen:
                seen.add(target)
                depths[target] = depths[source] + 1
                queue.append(target)
    return seen, edges, depths


def classify_indirect_call_window(texts: list[str], index: int) -> str:
    """Review decoded indirect-call shapes; anything unfamiliar stays unreviewed."""
    current = texts[index]
    window = texts[max(0, index - 20):index]
    if current == "call [rax]" and any(
        re.fullmatch(r"cmp \[rax\+0x20\], 0x0", text) for text in window
    ) and sum("+0xb0]" in text for text in window) >= 2:
        return "il2cpp_class_initializer_guard"
    return "unreviewed_indirect_call_shape"


def decoded_indirect_sites(mapper: Any, body: bytes, pointer: int) -> list[dict[str, Any]]:
    instructions = mapper.decode_x64_subset(body, pointer, stop_offset=len(body))
    texts = [str(row.get("text") or "") for row in instructions]
    rows: list[dict[str, Any]] = []
    for index, instruction in enumerate(instructions):
        text = texts[index]
        if not re.match(r"call (?!0x)", text):
            continue
        rows.append({
            "va": f"0x{pointer + int(instruction.get('offset') or 0):x}",
            "instruction": text,
            "classification": classify_indirect_call_window(texts, index),
            "window": texts[max(0, index - 8):index + 1],
        })
    return rows


def runtime_field_rows(
    metadata: Any,
    pe: Any,
    registration_summary: dict[str, Any],
    type_index: int,
) -> list[dict[str, Any]]:
    """Read current instance-field layout directly from MetadataRegistration."""
    count = int(registration_summary["fieldOffsetsCount"])
    if not 0 <= type_index < count:
        raise AuditError(f"field layout type index {type_index} outside table count {count}")
    table_va = int(registration_summary["fieldOffsets"], 16)
    offsets_va = pe.u64_at_va(table_va + type_index * 8)
    if not offsets_va:
        raise AuditError(f"type {type_index} has no runtime field-offset row")
    type_def = metadata.types[type_index]
    return [
        {
            "name": metadata.string(field.name_index),
            "token": f"0x{field.token:08x}",
            "offset": f"0x{pe.u32_at_va(offsets_va + index * 4):x}",
        }
        for index, field in enumerate(metadata.fields_for(type_def))
    ]


def select_instance_field_references(
    method_groups: list[dict[str, Any]],
    method_suffix: str,
    field_offset: str,
) -> tuple[str | None, list[dict[str, Any]]]:
    """Derive the stable ``this`` base register from a semantic method role."""
    candidates: list[tuple[str, dict[str, Any]]] = []
    pattern = re.compile(rf"\[([a-z][a-z0-9]*)\+{re.escape(field_offset)}\]")
    for group in method_groups:
        if not any(symbol.endswith(method_suffix) for symbol in group.get("symbols") or []):
            continue
        for reference in group.get("references") or []:
            match = pattern.search(str(reference.get("instruction") or ""))
            if match and match.group(1) not in {"rax", "rsp"}:
                candidates.append((match.group(1), reference))
    counts = Counter(register for register, _reference in candidates)
    if not counts:
        return None, []
    maximum = max(counts.values())
    bases = [register for register, count in counts.items() if count == maximum]
    if len(bases) != 1:
        return None, []
    base = bases[0]
    return base, [reference for register, reference in candidates if register == base]


def validate_closure(
    counts: dict[str, int],
    pending_field: dict[str, Any] | None,
    deferred: dict[str, Any],
    source_file: str,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for gate, expected in EXPECTED_DIRECT_CLOSURE.items():
        actual = counts.get(gate, 0)
        if actual != expected:
            failures.append({
                "validator": "nativeCrossSystemConsumerCensus",
                "gate": f"directClosure.{gate}",
                "expected": expected,
                "actual": actual,
                "sourceFile": source_file,
            })
    for key, expected in EXPECTED_PENDING_FIELD.items():
        actual = (pending_field or {}).get(key)
        if actual != expected:
            failures.append({
                "validator": "nativeCrossSystemConsumerCensus",
                "gate": f"deferredRefresh.pendingField.{key}",
                "expected": expected,
                "actual": actual,
                "sourceFile": source_file,
            })
    expected_methods = {
        "enqueueWriters": 2,
        "scheduledReaders": 1,
        "fieldWriterReferences": 1,
        "fieldReaderReferences": 3,
        "refreshEntityStatusTargets": 1,
        "conditionUpdateTargets": 1,
    }
    for gate, expected in expected_methods.items():
        actual = int(deferred.get(gate) or 0)
        if actual != expected:
            failures.append({
                "validator": "nativeCrossSystemConsumerCensus",
                "gate": f"deferredRefresh.{gate}",
                "expected": expected,
                "actual": actual,
                "sourceFile": source_file,
            })
    return failures


def build_report(gameassembly: Path, metadata_path: Path) -> dict[str, Any]:
    if not gameassembly.is_file() or not metadata_path.is_file():
        raise AuditError(f"missing original binary input: {gameassembly} / {metadata_path}")
    game_hash = sha256_file(gameassembly)
    metadata_hash = sha256_file(metadata_path)
    if game_hash != EXPECTED_GAME_ASSEMBLY_SHA256:
        raise AuditError(
            "GameAssembly hash changed; expected "
            f"{EXPECTED_GAME_ASSEMBLY_SHA256}, actual {game_hash}; revalidate family rules"
        )
    if metadata_hash != EXPECTED_METADATA_SHA256:
        raise AuditError(
            "global metadata hash changed; expected "
            f"{EXPECTED_METADATA_SHA256}, actual {metadata_hash}; revalidate method mapping"
        )

    mapper = load_module("native_cross_system_mapper", MAPPER_PATH)
    catalog = load_module("native_cross_system_catalog", CATALOG_PATH)
    metadata = catalog.Metadata(metadata_path)
    pe = mapper.PeImage(gameassembly)
    modules = mapper.parse_codegen_modules(pe, mapper.DEFAULT_CODE_REGISTRATION)
    ranges = mapper.image_method_ranges(metadata)
    _pointers_by_image, methods_by_pointer = mapper.build_pointer_indexes(
        pe, metadata, modules, ranges
    )
    registration = mapper.find_metadata_registration(pe, mapper.DEFAULT_CODE_REGISTRATION)
    if registration is None:
        raise AuditError("could not derive MetadataRegistration from current GameAssembly")
    generic = mapper.build_generic_method_index(
        pe, metadata, mapper.DEFAULT_CODE_REGISTRATION, registration
    )
    for pointer, aliases in generic.items():
        methods_by_pointer.setdefault(pointer, aliases)

    method_pointers = sorted(methods_by_pointer)
    family_by_pointer: dict[int, tuple[str, ...]] = {}
    for pointer, aliases in methods_by_pointer.items():
        families = tuple(sorted({family for row in aliases for family in api_families(row)}))
        if len(families) == 1 and admissible_pointer_aliases(aliases):
            family_by_pointer[pointer] = families

    calls_by_caller: dict[int, list[dict[str, Any]]] = defaultdict(list)
    family_call_counts: Counter[str] = Counter()
    section_call_candidates: Counter[str] = Counter()
    for section in pe.sections:
        section_name = str(section["name"])
        if section_name not in {".text", "il2cpp"}:
            continue
        data = pe.buf[section["rawPointer"]:section["rawPointer"] + section["rawSize"]]
        position = data.find(b"\xe8")
        while position >= 0:
            if position + 5 <= len(data):
                section_call_candidates[section_name] += 1
                call_va = pe.image_base + section["virtualAddress"] + position
                relative = struct.unpack_from("<i", data, position + 1)[0]
                target_va = call_va + 5 + relative
                families = family_by_pointer.get(target_va)
                if families:
                    caller_pos = bisect.bisect_right(method_pointers, call_va) - 1
                    if caller_pos >= 0:
                        caller_va = method_pointers[caller_pos]
                        next_va = (
                            method_pointers[caller_pos + 1]
                            if caller_pos + 1 < len(method_pointers)
                            else caller_va + 0x10000
                        )
                        if call_va < min(next_va, caller_va + 0x10000):
                            targets = methods_by_pointer[target_va]
                            calls_by_caller[caller_va].append({
                                "callVa": f"0x{call_va:x}",
                                "targetVa": f"0x{target_va:x}",
                                "families": list(families),
                                "targets": sorted({method_symbol(row) for row in targets}),
                            })
                            family_call_counts.update(families)
            position = data.find(b"\xe8", position + 1)

    rows: list[dict[str, Any]] = []
    for caller_va, calls in calls_by_caller.items():
        families = sorted({family for call in calls for family in call["families"]})
        family_set = set(families)
        relevant = (
            "mission_system" in family_set and len(family_set) >= 2
        ) or (
            "dynamic_scene" in family_set
            and bool({"level_script", "story"} & family_set)
        )
        aliases = methods_by_pointer[caller_va]
        if not relevant or not admissible_pointer_aliases(aliases):
            continue
        target_symbols = sorted({symbol for call in calls for symbol in call["targets"]})
        rows.append({
            "callerVa": f"0x{caller_va:x}",
            "callers": sorted({method_symbol(alias) for alias in aliases}),
            "families": families,
            "classification": classify_candidate(families, target_symbols),
            "targets": target_symbols,
            "callSites": calls,
        })
    rows.sort(key=lambda row: (row["families"], row["callerVa"]))

    seeds = {
        int(row["callerVa"], 16)
        for row in rows
        if row["classification"] == "mission_state_controls_dynamic_component_availability"
    }
    reachable, closure_edges, depths = build_direct_closure(
        pe, method_pointers, methods_by_pointer, seeds
    )
    indirect_sites: list[dict[str, Any]] = []
    for pointer in sorted(reachable):
        for site in decoded_indirect_sites(
            mapper, method_body(pe, method_pointers, pointer), pointer
        ):
            indirect_sites.append({
                "callerVa": f"0x{pointer:x}",
                "callers": sorted({method_symbol(row) for row in methods_by_pointer[pointer]}),
                **site,
            })
    reachable_family_counts = Counter(
        family
        for pointer in reachable
        for family in {
            family
            for alias in methods_by_pointer[pointer]
            for family in api_families(alias)
        }
    )
    closure_counts = {
        "seedMethods": len(seeds),
        "reachableMethods": len(reachable),
        "directEdges": len(closure_edges),
        "maximumDepth": max(depths.values(), default=0),
        "levelScriptMethods": reachable_family_counts.get("level_script", 0),
        "storyMethods": reachable_family_counts.get("story", 0),
        "reviewedIndirectSites": sum(
            site["classification"] != "unreviewed_indirect_call_shape"
            for site in indirect_sites
        ),
        "unreviewedIndirectSites": sum(
            site["classification"] == "unreviewed_indirect_call_shape"
            for site in indirect_sites
        ),
    }

    seed_owner_names = {
        str(alias.get("type") or "")
        for pointer in seeds
        for alias in methods_by_pointer[pointer]
    }
    if len(seed_owner_names) != 1:
        raise AuditError(
            "nativeCrossSystemConsumerCensus failed deferredRefresh.seedOwnerType: "
            f"expected 1, actual {len(seed_owner_names)}; source={source_path(gameassembly)}"
        )
    seed_owner = next(iter(seed_owner_names))
    owner_types = [
        type_def for type_def in metadata.types
        if metadata.type_full_name(type_def) == seed_owner
    ]
    if len(owner_types) != 1:
        raise AuditError(
            "nativeCrossSystemConsumerCensus failed deferredRefresh.metadataOwnerType: "
            f"expected 1, actual {len(owner_types)}; source={source_path(metadata_path)}"
        )
    registration_summary = mapper.metadata_registration_summary(pe, registration)
    field_rows = runtime_field_rows(
        metadata, pe, registration_summary, owner_types[0].index
    )
    pending_candidates = [
        row for row in field_rows
        if "pending" in row["name"].lower() and "refresh" in row["name"].lower()
    ]
    pending_field = pending_candidates[0] if len(pending_candidates) == 1 else None

    owner_methods: dict[str, list[int]] = defaultdict(list)
    for pointer, aliases in methods_by_pointer.items():
        for alias in aliases:
            if str(alias.get("type") or "") == seed_owner:
                owner_methods[str(alias.get("method") or "")].append(pointer)
    enqueue_methods = sorted({
        pointer
        for method_name, method_rows in owner_methods.items()
        if "Enqueue" in method_name and "Comp" in method_name
        for pointer in method_rows
    })
    before_tick_methods = sorted(set(owner_methods.get("BeforeTick") or []))
    field_offset_text = (pending_field or {}).get("offset", "")

    def method_field_references(pointer: int) -> list[dict[str, Any]]:
        body = method_body(pe, method_pointers, pointer)
        instructions = mapper.decode_x64_subset(body, pointer, stop_offset=len(body))
        marker = f"+{field_offset_text}]"
        return [
            {"va": f"0x{pointer + int(row.get('offset') or 0):x}", "instruction": row["text"]}
            for row in instructions
            if field_offset_text and marker in str(row.get("text") or "")
        ]

    writer_references = [
        {"va": f"0x{pointer:x}", "symbols": sorted({method_symbol(row) for row in methods_by_pointer[pointer]}),
         "references": method_field_references(pointer)}
        for pointer in enqueue_methods
    ]
    reader_references = [
        {"va": f"0x{pointer:x}", "symbols": sorted({method_symbol(row) for row in methods_by_pointer[pointer]}),
         "references": method_field_references(pointer)}
        for pointer in before_tick_methods
    ]
    writer_base, writer_instance_references = select_instance_field_references(
        writer_references, "._EnqueueOwnerComps", field_offset_text
    )
    reader_base, reader_instance_references = select_instance_field_references(
        reader_references, ".BeforeTick", field_offset_text
    )
    scheduled_targets = {
        target
        for pointer in before_tick_methods
        for target in direct_gameplay_targets(pe, method_pointers, methods_by_pointer, pointer)
    }
    scheduled_target_symbols = sorted({
        method_symbol(alias)
        for pointer in scheduled_targets
        for alias in methods_by_pointer[pointer]
    })
    deferred_counts = {
        "enqueueWriters": len(enqueue_methods),
        "scheduledReaders": len(before_tick_methods),
        "fieldWriterReferences": sum(
            1 for _reference in writer_instance_references
        ),
        "fieldReaderReferences": sum(
            1 for _reference in reader_instance_references
        ),
        "refreshEntityStatusTargets": sum(
            symbol.endswith(".RefreshEntityStatus") for symbol in scheduled_target_symbols
        ),
        "conditionUpdateTargets": sum(
            symbol.endswith("._UpdateConditionValue") for symbol in scheduled_target_symbols
        ),
    }

    failures = validate_counts(rows, source_path(gameassembly))
    failures.extend(validate_closure(
        closure_counts, pending_field, deferred_counts, source_path(gameassembly)
    ))
    if failures:
        first = failures[0]
        raise AuditError(
            f"{first['validator']} failed {first['gate']} for "
            f"{first.get('classification', 'all callers')}: expected "
            f"{first['expected']}, actual {first['actual']}; source={first['sourceFile']}"
        )
    class_counts = Counter(row["classification"] for row in rows)
    family_sets = Counter("+".join(row["families"]) for row in rows)
    return {
        "schemaVersion": "nativeCrossSystemConsumerCensus.v2",
        "source": {
            "gameAssembly": source_path(gameassembly),
            "gameAssemblySha256": game_hash,
            "globalMetadata": source_path(metadata_path),
            "globalMetadataSha256": metadata_hash,
            "sections": [".text", "il2cpp"],
        },
        "method": {
            "selection": "all direct E8 rel32 calls to unambiguous current managed API-family pointers",
            "idSeeds": 0,
            "maximumPointerAliases": MAX_POINTER_ALIASES,
            "mappedMethodPointers": len(methods_by_pointer),
            "familyTargetPointers": len(family_by_pointer),
            "rawCallOpcodeCandidatesBySection": dict(sorted(section_call_candidates.items())),
            "mappedFamilyCalls": dict(sorted(family_call_counts.items())),
        },
        "summary": {
            "crossSystemCallers": len(rows),
            "classificationCounts": dict(sorted(class_counts.items())),
            "familyCombinationCounts": dict(sorted(family_sets.items())),
            "missionLevelScriptCallers": sum(
                set(row["families"]) == {"mission_system", "level_script"} for row in rows
            ),
            "tripleOrGreaterFamilyCallers": sum(len(row["families"]) >= 3 for row in rows),
            "unreviewedCallers": class_counts.get("unreviewed_cross_system_call_shape", 0),
            "storyBindingsAdded": 0,
            "missionOrderEdgesAdded": 0,
        },
        "directConsumerClosure": {
            "method": (
                "Fixed-point traversal from every mission-state/DynamicScene caller through "
                "unambiguous Beyond.Gameplay direct calls; no content identity is seeded."
            ),
            "counts": closure_counts,
            "reachableFamilyCounts": dict(sorted(reachable_family_counts.items())),
            "seeds": [f"0x{pointer:x}" for pointer in sorted(seeds)],
            "reachableMethods": [
                {
                    "va": f"0x{pointer:x}",
                    "depth": depths[pointer],
                    "symbols": sorted({method_symbol(row) for row in methods_by_pointer[pointer]}),
                }
                for pointer in sorted(reachable)
            ],
            "directEdges": [
                {
                    "sourceVa": f"0x{source:x}",
                    "sourceSymbols": sorted({method_symbol(row) for row in methods_by_pointer[source]}),
                    "targetVa": f"0x{target:x}",
                    "targetSymbols": sorted({method_symbol(row) for row in methods_by_pointer[target]}),
                }
                for source, target in sorted(closure_edges)
            ],
            "indirectCallSites": indirect_sites,
        },
        "deferredRefreshClosure": {
            "ownerType": seed_owner,
            "ownerTypeToken": f"0x{owner_types[0].token:08x}",
            "pendingField": pending_field,
            "counts": deferred_counts,
            "enqueueWriters": writer_references,
            "scheduledReaders": reader_references,
            "instanceFieldAccess": {
                "writerBaseRegister": writer_base,
                "writerReferences": writer_instance_references,
                "readerBaseRegister": reader_base,
                "readerReferences": reader_instance_references,
            },
            "scheduledTargets": scheduled_target_symbols,
            "chain": [
                "MissionSystem mission/quest state",
                "DynamicScene cared component enqueue",
                f"{(pending_field or {}).get('name', '?')}@{field_offset_text or '?'}",
                f"{seed_owner}.BeforeTick",
                "DynamicSceneMissionControlSystem._UpdateConditionValue",
                "DynamicSceneEntitySystem.RefreshEntityStatus",
            ],
            "classification": "mission_state_drives_deferred_dynamic_scene_availability_refresh",
            "storyBindingsAdded": 0,
            "missionOrderEdgesAdded": 0,
        },
        "rows": rows,
        "finding": (
            "The current binary exposes mission-state consumers for DynamicScene component "
            "availability, but no direct MissionSystem/LevelScript caller and no caller that "
            "joins mission state, DynamicScene, and Story or LevelScript. Other cross-system "
            "callers are shared geometry, global loading, or Story visual context."
        ),
        "boundary": (
            "The mission-state consumer closure includes every unambiguous managed gameplay "
            "direct call and reviews decoded indirect call instructions; its sole indirect site "
            "is an IL2CPP class-initializer guard. The bundled partial decoder is not a general "
            "x64 proof, so reflection, XLua, server-only logic, opaque dynamic dispatch, and "
            "future builds remain outside this census. "
            "The MissionOption mission/dialog row relies on its separate pinned control-flow "
            "audit before interpreting the two calls as alternate actions."
        ),
        "validation": {"status": "passed", "failures": []},
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Native Cross-System Consumer Census",
        "",
        f"- Cross-system callers: **{summary['crossSystemCallers']}**",
        f"- Mission + LevelScript callers: **{summary['missionLevelScriptCallers']}**",
        f"- Three-or-more-family callers: **{summary['tripleOrGreaterFamilyCallers']}**",
        f"- Unreviewed callers: **{summary['unreviewedCallers']}**",
        f"- GameAssembly SHA-256: `{report['source']['gameAssemblySha256']}`",
        f"- Metadata SHA-256: `{report['source']['globalMetadataSha256']}`",
        "",
        report["finding"],
        "",
        "## Classification counts",
        "",
    ]
    for key, value in summary["classificationCounts"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Callers", ""])
    for row in report["rows"]:
        lines.append(
            f"- `{row['callerVa']}` `{row['classification']}`: "
            + ", ".join(f"`{caller}`" for caller in row["callers"])
        )
    lines.extend(["", "## Boundary", "", report["boundary"], ""])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build_report(args.gameassembly, args.metadata)
    except AuditError as exc:
        print(f"native cross-system consumer census failed: {exc}", file=sys.stderr)
        return 1
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(report), encoding="utf-8")
    print(
        "Native cross-system consumer census passed: "
        f"{report['summary']['crossSystemCallers']} callers, "
        f"{report['summary']['unreviewedCallers']} unreviewed, "
        f"{report['summary']['missionOrderEdgesAdded']} order edges"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
