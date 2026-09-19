"""Gameplay audio sidecars: skill, enemy, projectile and animation sound links.

Joins exact SkillData/BuffData references and animation callbacks to Wwise events
and decoded media. Ownership inferred from authored references is labelled as
inferred; nothing here establishes runtime playback."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict, deque
from struct import unpack_from
from pathlib import Path, PurePosixPath
from typing import Any
from scripts.webui.audio.semantics.context_utils import iter_asset_map_objects
from scripts.webui.audio.semantics.context_utils import json_dump
from scripts.webui.audio.semantics.context_utils import load_json_strict
from scripts.webui.audio.semantics.context_utils import normalize_posix

from scripts.game_data.extraction.animestudio_index_io import ObjectIndexUnavailable
from scripts.game_data.extraction.animestudio_index_io import iter_published_objects
from scripts.game_data.extraction.animestudio_index_io import raw_json_path_for_object

GAMEPLAY_INDEX_REL = Path("data/lang/{language}/gameplay/index.json")

GAMEPLAY_SFX_REL = Path("data/lang/{language}/gameplay/sound_effects.json")

GAMEPLAY_SFX_ANIMATION_CATALOG_NAME = "sound_effects_animation_catalog.json"

GAMEPLAY_SFX_ANIMATION_EVIDENCE_NAME = "sound_effects_animation_evidence.json"

GAMEPLAY_SFX_ANIMATION_EVIDENCE_SCHEMA_VERSION = 2

GAMEPLAY_AUDIO_EVENT_BYTES_RE = re.compile(rb"\b(?:au|bark|radio)_[A-Za-z0-9_]{2,160}\b")

GAMEPLAY_BUFF_BYTES_RE = re.compile(rb"\bbuff_[A-Za-z0-9_]{2,160}\b")

ANIMATION_CLIP_HASH_SUFFIX_RE = re.compile(r"_p[0-9a-f]{16}$", re.IGNORECASE)

ANIMATION_CLIP_PATH_ID_SUFFIX_RE = re.compile(r"_p(?P<path_id>[0-9a-f]{16})$", re.IGNORECASE)

ANIMATION_ACTOR_RE = re.compile(r"^A_(actor|monster)_([^_]+)_", re.IGNORECASE)

ENEMY_ID_TOKEN_RE = re.compile(r"^eny_\d+_([^_]+)", re.IGNORECASE)

CHARACTER_ID_TOKEN_RE = re.compile(r"^chr_\d+_([^_]+)", re.IGNORECASE)

ENEMY_ANIM_CONFIG_RE = re.compile(r"anim_cfg_eny_\d+_([^./\\]+)\.asset$", re.IGNORECASE)

ANIMATION_AUDIO_FUNCTIONS = frozenset({
    "PostAudioEvent",
    "PostAudioEventAdvance",
    "PostAudioEventAtPosition",
    "OnCustomFootStep",
})

ANIMATOR_CONTROLLER_REL = Path(
    "recovered/AnimeStudio-cli/StreamingAssets/json_by_type/AnimatorController"
)

ANIMATOR_CONTROLLER_RELS = (
    ANIMATOR_CONTROLLER_REL,
    Path("recovered/AnimeStudio-cli/Persistent/json_by_type/AnimatorController"),
)

ANIMATOR_OVERRIDE_CONTROLLER_REL = Path(
    "recovered/AnimeStudio-cli/StreamingAssets/json_by_type/AnimatorOverrideController"
)

ANIMATOR_OVERRIDE_CONTROLLER_RELS = (
    ANIMATOR_OVERRIDE_CONTROLLER_REL,
    Path("recovered/AnimeStudio-cli/Persistent/json_by_type/AnimatorOverrideController"),
)

ANIMATION_CLIP_REL = Path(
    "recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/AnimationClip"
)

ANIMATION_CLIP_RELS = (
    ANIMATION_CLIP_REL,
    Path("recovered/AnimeStudio-cli/Persistent/convert_by_type/AnimationClip"),
)

ANIMATOR_OVERRIDE_IDENTITY_RE = re.compile(
    r"(?:^|_)((?:eny|chr)_\d+_[^_]+)", re.IGNORECASE
)

GAMEPLAY_PROFILE_VOICE_RE = re.compile(r"(?:_combat_|_mono_(?:attack|skill))", re.IGNORECASE)

GAMEPLAY_AUDIO_LINK_FIELDS = (
    "src", "mediaId", "format", "bytes", "audioScope", "audioCategory",
    "audioCategoryDetail", "sourceBlock", "sourceBlockLabel", "sourceBank",
    "bankId", "bank", "wwiseMediaEvidence", "contentSha256",
)

def length_prefixed_matches(data: bytes, pattern: re.Pattern[bytes]) -> set[str]:
    """Return exact MemoryPack UTF-8 strings matching ``pattern``.

    Gameplay config strings are encoded as a four-byte byte length followed by
    UTF-8.  Requiring that boundary prevents incidental ASCII fragments from
    being promoted to authored references.
    """

    values: set[str] = set()
    for match in pattern.finditer(data):
        start = match.start()
        if start < 4 or unpack_from("<I", data, start - 4)[0] != len(match.group(0)):
            continue
        try:
            values.add(match.group(0).decode("ascii"))
        except UnicodeDecodeError:
            continue
    return values

def gameplay_config_records(export_root: Path, family: str) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for source in ("StreamingAssets", "Persistent"):
        root = export_root / "structured" / source / "Data" / "Json" / family
        if not root.exists():
            continue
        for path in sorted(root.glob("*.json")):
            try:
                data = path.read_bytes()
            except OSError:
                continue
            events = length_prefixed_matches(data, GAMEPLAY_AUDIO_EVENT_BYTES_RE)
            buffs = length_prefixed_matches(data, GAMEPLAY_BUFF_BYTES_RE)
            record = records.setdefault(path.stem, {"events": set(), "buffs": set(), "sources": set()})
            record["events"].update(events)
            record["buffs"].update(buffs)
            record["sources"].add(normalize_posix(path.relative_to(export_root)))
    return records

def iter_json_strings(value: Any):
    """Yield scalar strings from a decoded JSON value."""

    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_json_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_json_strings(child)

def enemy_template_source_files(export_root: Path) -> dict[str, list[Path]]:
    """Index EnemyData objects, preferring the published object index."""

    result: dict[str, list[Path]] = defaultdict(list)
    seen: set[Path] = set()
    index_ok = False
    for source in ("Persistent", "StreamingAssets"):
        try:
            for row in iter_published_objects(export_root, source):
                name = str(row.get("name") or "")
                if not name.lower().startswith("data_eny_"):
                    continue
                identity = name.removeprefix("data_")
                path = raw_json_path_for_object(export_root, source, row)
                if path is not None and path.resolve() not in seen:
                    seen.add(path.resolve())
                    result[identity].append(path)
            index_ok = True
        except ObjectIndexUnavailable:
            continue
    if index_ok:
        return {identity: sorted(paths) for identity, paths in sorted(result.items())}

    # Explicit compatibility path for exports predating the merged index.
    for source in ("Persistent", "StreamingAssets"):
        root = export_root / "recovered" / "AnimeStudio-cli" / source / "json_by_type" / "MonoBehaviour"
        if not root.exists():
            continue
        for path in root.glob("data_eny_*_p*.json"):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            prefix, separator, suffix = path.stem.rpartition("_p")
            if not separator or not suffix or not re.fullmatch(r"[0-9a-f]+", suffix, re.IGNORECASE):
                continue
            identity = prefix.removeprefix("data_")
            result[identity].append(path)
    return {identity: sorted(paths) for identity, paths in sorted(result.items())}

def enemy_template_skill_references(
    export_root: Path,
    enemies: list[dict[str, Any]],
    known_skill_ids: set[str],
    source_files: dict[str, list[Path]] | None = None,
) -> dict[str, dict[str, set[str]]]:
    """Return enemy -> SkillData ids recovered inside AbilitySystemData.

    Enemy variants frequently execute SkillData authored under a different
    canonical enemy id.  Matching only the current enemy-id prefix therefore
    hides otherwise playable attack audio.  The recovered EnemyData
    MonoBehaviours preserve the exact SkillData identifiers in their
    AbilitySystemData payload (including partially decoded string-hint tails),
    so require an exact match to an exported SkillData id before accepting the
    relationship.
    """

    indexed_files = source_files if source_files is not None else enemy_template_source_files(export_root)
    result: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    seen_paths: set[Path] = set()
    for enemy in enemies:
        owner_id = str(enemy.get("id") or "").strip()
        if not owner_id:
            continue
        identities = {
            str(value or "").strip()
            for value in (enemy.get("id"), enemy.get("templateId"), *(enemy.get("variantIds") or []))
            if str(value or "").strip()
        }
        for identity in sorted(identities):
            for path in indexed_files.get(identity) or []:
                resolved = path.resolve()
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)
                payload = load_json_strict(path, {})
                references = ((payload.get("references") or {}).get("RefIds") or []) if isinstance(payload, dict) else []
                matched: set[str] = set()
                for reference in references:
                    if not isinstance(reference, dict):
                        continue
                    type_info = reference.get("type") or {}
                    if str(type_info.get("class") or "") != "AbilitySystemData":
                        continue
                    matched.update(
                        value
                        for value in iter_json_strings(reference.get("data") or {})
                        if value in known_skill_ids
                    )
                if not matched:
                    continue
                try:
                    source = normalize_posix(path.relative_to(export_root))
                except ValueError:
                    source = normalize_posix(path)
                for skill_id in matched:
                    result[owner_id][skill_id].add(source)
    return {
        owner_id: {skill_id: sources for skill_id, sources in sorted(skills.items())}
        for owner_id, skills in sorted(result.items())
    }

def enemy_template_animation_tokens(
    export_root: Path,
    enemies: list[dict[str, Any]],
    source_files: dict[str, list[Path]] | None = None,
) -> dict[str, dict[str, set[str]]]:
    """Return enemy -> animation actor tokens with exact source files."""

    indexed_files = source_files if source_files is not None else enemy_template_source_files(export_root)
    result: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for enemy in enemies:
        owner_id = str(enemy.get("id") or "").strip()
        if not owner_id:
            continue
        identities = {
            str(value or "").strip()
            for value in (enemy.get("id"), enemy.get("templateId"), *(enemy.get("variantIds") or []))
            if str(value or "").strip()
        }
        for identity in sorted(identities):
            direct = ENEMY_ID_TOKEN_RE.match(identity)
            if direct:
                result[owner_id][direct.group(1).lower()].add("EnemyTable identity")
            seen_paths: set[Path] = set()
            for path in indexed_files.get(identity) or []:
                resolved = path.resolve()
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)
                payload = load_json_strict(path, {})
                try:
                    source = normalize_posix(path.relative_to(export_root))
                except ValueError:
                    source = normalize_posix(path)
                for value in iter_json_strings(payload):
                    match = ENEMY_ANIM_CONFIG_RE.search(value)
                    if match:
                        result[owner_id][match.group(1).lower()].add(source)
    return {
        owner_id: {token: sources for token, sources in sorted(tokens.items())}
        for owner_id, tokens in sorted(result.items())
    }

def animation_clip_action_kind(clip_name: str) -> str:
    value = clip_name.lower()
    if re.search(r"(?:^|_)(?:attack\d*|atk\d*|normal_attack|power_attack)(?:_|$)", value):
        return "attack"
    if re.search(r"(?:^|_)(?:skill\d*|combo|ultimate)(?:_|$)", value):
        return "skill"
    if re.search(r"(?:^|_)(?:damage|damaged|hit|death|die|down|break)(?:_|$)", value):
        return "reaction"
    if re.search(r"(?:^|_)(?:walk|run|move|turn|land|jump|fall|dash|sprint|idle)(?:_|$)", value):
        return "movement"
    return "action"

def animation_clip_context(clip_name: str) -> str:
    value = clip_name.lower()
    for token in ("battle", "dialog", "customized", "ui", "interact", "idle", "relax"):
        if re.search(rf"(?:^|_){token}(?:_|$)", value):
            return token
    return "other"

def gameplay_character_token_owners(entries: list[dict[str, Any]]) -> dict[str, list[str]]:
    token_owners: dict[str, set[str]] = defaultdict(set)
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("kind") != "character":
            continue
        owner_id = str(entry.get("id") or "").strip()
        if not owner_id:
            continue
        direct = CHARACTER_ID_TOKEN_RE.match(owner_id)
        if direct:
            token_owners[direct.group(1).lower()].add(owner_id)
        for group in entry.get("skillGroups") or []:
            for skill_id in group.get("actionSkillIds") or []:
                match = CHARACTER_ID_TOKEN_RE.match(str(skill_id or ""))
                if match:
                    token_owners[match.group(1).lower()].add(owner_id)
    return {token: sorted(owners) for token, owners in sorted(token_owners.items())}

def profile_voice_action_kind(vo_id: str) -> str:
    value = vo_id.lower()
    if "_mono_attack" in value:
        return "attackVoice"
    if "_mono_skill" in value or "_combat_skill" in value:
        return "skillVoice"
    if "_combat_hurt" in value or "_combat_dead" in value:
        return "reactionVoice"
    return "combatVoice"

def collect_gameplay_profile_voices(
    export_root: Path,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Collect exact CharacterTable combat/profile voice ownership."""

    character_table = {}
    character_source = ""
    for source in ("Persistent", "StreamingAssets"):
        path = export_root / "structured" / source / "Table" / "CharacterTable.json"
        payload = load_json_strict(path, {})
        if isinstance(payload, dict) and payload:
            character_table = payload
            try:
                character_source = normalize_posix(path.relative_to(export_root))
            except ValueError:
                character_source = normalize_posix(path)
            break

    trigger_keys: set[str] = set()
    for source in ("Persistent", "StreamingAssets"):
        path = export_root / "structured" / source / "Table" / "AIBark.json"
        payload = load_json_strict(path, {})
        if not isinstance(payload, dict):
            continue
        for value in payload.values():
            rows = value.get("array") if isinstance(value, dict) else None
            for row in rows or []:
                if not isinstance(row, dict):
                    continue
                trigger_keys.update(str(key or "").strip() for key in row.get("triggerKey") or [] if str(key or "").strip())
        if trigger_keys:
            break
    sorted_triggers = sorted(trigger_keys, key=lambda value: (-len(value), value))

    token_owners = gameplay_character_token_owners(entries)
    owners: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for character_id, row in sorted(character_table.items()):
        if not isinstance(row, dict):
            continue
        match = CHARACTER_ID_TOKEN_RE.match(str(character_id or ""))
        if not match:
            continue
        for owner_id in token_owners.get(match.group(1).lower()) or []:
            for voice in row.get("profileVoice") or []:
                if not isinstance(voice, dict):
                    continue
                vo_id = str(voice.get("voId") or "").strip()
                if not vo_id or not GAMEPLAY_PROFILE_VOICE_RE.search(vo_id):
                    continue
                key = (owner_id, vo_id.lower())
                if key in seen:
                    continue
                seen.add(key)
                tail = vo_id[len(str(character_id)) + 1:] if vo_id.lower().startswith(str(character_id).lower() + "_") else vo_id
                trigger_key = next(
                    (candidate for candidate in sorted_triggers if tail == candidate or tail.startswith(candidate + "_")),
                    "",
                )
                owners[owner_id].append({
                    "id": vo_id,
                    "actionKind": profile_voice_action_kind(vo_id),
                    "characterId": character_id,
                    "profileVoiceIndex": voice.get("voiceIndex"),
                    "triggerKey": trigger_key,
                    "source": character_source,
                })
    return {
        "owners": [
            {"ownerId": owner_id, "voices": sorted(voices, key=lambda row: str(row.get("id") or ""))}
            for owner_id, voices in sorted(owners.items())
        ],
        "counts": {
            "profileVoiceRefs": sum(len(voices) for voices in owners.values()),
            "profileVoiceOwners": len(owners),
            "profileVoiceRefsWithTrigger": sum(
                1 for voices in owners.values() for voice in voices if voice.get("triggerKey")
            ),
        },
    }

