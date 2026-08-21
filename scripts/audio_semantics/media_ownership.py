"""Project exact authored evidence into coarse decoded-media ownership.

Ownership is deliberately weaker than playback placement.  A possible Wwise
leaf can be owned by a scene definition, animation, component, or voice path
without proving that the leaf was selected or heard at runtime.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 3

CHARACTER_TABLE_RELS = (
    "structured/StreamingAssets/Table/CharacterTable.json",
    "structured/Persistent/Table/CharacterTable.json",
)
ENEMY_TABLE_RELS = (
    "structured/StreamingAssets/Table/EnemyTable.json",
    "structured/Persistent/Table/EnemyTable.json",
)
ENEMY_TEMPLATE_TABLE_RELS = (
    "structured/StreamingAssets/Table/EnemyTemplateTable.json",
    "structured/Persistent/Table/EnemyTemplateTable.json",
)
CHARACTER_KEY_RE = re.compile(r"^chr_(\d{4})_([a-z0-9]+)$", re.IGNORECASE)
ENEMY_KEY_RE = re.compile(r"^eny_\d+_[a-z0-9]+(?:_[a-z0-9]+)*$", re.IGNORECASE)
ANIMATION_CLIP_RE = re.compile(
    r"^a_(?P<family>actor|enemy|monster)_(?P<token>[^_]+)(?:_|$)",
    re.IGNORECASE,
)
CHARACTER_NUMERIC_EVENT_PREFIX_RE = re.compile(
    r"^(?:au_)?chr_(\d{4})(?:_|$)", re.IGNORECASE
)
CHARACTER_CONTEXT_OWNER_FIELDS = (
    "ownerId",
    "characterId",
    "speakerId",
    "speakerChannel",
    "speakerActorId",
)

ANIMATION_ACTION_CONTEXT_KINDS = frozenset({
    "characterAnimation",
    "enemyAnimation",
    "animationCallbackOwnerUnresolved",
})
ANIMATION_ACTION_FUNCTIONS = frozenset({
    "PostAudioEvent",
    "PostAudioEventAdvance",
    "PostAudioEventAtPosition",
})
ANIMATION_CLIP_PREFIXES = (
    "a_actor_",
    "a_enemy_",
    "a_monster_",
    "a_char_",
)

CONTEXT_OWNERSHIP_DOMAINS = {
    "sceneGlobalAudioEvent": "sceneEnvironment",
    "sceneEmitterAudioEvent": "sceneObject",
    "characterAnimation": "characterAnimation",
    "enemyAnimation": "enemyAnimation",
    "animationCallbackOwnerUnresolved": "animationCallback",
    "characterSkill": "characterGameplay",
    "enemySkill": "enemyGameplay",
    "buffPlaySoundAction": "gameplayAction",
    "projectileSoundField": "projectileGameplay",
    "monoBehaviourAudioIdField": "authoredComponent",
    "interactiveAudioTrigger": "interactiveObject",
    "interactiveComponentTrigger": "interactiveObject",
    "interactiveComponentPropertyAudio": "interactiveObject",
    "interactivePropertyMapAudio": "interactiveObject",
    "interactiveTemplateConfigAudio": "interactiveObject",
    "interactiveTemplateActionAudio": "interactiveObject",
    "interactiveEmbeddedActionAudio": "interactiveObject",
    "physicsAudioComponentEvent": "physicalEnvironment",
    "modelViewStateAudioEvent": "modelView",
    "modelViewStatePositionAudioEvent": "modelView",
    "charInteractAudioEvent": "characterInteraction",
    "levelSequenceAudio": "cutscene",
    "cutsceneTimeline": "cutscene",
    "levelScriptAudioAction": "levelScript",
    "levelScriptAudioCueBehaviorEvent": "levelScript",
    "levelScriptRadioTrigger": "levelScriptRadio",
    "audioGlobalConfigEvent": "globalAudioSystem",
    "audioGlobalConfigEventHash": "globalAudioSystem",
    "audioGlobalMusicCueBehaviorEvent": "globalAudioSystem",
    "uiAnimationOpenEvent": "ui",
    "activityPushPopupBgmEvent": "ui",
    "activityCenterBgmEvent": "ui",
    "uiVideoAudioEvent": "ui",
    "domainRegionSwitchEvent": "ui",
    "domainUpgradeAnimationEvent": "ui",
    "typedUiTableWwiseEvent": "ui",
    "snsVoiceMessageEvent": "snsVoice",
    "audioDialogVoiceDefinition": "voiceSystem",
    "responsiveDialogVoice": "voiceSystem",
    "voiceToneVariant": "voiceSystem",
    "voiceDefaultWwiseEvent": "voiceSystem",
    "voiceNarratingChannelEvent": "voiceSystem",
    "voiceRadioChannelEvent": "voiceSystem",
    "audioDialogOverrideWwiseEvent": "voiceSystem",
    "responsiveVoiceEventTemplate": "voiceSystem",
    "voiceTableWwiseEvent": "voiceSystem",
    "abilityVoiceTriggerAction": "voiceSystem",
}

SCENE_ROLE_DOMAINS = {
    "outdoorRoomToneEvent": ("sceneEnvironment", "ambience"),
    "authoredAmbientEmitterCandidate": ("sceneEnvironment", "ambience"),
    "authoredSceneEmitterEvent": ("sceneObject", None),
    "battleMusicTriggerEvent": ("sceneMusic", "music"),
    "levelInitEvent": ("sceneLifecycle", None),
    "levelInitEvents": ("sceneLifecycle", None),
    "levelExitEvents": ("sceneLifecycle", None),
}


def _normalized_src(value: Any) -> str:
    return str(value or "").strip().replace("\\", "/").casefold()


def _effective_category(row: dict[str, Any]) -> str:
    return str(
        row.get("semanticCategory") or row.get("audioCategory") or "unknown"
    ).strip().lower()


def collect_character_audio_identity_catalog(export_root: Path) -> dict[str, Any]:
    """Load exact playable-character ids from the current CharacterTable rows."""

    characters: dict[str, dict[str, Any]] = {}
    sources: list[str] = []
    malformed_sources: list[str] = []
    for relative in CHARACTER_TABLE_RELS:
        path = export_root / relative
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            malformed_sources.append(relative)
            continue
        if not isinstance(payload, dict):
            malformed_sources.append(relative)
            continue
        sources.append(relative)
        for raw_key in payload:
            character_id = str(raw_key or "").strip().casefold()
            match = CHARACTER_KEY_RE.fullmatch(character_id)
            if not match:
                continue
            row = characters.setdefault(character_id, {
                "characterId": character_id,
                "numericId": match.group(1),
                "token": match.group(2).casefold(),
                "sources": [],
            })
            row["sources"].append(relative)

    numeric_ids: dict[str, list[str]] = defaultdict(list)
    for character_id, row in characters.items():
        numeric_ids[str(row["numericId"])].append(character_id)
        row["sources"] = sorted(set(row["sources"]))
    conflicts = {
        numeric_id: sorted(character_ids)
        for numeric_id, character_ids in numeric_ids.items()
        if len(character_ids) != 1
    }
    status = "validatedCharacterTableKeys" if characters else "characterTableUnavailable"
    if malformed_sources and not sources:
        status = "characterTableMalformed"
    return {
        "schemaVersion": SCHEMA_VERSION,
        "status": status,
        "characters": sorted(characters.values(), key=lambda row: row["characterId"]),
        "sourceFiles": sorted(sources),
        "malformedSourceFiles": sorted(malformed_sources),
        "counts": {
            "characters": len(characters),
            "uniqueNumericIds": sum(len(rows) == 1 for rows in numeric_ids.values()),
            "conflictingNumericIds": len(conflicts),
        },
        "conflictingNumericIds": conflicts,
        "evidenceBoundary": (
            "Character ids are exact current-build CharacterTable keys. The catalog "
            "does not infer playable ownership from localized display names or asset "
            "filename similarity."
        ),
    }


def annotate_event_character_audio_identity(
    event_rows: Iterable[dict[str, Any]],
    character_catalog: dict[str, Any],
) -> dict[str, Any]:
    """Link authored character Event namespaces to exact CharacterTable ids."""

    characters = {
        str(row.get("characterId") or "").casefold(): row
        for row in character_catalog.get("characters") or ()
        if isinstance(row, dict) and row.get("characterId")
    }
    numeric_ids: dict[str, list[str]] = defaultdict(list)
    token_ids: dict[str, list[str]] = defaultdict(list)
    exact_patterns: dict[str, re.Pattern[str]] = {}
    for character_id, row in characters.items():
        numeric_ids[str(row.get("numericId") or "")].append(character_id)
        token = str(row.get("token") or "").casefold()
        if token:
            token_ids[token].append(character_id)
        exact_patterns[character_id] = re.compile(
            rf"(?<![a-z0-9]){re.escape(character_id)}(?![a-z0-9])",
            re.IGNORECASE,
        )

    matched = 0
    candidate_chr_namespace_events = 0
    candidate_token_prefix_events = 0
    ambiguous = 0
    character_ids: set[str] = set()
    match_status_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    context_relationship_counts: Counter[str] = Counter()
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(
            event.get("id") or event.get("eventId") or event.get("name") or ""
        ).strip()
        folded_event_id = event_id.casefold()
        token_prefix_matches = sorted(
            token
            for token in token_ids
            if folded_event_id == token or folded_event_id.startswith(f"{token}_")
        )
        is_chr_namespace = "chr_" in folded_event_id
        if not is_chr_namespace and not token_prefix_matches:
            continue
        if is_chr_namespace:
            candidate_chr_namespace_events += 1
        if token_prefix_matches:
            candidate_token_prefix_events += 1

        exact_matches = sorted(
            character_id
            for character_id, pattern in exact_patterns.items()
            if pattern.search(folded_event_id)
        )
        owner_ids: list[str] = []
        match_status = ""
        evidence = ""
        if len(exact_matches) == 1:
            owner_ids = exact_matches
            match_status = "exactCharacterTableKeyToken"
            evidence = "exactDelimitedCharacterTableKeyInWwiseEventId"
        elif len(exact_matches) > 1:
            event["characterAudioIdentityStatus"] = (
                "ambiguousMultipleCharacterTableKeyTokens"
            )
            event["characterAudioNameMatchedCandidateIds"] = exact_matches
            ambiguous += 1
            continue
        else:
            numeric_match = CHARACTER_NUMERIC_EVENT_PREFIX_RE.match(folded_event_id)
            numeric_candidates = (
                sorted(numeric_ids.get(numeric_match.group(1)) or ())
                if numeric_match
                else []
            )
            if len(numeric_candidates) == 1:
                owner_ids = numeric_candidates
                match_status = "uniqueCharacterTableNumericIdPrefix"
                evidence = "uniqueFourDigitCharacterTableIdInChrEventPrefix"
            elif len(numeric_candidates) > 1:
                event["characterAudioIdentityStatus"] = (
                    "ambiguousCharacterTableNumericIdPrefix"
                )
                event["characterAudioNameMatchedCandidateIds"] = numeric_candidates
                ambiguous += 1
                continue
            elif len(token_prefix_matches) == 1:
                token_candidates = sorted(token_ids[token_prefix_matches[0]])
                if len(token_candidates) == 1:
                    owner_ids = token_candidates
                    match_status = "uniqueCharacterTableTokenPrefix"
                    evidence = "uniqueCharacterTableTokenAtWwiseEventPrefix"
                else:
                    event["characterAudioIdentityStatus"] = (
                        "ambiguousCharacterTableTokenPrefix"
                    )
                    event["characterAudioNameMatchedCandidateIds"] = token_candidates
                    ambiguous += 1
                    continue
            elif len(token_prefix_matches) > 1:
                token_candidates = sorted({
                    character_id
                    for token in token_prefix_matches
                    for character_id in token_ids[token]
                })
                event["characterAudioIdentityStatus"] = (
                    "ambiguousMultipleCharacterTableTokenPrefixes"
                )
                event["characterAudioNameMatchedCandidateIds"] = token_candidates
                ambiguous += 1
                continue
        if not owner_ids:
            continue

        context_owner_ids: set[str] = set()
        for context in event.get("contexts") or ():
            if not isinstance(context, dict):
                continue
            for field in CHARACTER_CONTEXT_OWNER_FIELDS:
                value = str(context.get(field) or "").strip().casefold()
                if value in characters:
                    context_owner_ids.add(value)
        owner_set = set(owner_ids)
        if not context_owner_ids:
            context_relationship = "nameIdentityOnly"
        elif owner_set == context_owner_ids:
            context_relationship = "exactContextOwnerAgreement"
        elif owner_set <= context_owner_ids:
            context_relationship = "namedOwnerWithAdditionalCharacterContexts"
        else:
            context_relationship = "namedEventReferencedByOtherCharacterContexts"

        event["characterAudioIdentityStatus"] = match_status
        event["characterAudioOwnerIds"] = owner_ids
        event["characterAudioOwnerTokens"] = sorted({
            str(characters[owner_id].get("token") or "")
            for owner_id in owner_ids
            if characters[owner_id].get("token")
        })
        event["characterAudioNameMatchEvidence"] = evidence
        event["characterAudioContextOwnerIds"] = sorted(context_owner_ids)
        event["characterAudioContextRelationshipStatus"] = context_relationship
        matched += 1
        character_ids.update(owner_ids)
        match_status_counts[match_status] += 1
        category_counts[str(event.get("category") or "unknown")] += 1
        context_relationship_counts[context_relationship] += 1

    return {
        "schemaVersion": SCHEMA_VERSION,
        "catalogStatus": character_catalog.get("status") or "unknown",
        "catalogSourceFiles": list(character_catalog.get("sourceFiles") or ()),
        "catalogCounts": dict(character_catalog.get("counts") or {}),
        "candidateChrNamespaceEvents": candidate_chr_namespace_events,
        "candidateCharacterTokenPrefixEvents": candidate_token_prefix_events,
        "candidateCharacterNamespaceEvents": (
            candidate_chr_namespace_events + candidate_token_prefix_events
        ),
        "eventsWithCharacterAudioIdentity": matched,
        "eventsWithAmbiguousCharacterAudioIdentity": ambiguous,
        "charactersWithMatchedAudioEvents": len(character_ids),
        "matchStatusCounts": dict(sorted(match_status_counts.items())),
        "categoryCounts": dict(sorted(category_counts.items())),
        "contextRelationshipCounts": dict(sorted(context_relationship_counts.items())),
        "evidenceBoundary": (
            "A delimited full CharacterTable key in an Event id is exact authored "
            "namespace ownership. When the authored token is shortened or omitted, "
            "a leading chr_NNNN segment is accepted only when that four-digit id is "
            "unique in the current CharacterTable. An Event-leading internal character "
            "token is accepted only with an exact delimiter and one catalog owner. "
            "This recovers the named character "
            "domain, not an action, skill, runtime request, selected Wwise leaf, "
            "playback location, or audibility."
        ),
    }


def _load_overlay_table(
    export_root: Path,
    relatives: tuple[str, ...],
) -> tuple[dict[str, Any], list[str], list[str], list[str]]:
    """Load a table overlay and fail closed when its Persistent layer is bad.

    The Persistent layer is an authoritative overlay when it exists.  A bad
    Persistent file must therefore not silently fall back to StreamingAssets;
    otherwise a stale base table would look like a validated current catalog.
    """

    rows: dict[str, Any] = {}
    sources: list[str] = []
    conflicts: list[str] = []
    malformed_sources: list[str] = []
    malformed_persistent = False
    for relative in relatives:
        path = export_root / relative
        if not path.exists():
            continue
        is_persistent = "/persistent/" in f"/{relative}".casefold()
        if not path.is_file():
            malformed_sources.append(relative)
            if is_persistent:
                malformed_persistent = True
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            malformed_sources.append(relative)
            if is_persistent:
                malformed_persistent = True
            continue
        if not isinstance(payload, dict):
            malformed_sources.append(relative)
            if is_persistent:
                malformed_persistent = True
            continue
        sources.append(relative)
        for key, value in payload.items():
            folded = str(key or "").strip().casefold()
            if not folded:
                continue
            if folded in rows and rows[folded] != value:
                conflicts.append(folded)
            # Persistent is later in the tuple and is the effective overlay.
            rows[folded] = value
    if malformed_persistent:
        rows = {}
    return (
        rows,
        sorted(set(sources)),
        sorted(set(conflicts)),
        sorted(set(malformed_sources)),
    )


def collect_animation_entity_catalog(export_root: Path | None) -> dict[str, Any]:
    """Collect exact CharacterTable/EnemyTable animation identity surfaces."""

    root = Path(export_root) if export_root is not None else Path()
    (
        character_rows,
        character_sources,
        character_conflicts,
        character_malformed,
    ) = _load_overlay_table(
        root, CHARACTER_TABLE_RELS
    )
    enemy_rows, enemy_sources, enemy_conflicts, enemy_malformed = _load_overlay_table(
        root, ENEMY_TABLE_RELS
    )
    (
        template_rows,
        template_sources,
        template_conflicts,
        template_malformed,
    ) = _load_overlay_table(
        root, ENEMY_TEMPLATE_TABLE_RELS
    )

    character_ids = sorted(
        key for key in character_rows if CHARACTER_KEY_RE.fullmatch(key)
    )
    character_token_ids: dict[str, list[str]] = defaultdict(list)
    for character_id in character_ids:
        match = CHARACTER_KEY_RE.fullmatch(character_id)
        if match:
            character_token_ids[match.group(2).casefold()].append(character_id)

    enemy_instance_ids = sorted(
        key for key in enemy_rows if ENEMY_KEY_RE.fullmatch(key)
    )
    enemy_template_ids = sorted(
        key for key in template_rows if ENEMY_KEY_RE.fullmatch(key)
    )
    enemy_template_ids.extend(
        sorted({
            str(row.get("templateId") or "").strip().casefold()
            for row in enemy_rows.values()
            if isinstance(row, dict)
            and ENEMY_KEY_RE.fullmatch(str(row.get("templateId") or "").strip().casefold())
        })
    )
    enemy_template_ids = sorted(set(enemy_template_ids))
    enemy_token_instance_ids: dict[str, list[str]] = defaultdict(list)
    enemy_token_template_ids: dict[str, set[str]] = defaultdict(set)
    for enemy_id in enemy_instance_ids:
        match = re.match(r"^eny_\d+_([^_]+)", enemy_id, re.IGNORECASE)
        if match:
            enemy_token_instance_ids[match.group(1).casefold()].append(enemy_id)
        row = enemy_rows.get(enemy_id)
        template_id = str(row.get("templateId") or "").strip().casefold() if isinstance(row, dict) else ""
        if template_id and ENEMY_KEY_RE.fullmatch(template_id):
            token_match = re.match(r"^eny_\d+_([^_]+)", template_id, re.IGNORECASE)
            if token_match:
                enemy_token_template_ids[token_match.group(1).casefold()].add(template_id)
    for template_id in enemy_template_ids:
        match = re.match(r"^eny_\d+_([^_]+)", template_id, re.IGNORECASE)
        if match:
            enemy_token_template_ids[match.group(1).casefold()].add(template_id)

    source_files = {
        "CharacterTable": character_sources,
        "EnemyTable": enemy_sources,
        "EnemyTemplateTable": template_sources,
    }
    conflicts = {
        "CharacterTable": sorted(set(character_conflicts)),
        "EnemyTable": sorted(set(enemy_conflicts)),
        "EnemyTemplateTable": sorted(set(template_conflicts)),
    }
    malformed_sources = {
        "CharacterTable": sorted(set(character_malformed)),
        "EnemyTable": sorted(set(enemy_malformed)),
        "EnemyTemplateTable": sorted(set(template_malformed)),
    }
    table_statuses: dict[str, str] = {}
    for table_name, sources_for_table, malformed_for_table, conflicts_for_table in (
        ("CharacterTable", character_sources, character_malformed, character_conflicts),
        ("EnemyTable", enemy_sources, enemy_malformed, enemy_conflicts),
        ("EnemyTemplateTable", template_sources, template_malformed, template_conflicts),
    ):
        persistent_malformed = any(
            "/persistent/" in f"/{source}".casefold()
            for source in malformed_for_table
        )
        if persistent_malformed:
            table_statuses[table_name] = "malformedPersistentOverlay"
        elif malformed_for_table:
            table_statuses[table_name] = "malformed"
        elif conflicts_for_table:
            table_statuses[table_name] = "conflictedPersistentOverlay"
        elif sources_for_table:
            table_statuses[table_name] = "validated"
        else:
            table_statuses[table_name] = "missing"
    any_malformed = any(malformed_sources.values())
    any_conflict = any(conflicts.values())
    if any_malformed:
        catalog_status = "animationEntityCatalogMalformed"
    elif any_conflict:
        catalog_status = "animationEntityCatalogConflicted"
    elif character_ids or enemy_instance_ids or enemy_template_ids:
        catalog_status = "validatedAnimationEntityCatalog"
    else:
        catalog_status = "animationEntityCatalogUnavailable"
    return {
        "schemaVersion": 1,
        "status": catalog_status,
        "sourceFiles": source_files,
        "conflictingKeys": conflicts,
        "malformedSources": malformed_sources,
        "tableStatuses": table_statuses,
        "characterIds": character_ids,
        "characterTokenIds": {
            key: sorted(value) for key, value in sorted(character_token_ids.items())
        },
        "enemyInstanceIds": enemy_instance_ids,
        "enemyTemplateIds": enemy_template_ids,
        "enemyTokenInstanceIds": {
            key: sorted(value)
            for key, value in sorted(enemy_token_instance_ids.items())
        },
        "enemyTokenTemplateIds": {
            key: sorted(value)
            for key, value in sorted(enemy_token_template_ids.items())
        },
        "evidenceBoundary": (
            "CharacterTable keys are exact playable-character rows. EnemyTable keys "
            "are exact enemy instances/variants; EnemyTemplateTable keys and "
            "templateId fields are exact enemy templates. Animation clip tokens are "
            "accepted only against the current catalog and remain ambiguous when "
            "more than one identity is possible. No runtime execution is inferred."
        ),
    }


def _animation_clip_resolution(
    clip: Any,
    *,
    owner_kind: str,
    owner_id: str,
    known_owner_ids: set[str],
    catalog: dict[str, Any],
) -> dict[str, Any]:
    text = str(clip or "").strip()
    match = ANIMATION_CLIP_RE.match(text)
    if not match:
        return {
            "clip": text,
            "resolutionStatus": "unresolved",
            "tokenResolutionStatus": "unresolved",
            "ownershipStatus": "unresolved",
            "characterTableIds": [],
            "enemyTableIds": [],
            "enemyTemplateIds": [],
            "candidateEntityIds": [],
            "resolvedEntityIds": [],
        }
    family = match.group("family").casefold()
    token = match.group("token").casefold()
    owner_kind = str(owner_kind or "").strip().casefold()
    owner_id = str(owner_id or "").strip().casefold()
    if family == "actor":
        candidate_characters = list(
            (catalog.get("characterTokenIds") or {}).get(token) or []
        )
        candidate_enemies: list[str] = []
        candidate_templates: list[str] = []
        family_matches = owner_kind in {"", "character"}
    else:
        candidate_characters = []
        candidate_enemies = list(
            (catalog.get("enemyTokenInstanceIds") or {}).get(token) or []
        )
        candidate_templates = list(
            (catalog.get("enemyTokenTemplateIds") or {}).get(token) or []
        )
        family_matches = owner_kind in {"", "enemy"}
    candidates = set(candidate_characters) | set(candidate_enemies) | set(candidate_templates)
    if not family_matches or not token or not candidates:
        status = "unresolved"
        evidence = "animationClipTokenNoCurrentTableMatch"
    elif owner_id and owner_id in set(candidate_characters):
        status = "exactCharacterTableInstance"
        evidence = "exactCharacterTableKeyAndAnimationClipToken"
    elif owner_id and owner_id in set(candidate_enemies):
        status = "exactEnemyTableInstance"
        evidence = "exactEnemyTableKeyAndAnimationClipToken"
    elif owner_id and owner_id in set(candidate_templates):
        status = "exactEnemyTemplate"
        evidence = "exactEnemyTemplateKeyAndAnimationClipToken"
    elif owner_id and owner_id in known_owner_ids and len(candidates) == 1:
        status = "uniqueToken"
        evidence = "uniqueAnimationClipTokenForKnownOwner"
    elif not owner_id and len(candidates) == 1:
        status = "uniqueToken"
        evidence = "uniqueAnimationClipTokenInCurrentEntityCatalog"
    elif len(set(candidate_templates)) == 1 and family in {"enemy", "monster"}:
        status = "uniqueToken"
        evidence = "uniqueEnemyTemplateTokenWithVariantInstances"
    else:
        status = "ambiguous"
        evidence = "multipleCurrentEntityIdentitiesShareAnimationClipToken"
    candidate_entity_ids = sorted(candidates)[:32]
    resolved_entity_ids: list[str] = []
    if status.startswith("exact") and owner_id:
        resolved_entity_ids = [owner_id]
    ownership_status = (
        "resolved"
        if resolved_entity_ids
        else "candidateOnly"
        if status == "uniqueToken"
        else "unresolved"
    )
    return {
        "clip": text,
        "clipFamily": family,
        "clipToken": token,
        "ownerKind": owner_kind,
        "ownerId": owner_id,
        "resolutionStatus": status,
        "tokenResolutionStatus": status,
        "ownershipStatus": ownership_status,
        "resolutionEvidence": evidence,
        "characterTableIds": candidate_characters[:32],
        "enemyTableIds": candidate_enemies[:32],
        "enemyTemplateIds": candidate_templates[:32],
        "candidateEntityIds": candidate_entity_ids,
        "resolvedEntityIds": resolved_entity_ids,
    }
def annotate_event_animation_callback_links(
    event_rows: Iterable[dict[str, Any]],
    *,
    export_root: Path | None = None,
    entity_catalog: dict[str, Any] | None = None,
    limit: int = 32,
) -> dict[str, Any]:
    """Project exact serialized AnimationClip audio callbacks onto Events."""

    catalog = entity_catalog
    if catalog is None and export_root is not None:
        catalog = collect_animation_entity_catalog(export_root)
    catalog = catalog if isinstance(catalog, dict) else {}
    catalog_available = bool(catalog.get("status"))
    matched = 0
    unknown_category = 0
    with_controller_reachability = 0
    owner_kind_counts: Counter[str] = Counter()
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        clips: set[str] = set()
        owner_ids: set[str] = set()
        functions: set[str] = set()
        context_kinds: set[str] = set()
        action_kinds: set[str] = set()
        reachability: set[str] = set()
        controller_names: set[str] = set()
        clip_resolutions: list[dict[str, Any]] = []
        resolution_markers: set[str] = set()
        resolution_statuses: set[str] = set()
        token_resolution_statuses: set[str] = set()
        ownership_classes: set[str] = set()
        resolved_entity_ids: set[str] = set()
        candidate_entity_ids: set[str] = set()
        controller_membership_statuses: set[str] = set()
        occurrence_ownership: list[dict[str, Any]] = []
        occurrence_count = 0
        animation_contexts = [
            context for context in event.get("contexts") or ()
            if isinstance(context, dict)
            and str(context.get("kind") or "") in ANIMATION_ACTION_CONTEXT_KINDS
        ]
        eligible_contexts: list[tuple[dict[str, Any], set[str], set[str]]] = []
        for context in animation_contexts:
            supported_functions = {
                str(value) for value in context.get("animationFunctions") or ()
            } & ANIMATION_ACTION_FUNCTIONS
            context_clips = {
                str(value) for value in context.get("animationClips") or () if value
            }
            if supported_functions and context_clips:
                eligible_contexts.append((context, supported_functions, context_clips))
        event_owner_ids = {
            str(context.get("ownerId") or "").strip().casefold()
            for context, _supported_functions, _context_clips in eligible_contexts
            if str(context.get("ownerId") or "").strip()
            and str(context.get("kind") or "") in {
                "characterAnimation",
                "enemyAnimation",
            }
        }
        for context, supported_functions, context_clips in eligible_contexts:
            if not isinstance(context, dict):
                continue
            kind = str(context.get("kind") or "")
            if kind not in ANIMATION_ACTION_CONTEXT_KINDS:
                continue
            clips.update(context_clips)
            functions.update(supported_functions)
            context_kinds.add(kind)
            ownership_class = str(context.get("animationOwnershipClass") or "").strip()
            if ownership_class:
                ownership_classes.add(ownership_class)
            context_entity_ids = {
                str(value) for value in context.get("animationEntityIds") or () if str(value)
            }
            # A named character/enemy animation context is already a resolved
            # authored owner. Owner-unresolved callback contexts are not.
            context_owner_id = str(context.get("ownerId") or "").strip()
            if kind in {"characterAnimation", "enemyAnimation"} and context_owner_id:
                context_entity_ids.add(context_owner_id)
            resolved_entity_ids.update(
                value.casefold() for value in context_entity_ids if value
            )
            controller_membership_statuses.update(
                str(value)
                for value in context.get("animationControllerMembershipStatuses") or ()
                if str(value)
            )
            for occurrence in context.get("animationOccurrences") or ():
                if isinstance(occurrence, dict) and len(occurrence_ownership) < limit:
                    occurrence_ownership.append(dict(occurrence))
            context_owner_kind = str(context.get("ownerKind") or "").strip().casefold()
            if not context_owner_kind:
                context_owner_kind = (
                    "character" if kind == "characterAnimation"
                    else "enemy" if kind == "enemyAnimation" else ""
                )
            context_owner_id = str(context.get("ownerId") or "").strip()
            for clip in sorted(context_clips):
                resolution = _animation_clip_resolution(
                    clip,
                    owner_kind=context_owner_kind,
                    owner_id=context_owner_id,
                    known_owner_ids=event_owner_ids,
                    catalog=catalog,
                )
                marker = json.dumps(
                    resolution, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                if marker not in resolution_markers:
                    resolution_markers.add(marker)
                    clip_resolutions.append(resolution)
                resolution_statuses.add(
                    str(resolution.get("resolutionStatus") or "unresolved")
                )
                token_resolution_statuses.add(
                    str(resolution.get("tokenResolutionStatus") or "unresolved")
                )
                candidate_entity_ids.update(
                    str(value)
                    for key in (
                        "candidateEntityIds",
                        "characterTableIds",
                        "enemyTableIds",
                        "enemyTemplateIds",
                    )
                    for value in resolution.get(key) or ()
                    if str(value)
                )
                if str(resolution.get("resolutionStatus") or "").startswith("exact"):
                    resolved_entity_ids.update(
                        str(value).casefold()
                        for value in resolution.get("resolvedEntityIds") or ()
                        if str(value)
                    )
            action_kinds.update(
                str(value) for value in context.get("actionKinds") or () if value
            )
            clip_reachability = str(context.get("clipReachability") or "").strip()
            if clip_reachability:
                reachability.add(clip_reachability)
            owner_id = str(context.get("ownerId") or "").strip()
            if owner_id and kind in {"characterAnimation", "enemyAnimation"}:
                owner_ids.add(owner_id)
            for controller in context.get("animatorControllerContexts") or ():
                if not isinstance(controller, dict):
                    continue
                name = str(controller.get("name") or "").strip()
                if name:
                    controller_names.add(name)
            occurrence_count += int(context.get("animationOccurrenceCount") or 0)
            owner_kind_counts[kind] += 1
        if not clips:
            continue
        matched += 1
        if str(event.get("category") or "unknown") == "unknown":
            unknown_category += 1
        if "directAnimatorController" in reachability:
            with_controller_reachability += 1
        event["animationCallbackLinkStatus"] = (
            "exactSerializedAnimationClipAudioCallback"
        )
        event["animationCallbackClips"] = sorted(clips)[:limit]
        event["animationCallbackOwnerIds"] = sorted(owner_ids)[:limit]
        event["animationCallbackFunctions"] = sorted(functions)[:limit]
        event["animationCallbackContextKinds"] = sorted(context_kinds)[:limit]
        event["animationCallbackActionKinds"] = sorted(action_kinds)[:limit]
        event["animationCallbackReachabilityStatuses"] = sorted(reachability)[:limit]
        event["animationCallbackAnimatorControllerNames"] = sorted(
            controller_names
        )[:limit]
        event["animationCallbackOwnershipClasses"] = sorted(ownership_classes)[:limit]
        event["animationCallbackEntityIds"] = sorted(resolved_entity_ids)[:limit]
        event["animationCallbackControllerMembershipStatuses"] = sorted(
            controller_membership_statuses
        )[:limit]
        if catalog_available:
            event["animationCallbackClipResolutions"] = clip_resolutions[:limit]
            event["animationCallbackResolutionStatuses"] = sorted(resolution_statuses)[:limit]
            event["animationCallbackTokenResolutionStatuses"] = sorted(
                token_resolution_statuses
            )[:limit]
            event["animationCallbackTokenResolutionStatus"] = (
                next(iter(token_resolution_statuses))
                if len(token_resolution_statuses) == 1
                else "mixed"
                if token_resolution_statuses
                else "unresolved"
            )
            event["animationCallbackResolvedEntityIds"] = sorted(
                resolved_entity_ids
            )[:limit]
            event["animationCallbackCandidateEntityIds"] = sorted(
                candidate_entity_ids
            )[:limit]
            event["animationCallbackEntityIds"] = sorted(resolved_entity_ids)[:limit]
            event["animationCallbackOwnershipStatus"] = (
                "shared"
                if len(event_owner_ids) > 1
                else next(iter(resolution_statuses))
                if (
                    len(resolution_statuses) == 1
                    and next(iter(resolution_statuses)).startswith("exact")
                )
                else "resolved"
                if resolved_entity_ids
                else "candidateOnly"
                if "uniqueToken" in token_resolution_statuses
                else "ambiguous"
                if "ambiguous" in resolution_statuses
                else "unresolved"
            )
        else:
            event["animationCallbackResolvedEntityIds"] = sorted(
                resolved_entity_ids
            )[:limit]
            event["animationCallbackEntityIds"] = sorted(resolved_entity_ids)[:limit]
        event["animationCallbackOccurrences"] = occurrence_ownership
        event["animationCallbackOccurrenceCount"] = occurrence_count
        event["animationCallbackLinkEvidence"] = (
            "exactAnimationClipPostAudioEventContext"
        )
        event["animationCallbackLinkTruncated"] = any(
            len(values) > limit
            for values in (
                clips, owner_ids, functions, context_kinds, action_kinds,
                reachability, controller_names, ownership_classes,
                resolved_entity_ids, candidate_entity_ids,
                controller_membership_statuses, occurrence_ownership,
            )
        )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "eventsWithAnimationCallbackLink": matched,
        "unknownCategoryEventsWithAnimationCallbackLink": unknown_category,
        "eventsWithDirectAnimatorControllerReachability": (
            with_controller_reachability
        ),
        "animationCallbackOwnerKindCounts": dict(sorted(owner_kind_counts.items())),
        "animationEntityCatalogStatus": catalog.get("status") or "unavailable",
        "evidenceBoundary": (
            "A supported serialized PostAudioEvent callback on an AnimationClip "
            "proves that the clip requests the Wwise Event and preserves its authored "
            "character/enemy owner. AnimatorController membership is reported when "
            "available. The link does not prove Animator execution, callback timing, "
            "selected Wwise media, playback, audibility, or an SFX category."
        ),
    }


def canonical_animation_action_name(value: Any) -> str:
    """Return the conservative comparison key for an animation action name."""

    normalized = re.sub(
        r"[^a-z0-9]+", "_", str(value or "").casefold()
    ).strip("_")
    for prefix in ANIMATION_CLIP_PREFIXES:
        if normalized.startswith(prefix):
            return normalized[len(prefix):]
    return normalized


def annotate_event_animation_action_identity(
    event_rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Classify exact same-name AnimationClip callback Events as action SFX.

    The callback already proves the Event request.  The name comparison only
    recovers the coarser action-sound role; it does not add a new trigger or a
    runtime-execution claim.
    """

    matched = 0
    category_promotions = 0
    owner_kind_counts: Counter[str] = Counter()
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_name = canonical_animation_action_name(
            event.get("id") or event.get("eventId") or event.get("name")
        )
        if len(event_name) < 8 or "_" not in event_name:
            continue
        matching_clips: set[str] = set()
        owner_ids: set[str] = set()
        functions: set[str] = set()
        domains: set[str] = set()
        for context in event.get("contexts") or ():
            if not isinstance(context, dict):
                continue
            kind = str(context.get("kind") or "")
            if kind not in ANIMATION_ACTION_CONTEXT_KINDS:
                continue
            context_functions = {
                str(value) for value in context.get("animationFunctions") or ()
            }
            supported_functions = context_functions & ANIMATION_ACTION_FUNCTIONS
            if not supported_functions:
                continue
            context_matches = {
                str(clip)
                for clip in context.get("animationClips") or ()
                if canonical_animation_action_name(clip) == event_name
            }
            if not context_matches:
                continue
            matching_clips.update(context_matches)
            functions.update(supported_functions)
            owner_id = str(context.get("ownerId") or "").strip()
            if owner_id:
                owner_ids.add(owner_id)
            domains.add({
                "characterAnimation": "characterAction",
                "enemyAnimation": "enemyAction",
                "animationCallbackOwnerUnresolved": "animationAction",
            }[kind])
            owner_kind_counts[kind] += 1
        if not matching_clips:
            continue
        matched += 1
        event["animationActionNameMatchStatus"] = (
            "exactNormalizedAnimationClipNameEventId"
        )
        event["animationActionMatchingClips"] = sorted(matching_clips)
        event["animationActionOwnerIds"] = sorted(owner_ids)
        event["animationActionFunctions"] = sorted(functions)
        event["animationActionOwnershipDomains"] = sorted(domains)
        event["animationActionNameMatchEvidence"] = (
            "exactAnimationClipCallbackAndNormalizedNameIdentity"
        )
        if str(event.get("category") or "unknown") == "unknown":
            event["category"] = "sfx"
            event["categoryEvidence"] = "exactSameNameAnimationActionEvent"
            category_promotions += 1
    return {
        "schemaVersion": SCHEMA_VERSION,
        "eventsWithExactAnimationActionNameMatch": matched,
        "eventsPromotedToSfxByAnimationActionName": category_promotions,
        "animationActionOwnerKindCounts": dict(sorted(owner_kind_counts.items())),
        "evidenceBoundary": (
            "An exact normalized AnimationClip name and Wwise Event-id match is "
            "accepted only inside an existing PostAudioEvent callback context. It "
            "recovers an animation-action SFX role, not Animator execution, Wwise "
            "branch selection, playback, or audibility."
        ),
    }