def animation_clip_audio_events(data: bytes) -> tuple[str, list[dict[str, Any]]]:
    """Read the small scalar event portion of an exported Unity .anim YAML."""

    clip_name = ""
    current: dict[str, Any] | None = None
    events: list[dict[str, Any]] = []
    in_events = False
    event_index = -1

    def finish() -> None:
        nonlocal current
        if current and current.get("function") in ANIMATION_AUDIO_FUNCTIONS and current.get("eventId"):
            events.append(current)
        current = None

    for raw_line in data.splitlines():
        line = raw_line.decode("utf-8", errors="replace")
        if not clip_name and line.startswith("  m_Name: "):
            clip_name = line.removeprefix("  m_Name: ").strip().strip("'\"")
        elif line == "  m_Events:":
            in_events = True
        elif in_events and line.startswith("  - time: "):
            finish()
            event_index += 1
            raw_time = line.removeprefix("  - time: ").strip()
            try:
                time_value: float | str = float(raw_time)
            except ValueError:
                time_value = raw_time
            current = {"index": event_index, "time": time_value}
        elif current is not None and line.startswith("    functionName: "):
            current["function"] = line.removeprefix("    functionName: ").strip().strip("'\"")
        elif current is not None and line.startswith("    data: "):
            current["eventId"] = line.removeprefix("    data: ").strip().strip("'\"")
        elif current is not None and line.startswith("    floatParameter: "):
            raw_value = line.removeprefix("    floatParameter: ").strip()
            try:
                current["floatParameter"] = float(raw_value)
            except ValueError:
                current["floatParameter"] = raw_value
        elif current is not None and line.startswith("    intParameter: "):
            raw_value = line.removeprefix("    intParameter: ").strip()
            try:
                current["intParameter"] = int(raw_value)
            except ValueError:
                current["intParameter"] = raw_value
    finish()
    return clip_name, events

def animation_clip_path_id(path: Path) -> int | None:
    """Recover the signed Unity PathID encoded in an exported clip filename."""

    match = ANIMATION_CLIP_PATH_ID_SUFFIX_RE.search(path.stem)
    if not match:
        return None
    try:
        value = int(match.group("path_id"), 16)
    except (TypeError, ValueError):
        return None
    return value - (1 << 64) if value >= (1 << 63) else value

def animestudio_storage_root(path: Path) -> str:
    """Return the VFS storage root encoded in an AnimeStudio export path."""

    lowered = {part.lower(): part for part in path.parts}
    for storage_root in ("StreamingAssets", "Persistent"):
        if storage_root.lower() in lowered:
            return storage_root
    return ""

def _animator_data_node(value: Any) -> dict[str, Any] | None:
    """Unwrap one serialized Unity ``OffsetPtr.data`` value safely."""

    if not isinstance(value, dict):
        return None
    nested = value.get("data")
    return nested if isinstance(nested, dict) else value

def animator_controller_state_clip_refs(
    payload: dict[str, Any],
) -> dict[int, list[dict[str, Any]]]:
    """Return authored state/blend-tree references keyed by clip slot.

    Unity's serialized ``m_AnimationClips`` array is the only stable bridge
    from an AnimatorController state to an AnimationClip in the exported
    JSON.  This parser deliberately reports authored membership only: it does
    not follow transitions, parameters, entry selectors, or runtime layer
    activation.  Malformed nodes are skipped rather than guessed.
    """

    clips = payload.get("m_AnimationClips")
    controller = _animator_data_node(payload.get("m_Controller"))
    if not isinstance(clips, list) or not isinstance(controller, dict):
        return {}
    valid_slots = {
        index
        for index, clip in enumerate(clips)
        if isinstance(clip, dict)
        and isinstance(clip.get("m_PathID"), int)
        and not isinstance(clip.get("m_PathID"), bool)
        and int(clip.get("m_PathID") or 0) != 0
    }
    if not valid_slots:
        return {}

    layers = controller.get("m_LayerArray")
    layer_roots: dict[int, list[int]] = defaultdict(list)
    if isinstance(layers, list):
        for layer_index, layer_value in enumerate(layers):
            layer = _animator_data_node(layer_value)
            if not isinstance(layer, dict):
                continue
            state_machine_index = layer.get("m_StateMachineIndex")
            if isinstance(state_machine_index, int) and not isinstance(state_machine_index, bool):
                layer_roots.setdefault(int(state_machine_index), []).append(layer_index)

    state_machines = controller.get("m_StateMachineArray")
    if not isinstance(state_machines, list):
        return {}
    result: dict[int, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[int, int, int, int]] = set()
    for state_machine_index, state_machine_value in enumerate(state_machines):
        state_machine = _animator_data_node(state_machine_value)
        if not isinstance(state_machine, dict):
            continue
        states = state_machine.get("m_StateConstantArray")
        if not isinstance(states, list):
            continue
        for state_index, state_value in enumerate(states):
            state = _animator_data_node(state_value)
            if not isinstance(state, dict):
                continue
            blend_trees = state.get("m_BlendTreeConstantArray")
            if not isinstance(blend_trees, list):
                continue
            for tree_index, tree_value in enumerate(blend_trees):
                tree = _animator_data_node(tree_value)
                if not isinstance(tree, dict):
                    continue
                nodes = tree.get("m_NodeArray")
                if not isinstance(nodes, list):
                    continue
                for node_index, node_value in enumerate(nodes):
                    node = _animator_data_node(node_value)
                    if not isinstance(node, dict):
                        continue
                    clip_slot = node.get("m_ClipID")
                    if (
                        not isinstance(clip_slot, int)
                        or isinstance(clip_slot, bool)
                        or clip_slot not in valid_slots
                    ):
                        continue
                    key = (state_machine_index, state_index, tree_index, node_index)
                    if key in seen:
                        continue
                    seen.add(key)
                    result[int(clip_slot)].append({
                        "stateMachineIndex": state_machine_index,
                        "stateIndex": state_index,
                        "stateNameHash": state.get("m_NameID"),
                        "statePathHash": state.get("m_FullPathID"),
                        "stateTagHash": state.get("m_TagID"),
                        "stateMachineLayerIndices": list(layer_roots.get(state_machine_index) or []),
                        "stateMachineReferencedByLayer": state_machine_index in layer_roots,
                        "blendTreeIndex": tree_index,
                        "blendTreeNodeIndex": node_index,
                        "blendType": node.get("m_BlendType"),
                        "clipSlot": int(clip_slot),
                        "reachability": "authoredStateMembership",
                        "runtimeExecution": "unobserved",
                    })
    for rows in result.values():
        rows.sort(key=lambda row: (
            int(row.get("stateMachineIndex") or 0),
            int(row.get("stateIndex") or 0),
            int(row.get("blendTreeIndex") or 0),
            int(row.get("blendTreeNodeIndex") or 0),
        ))
    return dict(result)

def collect_animation_controller_index(export_root: Path) -> dict[str, Any]:
    """Index resolved AnimatorController->AnimationClip PPtrs fail-closed.

    The exported ``$animestudio.pptrReferences`` records are the only accepted
    evidence here.  Name matching, raw controller payload guesses, and
    AnimatorOverrideController pairs are deliberately excluded until their
    serialized-file context can be resolved without ambiguity.
    """

    roots = [export_root / rel for rel in ANIMATOR_CONTROLLER_RELS]
    available_roots = [root for root in roots if root.is_dir()]
    by_clip_path_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    by_clip_storage_path_id: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    counts = {
        "status": "unavailable" if not available_roots else "complete",
        "sourceRoot": normalize_posix(ANIMATOR_CONTROLLER_REL),
        "sourceRoots": [
            normalize_posix(rel) for rel in ANIMATOR_CONTROLLER_RELS
        ],
        "availableSourceRoots": [
            normalize_posix(root.relative_to(export_root)) for root in available_roots
        ],
        "filesScanned": 0,
        "filesWithDirectReferences": 0,
        "malformedFiles": 0,
        "directReferenceCount": 0,
        "uniqueReferencedClipPathIds": 0,
        "controllerCount": 0,
        "controllersWithAuthoredStateRefs": 0,
        "authoredStateClipReferenceCount": 0,
        "overrideControllersExcluded": True,
    }
    if not available_roots:
        return {
            "byClipPathId": {},
            "byClipStoragePathId": {},
            "summary": counts,
        }

    seen_controllers: set[tuple[str, str, str]] = set()
    seen_references: set[tuple[int, str, str, str]] = set()
    controller_paths = sorted(
        (path for root in available_roots for path in root.glob("*.json")),
        key=lambda value: normalize_posix(value.relative_to(export_root)).lower(),
    )
    for path in controller_paths:
        counts["filesScanned"] += 1
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError):
            counts["malformedFiles"] += 1
            continue
        if not isinstance(payload, dict):
            counts["malformedFiles"] += 1
            continue
        metadata = payload.get("$animestudio")
        if not isinstance(metadata, dict) or metadata.get("type") != "AnimatorController":
            # A valid JSON file without the exporter identity envelope is not
            # safe to use as a direct-reference source.
            counts["malformedFiles"] += 1
            continue
        references = metadata.get("pptrReferences")
        if not isinstance(references, list):
            counts["malformedFiles"] += 1
            continue
        controller_name = str(
            payload.get("m_Name") or metadata.get("name") or path.stem
        ).strip()
        controller_source_file = str(metadata.get("sourceFile") or "").strip()
        controller_path_id = metadata.get("pathId")
        storage_root = animestudio_storage_root(path)
        controller_key = (
            controller_source_file,
            str(controller_path_id) if isinstance(controller_path_id, int) else "",
            normalize_posix(path.relative_to(export_root)),
        )
        state_refs_by_slot = animator_controller_state_clip_refs(payload)
        file_contexts: dict[tuple[int, str], dict[str, Any]] = {}
        file_state_ref_count = sum(len(rows) for rows in state_refs_by_slot.values())
        if file_state_ref_count:
            counts["controllersWithAuthoredStateRefs"] += 1
            counts["authoredStateClipReferenceCount"] += file_state_ref_count
        direct_file_reference_count = 0
        for reference in references:
            if not isinstance(reference, dict):
                continue
            target = reference.get("target")
            target = target if isinstance(target, dict) else {}
            target_type = str(
                reference.get("targetType") or target.get("type") or ""
            )
            resolution_status = str(reference.get("resolutionStatus") or "")
            if target_type != "AnimationClip" or not resolution_status.startswith("resolved"):
                continue
            target_path_id = reference.get("targetPathId")
            if not isinstance(target_path_id, int) or isinstance(target_path_id, bool):
                target_path_id = target.get("pathId")
            target_source_file = str(
                reference.get("targetSourceFile") or target.get("serializedFile") or ""
            ).strip()
            if (
                not isinstance(target_path_id, int)
                or isinstance(target_path_id, bool)
                or not target_source_file
            ):
                continue
            reference_key = (
                target_path_id,
                target_source_file,
                controller_key[2],
                controller_key[0],
            )
            if reference_key in seen_references:
                continue
            seen_references.add(reference_key)
            if controller_key not in seen_controllers:
                seen_controllers.add(controller_key)
                counts["controllerCount"] += 1
            context_key = (target_path_id, target_source_file)
            context = file_contexts.get(context_key)
            if context is None:
                context = {
                    "name": controller_name,
                    "sourcePath": controller_key[2],
                    "sourceFile": controller_source_file,
                    "pathId": controller_path_id,
                    "targetSourceFile": target_source_file,
                    "storageRoot": storage_root,
                    "resolutionStatus": resolution_status,
                    "clipSlots": [],
                    "authoredStateReferences": [],
                }
                file_contexts[context_key] = context
            reference_path = str(reference.get("path") or "")
            slot_match = re.search(r"m_AnimationClips\[(\d+)\]", reference_path)
            if slot_match:
                clip_slot = int(slot_match.group(1))
                if clip_slot not in context["clipSlots"]:
                    context["clipSlots"].append(clip_slot)
                for state_ref in state_refs_by_slot.get(clip_slot) or []:
                    if state_ref not in context["authoredStateReferences"]:
                        context["authoredStateReferences"].append(dict(state_ref))
            direct_file_reference_count += 1
            counts["directReferenceCount"] += 1
        for context_key, context in file_contexts.items():
            context["clipSlots"] = sorted(context.get("clipSlots") or [])
            context["authoredStateReferences"] = sorted(
                context.get("authoredStateReferences") or [],
                key=lambda row: (
                    int(row.get("stateMachineIndex") or 0),
                    int(row.get("stateIndex") or 0),
                    int(row.get("blendTreeIndex") or 0),
                    int(row.get("blendTreeNodeIndex") or 0),
                ),
            )
            context["authoredStateReferenceCount"] = len(context["authoredStateReferences"])
            by_clip_path_id[context_key[0]].append(context)
            by_clip_storage_path_id[(storage_root, context_key[0])].append(context)
        if direct_file_reference_count:
            counts["filesWithDirectReferences"] += 1

    for path_id, contexts in by_clip_path_id.items():
        by_clip_path_id[path_id] = sorted(
            contexts,
            key=lambda row: (
                str(row.get("name") or ""),
                str(row.get("sourcePath") or ""),
                str(row.get("targetSourceFile") or ""),
            ),
        )
    counts["uniqueReferencedClipPathIds"] = len(by_clip_path_id)
    if counts["malformedFiles"] and counts["filesWithDirectReferences"]:
        counts["status"] = "partial"
    for storage_path_id, contexts in by_clip_storage_path_id.items():
        by_clip_storage_path_id[storage_path_id] = sorted(
            contexts,
            key=lambda row: (
                str(row.get("name") or ""),
                str(row.get("sourcePath") or ""),
                str(row.get("targetSourceFile") or ""),
            ),
        )
    return {
        "byClipPathId": dict(by_clip_path_id),
        "byClipStoragePathId": dict(by_clip_storage_path_id),
        "summary": counts,
    }

def collect_animation_override_index(export_root: Path) -> dict[str, Any]:
    """Index serialized AnimatorOverrideController clip substitutions.

    The current AnimeStudio JSON exporter writes the raw override payload but
    does not attach its ``$animestudio`` source-file envelope.  Unity PPtrs are
    therefore only safe to join by a PathID when that PathID is unique in its
    exported VFS storage root.  Keep that limitation explicit: these rows annotate an
    effective clip substitution, but never claim an exact serialized-file
    join or live override activation.
    """

    roots = [export_root / rel for rel in ANIMATOR_OVERRIDE_CONTROLLER_RELS]
    available_roots = [root for root in roots if root.is_dir()]
    clip_roots = [export_root / rel for rel in ANIMATION_CLIP_RELS]
    controller_roots = [export_root / rel for rel in ANIMATOR_CONTROLLER_RELS]
    counts = {
        "status": "unavailable" if not available_roots else "complete",
        "sourceRoot": normalize_posix(ANIMATOR_OVERRIDE_CONTROLLER_REL),
        "sourceRoots": [
            normalize_posix(rel) for rel in ANIMATOR_OVERRIDE_CONTROLLER_RELS
        ],
        "clipSourceRoot": normalize_posix(ANIMATION_CLIP_REL),
        "clipSourceRoots": [normalize_posix(rel) for rel in ANIMATION_CLIP_RELS],
        "filesScanned": 0,
        "malformedFiles": 0,
        "malformedReferences": 0,
        "overrideControllerCount": 0,
        "controllerPathIdReferences": 0,
        "controllerPathIdCorpusUnique": 0,
        "controllerSourceExact": 0,
        "controllerPathIdUnresolved": 0,
        "controllerPathIdAmbiguous": 0,
        "overrideReferenceCount": 0,
        "baseClipReferenceCount": 0,
        "replacementReferenceCount": 0,
        "effectiveClipReferenceCount": 0,
        "effectiveClipCorpusUniqueReferences": 0,
        "effectiveClipSourceExactReferences": 0,
        "effectiveClipMissingReferences": 0,
        "effectiveClipAmbiguousReferences": 0,
        "uniqueEffectiveClipPathIds": 0,
        "assetIdentityTokenCount": 0,
        "assetIdentityTokenReferences": 0,
        "sourceBoundary": (
            "Override payloads have no exporter source-file envelope. When the AssetMap "
            "uniquely identifies the override object's Source+PathID and a PPtr has FileID=0, "
            "same-file controller/clip joins are exact; all other joins remain VFS-root-scoped "
            "corpus-unique PathID annotations. Neither proves live override activation."
        ),
    }
    if not available_roots:
        return {
            "byClipPathId": {},
            "byClipStoragePathId": {},
            "summary": counts,
        }

    def path_id(value: Any) -> int | None:
        if not isinstance(value, int) or isinstance(value, bool) or value == 0:
            return None
        return int(value)

    def is_local_file_id(pointer: dict[str, Any]) -> bool:
        value = pointer.get("m_FileID")
        return isinstance(value, int) and not isinstance(value, bool) and value == 0

    # Recover the serialized-file source of exported override/controller/clip
    # objects from the generated AssetMap.  This is stronger than a bare PathID
    # only for FileID=0 pointers, whose target is in the same serialized file.
    asset_sources: dict[tuple[str, str, int], list[str]] = defaultdict(list)
    for storage_root in ("StreamingAssets", "Persistent"):
        asset_map = (
            export_root / "recovered" / "AnimeStudio-cli" / storage_root
            / "maps" / f"endfield_{storage_root.lower()}_assets.json"
        )
        for entry in iter_asset_map_objects(asset_map):
            if not isinstance(entry, dict):
                continue
            asset_type = str(entry.get("Type") or "")
            if asset_type not in {"AnimationClip", "AnimatorController", "AnimatorOverrideController"}:
                continue
            asset_path_id = path_id(entry.get("PathID"))
            source = normalize_posix(str(entry.get("Source") or "")).lower()
            if asset_path_id is None or not source:
                continue
            key = (storage_root, asset_type, asset_path_id)
            if source not in asset_sources[key]:
                asset_sources[key].append(source)

    # PathID uniqueness is measured over the actual exported AnimationClip
    # files within one VFS storage root, not over names. Ambiguous or missing
    # IDs remain visible but are excluded from stronger reachability claims.
    clip_paths_by_storage_id: dict[tuple[str, int], list[str]] = defaultdict(list)
    for clip_root in clip_roots:
        if clip_root.is_dir():
            storage_root = animestudio_storage_root(clip_root)
            for path in clip_root.glob("*.anim"):
                clip_path_id = animation_clip_path_id(path)
                if clip_path_id is None:
                    continue
                relative_path = normalize_posix(path.relative_to(export_root))
                clip_paths_by_storage_id[(storage_root, clip_path_id)].append(relative_path)
    for paths in clip_paths_by_storage_id.values():
        paths.sort()

    # Controller JSON has an identity envelope, unlike override JSON.  Use it
    # only to label a storage-root-scoped corpus-unique target; the override's
    # missing FileID source context is deliberately not reconstructed from names.
    controller_paths_by_storage_id: dict[
        tuple[str, int], list[dict[str, Any]]
    ] = defaultdict(list)
    for controller_root in controller_roots:
        if controller_root.is_dir():
            storage_root = animestudio_storage_root(controller_root)
            for path in controller_root.glob("*.json"):
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, ValueError):
                    continue
                if not isinstance(payload, dict):
                    continue
                metadata = payload.get("$animestudio")
                if not isinstance(metadata, dict) or metadata.get("type") != "AnimatorController":
                    continue
                controller_path_id = path_id(metadata.get("pathId"))
                if controller_path_id is None:
                    continue
                context = {
                    "name": str(payload.get("m_Name") or metadata.get("name") or path.stem),
                    "sourcePath": normalize_posix(path.relative_to(export_root)),
                    "sourceFile": str(metadata.get("sourceFile") or ""),
                    "pathId": controller_path_id,
                    "storageRoot": storage_root,
                    "assetMapSources": list(asset_sources.get(
                        (storage_root, "AnimatorController", controller_path_id), []
                    )),
                }
                controller_paths_by_storage_id[
                    (storage_root, controller_path_id)
                ].append(context)

    by_clip_path_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    by_clip_storage_path_id: dict[
        tuple[str, int], list[dict[str, Any]]
    ] = defaultdict(list)
    identity_tokens: set[str] = set()
    override_paths = sorted(
        (path for root in available_roots for path in root.glob("*.json")),
        key=lambda value: normalize_posix(value.relative_to(export_root)).lower(),
    )
    for path in override_paths:
        storage_root = animestudio_storage_root(path)
        counts["filesScanned"] += 1
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError):
            counts["malformedFiles"] += 1
            continue
        if not isinstance(payload, dict) or not isinstance(payload.get("m_Clips"), list):
            counts["malformedFiles"] += 1
            continue
        counts["overrideControllerCount"] += 1
        override_name = str(payload.get("m_Name") or path.stem)
        identity_match = ANIMATOR_OVERRIDE_IDENTITY_RE.search(path.stem)
        identity_token = identity_match.group(1).lower() if identity_match else ""
        if identity_token:
            identity_tokens.add(identity_token)

        controller_pointer = payload.get("m_Controller")
        controller_pointer = controller_pointer if isinstance(controller_pointer, dict) else {}
        controller_path_id = path_id(controller_pointer.get("m_PathID"))
        override_path_id = animation_clip_path_id(path)
        override_sources = asset_sources.get(
            (storage_root, "AnimatorOverrideController", override_path_id or 0), []
        )
        override_source = override_sources[0] if len(override_sources) == 1 else ""
        counts["controllerPathIdReferences"] += 1
        controller_matches = (
            controller_paths_by_storage_id.get((storage_root, controller_path_id or 0)) or []
        )
        exact_controller_matches = [
            row for row in controller_matches
            if override_source
            and is_local_file_id(controller_pointer)
            and override_source in (row.get("assetMapSources") or [])
        ]
        if len(exact_controller_matches) == 1:
            controller_join_status = "exactSameSerializedFileControllerPathId"
            controller_context = exact_controller_matches[0]
            counts["controllerSourceExact"] += 1
        elif len(controller_matches) == 1:
            controller_join_status = "corpusUniqueControllerPathId"
            controller_context = controller_matches[0]
            counts["controllerPathIdCorpusUnique"] += 1
        elif len(controller_matches) > 1:
            controller_join_status = "ambiguousControllerPathId"
            controller_context = {}
            counts["controllerPathIdAmbiguous"] += 1
        else:
            controller_join_status = "missingControllerPathId"
            controller_context = {}
            counts["controllerPathIdUnresolved"] += 1

        for clip_index, row in enumerate(payload.get("m_Clips") or []):
            if not isinstance(row, dict):
                counts["malformedReferences"] += 1
                continue
            original_pointer = row.get("m_OriginalClip")
            original_pointer = original_pointer if isinstance(original_pointer, dict) else {}
            override_pointer = row.get("m_OverrideClip")
            override_pointer = override_pointer if isinstance(override_pointer, dict) else {}
            original_path_id = path_id(original_pointer.get("m_PathID"))
            override_path_id = path_id(override_pointer.get("m_PathID"))
            if original_path_id is None:
                counts["malformedReferences"] += 1
                continue
            is_replacement = not bool(override_pointer.get("IsNull")) and override_path_id is not None
            effective_path_id = override_path_id if is_replacement else original_path_id
            counts["overrideReferenceCount"] += 1
            counts["effectiveClipReferenceCount"] += 1
            if is_replacement:
                counts["replacementReferenceCount"] += 1
            else:
                counts["baseClipReferenceCount"] += 1
            clip_matches = clip_paths_by_storage_id.get((storage_root, effective_path_id)) or []
            effective_pointer = override_pointer if is_replacement else original_pointer
            exact_clip_source = bool(
                override_source
                and is_local_file_id(effective_pointer)
                and override_source in asset_sources.get(
                    (storage_root, "AnimationClip", effective_path_id), []
                )
            )
            if exact_clip_source:
                clip_join_status = "exactSameSerializedFileAnimationClipPathId"
                counts["effectiveClipSourceExactReferences"] += 1
            elif len(clip_matches) == 1:
                clip_join_status = "corpusUniqueAnimationClipPathId"
                counts["effectiveClipCorpusUniqueReferences"] += 1
            elif len(clip_matches) > 1:
                clip_join_status = "ambiguousAnimationClipPathId"
                counts["effectiveClipAmbiguousReferences"] += 1
            else:
                clip_join_status = "missingAnimationClipPathId"
                counts["effectiveClipMissingReferences"] += 1
            context = {
                "overrideName": override_name,
                "overrideSourcePath": normalize_posix(path.relative_to(export_root)),
                "overrideControllerPathId": controller_path_id,
                "overrideAssetMapSource": override_source,
                "controllerJoinStatus": controller_join_status,
                "controllerName": controller_context.get("name") or "",
                "controllerSourcePath": controller_context.get("sourcePath") or "",
                "controllerSourceFile": controller_context.get("sourceFile") or "",
                "originalClipPathId": original_path_id,
                "overrideClipPathId": override_path_id,
                "effectiveClipPathId": effective_path_id,
                "clipIndex": clip_index,
                "mappingKind": "replacement" if is_replacement else "baseClip",
                "clipJoinStatus": clip_join_status,
                "effectiveClipSourcePaths": clip_matches,
                "assetIdentityToken": identity_token,
                "runtimeActivation": "unobserved",
                "storageRoot": storage_root,
            }
            by_clip_path_id[effective_path_id].append(context)
            by_clip_storage_path_id[(storage_root, effective_path_id)].append(context)

    counts["uniqueEffectiveClipPathIds"] = len(by_clip_path_id)
    counts["assetIdentityTokenCount"] = len(identity_tokens)
    counts["assetIdentityTokenReferences"] = sum(
        1
        for contexts in by_clip_path_id.values()
        for context in contexts
        if context.get("assetIdentityToken")
    )
    if (
        counts["malformedFiles"]
        or counts["malformedReferences"]
        or counts["controllerPathIdUnresolved"]
        or counts["controllerPathIdAmbiguous"]
        or counts["effectiveClipMissingReferences"]
        or counts["effectiveClipAmbiguousReferences"]
    ):
        counts["status"] = "partial"
    for contexts in by_clip_path_id.values():
        contexts.sort(
            key=lambda row: (
                str(row.get("overrideName") or ""),
                int(row.get("clipIndex") or 0),
                str(row.get("overrideSourcePath") or ""),
            )
        )
    for contexts in by_clip_storage_path_id.values():
        contexts.sort(
            key=lambda row: (
                str(row.get("overrideName") or ""),
                int(row.get("clipIndex") or 0),
                str(row.get("overrideSourcePath") or ""),
            )
        )
    return {
        "byClipPathId": dict(by_clip_path_id),
        "byClipStoragePathId": dict(by_clip_storage_path_id),
        "summary": counts,
    }

def animation_controller_contexts(
    controller_index: dict[str, Any], path: Path
) -> list[dict[str, Any]]:
    """Return direct controller contexts for one exported AnimationClip."""

    path_id = animation_clip_path_id(path)
    if path_id is None:
        return []
    contexts = controller_index.get((animestudio_storage_root(path), path_id)) or {}
    return [dict(row) for row in contexts if isinstance(row, dict)]

def animation_override_contexts(
    override_index: dict[str, Any], path: Path
) -> list[dict[str, Any]]:
    """Return corpus-unique override substitutions for one AnimationClip."""

    path_id = animation_clip_path_id(path)
    if path_id is None:
        return []
    contexts = override_index.get((animestudio_storage_root(path), path_id)) or {}
    return [dict(row) for row in contexts if isinstance(row, dict)]

def animation_override_reachability_status(contexts: Iterable[dict[str, Any]]) -> str:
    """Classify exact same-file mappings ahead of bounded corpus-unique joins."""

    rows = [row for row in contexts if isinstance(row, dict)]
    if any(
        str(row.get("clipJoinStatus") or "").startswith("exactSameSerializedFile")
        and str(row.get("controllerJoinStatus") or "").startswith("exactSameSerializedFile")
        for row in rows
    ):
        return "exactAnimatorOverrideMapping"
    if any(
        str(row.get("clipJoinStatus") or "") == "corpusUniqueAnimationClipPathId"
        and str(row.get("controllerJoinStatus") or "") == "corpusUniqueControllerPathId"
        for row in rows
    ):
        return "corpusUniqueAnimatorOverrideMapping"
    return "unresolved"

def animation_clip_reachability_status(
    evidence: Iterable[dict[str, Any]],
) -> str:
    """Classify one Event's clip rows without promoting unresolved evidence."""

    rows = [row for row in evidence if isinstance(row, dict)]
    direct = sum(bool(row.get("animatorControllerCount")) for row in rows)
    if not direct:
        return "unresolved"
    if direct == len(rows):
        return "directAnimatorController"
    return "mixedAnimatorControllerReachability"