def _iter_scene_events(
    scene_semantics: dict[str, Any],
) -> Iterable[tuple[dict[str, Any], str, str | None, str]]:
    for scene in scene_semantics.get("scenes") or ():
        if not isinstance(scene, dict):
            continue
        scene_id = str(scene.get("sceneId") or "").strip() or None
        for definition in scene.get("definitions") or ():
            if not isinstance(definition, dict):
                continue
            for event in definition.get("events") or ():
                if isinstance(event, dict):
                    yield event, str(event.get("role") or "unknown"), scene_id, (
                        "exactAudioMapDataSceneEventToPossibleWwiseMedia"
                    )
        audio_level = scene.get("audioLevel") or {}
        if isinstance(audio_level, dict):
            for event in audio_level.get("events") or ():
                if isinstance(event, dict):
                    yield event, str(event.get("role") or "unknown"), scene_id, (
                        "exactAudioLevelEventToPossibleWwiseMedia"
                    )
    for emitter in scene_semantics.get("sceneEmitters") or ():
        if not isinstance(emitter, dict):
            continue
        for event in emitter.get("eventRequests") or ():
            if isinstance(event, dict):
                yield event, str(event.get("semanticRole") or "unknown"), None, (
                    "exactSceneComponentEventToPossibleWwiseMedia"
                )