def collect_gameplay_animation_audio(
    export_root: Path,
    entries: list[dict[str, Any]],
    enemies: list[dict[str, Any]],
    enemy_source_files: dict[str, list[Path]] | None = None,
) -> dict[str, Any]:
    """Collect exact AnimationClip audio callbacks with bounded actor ownership."""

    token_owners: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for token, owner_ids in gameplay_character_token_owners(entries).items():
        for owner_id in owner_ids:
            token_owners[("actor", token)].append({
                "ownerKind": "character",
                "ownerId": owner_id,
                "ownershipSources": ["Gameplay character/action identifiers"],
            })

    enemy_tokens = enemy_template_animation_tokens(export_root, enemies, enemy_source_files)
    for owner_id, tokens in enemy_tokens.items():
        for token, sources in tokens.items():
            token_owners[("monster", token)].append({
                "ownerKind": "enemy",
                "ownerId": owner_id,
                "ownershipSources": sorted(sources),
            })

    roots = [export_root / rel for rel in ANIMATION_CLIP_RELS]
    owners: dict[tuple[str, str], dict[str, Any]] = {}
    unowned_events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    controller_index_data = collect_animation_controller_index(export_root)
    controller_index = controller_index_data.get("byClipStoragePathId") or {}
    override_index_data = collect_animation_override_index(export_root)
    override_index = override_index_data.get("byClipStoragePathId") or {}
    controller_reachable_clips = 0
    controller_unresolved_clips = 0
    controller_reachable_callback_rows = 0
    controller_unresolved_callback_rows = 0
    override_reachable_clips = 0
    override_unresolved_clips = 0
    override_reachable_callback_rows = 0
    override_unresolved_callback_rows = 0
    scanned_clips = 0
    matched_clips = 0
    unowned_clips = 0
    owned_callback_rows = 0
    unowned_callback_rows = 0
    for root in roots:
        if not root.exists():
            continue
        candidate_paths = sorted([
            *root.glob("A_actor_*.anim"),
            *root.glob("A_monster_*.anim"),
        ])
        for path in candidate_paths:
            scanned_clips += 1
            filename_clip_name = ANIMATION_CLIP_HASH_SUFFIX_RE.sub("", path.stem)
            filename_match = ANIMATION_ACTOR_RE.match(filename_clip_name)
            matched_owners = (
                token_owners.get(
                    (filename_match.group(1).lower(), filename_match.group(2).lower())
                ) or []
                if filename_match
                else []
            )
            try:
                data = path.read_bytes()
            except OSError:
                continue
            if b"functionName: PostAudio" not in data and b"functionName: OnCustomFootStep" not in data:
                continue
            clip_name, clip_events = animation_clip_audio_events(data)
            if not clip_events:
                continue
            clip_kind = animation_clip_action_kind(clip_name)
            clip_context = animation_clip_context(clip_name)
            controller_contexts = animation_controller_contexts(controller_index, path)
            clip_reachability = (
                "directAnimatorController" if controller_contexts else "unresolved"
            )
            override_contexts = animation_override_contexts(override_index, path)
            override_reachability = animation_override_reachability_status(override_contexts)
            if controller_contexts:
                controller_reachable_clips += 1
                controller_reachable_callback_rows += len(clip_events)
            else:
                controller_unresolved_clips += 1
                controller_unresolved_callback_rows += len(clip_events)
            if override_reachability != "unresolved":
                override_reachable_clips += 1
                override_reachable_callback_rows += len(clip_events)
            else:
                override_unresolved_clips += 1
                override_unresolved_callback_rows += len(clip_events)
            try:
                clip_source = normalize_posix(path.relative_to(export_root))
            except ValueError:
                clip_source = normalize_posix(path)
            base_evidence = {
                "kind": "animationClipEvent",
                "clip": clip_name,
                "clipSource": clip_source,
                "actionKind": clip_kind,
                "clipContext": clip_context,
                "clipReachability": clip_reachability,
                "animatorControllerCount": len(controller_contexts),
                "animatorControllerContexts": controller_contexts,
                "overrideReachability": override_reachability,
                "animatorOverrideCount": len(override_contexts),
                "animatorOverrideContexts": override_contexts,
            }
            if matched_owners:
                matched_clips += 1
                owned_callback_rows += len(clip_events)
                for owner in matched_owners:
                    owner_key = (owner["ownerKind"], owner["ownerId"])
                    record = owners.setdefault(owner_key, {
                        **owner,
                        "events": defaultdict(list),
                    })
                    for event in clip_events:
                        authored_event_id = str(event.get("eventId") or "").strip()
                        event_key = authored_event_id.lower()
                        if not event_key:
                            continue
                        record["events"][event_key].append({
                            **base_evidence,
                            "authoredEventId": authored_event_id,
                            "eventIndex": event.get("index"),
                            "time": event.get("time"),
                            "function": event.get("function"),
                            "floatParameter": event.get("floatParameter"),
                            "intParameter": event.get("intParameter"),
                        })
            else:
                unowned_clips += 1
                unowned_callback_rows += len(clip_events)
                for event in clip_events:
                    authored_event_id = str(event.get("eventId") or "").strip()
                    event_key = authored_event_id.lower()
                    if not event_key:
                        continue
                    unowned_events[event_key].append({
                        **base_evidence,
                        "authoredEventId": authored_event_id,
                        "ownerStatus": "unresolved",
                        "actorKindToken": filename_match.group(1).lower() if filename_match else "",
                        "actorIdentityToken": filename_match.group(2).lower() if filename_match else "",
                        "eventIndex": event.get("index"),
                        "time": event.get("time"),
                        "function": event.get("function"),
                        "floatParameter": event.get("floatParameter"),
                        "intParameter": event.get("intParameter"),
                    })

    event_names = {
        event_key
        for owner in owners.values()
        for event_key in owner["events"]
    }.union(unowned_events)
    normalized_owners: list[dict[str, Any]] = []
    for owner in owners.values():
        normalized_owners.append({
            **owner,
            "events": {
                event_key: sorted(
                    evidence,
                    key=lambda row: (str(row.get("clip") or ""), float(row.get("time") or 0), str(row.get("function") or "")),
                )
                for event_key, evidence in sorted(owner["events"].items())
            },
        })
    return {
        "eventNames": event_names,
        "owners": sorted(normalized_owners, key=lambda row: (row["ownerKind"], row["ownerId"])),
        "unownedEvents": {
            event_key: sorted(
                evidence,
                key=lambda row: (
                    str(row.get("clip") or ""),
                    float(row.get("time") or 0),
                    str(row.get("function") or ""),
                ),
            )
            for event_key, evidence in sorted(unowned_events.items())
        },
        "counts": {
            "animationAudioClipsScanned": scanned_clips,
            "animationAudioClipsOwned": matched_clips,
            "animationAudioClipsOwnerUnresolved": unowned_clips,
            "animationAudioCallbackRows": owned_callback_rows + unowned_callback_rows,
            "animationAudioOwnedCallbackRows": owned_callback_rows,
            "animationAudioOwnerUnresolvedCallbackRows": unowned_callback_rows,
            "animationAudioEventNames": len(event_names),
            "animationAudioOwnerEventRefs": sum(len(owner["events"]) for owner in owners.values()),
            "animationAudioOwnerUnresolvedEventRefs": len(unowned_events),
            "animationAudioControllerReachableClips": controller_reachable_clips,
            "animationAudioControllerUnresolvedClips": controller_unresolved_clips,
            "animationAudioControllerReachableCallbackRows": controller_reachable_callback_rows,
            "animationAudioControllerUnresolvedCallbackRows": controller_unresolved_callback_rows,
            "animationAudioControllerReferences": int(
                (controller_index_data.get("summary") or {}).get("directReferenceCount") or 0
            ),
            "animationAudioOverrideReachableClips": override_reachable_clips,
            "animationAudioOverrideUnresolvedClips": override_unresolved_clips,
            "animationAudioOverrideReachableCallbackRows": override_reachable_callback_rows,
            "animationAudioOverrideUnresolvedCallbackRows": override_unresolved_callback_rows,
            "animationAudioOverrideReferences": int(
                (override_index_data.get("summary") or {}).get("overrideReferenceCount") or 0
            ),
        },
        "animationControllerIndex": controller_index_data.get("summary") or {},
        "animationOverrideIndex": override_index_data.get("summary") or {},
    }

def gameplay_buff_audio(
    initial_buff_ids: set[str],
    buff_records: dict[str, dict[str, Any]],
) -> dict[str, set[str]]:
    """Return event -> contributing BuffData ids through exact buff references."""

    events: dict[str, set[str]] = defaultdict(set)
    queue: deque[str] = deque(sorted(initial_buff_ids))
    visited: set[str] = set()
    while queue:
        buff_id = queue.popleft()
        if not buff_id or buff_id in visited:
            continue
        visited.add(buff_id)
        record = buff_records.get(buff_id) or {}
        for event_id in record.get("events") or set():
            events[event_id].add(buff_id)
        for linked_id in sorted(record.get("buffs") or set()):
            if linked_id not in visited:
                queue.append(linked_id)
    return events

def play_sound_action_marker(row: dict[str, Any]) -> tuple[Any, ...]:
    """Stable identity for one decoded BuffData PlaySound timeline action."""

    return tuple(
        row.get(key)
        for key in (
            "buffId", "eventId", "timelineActionIndex", "actionDataIndex",
            "startFrame", "endFrame", "serverActionIndex",
        )
    )

def seed_buff_play_sound_events(
    buff_records: dict[str, dict[str, Any]],
    by_buff_event: dict[str, dict[str, list[dict[str, Any]]]],
) -> int:
    """Add exact typed PlaySound Events to their owning BuffData records.

    PlaySoundActionData uses a typed MemoryPack string slot that is not always
    visible to the generic length-prefixed string inventory.  Seeding only the
    exact decoder rows lets the existing BuffData dependency traversal carry
    those requests to gameplay owners without inventing an owner for an
    otherwise unreachable BuffData record.
    """

    seeded = 0
    for buff_id, events in sorted((by_buff_event or {}).items()):
        record = buff_records.get(str(buff_id))
        if not isinstance(record, dict):
            continue
        record_events = record.setdefault("events", set())
        for event_key, actions in sorted((events or {}).items()):
            authored_ids = {
                str(action.get("eventId") or "").strip()
                for action in actions or []
                if isinstance(action, dict) and str(action.get("eventId") or "").strip()
            }
            if not authored_ids and str(event_key or "").strip():
                authored_ids.add(str(event_key).strip())
            for event_id in sorted(authored_ids):
                if event_id in record_events:
                    continue
                record_events.add(event_id)
                seeded += 1
    return seeded