def annotate_media_coarse_ownership(
    media_rows: Iterable[dict[str, Any]],
    scene_semantics: dict[str, Any] | None,
    *,
    event_rows: Iterable[dict[str, Any]] | None = None,
    limit: int = 32,
) -> dict[str, Any]:
    """Attach conservative coarse ownership without changing playback status."""

    media = [row for row in media_rows if isinstance(row, dict)]
    unknown_before = sum(_effective_category(row) == "unknown" for row in media)
    by_src: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    claims: dict[int, dict[str, set[str]]] = defaultdict(
        lambda: {
            "domains": set(),
            "roles": set(),
            "sceneIds": set(),
            "evidence": set(),
            "categories": set(),
            "actionEventIds": set(),
            "actionClips": set(),
            "actionOwnerIds": set(),
            "characterEventIds": set(),
            "characterOwnerIds": set(),
            "characterOwnerTokens": set(),
            "characterIdentityStatuses": set(),
            "characterContextRelationships": set(),
            "callbackEventIds": set(),
            "callbackClips": set(),
            "callbackOwnerIds": set(),
            "callbackFunctions": set(),
            "callbackReachability": set(),
            "callbackControllers": set(),
            "callbackOwnershipClasses": set(),
            "callbackEntityIds": set(),
            "callbackResolvedEntityIds": set(),
            "callbackCandidateEntityIds": set(),
            "callbackControllerMembershipStatuses": set(),
            "callbackResolutionStatuses": set(),
            "callbackTokenResolutionStatuses": set(),
            "callbackOwnershipStatuses": set(),
            "callbackOccurrences": [],
        }
    )
    row_by_marker: dict[int, dict[str, Any]] = {}
    initially_unknown: set[int] = set()
    for row in media:
        marker = id(row)
        row_by_marker[marker] = row
        if _effective_category(row) == "unknown":
            initially_unknown.add(marker)
        src = _normalized_src(row.get("src"))
        if src:
            by_src[src].append(row)
        try:
            media_id = int(row.get("id"))
        except (TypeError, ValueError):
            continue
        by_id[media_id].append(row)

    def add_claim(
        row: dict[str, Any],
        *,
        domain: str,
        role: str,
        evidence: str,
        scene_id: str | None = None,
        category: str | None = None,
    ) -> None:
        target = claims[id(row)]
        target["domains"].add(domain)
        target["roles"].add(role)
        target["evidence"].add(evidence)
        if scene_id:
            target["sceneIds"].add(scene_id)
        if category:
            target["categories"].add(category)

    if isinstance(scene_semantics, dict):
        for event, role, scene_id, evidence in _iter_scene_events(scene_semantics):
            domain, category = SCENE_ROLE_DOMAINS.get(role, ("sceneAudio", None))
            for leaf in event.get("possibleMedia") or ():
                if not isinstance(leaf, dict):
                    continue
                candidates: list[dict[str, Any]] = []
                claim_evidence = evidence
                src = _normalized_src(leaf.get("src"))
                if src and len(by_src.get(src) or ()) == 1:
                    candidates = by_src[src]
                if not candidates:
                    try:
                        media_id = int(leaf.get("id"))
                    except (TypeError, ValueError):
                        continue
                    if len(by_id.get(media_id) or ()) == 1:
                        candidates = by_id[media_id]
                        claim_evidence = f"{evidence}ByUniqueMediaId"
                for row in candidates:
                    add_claim(
                        row,
                        domain=domain,
                        role=role,
                        evidence=claim_evidence,
                        scene_id=scene_id,
                        category=category,
                    )

    for row in media:
        for context_kind in row.get("eventContextKinds") or ():
            domain = CONTEXT_OWNERSHIP_DOMAINS.get(str(context_kind))
            if domain:
                add_claim(
                    row,
                    domain=domain,
                    role=str(context_kind),
                    evidence="exactEventContextToPossibleWwiseMedia",
                )

        authored_path = _normalized_src(row.get("externalAuthoredPath"))
        authored_id = str(row.get("externalAuthoredAudioId") or "").strip().lower()
        if (
            row.get("externalMediaIdentityStatus") == "recoveredAuthoredPathHash"
            and "/narrating/" in f"/{authored_path}"
            and authored_id.startswith("au_voice_")
        ):
            add_claim(
                row,
                domain="missionNarrationVoice",
                role="externalAuthoredNarrationPath",
                evidence="exactRecoveredAuthoredExternalPathIdentity",
                category="voice",
            )

    action_events: dict[str, dict[str, Any]] = {}
    for event in event_rows or ():
        if not isinstance(event, dict):
            continue
        if event.get("animationActionNameMatchStatus") != (
            "exactNormalizedAnimationClipNameEventId"
        ):
            continue
        for value in (event.get("id"), event.get("eventId"), event.get("name")):
            key = str(value or "").strip().casefold()
            if key:
                action_events[key] = event
    media_with_action_match: set[int] = set()
    for row in media:
        for event_id in row.get("eventIds") or ():
            event = action_events.get(str(event_id or "").strip().casefold())
            if not event:
                continue
            domains = event.get("animationActionOwnershipDomains") or (
                "animationAction",
            )
            for domain in domains:
                add_claim(
                    row,
                    domain=str(domain),
                    role="sameNameAnimationActionEvent",
                    evidence="exactAnimationClipCallbackAndNormalizedNameIdentity",
                    category="sfx",
                )
            target = claims[id(row)]
            target["actionEventIds"].add(str(event.get("id") or event_id))
            target["actionClips"].update(
                str(value) for value in event.get("animationActionMatchingClips") or ()
            )
            target["actionOwnerIds"].update(
                str(value) for value in event.get("animationActionOwnerIds") or ()
            )
            media_with_action_match.add(id(row))

    character_events: dict[str, dict[str, Any]] = {}
    for event in event_rows or ():
        if not isinstance(event, dict) or not event.get("characterAudioOwnerIds"):
            continue
        for value in (event.get("id"), event.get("eventId"), event.get("name")):
            key = str(value or "").strip().casefold()
            if key:
                character_events[key] = event
    media_with_character_identity: set[int] = set()
    shared_character_media: set[int] = set()
    for row in media:
        for event_id in row.get("eventIds") or ():
            event = character_events.get(str(event_id or "").strip().casefold())
            if not event:
                continue
            role = (
                "namedCharacterVoiceEvent"
                if str(event.get("category") or "unknown") == "voice"
                else "namedCharacterAudioEvent"
            )
            add_claim(
                row,
                domain="characterAudio",
                role=role,
                evidence=str(event.get("characterAudioNameMatchEvidence") or (
                    "exactCharacterTableIdentityInWwiseEventId"
                )),
            )
            target = claims[id(row)]
            target["characterEventIds"].add(str(event.get("id") or event_id))
            target["characterOwnerIds"].update(
                str(value) for value in event.get("characterAudioOwnerIds") or ()
            )
            target["characterOwnerTokens"].update(
                str(value) for value in event.get("characterAudioOwnerTokens") or ()
            )
            target["characterIdentityStatuses"].add(
                str(event.get("characterAudioIdentityStatus") or "")
            )
            target["characterContextRelationships"].add(
                str(event.get("characterAudioContextRelationshipStatus") or "")
            )
            media_with_character_identity.add(id(row))

    callback_events: dict[str, dict[str, Any]] = {}
    for event in event_rows or ():
        if not isinstance(event, dict) or event.get("animationCallbackLinkStatus") != (
            "exactSerializedAnimationClipAudioCallback"
        ):
            continue
        for value in (event.get("id"), event.get("eventId"), event.get("name")):
            key = str(value or "").strip().casefold()
            if key:
                callback_events[key] = event
    media_with_callback_link: set[int] = set()
    shared_callback_owner_media: set[int] = set()
    for row in media:
        for event_id in row.get("eventIds") or ():
            event = callback_events.get(str(event_id or "").strip().casefold())
            if not event:
                continue
            context_kinds = set(event.get("animationCallbackContextKinds") or ())
            domains = {
                {
                    "characterAnimation": "characterAnimation",
                    "enemyAnimation": "enemyAnimation",
                    "animationCallbackOwnerUnresolved": "animationCallback",
                }[kind]
                for kind in context_kinds
                if kind in ANIMATION_ACTION_CONTEXT_KINDS
            } or {"animationCallback"}
            for domain in domains:
                add_claim(
                    row,
                    domain=domain,
                    role="animationAudioCallbackEvent",
                    evidence="exactAnimationClipPostAudioEventContext",
                )
            target = claims[id(row)]
            target["callbackEventIds"].add(str(event.get("id") or event_id))
            target["callbackClips"].update(
                str(value) for value in event.get("animationCallbackClips") or ()
            )
            target["callbackOwnerIds"].update(
                str(value) for value in event.get("animationCallbackOwnerIds") or ()
            )
            target["callbackFunctions"].update(
                str(value) for value in event.get("animationCallbackFunctions") or ()
            )
            target["callbackReachability"].update(
                str(value)
                for value in event.get("animationCallbackReachabilityStatuses") or ()
            )
            target["callbackControllers"].update(
                str(value)
                for value in event.get("animationCallbackAnimatorControllerNames") or ()
            )
            target["callbackOwnershipClasses"].update(
                str(value) for value in event.get("animationCallbackOwnershipClasses") or ()
            )
            target["callbackEntityIds"].update(
                str(value) for value in event.get("animationCallbackEntityIds") or ()
            )
            target["callbackResolvedEntityIds"].update(
                str(value)
                for value in event.get("animationCallbackResolvedEntityIds") or ()
            )
            target["callbackCandidateEntityIds"].update(
                str(value)
                for value in event.get("animationCallbackCandidateEntityIds") or ()
            )
            target["callbackControllerMembershipStatuses"].update(
                str(value)
                for value in event.get("animationCallbackControllerMembershipStatuses") or ()
            )
            target["callbackResolutionStatuses"].update(
                str(value) for value in event.get("animationCallbackResolutionStatuses") or ()
            )
            target["callbackTokenResolutionStatuses"].update(
                str(value)
                for value in event.get("animationCallbackTokenResolutionStatuses") or ()
            )
            ownership_status = str(
                event.get("animationCallbackOwnershipStatus") or ""
            ).strip()
            if ownership_status:
                target["callbackOwnershipStatuses"].add(ownership_status)
            for resolution in event.get("animationCallbackClipResolutions") or ():
                if isinstance(resolution, dict) and len(target["callbackOccurrences"]) < limit:
                    target["callbackOccurrences"].append(dict(resolution))
            media_with_callback_link.add(id(row))

    domain_counts: Counter[str] = Counter()
    category_promotions = 0
    previously_unknown_owned = 0
    unknown_use_owned = 0
    purpose_recovered = 0
    multiple_domains = 0
    for marker, claim in claims.items():
        row = row_by_marker[marker]
        domains = sorted(claim["domains"])
        if not domains:
            continue
        for domain in domains:
            domain_counts[domain] += 1
        row["coarseOwnershipDomains"] = domains[:limit]
        row["coarseOwnershipDomainCount"] = len(domains)
        row["coarseOwnershipRoles"] = sorted(claim["roles"])[:limit]
        row["coarseOwnershipSceneIds"] = sorted(claim["sceneIds"])[:limit]
        row["coarseOwnershipEvidence"] = sorted(claim["evidence"])[:limit]
        row["coarseOwnershipStatus"] = "exactAuthoredDomainToPossibleMedia"
        row["coarseOwnershipTruncated"] = any(
            len(claim[key]) > limit
            for key in (
                "domains", "roles", "sceneIds", "evidence",
                "characterEventIds", "characterOwnerIds", "characterOwnerTokens",
                "characterIdentityStatuses", "characterContextRelationships",
                "callbackEventIds", "callbackClips", "callbackOwnerIds",
                "callbackFunctions", "callbackReachability", "callbackControllers",
                "callbackOwnershipClasses", "callbackEntityIds",
                "callbackResolvedEntityIds", "callbackCandidateEntityIds",
                "callbackControllerMembershipStatuses", "callbackResolutionStatuses",
                "callbackTokenResolutionStatuses",
                "callbackOwnershipStatuses",
                "callbackOccurrences",
            )
        )
        if claim["actionEventIds"]:
            row["animationActionEventIds"] = sorted(claim["actionEventIds"])[:limit]
            row["animationActionMatchingClips"] = sorted(claim["actionClips"])[:limit]
            row["animationActionOwnerIds"] = sorted(claim["actionOwnerIds"])[:limit]
            row["animationActionNameMatchEvidence"] = (
                "exactAnimationClipCallbackAndNormalizedNameIdentity"
            )
        if claim["characterEventIds"]:
            character_owner_ids = sorted(claim["characterOwnerIds"])
            row["characterAudioEventIds"] = sorted(claim["characterEventIds"])[:limit]
            row["characterAudioOwnerIds"] = character_owner_ids[:limit]
            row["characterAudioOwnerTokens"] = sorted(
                claim["characterOwnerTokens"]
            )[:limit]
            row["characterAudioIdentityStatuses"] = sorted(
                value for value in claim["characterIdentityStatuses"] if value
            )[:limit]
            row["characterAudioContextRelationshipStatuses"] = sorted(
                value for value in claim["characterContextRelationships"] if value
            )[:limit]
            row["characterAudioOwnershipStatus"] = (
                "exactNamedCharacterEventToPossibleMedia"
                if len(character_owner_ids) == 1
                else "sharedAcrossNamedCharacterEvents"
            )
            row["characterAudioOwnershipEvidence"] = (
                "exactCharacterTableEventIdentityToPossibleWwiseMedia"
            )
            if len(character_owner_ids) > 1:
                shared_character_media.add(marker)
        if claim["callbackEventIds"]:
            callback_owner_ids = sorted(claim["callbackOwnerIds"])
            row["animationCallbackEventIds"] = sorted(
                claim["callbackEventIds"]
            )[:limit]
            row["animationCallbackClips"] = sorted(claim["callbackClips"])[:limit]
            row["animationCallbackOwnerIds"] = callback_owner_ids[:limit]
            row["animationCallbackFunctions"] = sorted(
                claim["callbackFunctions"]
            )[:limit]
            row["animationCallbackReachabilityStatuses"] = sorted(
                claim["callbackReachability"]
            )[:limit]
            row["animationCallbackAnimatorControllerNames"] = sorted(
                claim["callbackControllers"]
            )[:limit]
            row["animationCallbackOwnershipClasses"] = sorted(
                claim["callbackOwnershipClasses"]
            )[:limit]
            row["animationCallbackEntityIds"] = sorted(
                claim["callbackEntityIds"]
            )[:limit]
            row["animationCallbackResolvedEntityIds"] = sorted(
                claim["callbackResolvedEntityIds"] or claim["callbackEntityIds"]
            )[:limit]
            row["animationCallbackCandidateEntityIds"] = sorted(
                claim["callbackCandidateEntityIds"]
            )[:limit]
            row["animationCallbackControllerMembershipStatuses"] = sorted(
                claim["callbackControllerMembershipStatuses"]
            )[:limit]
            row["animationCallbackResolutionStatuses"] = sorted(
                claim["callbackResolutionStatuses"]
            )[:limit]
            row["animationCallbackTokenResolutionStatuses"] = sorted(
                claim["callbackTokenResolutionStatuses"]
            )[:limit]
            row["animationCallbackClipResolutions"] = claim["callbackOccurrences"][:limit]
            if claim["callbackOwnershipStatuses"]:
                row["animationCallbackOwnershipStatus"] = (
                    "shared"
                    if len(callback_owner_ids) > 1
                    else next(iter(claim["callbackOwnershipStatuses"]))
                    if len(claim["callbackOwnershipStatuses"]) == 1
                    else "ambiguous"
                    if "ambiguous" in claim["callbackOwnershipStatuses"]
                    else "unresolved"
                )
            elif claim["callbackResolutionStatuses"]:
                row["animationCallbackOwnershipStatus"] = (
                    "shared"
                    if len(callback_owner_ids) > 1
                    else next(iter(claim["callbackResolutionStatuses"]))
                    if len(claim["callbackResolutionStatuses"]) == 1
                    else "ambiguous"
                    if "ambiguous" in claim["callbackResolutionStatuses"]
                    else "unresolved"
                )
            else:
                row["animationCallbackOwnershipStatus"] = (
                    "animationCallbackOwnerUnresolvedToPossibleMedia"
                    if not callback_owner_ids
                    else (
                        "exactAnimationCallbackOwnerToPossibleMedia"
                        if len(callback_owner_ids) == 1
                        else "sharedAcrossAnimationCallbackOwners"
                    )
                )
            row["animationCallbackLinkEvidence"] = (
                "exactAnimationClipPostAudioEventContextToPossibleWwiseMedia"
            )
            if len(callback_owner_ids) > 1:
                shared_callback_owner_media.add(marker)
        if len(domains) > 1:
            multiple_domains += 1
        if marker in initially_unknown:
            previously_unknown_owned += 1
        if row.get("purposeKnowledgeStatus") == "unknownUse":
            unknown_use_owned += 1
            row["purposeKnowledgeStatus"] = "coarseOwnershipKnown"
            row["purposeInvestigationPriority"] = "resolved"
            row["purposeRecoveryEvidence"] = "exactCoarseOwnershipDomain"
            purpose_recovered += 1
        categories = sorted(claim["categories"])
        if (
            str(row.get("audioCategory") or "unknown") == "unknown"
            and not row.get("semanticCategory")
            and len(categories) == 1
        ):
            row["semanticCategory"] = categories[0]
            row["semanticCategoryEvidence"] = "exactCoarseOwnershipRole"
            row["semanticCategoryOwnershipRoles"] = sorted(claim["roles"])[:limit]
            category_promotions += 1

    unknown_after = sum(_effective_category(row) == "unknown" for row in media)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "mediaWithCoarseOwnership": len(claims),
        "mediaWithMultipleCoarseOwnershipDomains": multiple_domains,
        "mediaWithCoarseOwnershipPreviouslyUnknownCategory": previously_unknown_owned,
        "unknownUseMediaWithCoarseOwnership": unknown_use_owned,
        "mediaPurposeRecoveredByCoarseOwnership": purpose_recovered,
        "mediaWithExactAnimationActionNameMatch": len(media_with_action_match),
        "mediaWithCharacterAudioIdentity": len(media_with_character_identity),
        "mediaSharedAcrossNamedCharacterEvents": len(shared_character_media),
        "mediaWithAnimationCallbackLink": len(media_with_callback_link),
        "mediaSharedAcrossAnimationCallbackOwners": len(
            shared_callback_owner_media
        ),
        "mediaSemanticCategoryFromCoarseOwnership": category_promotions,
        "effectiveCategoryUnknownBeforeCoarseOwnership": unknown_before,
        "effectiveCategoryUnknownAfterCoarseOwnership": unknown_after,
        "coarseOwnershipDomainCounts": dict(sorted(domain_counts.items())),
        "evidenceBoundary": (
            "Coarse ownership joins exact authored Event/component/voice-path evidence "
            "to possible Wwise media leaves. It identifies a domain such as scene "
            "environment, animation, component, interaction, or mission narration; it "
            "does not prove runtime activation, selected leaf, playback, or audibility."
        ),
    }