def annotate_play_sound_action_owner_links(
    actions: list[dict[str, Any]],
    owners: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Keep every decoded action while explicitly marking unresolved owners."""

    linked_markers: set[tuple[Any, ...]] = set()
    for owner in owners:
        for evidence_rows in (owner.get("events") or {}).values():
            for evidence in evidence_rows or []:
                if not isinstance(evidence, dict):
                    continue
                for action in evidence.get("playSoundActions") or []:
                    if isinstance(action, dict):
                        linked_markers.add(play_sound_action_marker(action))
    annotated = []
    linked = 0
    for action in actions:
        has_link = play_sound_action_marker(action) in linked_markers
        linked += int(has_link)
        annotated.append({
            **action,
            "ownerLinkStatus": "linkedThroughBuffDependency" if has_link else "unresolved",
        })
    return annotated, {
        "buffPlaySoundActionsLinkedToGameplayOwner": linked,
        "buffPlaySoundActionsOwnerUnresolved": len(annotated) - linked,
    }

def collect_buff_play_sound_actions(
    export_root: Path,
    buff_records: dict[str, dict[str, Any]],
    *,
    decoder: Any | None = None,
) -> dict[str, Any]:
    """Decode exact current-build PlaySound timeline actions from BuffData.

    The generic string scan proves only that a BuffData dependency contains an
    event id.  The MemoryPack action decoder additionally recovers the authored
    timeline frame window and the PlaySoundActionData lifetime/routing controls.
    TargetSettings is decoded through the typed MemoryPack reader when its
    self-derived envelope boundary is consumed exactly.  Unknown selector
    subtypes retain the bounded opaque fallback; neither representation claims
    that a runtime target or branch was actually selected.
    """

    if decoder is None:
        from scripts.game_data.memorypack.buff import (
            BUFF_ABILITY_ACTION_TAG_MEMBER_COUNTS,
            BUFF_PLAY_SOUND_ACTION_TAG,
            consume_buff_play_sound_action,
        )
        from scripts.game_data.memorypack.core import MEMORYPACK_UNION_WIDE_TAG

        member_count = BUFF_ABILITY_ACTION_TAG_MEMBER_COUNTS[BUFF_PLAY_SOUND_ACTION_TAG]
        signature = bytes([MEMORYPACK_UNION_WIDE_TAG]) + int(BUFF_PLAY_SOUND_ACTION_TAG).to_bytes(2, "little") + bytes([member_count])

        def decoder(_path: Path, data: bytes, _size: int) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
            """Find locally self-bounded single-item PlaySound timeline records.

            This deliberately does not depend on the broad BuffData schema or
            tail parser.  The current records have a one-item SequenceActionData
            envelope immediately before the typed union item and the two guard
            booleans/startFrame/ForceSyncAnimData boundary immediately after it.
            """

            rows: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
            position = data.find(signature)
            while position >= 0:
                record_start = position - 10
                try:
                    if (
                        record_start < 0
                        or data[record_start] != 4
                        or data[position - 5] != 3
                        or unpack_from("<I", data, position - 4)[0] != 1
                    ):
                        raise ValueError("not-single-item-timeline-envelope")
                    end_frame = unpack_from("<i", data, record_start + 1)[0]
                    action, action_end = consume_buff_play_sound_action(
                        data,
                        position,
                        len(data),
                        3,
                        member_count,
                    )
                    if action_end + 7 > len(data):
                        raise ValueError("truncated-timeline-suffix")
                    only_guard = data[action_end]
                    only_main_char = data[action_end + 1]
                    if only_guard not in (0, 1) or only_main_char not in (0, 1):
                        raise ValueError("invalid-timeline-guard-bool")
                    start_frame = unpack_from("<i", data, action_end + 2)[0]
                    if data[action_end + 6] != 4:
                        raise ValueError("missing-force-sync-boundary")
                    rows.append((
                        {"index": len(rows), "startFrame": start_frame, "endFrame": end_frame},
                        {
                            "onlyExecuteWhenSourceIsGuard": bool(only_guard),
                            "onlyExecuteWhenSourceIsMainChar": bool(only_main_char),
                        },
                        action,
                    ))
                except (IndexError, ValueError):
                    pass
                position = data.find(signature, position + 1)
            return rows

    merged: dict[tuple[Any, ...], dict[str, Any]] = {}
    decoded_files = 0
    decode_failures = 0
    for buff_id, record in sorted(buff_records.items()):
        for source in sorted(record.get("sources") or set()):
            path = export_root / PurePosixPath(str(source))
            try:
                data = path.read_bytes()
                decoded_actions = decoder(path, data, len(data)) or []
            except (OSError, ValueError):
                decode_failures += 1
                continue
            if not decoded_actions:
                continue
            source_has_play_sound = False
            for action_index, (timeline, sequence, action) in enumerate(decoded_actions):
                event_id = str(action.get("soundEvent") or "").strip()
                if not event_id:
                    continue
                source_has_play_sound = True
                prefix = action.get("prefix") or {}
                target = action.get("targetSettingsEnvelopePartial") or {}
                row = {
                    "buffId": buff_id,
                    "eventId": event_id,
                    "timelineActionIndex": timeline.get("index"),
                    "actionDataIndex": action_index,
                    "startFrame": timeline.get("startFrame"),
                    "endFrame": timeline.get("endFrame"),
                    "onlyExecuteWhenSourceIsGuard": bool(sequence.get("onlyExecuteWhenSourceIsGuard")),
                    "onlyExecuteWhenSourceIsMainChar": bool(sequence.get("onlyExecuteWhenSourceIsMainChar")),
                    "isEnabled": bool(prefix.get("isEnable")),
                    "priorityLevel": prefix.get("priorityLevel"),
                    "priorityOffset": prefix.get("priorityOffset"),
                    "serverActionIndex": prefix.get("serverActionIndex"),
                    "canInterruptTimeMs": action.get("canInterruptTimeMs"),
                    "interruptFadeDurationMs": action.get("intrptFadeDurationMs"),
                    "jumpToWhenPlayMs": action.get("jumpToWhenPlayMs"),
                    "stopFadeDurationMs": action.get("stopFadeDurationMs"),
                    "stopOnEnd": bool(action.get("stopOnEnd")),
                    "useTempEmitter": bool(action.get("useTempEmitter")),
                    "followMountPoint": bool(action.get("followMountPoint")),
                    "mountPoint": str(action.get("mountPoint") or ""),
                    "targetSettingsStatus": str(target.get("semanticStatus") or "unresolved"),
                    "targetSettingsShape": str(target.get("shape") or ""),
                    "targetSelector": str(target.get("stringSlotValue") or ""),
                    "targetSettings": target,
                    "timeDilationFadeInDurationMs": action.get("timeDilationFadeInDurationMs"),
                    "timeDilationFadeOutDurationMs": action.get("timeDilationFadeOutDurationMs"),
                    "timeDilationPauseThreshold": action.get("timeDilationPauseThreshold"),
                    "timeDilationSeekThreshold": action.get("timeDilationSeekThreshold"),
                    "useTimeDilationPauseAndSeek": bool(action.get("useTimeDilationPauseAndSeek")),
                    "useWeaponMountPoint": bool(action.get("useWeaponMountPoint")),
                    "weaponIndex": action.get("weaponIndex"),
                    "weaponMountPoint": str(action.get("weaponMountPoint") or ""),
                    "sourcePaths": [str(source)],
                    "evidence": "memoryPackPlaySoundActionData",
                    "runtimeConditionStatus": "unresolved",
                }
                marker = tuple(
                    json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    for key, value in row.items()
                    if key not in {"sourcePaths"}
                )
                existing = merged.get(marker)
                if existing is None:
                    merged[marker] = row
                else:
                    existing["sourcePaths"] = sorted(set(existing["sourcePaths"]).union(row["sourcePaths"]))
            if source_has_play_sound:
                decoded_files += 1

    by_buff_event: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in merged.values():
        by_buff_event[str(row["buffId"])][str(row["eventId"]).lower()].append(row)
    return {
        "byBuffEvent": {
            buff_id: {
                event_id: sorted(
                    rows,
                    key=lambda row: (
                        int(row.get("startFrame") or 0),
                        int(row.get("endFrame") or 0),
                        int(row.get("serverActionIndex") or 0),
                    ),
                )
                for event_id, rows in sorted(events.items())
            }
            for buff_id, events in sorted(by_buff_event.items())
        },
        "counts": {
            "buffPlaySoundDecodedSourceFiles": decoded_files,
            "buffPlaySoundDecodeFailures": decode_failures,
            "buffPlaySoundActionOccurrences": len(merged),
            "buffPlaySoundUniqueEvents": len({str(row["eventId"]).lower() for row in merged.values()}),
        },
    }

def collect_gameplay_audio_references(
    webui_root: Path,
    export_root: Path,
    language: str,
) -> dict[str, Any]:
    """Collect evidence-backed SkillData/BuffData audio ownership for Gameplay."""

    gameplay_path = webui_root / Path(str(GAMEPLAY_INDEX_REL).format(language=language))
    gameplay = load_json_strict(gameplay_path, {})
    entries = (gameplay.get("entries") or []) if isinstance(gameplay, dict) else []
    character_skills: dict[str, tuple[str, str]] = {}
    enemies: list[dict[str, Any]] = []
    enemy_ids: list[tuple[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        kind = str(entry.get("kind") or "")
        owner_id = str(entry.get("id") or "")
        if kind == "character":
            for group in entry.get("skillGroups") or []:
                if not isinstance(group, dict):
                    continue
                group_id = str(group.get("id") or "")
                skills = group.get("skills") or [
                    {"id": value}
                    for value in group.get("actionSkillIds") or []
                ]
                for skill in skills:
                    skill_id = str((skill or {}).get("id") or "") if isinstance(skill, dict) else ""
                    if skill_id:
                        character_skills[skill_id] = (owner_id, group_id)
        elif kind == "enemy" and owner_id:
            enemies.append(entry)
            for value in (entry.get("id"), entry.get("templateId"), *(entry.get("variantIds") or [])):
                key = str(value or "").strip()
                if key:
                    enemy_ids.append((key, owner_id))
    enemy_ids = sorted(set(enemy_ids), key=lambda row: (-len(row[0]), row[0], row[1]))
    character_skill_ids = sorted(character_skills, key=lambda value: (-len(value), value))

    skill_records = gameplay_config_records(export_root, "SkillData")
    buff_records = gameplay_config_records(export_root, "BuffData")
    skill_play_sound = collect_buff_play_sound_actions(export_root, skill_records)
    skill_play_sound_by_id = skill_play_sound.get("byBuffEvent") or {}
    seeded_skill_play_sound_events = seed_buff_play_sound_events(
        skill_records,
        skill_play_sound_by_id,
    )
    buff_play_sound = collect_buff_play_sound_actions(export_root, buff_records)
    buff_play_sound_by_id = buff_play_sound.get("byBuffEvent") or {}
    seeded_play_sound_events = seed_buff_play_sound_events(
        buff_records,
        buff_play_sound_by_id,
    )

    def play_sound_rows(event_id: str, buff_ids: set[str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        event_key = event_id.lower()
        for buff_id in sorted(buff_ids):
            rows.extend((buff_play_sound_by_id.get(buff_id) or {}).get(event_key) or [])
        return rows

    def skill_play_sound_rows(event_id: str, skill_id: str) -> list[dict[str, Any]]:
        rows = (
            (skill_play_sound_by_id.get(skill_id) or {}).get(event_id.lower()) or []
        )
        return [
            {
                **{key: value for key, value in row.items() if key != "buffId"},
                "skillId": skill_id,
                "configKind": "SkillData",
                "configId": skill_id,
            }
            for row in rows
            if isinstance(row, dict)
        ]

    enemy_source_files = enemy_template_source_files(export_root)
    enemy_template_skills = enemy_template_skill_references(
        export_root,
        enemies,
        set(skill_records),
        enemy_source_files,
    )
    template_owners_by_skill: dict[str, list[tuple[str, set[str]]]] = defaultdict(list)
    for enemy_id, skills in enemy_template_skills.items():
        for skill_id, sources in skills.items():
            template_owners_by_skill[skill_id].append((enemy_id, sources))
    owners: list[dict[str, Any]] = []
    authored_play_sound_actions = [
        row
        for events in (buff_play_sound.get("byBuffEvent") or {}).values()
        for rows in events.values()
        for row in rows
    ]
    event_names: set[str] = {
        str(row.get("eventId") or "").lower()
        for row in authored_play_sound_actions
        if str(row.get("eventId") or "")
    }
    owned_skill_ids: set[str] = set()

    for skill_id, record in sorted(skill_records.items()):
        matched_owners: list[dict[str, Any]] = []
        if skill_id in character_skills:
            owner_id, group_id = character_skills[skill_id]
            matched_owners.append({
                "ownerKind": "character",
                "ownerId": owner_id,
                "groupId": group_id,
                "confidence": "direct",
                "ownershipMethod": "gameplaySkillId",
                "ownershipSources": [],
            })
        else:
            character_match = next(
                (candidate for candidate in character_skill_ids if skill_id.startswith(candidate + "_")),
                None,
            )
            if character_match:
                owner_id, group_id = character_skills[character_match]
                matched_owners.append({
                    "ownerKind": "character",
                    "ownerId": owner_id,
                    "groupId": group_id,
                    "confidence": "inferred",
                    "ownershipMethod": "playableSkillFamilyPrefix",
                    "ownershipSources": [],
                })

        for enemy_id, ownership_sources in template_owners_by_skill.get(skill_id) or []:
            matched_owners.append({
                "ownerKind": "enemy",
                "ownerId": enemy_id,
                "groupId": "",
                "confidence": "inferred",
                "ownershipMethod": "enemyTemplateAbilitySystemSkill",
                "ownershipSources": sorted(ownership_sources),
            })

        if not any(owner["ownerKind"] == "enemy" for owner in matched_owners):
            enemy_match = next(
                ((candidate, enemy_id) for candidate, enemy_id in enemy_ids if skill_id == candidate or skill_id.startswith(candidate + "_")),
                None,
            )
            if enemy_match:
                matched_owners.append({
                    "ownerKind": "enemy",
                    "ownerId": enemy_match[1],
                    "groupId": "",
                    "confidence": "inferred",
                    "ownershipMethod": "enemyIdPrefix",
                    "ownershipSources": [],
                })
        if not matched_owners:
            continue

        event_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event_id in sorted(record.get("events") or set()):
            evidence = {"kind": "skillData", "skillId": skill_id}
            actions = skill_play_sound_rows(event_id, skill_id)
            if actions:
                evidence["playSoundActions"] = actions
            event_evidence[event_id].append(evidence)
        for event_id, buff_ids in gameplay_buff_audio(set(record.get("buffs") or set()), buff_records).items():
            evidence = {
                "kind": "skillBuffData",
                "skillId": skill_id,
                "buffIds": sorted(buff_ids),
            }
            actions = play_sound_rows(event_id, buff_ids)
            if actions:
                evidence["playSoundActions"] = actions
            event_evidence[event_id].append(evidence)
        if not event_evidence:
            continue
        owned_skill_ids.add(skill_id)
        event_names.update(event_evidence)
        seen_owner_keys: set[tuple[str, str, str]] = set()
        for matched_owner in matched_owners:
            owner_key = (
                str(matched_owner.get("ownerKind") or ""),
                str(matched_owner.get("ownerId") or ""),
                str(matched_owner.get("groupId") or ""),
            )
            if owner_key in seen_owner_keys:
                continue
            seen_owner_keys.add(owner_key)
            owners.append({
                **matched_owner,
                "skillId": skill_id,
                "sources": sorted(record.get("sources") or set()),
                "events": dict(event_evidence),
            })

    for enemy in enemies:
        owner_id = str(enemy.get("id") or "")
        born_buffs = {str(value or "").strip() for value in enemy.get("bornBuffs") or [] if str(value or "").strip()}
        buff_events = gameplay_buff_audio(born_buffs, buff_records)
        if not buff_events:
            continue
        event_names.update(buff_events)
        owners.append({
            "ownerKind": "enemy",
            "ownerId": owner_id,
            "groupId": "",
            "skillId": "",
            "confidence": "direct",
            "ownershipMethod": "enemyBornBuffField",
            "ownershipSources": [],
            "sources": [],
            "events": {
                event_id: [{
                    "kind": "enemyBornBuffData",
                    "buffIds": sorted(buff_ids),
                    **(
                        {"playSoundActions": play_sound_rows(event_id, buff_ids)}
                        if play_sound_rows(event_id, buff_ids)
                        else {}
                    ),
                }]
                for event_id, buff_ids in sorted(buff_events.items())
            },
        })

    animation_audio = collect_gameplay_animation_audio(
        export_root,
        entries,
        enemies,
        enemy_source_files,
    )
    profile_voices = collect_gameplay_profile_voices(export_root, entries)
    event_names.update(animation_audio.get("eventNames") or set())
    authored_config_event_references: list[dict[str, Any]] = []
    for config_kind, records in (("SkillData", skill_records), ("BuffData", buff_records)):
        for config_id, record in sorted(records.items()):
            for event_id in sorted(record.get("events") or set()):
                if event_id in event_names:
                    continue
                authored_config_event_references.append({
                    "eventId": event_id,
                    "configKind": config_kind,
                    "configId": config_id,
                    "sourcePaths": sorted(record.get("sources") or set()),
                    "ownerLinkStatus": "unresolved",
                    "evidence": "exactMemoryPackLengthPrefixedAudioEventString",
                    "runtimeExecutionStatus": "configRuntimeExecutionNotObserved",
                })
    event_names.update(
        str(row.get("eventId") or "")
        for row in authored_config_event_references
        if str(row.get("eventId") or "")
    )
    authored_play_sound_actions, play_sound_owner_counts = (
        annotate_play_sound_action_owner_links(authored_play_sound_actions, owners)
    )
    return {
        "eventNames": event_names,
        "owners": owners,
        "authoredPlaySoundActions": authored_play_sound_actions,
        "authoredConfigEventReferences": authored_config_event_references,
        "animationOwners": animation_audio.get("owners") or [],
        "unownedAnimationEvents": animation_audio.get("unownedEvents") or {},
        "profileVoiceOwners": profile_voices.get("owners") or [],
        "counts": {
            "gameplayCharacterSkills": len(character_skills),
            "audioOwnedSkills": len(owned_skill_ids),
            "audioReferences": sum(len(owner.get("events") or {}) for owner in owners),
            "audioEventNames": len(event_names),
            "authoredConfigEventReferences": len(authored_config_event_references),
            "authoredConfigEventReferenceEvents": len({
                str(row.get("eventId") or "")
                for row in authored_config_event_references
                if str(row.get("eventId") or "")
            }),
            "enemyTemplatesWithSkillReferences": len(enemy_template_skills),
            "enemyTemplateSkillReferences": sum(len(skills) for skills in enemy_template_skills.values()),
            **(buff_play_sound.get("counts") or {}),
            "buffPlaySoundSeededEventRefs": seeded_play_sound_events,
            "skillPlaySoundDecodedSourceFiles": int(
                (skill_play_sound.get("counts") or {}).get("buffPlaySoundDecodedSourceFiles") or 0
            ),
            "skillPlaySoundActionOccurrences": int(
                (skill_play_sound.get("counts") or {}).get("buffPlaySoundActionOccurrences") or 0
            ),
            "skillPlaySoundUniqueEvents": int(
                (skill_play_sound.get("counts") or {}).get("buffPlaySoundUniqueEvents") or 0
            ),
            "skillPlaySoundSeededEventRefs": seeded_skill_play_sound_events,
            **play_sound_owner_counts,
            **(animation_audio.get("counts") or {}),
            **(profile_voices.get("counts") or {}),
        },
        "animationControllerIndex": animation_audio.get("animationControllerIndex") or {},
    }

def compact_gameplay_audio_link(entry: dict[str, Any]) -> dict[str, Any]:
    compact = {
        key: entry[key]
        for key in GAMEPLAY_AUDIO_LINK_FIELDS
        if entry.get(key) is not None
    }
    if compact.get("wwiseMediaEvidence"):
        compact["wwiseMediaEvidence"] = [
            {
                key: row[key]
                for key in (
                    "rootActionIds", "soundObjectCount", "relationTypes",
                    "selectionPaths", "bankId", "bankPackage",
                )
                if row.get(key) not in (None, "", [])
            }
            for row in compact["wwiseMediaEvidence"]
            if isinstance(row, dict)
        ]
    return compact

def link_gameplay_audio(
    webui_root: Path,
    language: str,
    references: dict[str, Any],
    event_audio_by_id: dict[str, list[dict[str, Any]]],
    event_evidence: list[dict[str, Any]],
    dialog_audio_by_id: dict[str, dict[str, Any]] | None = None,
) -> dict[str, int]:
    """Write compact Gameplay SFX sidecar with typed possible media leaves."""

    event_evidence_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in event_evidence:
        event_key = str(row.get("eventId") or "").strip().lower() if isinstance(row, dict) else ""
        if event_key:
            event_evidence_by_id[event_key].append(row)
    found_events = set(event_evidence_by_id)
    event_cache: dict[str, dict[str, Any]] = {}

    def gameplay_trigger_binding(owner: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
        owner_kind = str(owner.get("ownerKind") or "")
        confidence = str(owner.get("confidence") or "inferred")
        method = str(owner.get("ownershipMethod") or "")
        evidence_kinds = sorted({str(row.get("kind") or "") for row in evidence if isinstance(row, dict) and row.get("kind")})
        relation_types: list[str] = []
        if "skillData" in evidence_kinds:
            relation_types.append("skillDataEventReference")
        if "skillBuffData" in evidence_kinds:
            relation_types.append("skillBuffChain")
        if "enemyBornBuffData" in evidence_kinds:
            relation_types.append("enemyBornBuffChain")
        play_sound_actions = [
            action
            for row in evidence
            if isinstance(row, dict)
            for action in row.get("playSoundActions") or []
            if isinstance(action, dict)
        ]
        if play_sound_actions:
            if any(action.get("configKind") == "SkillData" for action in play_sound_actions):
                relation_types.append("skillPlaySoundAction")
            if any(action.get("configKind") != "SkillData" for action in play_sound_actions):
                relation_types.append("buffPlaySoundAction")
        if owner_kind == "character" and confidence == "direct" and method == "gameplaySkillId":
            status = "exactSkillConfig"
        elif owner_kind == "enemy" and confidence == "direct" and method == "enemyBornBuffField":
            status = "exactEnemyBornBuffConfig"
        else:
            status = "inferredSkillConfigOwner"
        if play_sound_actions:
            request_evidence = (
                "exactAuthoredPlaySoundAction"
                if status != "inferredSkillConfigOwner"
                else "inferredOwnerExactAuthoredPlaySoundAction"
            )
            activation_status = "authoredFrameWindowRecoveredConditionUnresolved"
        else:
            request_evidence = (
                "exactAuthoredDependency"
                if status != "inferredSkillConfigOwner"
                else "inferredOwnerExactAuthoredDependency"
            )
            activation_status = "conditionAndTimingUnresolved"
        binding = {
            "status": status,
            "requestEvidence": request_evidence,
            "runtimeActivationStatus": activation_status,
            "ownerKind": owner_kind,
            "ownerId": str(owner.get("ownerId") or ""),
            "groupId": str(owner.get("groupId") or ""),
            "skillId": str(owner.get("skillId") or ""),
            "confidence": confidence,
            "ownershipMethod": method,
            "relationTypes": relation_types,
            "evidenceKinds": evidence_kinds,
            "buffIds": sorted({
                str(buff_id)
                for row in evidence
                if isinstance(row, dict)
                for buff_id in row.get("buffIds") or []
                if str(buff_id)
            }),
            "sourcePaths": sorted(set(filter(None, [
                *(owner.get("sources") or []),
                *(owner.get("ownershipSources") or []),
                *(
                    source_path
                    for action in play_sound_actions
                    for source_path in action.get("sourcePaths") or []
                ),
            ]))),
        }
        if play_sound_actions:
            binding["playSoundActions"] = play_sound_actions
        return binding

    def linked_event(event_id: str) -> dict[str, Any]:
        event_key = event_id.lower()
        if event_key in event_cache:
            return event_cache[event_key]
        media: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for entry in event_audio_by_id.get(event_key) or []:
            compact = compact_gameplay_audio_link(entry)
            key = (str(compact.get("src") or ""), str(compact.get("mediaId") or ""))
            if not key[0] or key in seen:
                continue
            seen.add(key)
            media.append(compact)
        content_counts = Counter(
            str(row.get("contentSha256") or "")
            for row in media
            if row.get("contentSha256")
        )
        for row in media:
            content_hash = str(row.get("contentSha256") or "")
            if content_hash and content_counts[content_hash] > 1:
                row["contentEquivalentCount"] = content_counts[content_hash]
        evidence_rows = event_evidence_by_id.get(event_key, [])
        selector_containers: dict[str, dict[str, int]] = {}
        seen_selector_nodes: set[tuple[int, int]] = set()
        for definition_index, evidence_row in enumerate(evidence_rows):
            bank_id = int(evidence_row.get("bankId") or definition_index)
            for container in evidence_row.get("containerEvidence") or []:
                if not isinstance(container, dict):
                    continue
                object_id = int(container.get("objectId") or 0)
                node_key = (bank_id, object_id)
                if object_id and node_key in seen_selector_nodes:
                    continue
                if object_id:
                    seen_selector_nodes.add(node_key)
                object_type = int(container.get("objectType") or 0)
                if object_type == 5:
                    selector_kind = "sequenceItem" if int(container.get("mode") or 0) == 1 else "randomAlternative"
                else:
                    selector_kind = {
                        6: "switchCandidate",
                        7: "groupChild",
                        9: "layerChild",
                    }.get(object_type, str(container.get("edgeKind") or "unknown"))
                counts = selector_containers.setdefault(selector_kind, {"nodeCount": 0, "childEdgeCount": 0})
                counts["nodeCount"] += 1
                counts["childEdgeCount"] += int(container.get("childCount") or 0)
        selector_evidence = {
            "bankDefinitionCount": len(evidence_rows),
            "rootStopActionCount": sum(int(row.get("rootStopActionCount") or 0) for row in evidence_rows),
            "containers": selector_containers,
        }
        action_dispatch_evidence: list[dict[str, Any]] = []
        for evidence_row in evidence_rows:
            dispatch = evidence_row.get("actionDispatchEvidence") or {}
            if not isinstance(dispatch, dict) or not dispatch:
                continue
            actions: list[dict[str, Any]] = []
            for action in evidence_row.get("actionEvidence") or []:
                if not isinstance(action, dict) or action.get("operation") not in {"play", "playEvent"}:
                    continue
                actions.append({
                    "actionId": action.get("actionId"),
                    "eventActionOrdinal": action.get("eventActionOrdinal"),
                    "operation": action.get("operation"),
                    "actionParserStatus": action.get("actionParserStatus"),
                    "delay": action.get("delay") or {},
                    "transition": action.get("transition") or {},
                    "probability": action.get("probability") or {},
                })
            action_dispatch_evidence.append({
                "bankId": evidence_row.get("bankId"),
                "bankVersion": evidence_row.get("bankVersion"),
                "timingClass": dispatch.get("timingClass"),
                "playbackActionCount": int(dispatch.get("playbackActionCount") or 0),
                "typedPlaybackActionCount": int(dispatch.get("typedPlaybackActionCount") or 0),
                "failedPlaybackActionCount": int(dispatch.get("failedPlaybackActionCount") or 0),
                "controlActionCount": int(dispatch.get("controlActionCount") or 0),
                "typedControlActionCount": int(dispatch.get("typedControlActionCount") or 0),
                "failedControlActionCount": int(dispatch.get("failedControlActionCount") or 0),
                "controlOperationCounts": dispatch.get("controlOperationCounts") or {},
                "multiPlayback": bool(dispatch.get("multiPlayback")),
                "simultaneityCandidate": bool(dispatch.get("simultaneityCandidate")),
                "explicitDelayActionCount": int(dispatch.get("explicitDelayActionCount") or 0),
                "explicitTransitionActionCount": int(dispatch.get("explicitTransitionActionCount") or 0),
                "probabilityGatedActionCount": int(dispatch.get("probabilityGatedActionCount") or 0),
                "evidenceBoundary": dispatch.get("evidenceBoundary"),
                "actions": actions,
            })
        root_action_ids = sorted({
            int(root_action_id)
            for item in media
            for row in item.get("wwiseMediaEvidence") or []
            for root_action_id in row.get("rootActionIds") or []
            if isinstance(root_action_id, int)
        })
        relation_types = sorted({
            str(relation)
            for item in media
            for row in item.get("wwiseMediaEvidence") or []
            for relation in row.get("relationTypes") or []
            if str(relation)
        })
        traversal_status = (
            "partial" if any(row.get("traversalStatus") == "partial" for row in evidence_rows)
            else "complete" if evidence_rows else "unresolved"
        )
        value = {
            "id": event_id,
            "foundInWwise": event_key in found_events,
            "hasPlayableMedia": bool(media),
            "possibleMediaCount": len(media),
            "playableCandidates": len(media),
            "playRootCount": len(root_action_ids) or max(
                (int(row.get("rootPlayActionCount") or 0) for row in evidence_rows),
                default=0,
            ),
            "playRootActionIds": root_action_ids,
            "mediaRelationTypes": relation_types,
            "traversalStatus": traversal_status,
            "unresolvedNodeCount": sum(len(row.get("unresolvedNodes") or []) for row in evidence_rows),
            "selectorEvidence": selector_evidence,
            "actionDispatchEvidence": action_dispatch_evidence,
            "runtimeSelection": (
                "eventNotFoundInWwise" if event_key not in found_events
                else "noDecodedPossibleMedia" if not media
                else "runtimeBranchUnresolved" if any(value != "directSound" for value in relation_types)
                else "multiplePlayRootsTimingUnresolved" if len(root_action_ids) > 1
                else "singlePossibleMedia" if len(media) == 1
                else "multiplePossibleMediaUnresolved"
            ),
            "audio": media,
        }
        event_cache[event_key] = value
        return value

    characters: dict[str, dict[str, Any]] = {}
    enemies: dict[str, dict[str, Any]] = {}
    animation_event_catalog: dict[str, dict[str, Any]] = {}
    discovered_refs = 0
    linked_refs = 0
    candidate_count = 0
    animation_linked_refs = 0
    animation_candidate_count = 0
    profile_voice_linked_refs = 0
    profile_voice_media_keys: set[str] = set()

    def normalized_animation_events(owner: dict[str, Any]) -> list[tuple[str, list[dict[str, Any]]]]:
        merged: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for authored_event_id, evidence_rows in (owner.get("events") or {}).items():
            authored = str(authored_event_id or "").strip()
            event_key = authored.lower()
            if not event_key:
                continue
            for evidence in evidence_rows or []:
                row = dict(evidence) if isinstance(evidence, dict) else {"value": evidence}
                row.setdefault("authoredEventId", authored)
                merged[event_key].append(row)
        return sorted(merged.items())

    animation_owner_ids: dict[tuple[str, str], set[str]] = defaultdict(set)
    for owner in references.get("animationOwners") or []:
        owner_kind = str(owner.get("ownerKind") or "")
        owner_id = str(owner.get("ownerId") or "")
        if owner_kind not in {"character", "enemy"} or not owner_id:
            continue
        for event_key, _evidence in normalized_animation_events(owner):
            animation_owner_ids[(owner_kind, event_key)].add(owner_id)
    for owner in references.get("owners") or []:
        event_rows: list[dict[str, Any]] = []
        for event_id, evidence in sorted((owner.get("events") or {}).items()):
            discovered_refs += 1
            linked = linked_event(event_id)
            candidates = int(linked.get("playableCandidates") or 0)
            if candidates:
                linked_refs += 1
                candidate_count += candidates
            event_rows.append({
                **linked,
                "evidence": evidence,
                "triggerBindings": [gameplay_trigger_binding(owner, evidence)],
            })
        if not event_rows:
            continue
        owner_kind = str(owner.get("ownerKind") or "")
        owner_id = str(owner.get("ownerId") or "")
        if owner_kind == "character":
            group_id = str(owner.get("groupId") or "")
            groups = characters.setdefault(owner_id, {"groups": {}})["groups"]
            group = groups.setdefault(group_id, {"skillIds": [], "events": []})
            skill_id = str(owner.get("skillId") or "")
            if skill_id and skill_id not in group["skillIds"]:
                group["skillIds"].append(skill_id)
            group.setdefault("ownershipConfidence", []).append(owner.get("confidence") or "direct")
            group.setdefault("ownershipMethods", []).append(owner.get("ownershipMethod") or "")
            group.setdefault("ownershipSources", []).extend(owner.get("ownershipSources") or [])
            existing = {str(row.get("id") or ""): row for row in group["events"]}
            for event in event_rows:
                event_id = str(event.get("id") or "")
                if event_id not in existing:
                    event["sourceSkillIds"] = [skill_id] if skill_id else []
                    group["events"].append(event)
                    existing[event_id] = event
                else:
                    existing[event_id].setdefault("evidence", []).extend(event.get("evidence") or [])
                    bindings = existing[event_id].setdefault("triggerBindings", [])
                    binding_markers = {
                        json.dumps(binding, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                        for binding in bindings
                    }
                    for binding in event.get("triggerBindings") or []:
                        marker = json.dumps(binding, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                        if marker not in binding_markers:
                            binding_markers.add(marker)
                            bindings.append(binding)
                    if skill_id and skill_id not in existing[event_id].setdefault("sourceSkillIds", []):
                        existing[event_id]["sourceSkillIds"].append(skill_id)
        elif owner_kind == "enemy":
            skill_id = str(owner.get("skillId") or "")
            record = enemies.setdefault(owner_id, {
                "skillIds": [],
                "ownershipConfidence": [],
                "ownershipMethods": [],
                "ownershipSources": [],
                "includesSpawnBuffAudio": False,
                "events": [],
            })
            if skill_id and skill_id not in record["skillIds"]:
                record["skillIds"].append(skill_id)
            if not skill_id:
                record["includesSpawnBuffAudio"] = True
            record["ownershipConfidence"].append(owner.get("confidence") or "inferred")
            record["ownershipMethods"].append(owner.get("ownershipMethod") or "")
            record["ownershipSources"].extend(owner.get("ownershipSources") or [])
            existing = {str(row.get("id") or ""): row for row in record["events"]}
            for event in event_rows:
                event_id = str(event.get("id") or "")
                if event_id not in existing:
                    event["sourceSkillIds"] = [skill_id] if skill_id else []
                    record["events"].append(event)
                    existing[event_id] = event
                else:
                    existing[event_id].setdefault("evidence", []).extend(event.get("evidence") or [])
                    bindings = existing[event_id].setdefault("triggerBindings", [])
                    binding_markers = {
                        json.dumps(binding, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                        for binding in bindings
                    }
                    for binding in event.get("triggerBindings") or []:
                        marker = json.dumps(binding, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                        if marker not in binding_markers:
                            binding_markers.add(marker)
                            bindings.append(binding)
                    if skill_id and skill_id not in existing[event_id].setdefault("sourceSkillIds", []):
                        existing[event_id]["sourceSkillIds"].append(skill_id)

    for owner in references.get("animationOwners") or []:
        owner_kind = str(owner.get("ownerKind") or "")
        owner_id = str(owner.get("ownerId") or "")
        if owner_kind not in {"character", "enemy"}:
            continue
        resolved_events: list[dict[str, Any]] = []
        for event_id, evidence in normalized_animation_events(owner):
            discovered_refs += 1
            linked = linked_event(event_id)
            candidates = int(linked.get("playableCandidates") or 0)
            if candidates:
                linked_refs += 1
                animation_linked_refs += 1
                candidate_count += candidates
                animation_candidate_count += candidates
            action_kinds = sorted({str(row.get("actionKind") or "action") for row in evidence})
            clips = sorted({str(row.get("clip") or "") for row in evidence if row.get("clip")})
            functions = sorted({str(row.get("function") or "") for row in evidence if row.get("function")})
            clip_contexts = sorted({str(row.get("clipContext") or "other") for row in evidence})
            animator_controller_contexts: list[dict[str, Any]] = []
            animator_controller_seen: set[str] = set()
            for row in evidence:
                for context in row.get("animatorControllerContexts") or []:
                    if not isinstance(context, dict):
                        continue
                    marker = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    if marker in animator_controller_seen:
                        continue
                    animator_controller_seen.add(marker)
                    animator_controller_contexts.append(dict(context))
            animator_controller_contexts.sort(
                key=lambda row: (
                    str(row.get("name") or ""),
                    str(row.get("sourcePath") or ""),
                    str(row.get("targetSourceFile") or ""),
                )
            )
            animator_override_contexts: list[dict[str, Any]] = []
            animator_override_seen: set[str] = set()
            for row in evidence:
                for context in row.get("animatorOverrideContexts") or []:
                    if not isinstance(context, dict):
                        continue
                    marker = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    if marker in animator_override_seen:
                        continue
                    animator_override_seen.add(marker)
                    animator_override_contexts.append(dict(context))
            animator_override_contexts.sort(
                key=lambda row: (
                    str(row.get("overrideName") or ""),
                    int(row.get("clipIndex") or 0),
                    str(row.get("overrideSourcePath") or ""),
                )
            )
            animator_controller_reachable_clip_count = len({
                str(row.get("clip") or "")
                for row in evidence
                if row.get("clip") and row.get("animatorControllerCount")
            })
            animator_controller_unresolved_clip_count = len({
                str(row.get("clip") or "")
                for row in evidence
                if row.get("clip") and not row.get("animatorControllerCount")
            })
            authored_event_ids = sorted({
                str(row.get("authoredEventId") or event_id)
                for row in evidence
                if str(row.get("authoredEventId") or event_id)
            })
            owner_count = len(animation_owner_ids.get((owner_kind, event_id.lower()), set())) or 1
            owner_scope = (
                "sharedPlayableCharacters" if owner_kind == "character" and owner_count > 1
                else "singlePlayableCharacter" if owner_kind == "character"
                else "sharedEnemyTemplates" if owner_count > 1
                else "singleEnemyTemplate"
            )
            event = {
                "id": event_id,
                "foundInWwise": linked.get("foundInWwise"),
                "possibleMediaCount": linked.get("possibleMediaCount"),
                "playableCandidates": linked.get("playableCandidates"),
                "playRootCount": linked.get("playRootCount"),
                "mediaRelationTypes": linked.get("mediaRelationTypes") or [],
                "selectorEvidence": linked.get("selectorEvidence") or {},
                "actionDispatchEvidence": linked.get("actionDispatchEvidence") or [],
                "traversalStatus": linked.get("traversalStatus"),
                "runtimeSelection": linked.get("runtimeSelection"),
                "evidence": evidence,
                "actionKinds": action_kinds,
                "animationFunctions": functions,
                "animationClipContexts": clip_contexts,
                "clipReachability": animation_clip_reachability_status(evidence),
                "animatorControllerCount": len(animator_controller_contexts),
                "animatorControllerContexts": animator_controller_contexts,
                "animatorControllerReachableClipCount": animator_controller_reachable_clip_count,
                "animatorControllerUnresolvedClipCount": animator_controller_unresolved_clip_count,
                "overrideReachability": animation_override_reachability_status(
                    animator_override_contexts
                ),
                "animatorOverrideCount": len(animator_override_contexts),
                "animatorOverrideContexts": animator_override_contexts,
                "authoredEventIds": authored_event_ids,
                "eventAliases": [value for value in authored_event_ids if value != event_id],
                "sourceAnimationClips": clips,
                "animationOwnerCount": owner_count,
                "animationOwnershipScope": owner_scope,
                "possibleMediaScope": "sharedEventGraph" if owner_count > 1 else "singleOwnerEventGraph",
            }
            animation_event_catalog.setdefault(event_id.lower(), linked)
            resolved_events.append(event)
        if not resolved_events:
            continue
        if owner_kind == "character":
            record = characters.setdefault(owner_id, {"groups": {}})
        else:
            record = enemies.setdefault(owner_id, {
                "skillIds": [],
                "ownershipConfidence": [],
                "ownershipMethods": [],
                "ownershipSources": [],
                "includesSpawnBuffAudio": False,
                "events": [],
            })
        record["animationOwnershipConfidence"] = "inferred"
        record["animationOwnershipMethod"] = "animationClipActorToken"
        record.setdefault("animationOwnershipSources", []).extend(owner.get("ownershipSources") or [])
        animation_events = record.setdefault("animationEvents", [])
        existing = {str(row.get("id") or "").lower(): row for row in animation_events}
        for event in resolved_events:
            event_id = str(event.get("id") or "")
            event_key = event_id.lower()
            if event_key not in existing:
                animation_events.append(event)
                existing[event_key] = event
            else:
                current = existing[event_key]
                current.setdefault("evidence", []).extend(event.get("evidence") or [])
                current["actionKinds"] = sorted(
                    set(current.get("actionKinds") or []).union(event.get("actionKinds") or [])
                )
                current["animationFunctions"] = sorted(
                    set(current.get("animationFunctions") or []).union(event.get("animationFunctions") or [])
                )
                current["animationClipContexts"] = sorted(
                    set(current.get("animationClipContexts") or []).union(event.get("animationClipContexts") or [])
                )
                current_override_contexts = current.setdefault("animatorOverrideContexts", [])
                override_markers = {
                    json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    for row in current_override_contexts
                    if isinstance(row, dict)
                }
                for row in event.get("animatorOverrideContexts") or []:
                    if not isinstance(row, dict):
                        continue
                    marker = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    if marker not in override_markers:
                        override_markers.add(marker)
                        current_override_contexts.append(dict(row))
                current_override_contexts.sort(
                    key=lambda row: (
                        str(row.get("overrideName") or ""),
                        int(row.get("clipIndex") or 0),
                        str(row.get("overrideSourcePath") or ""),
                    )
                )
                current["animatorOverrideCount"] = len(current_override_contexts)
                current["overrideReachability"] = animation_override_reachability_status(
                    current_override_contexts
                )
                current["authoredEventIds"] = sorted(
                    set(current.get("authoredEventIds") or []).union(event.get("authoredEventIds") or [])
                )
                current["sourceAnimationClips"] = sorted(
                    set(current.get("sourceAnimationClips") or []).union(event.get("sourceAnimationClips") or [])
                )
                if event_id != current.get("id"):
                    current["eventAliases"] = sorted(
                        set(current.get("eventAliases") or []).union({event_id})
                    )

    for owner in references.get("profileVoiceOwners") or []:
        owner_id = str(owner.get("ownerId") or "")
        if not owner_id:
            continue
        resolved_voices: list[dict[str, Any]] = []
        for voice in owner.get("voices") or []:
            voice_id = str(voice.get("id") or "")
            if not voice_id:
                continue
            discovered_refs += 1
            audio = (dialog_audio_by_id or {}).get(voice_id.lower())
            if not audio:
                continue
            compact = compact_gameplay_audio_link(audio)
            if not compact.get("src"):
                continue
            linked_refs += 1
            profile_voice_linked_refs += 1
            candidate_count += 1
            profile_voice_media_keys.add(str(compact.get("src") or compact.get("mediaId") or voice_id))
            resolved_voices.append({
                "id": voice_id,
                "actionKinds": [voice.get("actionKind") or "combatVoice"],
                "runtimeSelection": "profileVoiceEntry",
                "playableCandidates": 1,
                "audio": [compact],
                "evidence": [{
                    "kind": "characterProfileVoice",
                    "characterId": voice.get("characterId"),
                    "profileVoiceIndex": voice.get("profileVoiceIndex"),
                    "triggerKey": voice.get("triggerKey") or "",
                    "source": voice.get("source") or "",
                }],
            })
        if resolved_voices:
            record = characters.setdefault(owner_id, {"groups": {}})
            record.setdefault("profileVoices", []).extend(resolved_voices)

    def finalize_trigger_event(event: dict[str, Any]) -> None:
        bindings = event.get("triggerBindings") or []
        statuses = {str(binding.get("status") or "") for binding in bindings if isinstance(binding, dict)}
        if "exactSkillConfig" in statuses:
            event["triggerBindingStatus"] = "exactSkillConfig"
        elif "exactEnemyBornBuffConfig" in statuses:
            event["triggerBindingStatus"] = "exactEnemyBornBuffConfig"
        elif bindings:
            event["triggerBindingStatus"] = "inferredSkillConfigOwner"
        event["triggerRelationTypes"] = sorted({
            str(relation)
            for binding in bindings
            if isinstance(binding, dict)
            for relation in binding.get("relationTypes") or []
            if str(relation)
        })

    for value in characters.values():
        for group in value.get("groups", {}).values():
            group["skillIds"].sort()
            group["ownershipConfidence"] = "inferred" if "inferred" in group.pop("ownershipConfidence", []) else "direct"
            group["ownershipMethods"] = sorted(set(filter(None, group.get("ownershipMethods") or [])))
            group["ownershipSources"] = sorted(set(filter(None, group.get("ownershipSources") or [])))
            for event in group["events"]:
                finalize_trigger_event(event)
            group["events"].sort(key=lambda row: str(row.get("id") or ""))
        value["animationOwnershipSources"] = sorted(set(filter(None, value.get("animationOwnershipSources") or [])))
        value.get("animationEvents", []).sort(key=lambda row: str(row.get("id") or ""))
        value.get("profileVoices", []).sort(key=lambda row: str(row.get("id") or ""))
    for value in enemies.values():
        value["skillIds"].sort()
        for event in value["events"]:
            finalize_trigger_event(event)
        value["events"].sort(key=lambda row: str(row.get("id") or ""))
        value["ownershipConfidence"] = "inferred" if "inferred" in value.pop("ownershipConfidence", []) else "direct"
        value["ownershipMethods"] = sorted(set(filter(None, value.get("ownershipMethods") or [])))
        value["ownershipSources"] = sorted(set(filter(None, value.get("ownershipSources") or [])))
        value["animationOwnershipSources"] = sorted(set(filter(None, value.get("animationOwnershipSources") or [])))
        value.get("animationEvents", []).sort(key=lambda row: str(row.get("id") or ""))

    def possible_media_count(event: dict[str, Any]) -> int:
        return len([row for row in event.get("audio") or [] if row.get("src")]) or int(
            event.get("possibleMediaCount") or event.get("playableCandidates") or 0
        )

    def character_audio_metrics(value: dict[str, Any]) -> dict[str, int]:
        skill_events = [
            event
            for group in (value.get("groups") or {}).values()
            for event in group.get("events") or []
        ]
        animation_events = list(value.get("animationEvents") or [])
        profile_voices = list(value.get("profileVoices") or [])
        wwise_event_keys = {
            str(event.get("id") or "").lower()
            for event in [*skill_events, *animation_events]
            if event.get("id")
        }
        event_media_pairs: set[tuple[str, str]] = set()
        media_ids: set[str] = set()
        content_hashes: set[str] = set()
        for event_key in wwise_event_keys:
            linked = event_cache.get(event_key)
            if not isinstance(linked, dict):
                continue
            for media in linked.get("audio") or []:
                media_key = str(media.get("mediaId") or media.get("src") or "")
                if not media_key:
                    continue
                event_media_pairs.add((event_key, media_key))
                media_ids.add(media_key)
                if media.get("contentSha256"):
                    content_hashes.add(str(media["contentSha256"]))
        for voice in profile_voices:
            for media in voice.get("audio") or []:
                media_key = str(media.get("mediaId") or media.get("src") or "")
                if media_key:
                    media_ids.add(media_key)
                if media.get("contentSha256"):
                    content_hashes.add(str(media["contentSha256"]))
        shared_animation = [
            event for event in animation_events
            if int(event.get("animationOwnerCount") or 0) > 1
        ]
        single_owner_animation = [
            event for event in animation_events
            if int(event.get("animationOwnerCount") or 0) <= 1
        ]
        return {
            "skillEventAssociationCount": len(skill_events),
            "skillUniqueEventCount": len({str(event.get("id") or "").lower() for event in skill_events if event.get("id")}),
            "skillPossibleMediaAssociationCount": sum(possible_media_count(event) for event in skill_events),
            "exactSkillTriggerEventCount": sum(event.get("triggerBindingStatus") == "exactSkillConfig" for event in skill_events),
            "inferredSkillTriggerEventCount": sum(event.get("triggerBindingStatus") != "exactSkillConfig" for event in skill_events),
            "animationEventCount": len(animation_events),
            "animationCallbackOccurrenceCount": sum(int(event.get("animationOccurrenceCount") or len(event.get("evidence") or [])) for event in animation_events),
            "animationPossibleMediaAssociationCount": sum(possible_media_count(event) for event in animation_events),
            "sharedAnimationEventCount": len(shared_animation),
            "sharedAnimationPossibleMediaAssociationCount": sum(possible_media_count(event) for event in shared_animation),
            "singleOwnerAnimationEventCount": len(single_owner_animation),
            "singleOwnerAnimationPossibleMediaAssociationCount": sum(possible_media_count(event) for event in single_owner_animation),
            "footstepSystemEventCount": sum("OnCustomFootStep" in (event.get("animationFunctions") or []) for event in animation_events),
            "directProfileFileCount": sum(possible_media_count(event) for event in profile_voices),
            "eventAssociationCount": len(skill_events) + len(animation_events),
            "candidateAssociationCount": sum(possible_media_count(event) for event in [*skill_events, *animation_events, *profile_voices]),
            "uniqueWwiseEventCount": len(wwise_event_keys),
            "uniqueEventMediaPairCount": len(event_media_pairs),
            "uniqueMediaIdCount": len(media_ids),
            "knownUniqueContentSha256Count": len(content_hashes),
        }

    for value in characters.values():
        value["metrics"] = character_audio_metrics(value)

    unique_event_media_pairs = sum(
        len(value.get("audio") or [])
        for value in event_cache.values()
        if isinstance(value, dict)
    )
    unique_playable_files = {
        str(audio.get("src") or audio.get("mediaId") or "")
        for value in event_cache.values()
        if isinstance(value, dict)
        for audio in value.get("audio") or []
        if audio.get("src") or audio.get("mediaId")
    }
    unique_playable_files.update(profile_voice_media_keys)
    character_animation_event_keys = {
        str(event.get("id") or "").lower()
        for owner in characters.values()
        for event in owner.get("animationEvents") or []
        if event.get("id")
    }
    character_animation_shared_event_keys = {
        key for key in character_animation_event_keys
        if len(animation_owner_ids.get(("character", key), set())) > 1
    }
    character_animation_shared_associations = sum(
        1
        for owner in characters.values()
        for event in owner.get("animationEvents") or []
        if int(event.get("animationOwnerCount") or 0) > 1
    )
    character_animation_single_owner_possible_media = sum(
        int(event.get("possibleMediaCount") or event.get("playableCandidates") or 0)
        for owner in characters.values()
        for event in owner.get("animationEvents") or []
        if int(event.get("animationOwnerCount") or 0) <= 1
    )
    character_animation_shared_graph_possible_media = sum(
        int((animation_event_catalog.get(key) or {}).get("possibleMediaCount") or 0)
        for key in character_animation_shared_event_keys
    )
    serialized_skill_events = [
        event
        for owner in characters.values()
        for group in (owner.get("groups") or {}).values()
        for event in group.get("events") or []
    ] + [
        event
        for owner in enemies.values()
        for event in owner.get("events") or []
    ]
    serialized_animation_events = [
        event
        for bucket in (characters, enemies)
        for owner in bucket.values()
        for event in owner.get("animationEvents") or []
    ]
    serialized_profile_voices = [
        event
        for owner in characters.values()
        for event in owner.get("profileVoices") or []
    ]
    serialized_refs = len(serialized_skill_events) + len(serialized_animation_events) + len(serialized_profile_voices)
    serialized_playable_refs = sum(
        possible_media_count(event) > 0
        for event in [*serialized_skill_events, *serialized_animation_events, *serialized_profile_voices]
    )
    serialized_candidate_associations = sum(
        possible_media_count(event)
        for event in [*serialized_skill_events, *serialized_animation_events, *serialized_profile_voices]
    )
    serialized_animation_candidates = sum(possible_media_count(event) for event in serialized_animation_events)
    serialized_exact_skill_triggers = sum(
        event.get("triggerBindingStatus") == "exactSkillConfig"
        for event in serialized_skill_events
    )
    serialized_exact_enemy_born_triggers = sum(
        event.get("triggerBindingStatus") == "exactEnemyBornBuffConfig"
        for event in serialized_skill_events
    )
    serialized_inferred_skill_triggers = sum(
        event.get("triggerBindingStatus") == "inferredSkillConfigOwner"
        for event in serialized_skill_events
    )
    stats = {
        **(references.get("counts") or {}),
        "gameplayAudioRefs": discovered_refs,
        "gameplayAudioRefsDiscovered": discovered_refs,
        "gameplayAudioRefsLinked": serialized_playable_refs,
        "gameplaySerializedAudioRefs": serialized_refs,
        "gameplayReferenceOnlyAudioRefs": serialized_refs - serialized_playable_refs,
        "gameplayRawAudioRefsLinked": linked_refs,
        "gameplayAudioCandidates": unique_event_media_pairs + len(profile_voice_media_keys),
        "gameplayPossibleMediaAssociations": serialized_candidate_associations,
        "gameplaySerializedPossibleMediaAssociations": serialized_candidate_associations,
        "gameplayRawPossibleMediaAssociations": candidate_count,
        "exactSkillConfigTriggerRefs": serialized_exact_skill_triggers,
        "exactEnemyBornBuffTriggerRefs": serialized_exact_enemy_born_triggers,
        "inferredSkillConfigOwnerRefs": serialized_inferred_skill_triggers,
        "gameplayUniqueEventMediaPairs": unique_event_media_pairs,
        "gameplayUniquePlayableFiles": len(unique_playable_files),
        "animationAudioRefsLinked": sum(possible_media_count(event) > 0 for event in serialized_animation_events),
        "animationAudioRefsSerialized": len(serialized_animation_events),
        "animationAudioRawRefsLinked": animation_linked_refs,
        "animationAudioPossibleMediaAssociations": serialized_animation_candidates,
        "animationAudioRawPossibleMediaAssociations": animation_candidate_count,
        "characterAnimationUniqueEvents": len(character_animation_event_keys),
        "characterAnimationSharedEvents": len(character_animation_shared_event_keys),
        "characterAnimationSharedEventAssociations": character_animation_shared_associations,
        "characterAnimationSingleOwnerPossibleMediaAssociations": character_animation_single_owner_possible_media,
        "characterAnimationSharedGraphPossibleMedia": character_animation_shared_graph_possible_media,
        "profileVoiceRefsLinked": profile_voice_linked_refs,
        "charactersWithPlayableSfx": len(characters),
        "enemiesWithPlayableSfx": len(enemies),
    }
    path = webui_root / Path(str(GAMEPLAY_SFX_REL).format(language=language))
    animation_evidence: dict[str, Any] = {
        "characters": {},
        "enemies": {},
    }
    for bucket_name, bucket in (("characters", characters), ("enemies", enemies)):
        for owner_id, owner in bucket.items():
            evidence_events: list[dict[str, Any]] = []
            for event in owner.get("animationEvents") or []:
                evidence_events.append({
                    "id": event.get("id"),
                    "actionKinds": event.get("actionKinds") or [],
                    "animationFunctions": event.get("animationFunctions") or [],
                    "animationClipContexts": event.get("animationClipContexts") or [],
                    "clipReachability": event.get("clipReachability") or "unresolved",
                    "animatorControllerCount": int(event.get("animatorControllerCount") or 0),
                    "animatorControllerContexts": event.get("animatorControllerContexts") or [],
                    "animatorControllerReachableClipCount": int(
                        event.get("animatorControllerReachableClipCount") or 0
                    ),
                    "animatorControllerUnresolvedClipCount": int(
                        event.get("animatorControllerUnresolvedClipCount") or 0
                    ),
                    "overrideReachability": event.get("overrideReachability") or "unresolved",
                    "animatorOverrideCount": int(event.get("animatorOverrideCount") or 0),
                    "animatorOverrideContexts": event.get("animatorOverrideContexts") or [],
                    "sourceAnimationClips": event.get("sourceAnimationClips") or [],
                    "animationOwnerCount": event.get("animationOwnerCount"),
                    "animationOwnershipScope": event.get("animationOwnershipScope"),
                    "possibleMediaScope": event.get("possibleMediaScope"),
                    "authoredEventIds": event.get("authoredEventIds") or [],
                    "eventAliases": event.get("eventAliases") or [],
                    "evidence": event.get("evidence") or [],
                })
                clips = event.get("sourceAnimationClips") or []
                event["animationClipCount"] = len(clips)
                event["sourceAnimationClips"] = clips[:4]
                event["animationOccurrenceCount"] = len(event.get("evidence") or [])
                event.pop("evidence", None)
            if evidence_events:
                animation_evidence[bucket_name][owner_id] = evidence_events
    unresolved_animation_events: list[dict[str, Any]] = []
    for event_id, evidence in sorted((references.get("unownedAnimationEvents") or {}).items()):
        rows = [row for row in evidence or [] if isinstance(row, dict)]
        controller_contexts: list[dict[str, Any]] = []
        controller_context_seen: set[str] = set()
        for row in rows:
            for context in row.get("animatorControllerContexts") or []:
                if not isinstance(context, dict):
                    continue
                marker = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                if marker in controller_context_seen:
                    continue
                controller_context_seen.add(marker)
                controller_contexts.append(dict(context))
        controller_contexts.sort(
            key=lambda row: (
                str(row.get("name") or ""),
                str(row.get("sourcePath") or ""),
                str(row.get("targetSourceFile") or ""),
            )
        )
        controller_reachable_clips = len({
            str(row.get("clip") or "")
            for row in rows
            if row.get("clip") and row.get("animatorControllerCount")
        })
        controller_unresolved_clips = len({
            str(row.get("clip") or "")
            for row in rows
            if row.get("clip") and not row.get("animatorControllerCount")
        })
        override_contexts: list[dict[str, Any]] = []
        override_context_seen: set[str] = set()
        for row in rows:
            for context in row.get("animatorOverrideContexts") or []:
                if not isinstance(context, dict):
                    continue
                marker = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                if marker in override_context_seen:
                    continue
                override_context_seen.add(marker)
                override_contexts.append(dict(context))
        override_contexts.sort(
            key=lambda row: (
                str(row.get("overrideName") or ""),
                int(row.get("clipIndex") or 0),
                str(row.get("overrideSourcePath") or ""),
            )
        )
        unresolved_animation_events.append({
            "id": event_id,
            "actionKinds": sorted({str(row.get("actionKind") or "action") for row in rows}),
            "animationFunctions": sorted({str(row.get("function") or "") for row in rows if row.get("function")}),
            "animationClipContexts": sorted({str(row.get("clipContext") or "other") for row in rows}),
            "clipReachability": animation_clip_reachability_status(rows),
            "animatorControllerCount": len(controller_contexts),
            "animatorControllerContexts": controller_contexts,
            "animatorControllerReachableClipCount": controller_reachable_clips,
            "animatorControllerUnresolvedClipCount": controller_unresolved_clips,
            "overrideReachability": animation_override_reachability_status(override_contexts),
            "animatorOverrideCount": len(override_contexts),
            "animatorOverrideContexts": override_contexts,
            "sourceAnimationClips": sorted({str(row.get("clip") or "") for row in rows if row.get("clip")}),
            "authoredEventIds": sorted({
                str(row.get("authoredEventId") or event_id)
                for row in rows
                if str(row.get("authoredEventId") or event_id)
            }),
            "ownerStatus": "unresolved",
            "evidence": rows,
        })
    if unresolved_animation_events:
        animation_evidence["ownerUnresolved"] = unresolved_animation_events
    json_dump(path.with_name(GAMEPLAY_SFX_ANIMATION_CATALOG_NAME), {
        "schemaVersion": 1,
        "language": language,
        "events": animation_event_catalog,
    })
    json_dump(path.with_name(GAMEPLAY_SFX_ANIMATION_EVIDENCE_NAME), {
        "schemaVersion": GAMEPLAY_SFX_ANIMATION_EVIDENCE_SCHEMA_VERSION,
        "language": language,
        "animationControllerIndex": references.get("animationControllerIndex") or {},
        **animation_evidence,
    })
    json_dump(path, {
        "schemaVersion": 5,
        "language": language,
        "counts": stats,
        "animationEventCatalogPath": GAMEPLAY_SFX_ANIMATION_CATALOG_NAME,
        "animationEvidencePath": GAMEPLAY_SFX_ANIMATION_EVIDENCE_NAME,
        "authoredPlaySoundActions": references.get("authoredPlaySoundActions") or [],
        "authoredConfigEventReferences": references.get("authoredConfigEventReferences") or [],
        "characters": characters,
        "enemies": enemies,
        "scope": {
            "source": "SkillData/BuffData event references, decoded BuffData PlaySound actions, EnemyData ability bundles, AnimationClip audio callbacks, CharacterTable profile voices, and Wwise HIRC traversal",
            "playSoundActionBoundary": "Current MemoryPack PlaySoundActionData yields exact event, frame window, stop/fade, routing, time-dilation controls, and typed TargetSettings when the nested reader lands exactly; runtime activation conditions and selected targets remain unresolved.",
            "characterOwnership": "direct gameplay skill id",
            "characterFamilyOwnership": "longest playable skill id prefix inferred for authored child SkillData",
            "enemyOwnership": "exact SkillData identifiers recovered from enemy-template AbilitySystemData, with enemy-id prefix fallback and exact born-buff fields",
            "enemyTemplateBoundary": "AbilitySystemData containment is exact, while identifiers preserved only in partially decoded string-hint tails remain ownership-inferred.",
            "animationOwnership": "exact AnimationClip callback, timestamp, and payload; actor ownership inferred from exact character/enemy animation tokens and recovered enemy animation-config reuse; direct resolved AnimatorController PPtrs now annotate authored state/blend-tree membership when serialized state data is valid, while AnimatorOverrideController substitutions annotate only corpus-unique PathID joins and live state selection remains unresolved",
            "animationControllerBoundary": "A direct resolved AnimationClip PPtr in an exported AnimatorController proves authored controller membership. authoredStateReferences additionally prove the controller-local m_AnimationClips slot -> StateConstant -> BlendTree node path and whether that state machine is referenced by a layer; they do not prove transition selection or live Animator execution. AnimatorOverrideController rows now preserve original/effective clip substitutions when both controller and clip PathIDs are unique in the exported corpus, but the raw override payload has no serialized-file envelope, so these are not exact Unity-file joins and do not prove live activation. No animation callback is promoted into a skill trigger by this evidence.",
            "unownedAnimationBoundary": "Every actor/monster AnimationClip callback with a supported audio function is retained. Clips without a bounded playable-character or enemy-template token stay owner-unresolved and appear only in the debug Audio evidence surface; generic non-actor clip indexing remains a separate exporter gap.",
            "animationMediaBoundary": "An owned clip proves that its callback requests the Event. Shared playable-character Events expose a shared Wwise selector graph; its reachable leaves are not attributed to one character until switch/state values are decoded.",
            "profileVoiceOwnership": "direct CharacterTable.profileVoice ownership linked to the exact AudioDialog path stem; bark/random selection remains unresolved",
            "referenceOnlyBoundary": "Exact SkillData/BuffData and owned AnimationClip trigger contexts remain serialized when the Event is absent from current Wwise banks or has no decoded possible media; Gameplay only renders records with playable files.",
            "unownedConfigBoundary": "A length-prefixed au_* string in one exact SkillData/BuffData binary proves an authored gameplay-config audio reference even when no character/enemy owner is recovered. It does not identify the field subtype, activation condition, runtime owner, Event posting, selected media, or audibility.",
            "runtimeSelection": "Possible media files come from typed Wwise v150 edges and are grouped by Play root and selector relation; the live branch selected by switches, states, random/sequence containers, and layers remains unresolved.",
            "actionDispatchBoundary": "Typed v150 Event Action ordinals and serialized DelayTime, TransitionTime, and Probability properties are preserved. They prove authored dispatch membership and controls, not live action execution, evaluated probability, or sample-accurate audible simultaneity.",
        },
    })
    return stats
