"""Authored table sources that give a Wwise event an alias.

Each collector reads one authored table -- voice, typed UI, SNS voice, audio
dialog, skill-id dictionary -- and yields event aliases. An alias is an authored
name for an event, not evidence that the event plays."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from .context_utils import display_path
from .context_utils import load_json_strict
from .identifiers import audio_hash_generator_compute

def collect_audio_dialog_wwise_event_aliases(
    audio_dialog_paths: list[Path],
    wwise_event_inventory: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Recover Wwise Event names from exact AudioDialog voice identities.

    ``AudioDialog`` keys are signed voice ids, while ``path`` is the authored
    voice identity.  A path is promoted only when its exact current-build
    ``AudioHashGenerator`` value equals both that row id and a type-4 Event id
    in the complete Wwise inventory.  This three-way equality avoids treating
    the many external-only AudioDialog paths as bank Event names.
    """

    event_hashes = {
        int(row.get("eventHash")) & 0xFFFFFFFF
        for row in wwise_event_inventory
        if isinstance(row, dict) and isinstance(row.get("eventHash"), int)
    }
    candidates: dict[int, dict[str, Any]] = {}
    conflicts: set[int] = set()
    for path in audio_dialog_paths:
        payload = load_json_strict(path, {})
        if not isinstance(payload, dict):
            continue
        source = display_path(path)
        for raw_voice_id, value in payload.items():
            if not isinstance(value, dict):
                continue
            name = str(value.get("path") or "").strip()
            try:
                signed_voice_id = int(raw_voice_id)
            except (TypeError, ValueError):
                continue
            event_hash = signed_voice_id & 0xFFFFFFFF
            if (
                not name
                or event_hash not in event_hashes
                or audio_hash_generator_compute(name) != event_hash
            ):
                continue
            row = candidates.get(event_hash)
            if row is not None and str(row.get("name") or "").casefold() != name.casefold():
                conflicts.add(event_hash)
                continue
            if row is None:
                row = {
                    "eventHash": event_hash,
                    "eventHashHex": f"0x{event_hash:08x}",
                    "voiceId": signed_voice_id,
                    "name": name,
                    "codec": value.get("codec"),
                    "speakerChannel": value.get("speakerChannel") or "",
                    "voType": value.get("voType"),
                    "overrideWwiseEvent": value.get("overrideWwiseEvent") or "",
                    "sources": [],
                    "evidence": "audioDialogPathHashEqualsVoiceIdAndWwiseEventId",
                }
                candidates[event_hash] = row
            if source not in row["sources"]:
                row["sources"].append(source)
    for event_hash in conflicts:
        candidates.pop(event_hash, None)
    rows = list(candidates.values())
    for row in rows:
        row["sources"].sort()
    rows.sort(key=lambda row: (str(row.get("name") or ""), int(row["eventHash"])))
    return rows

VOICE_TABLE_WWISE_EVENT_FIELDS = {
    "AudioDialogConfigs.json": {
        "charMonoOverrideEvent": (
            "voiceDefaultEvent",
            "AudioDialogConfigs.charMonoOverrideEvent -> VoicePlayer.SetDefaultEvent/PlayVoice",
        ),
        "defaultWwiseEvent": (
            "voiceDefaultEvent",
            "AudioDialogConfigs.defaultWwiseEvent -> VoicePlayer.SetDefaultEvent/PlayVoice",
        ),
    },
    "AudioDialogChannel.json": {
        "narratingWwiseEvent": (
            "narratingChannelEvent",
            "SpeakerChannelData.narratingWwiseEvent -> VoiceUtilsInternal.SelectWwiseEvent -> VoicePlayer.PlayVoice",
        ),
        "radioWwiseEvent": (
            "radioChannelEvent",
            "SpeakerChannelData.radioWwiseEvent -> VoiceUtilsInternal.SelectWwiseEvent -> VoicePlayer.PlayVoice",
        ),
    },
    "AudioDialog.json": {
        "overrideWwiseEvent": (
            "voiceDefinitionOverrideEvent",
            "VoiceData.overrideWwiseEvent -> RuntimeVoiceData.overrideWwiseEvent -> VoiceUtilsInternal.SelectWwiseEvent -> VoicePlayer.PlayVoice",
        ),
    },
    "ResponsiveTriggers.json": {
        "eventTemplate": (
            "responsiveVoiceEventTemplate",
            "ResponsiveDialogTriggerData.eventTemplate -> response selection -> VoiceSpeakChannelProcessor._PlayVoice -> VoicePlayer.PlayVoice",
        ),
    },
}

TYPED_UI_TABLE_WWISE_EVENT_FIELDS = {
    "ActivityStaminaRefundBgStateTable.json": {
        "audioOnOpen": (
            "uiAnimationOpenEvent",
            "ActivityStaminaDiscountCtrl._GetAudioOnOpen -> UIAnimationWrapper.SetAudioOnOpen/PlayOpenAudio -> AudioUIUtil.PostUIEvent",
            [
                "Data/LuaScripts/UI/Panels/ActivityStaminaDiscount/ActivityStaminaDiscountCtrl.lua:70-81",
                "GameAssembly:UIAnimationWrapper.PlayOpenAudio -> AudioUIUtil.PostUIEvent",
            ],
        ),
    },
    "ActivityPushPopupTable.json": {
        "bgm": (
            "activityPushPopupBgmEvent",
            "ActivityPushPopupCtrl._UpdateBgm -> AudioManager.PostEvent",
            ["Data/LuaScripts/UI/Panels/ActivityPushPopup/ActivityPushPopupCtrl.lua:51-56"],
        ),
    },
    "ActivityTable.json": {
        "bgm": (
            "activityCenterBgmEvent",
            "PhaseActivityCenter phase transition/selection -> AudioManager.PostEvent",
            ["Data/LuaScripts/Phase/ActivityCenter/PhaseActivityCenter.lua:119-126,192-198"],
        ),
    },
    "ActivitySkipChapterTable.json": {
        "videoAudioKey": (
            "uiVideoAudioEvent",
            "ActivitySkipChapter1Ctrl._StartPlayVideo -> VideoPlayer.PlayAudio -> AudioAdapter.PostEvent",
            [
                "Data/LuaScripts/UI/Panels/ActivitySkipChapter1/ActivitySkipChapter1Ctrl.lua:46-77",
                "Data/LuaScripts/UI/Widgets/VideoPlayer.lua:414-460",
            ],
        ),
    },
    "GachaCharPoolTable.json": {
        "videoAudioKey": (
            "uiVideoAudioEvent",
            "GachaPoolVideoCtrl._StartPlayVideo/_ReplayVideo -> VideoPlayer.PlayAudio -> AudioAdapter.PostEvent",
            [
                "Data/LuaScripts/UI/Panels/GachaPoolVideo/GachaPoolVideoCtrl.lua:49-106",
                "Data/LuaScripts/UI/Widgets/VideoPlayer.lua:414-460",
            ],
        ),
    },
    "DomainDataTable.json": {
        "audKeySwitchRegionPopup": (
            "domainRegionSwitchEvent",
            "SettlementSwitchRegionPopupCtrl region-button listener -> AudioManager.PostEvent",
            ["Data/LuaScripts/UI/Panels/SettlementSwitchRegionPopup/SettlementSwitchRegionPopupCtrl.lua:112-118"],
        ),
        "audKeyUpToastLevelUpAfterEnhance": (
            "domainUpgradeAnimationEvent",
            "DomainUpgradeCtrl._StartPlayUpgradeAni non-level-up entry -> AudioAdapter.PostEvent",
            ["Data/LuaScripts/UI/Panels/DomainUpgrade/DomainUpgradeCtrl.lua:163-167"],
        ),
        "audKeyUpToastLevelUpMoment": (
            "domainUpgradeAnimationEvent",
            "DomainUpgradeCtrl progress tween completion -> AudioAdapter.PostEvent",
            ["Data/LuaScripts/UI/Panels/DomainUpgrade/DomainUpgradeCtrl.lua:187-193"],
        ),
        "audKeyUpToastLevelUpPreEnhance": (
            "domainUpgradeAnimationEvent",
            "DomainUpgradeCtrl._StartPlayUpgradeAni level-up entry -> AudioAdapter.PostEvent",
            ["Data/LuaScripts/UI/Panels/DomainUpgrade/DomainUpgradeCtrl.lua:163-167"],
        ),
        "audKeyUpToastNotLevelUpEnhance": (
            "domainUpgradeAnimationEvent",
            "DomainUpgradeCtrl progress animation start -> AudioAdapter.PostEvent",
            ["Data/LuaScripts/UI/Panels/DomainUpgrade/DomainUpgradeCtrl.lua:184-190"],
        ),
    },
}

def collect_voice_table_wwise_event_aliases(
    export_root: Path,
    wwise_event_inventory: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Recover exact Wwise Event names from typed voice-table Event fields.

    These fields are named Event/override/template getters in current IL2CPP
    metadata and feed ``VoiceUtilsInternal.SelectWwiseEvent`` or the response
    voice route.  A string is accepted only when its exact game hash is a
    current type-4 Event id. Conflicting strings for one uint32 fail closed.
    Duplicate StreamingAssets/Persistent rows are collapsed while retaining
    both sources and bounded row-path samples.
    """

    event_hashes = {
        int(row.get("eventHash")) & 0xFFFFFFFF
        for row in wwise_event_inventory
        if isinstance(row, dict) and isinstance(row.get("eventHash"), int)
    }
    candidates: dict[int, dict[str, Any]] = {}
    conflicts: set[int] = set()

    def add_value(
        *,
        name: str,
        table: str,
        field: str,
        route_kind: str,
        runtime_route: str,
        row_path: tuple[str, ...],
        source: str,
    ) -> None:
        event_hash = audio_hash_generator_compute(name)
        if event_hash not in event_hashes:
            return
        row = candidates.get(event_hash)
        if row is not None and str(row.get("name") or "").casefold() != name.casefold():
            conflicts.add(event_hash)
            return
        if row is None:
            row = {
                "eventHash": event_hash,
                "eventHashHex": f"0x{event_hash:08x}",
                "name": name,
                "usages": {},
                "evidence": "typedVoiceTableEventFieldHashEqualsCurrentWwiseEventId",
            }
            candidates[event_hash] = row
        usage_key = (table, field, route_kind, runtime_route)
        usage = row["usages"].setdefault(usage_key, {
            "table": table,
            "field": field,
            "routeKind": route_kind,
            "runtimeRoute": runtime_route,
            "rowPaths": set(),
            "sources": set(),
        })
        usage["rowPaths"].add("/".join(row_path) if row_path else "<root>")
        usage["sources"].add(source)

    def visit(
        value: Any,
        *,
        table: str,
        fields: dict[str, tuple[str, str]],
        row_path: tuple[str, ...],
        source: str,
    ) -> None:
        if isinstance(value, dict):
            for raw_field, child in value.items():
                field = str(raw_field)
                spec = fields.get(field)
                if spec is not None and isinstance(child, str) and child.strip():
                    add_value(
                        name=child.strip(),
                        table=table,
                        field=field,
                        route_kind=spec[0],
                        runtime_route=spec[1],
                        row_path=row_path,
                        source=source,
                    )
                visit(
                    child,
                    table=table,
                    fields=fields,
                    row_path=row_path + (field,),
                    source=source,
                )
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(
                    child,
                    table=table,
                    fields=fields,
                    row_path=row_path + (str(index),),
                    source=source,
                )

    for source_root in ("StreamingAssets", "Persistent"):
        table_root = export_root / "structured" / source_root / "Table"
        for table, fields in VOICE_TABLE_WWISE_EVENT_FIELDS.items():
            path = table_root / table
            if not path.is_file():
                continue
            payload = load_json_strict(path, {})
            if not isinstance(payload, (dict, list)):
                continue
            visit(
                payload,
                table=table,
                fields=fields,
                row_path=(),
                source=display_path(path),
            )

    for event_hash in conflicts:
        candidates.pop(event_hash, None)
    rows: list[dict[str, Any]] = []
    for row in candidates.values():
        usages = []
        for usage in row.pop("usages").values():
            paths = sorted(usage.pop("rowPaths"))
            sources = sorted(usage.pop("sources"))
            usages.append({
                **usage,
                "occurrenceCount": len(paths),
                "rowPathSamples": paths[:20],
                "rowPathsTruncated": len(paths) > 20,
                "sources": sources,
            })
        usages.sort(key=lambda usage: (usage["table"], usage["field"], usage["routeKind"]))
        row["usages"] = usages
        rows.append(row)
    rows.sort(key=lambda row: (str(row.get("name") or "").casefold(), int(row["eventHash"])))
    return rows

def collect_typed_ui_table_wwise_event_aliases(
    export_root: Path,
    wwise_event_inventory: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Recover Event names from metadata-typed fields with exact Lua consumers.

    Generic string/hash matches are deliberately excluded. Each admitted field
    has a current metadata getter and a current decrypted-Lua path to an audio
    API; the exact string hash must also be a current type-4 Event id.
    Duplicate StreamingAssets/Persistent logical rows are collapsed.
    """

    event_hashes = {
        int(row.get("eventHash")) & 0xFFFFFFFF
        for row in wwise_event_inventory
        if isinstance(row, dict) and isinstance(row.get("eventHash"), int)
    }
    candidates: dict[int, dict[str, Any]] = {}
    conflicts: set[int] = set()

    def visit(
        value: Any,
        *,
        table: str,
        fields: dict[str, tuple[str, str, list[str]]],
        row_path: tuple[str, ...],
        source: str,
    ) -> None:
        if isinstance(value, dict):
            for raw_field, child in value.items():
                field = str(raw_field)
                spec = fields.get(field)
                if spec is not None and isinstance(child, str) and child.strip():
                    name = child.strip()
                    event_hash = audio_hash_generator_compute(name)
                    if event_hash in event_hashes:
                        row = candidates.get(event_hash)
                        if row is not None and str(row.get("name") or "").casefold() != name.casefold():
                            conflicts.add(event_hash)
                        else:
                            if row is None:
                                row = {
                                    "eventHash": event_hash,
                                    "eventHashHex": f"0x{event_hash:08x}",
                                    "name": name,
                                    "usages": {},
                                    "evidence": "typedTableGetterAndLuaAudioConsumerHashEqualsCurrentWwiseEventId",
                                }
                                candidates[event_hash] = row
                            usage_key = (table, field, spec[0], spec[1])
                            usage = row["usages"].setdefault(usage_key, {
                                "table": table,
                                "field": field,
                                "routeKind": spec[0],
                                "runtimeRoute": spec[1],
                                "consumerEvidence": list(spec[2]),
                                "rowPaths": set(),
                                "sources": set(),
                            })
                            usage["rowPaths"].add("/".join(row_path) if row_path else "<root>")
                            usage["sources"].add(source)
                visit(child, table=table, fields=fields, row_path=row_path + (field,), source=source)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, table=table, fields=fields, row_path=row_path + (str(index),), source=source)

    for source_root in ("StreamingAssets", "Persistent"):
        table_root = export_root / "structured" / source_root / "Table"
        for table, fields in TYPED_UI_TABLE_WWISE_EVENT_FIELDS.items():
            path = table_root / table
            if not path.is_file():
                continue
            payload = load_json_strict(path, {})
            if isinstance(payload, (dict, list)):
                visit(payload, table=table, fields=fields, row_path=(), source=display_path(path))

    for event_hash in conflicts:
        candidates.pop(event_hash, None)
    rows: list[dict[str, Any]] = []
    for row in candidates.values():
        usages = []
        for usage in row.pop("usages").values():
            paths = sorted(usage.pop("rowPaths"))
            sources = sorted(usage.pop("sources"))
            usages.append({
                **usage,
                "occurrenceCount": len(paths),
                "rowPathSamples": paths[:20],
                "rowPathsTruncated": len(paths) > 20,
                "sources": sources,
            })
        usages.sort(key=lambda usage: (usage["table"], usage["field"], usage["routeKind"]))
        row["usages"] = usages
        rows.append(row)
    rows.sort(key=lambda row: (str(row.get("name") or "").casefold(), int(row["eventHash"])))
    return rows

def collect_sns_voice_wwise_event_aliases(
    export_root: Path,
    wwise_event_inventory: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Recover SNS Voice-node Event names from the typed content payload.

    Current metadata fixes ``SNSDialogContentType.Voice`` at value 5. The
    decrypted Lua Voice widget reads ``contentParam[0]`` as ``voiceId`` and
    passes it directly to ``AudioAdapter.PostEvent``. Other positional SNS
    parameters remain excluded.
    """

    event_hashes = {
        int(row.get("eventHash")) & 0xFFFFFFFF
        for row in wwise_event_inventory
        if isinstance(row, dict) and isinstance(row.get("eventHash"), int)
    }
    candidates: dict[int, dict[str, Any]] = {}
    conflicts: set[int] = set()
    for source_root in ("StreamingAssets", "Persistent"):
        path = export_root / "structured" / source_root / "Table" / "SNSDialogTable.json"
        payload = load_json_strict(path, {})
        if not isinstance(payload, dict):
            continue
        for raw_dialog_id, raw_dialog in payload.items():
            if not isinstance(raw_dialog, dict):
                continue
            dialog_id = str(raw_dialog.get("dialogId") or raw_dialog_id)
            contents = raw_dialog.get("dialogContentData")
            if not isinstance(contents, dict):
                continue
            for raw_content_id, content in contents.items():
                if not isinstance(content, dict) or content.get("contentType") != 5:
                    continue
                params = content.get("contentParam")
                if not isinstance(params, list) or not params or not isinstance(params[0], str):
                    continue
                name = params[0].strip()
                if not name:
                    continue
                event_hash = audio_hash_generator_compute(name)
                if event_hash not in event_hashes:
                    continue
                previous = candidates.get(event_hash)
                if previous is not None and str(previous.get("name") or "").casefold() != name.casefold():
                    conflicts.add(event_hash)
                    continue
                if previous is None:
                    previous = {
                        "eventHash": event_hash,
                        "eventHashHex": f"0x{event_hash:08x}",
                        "name": name,
                        "usages": {},
                        "evidence": "snsVoiceContentTypeAndLuaPostEventHashEqualsCurrentWwiseEventId",
                    }
                    candidates[event_hash] = previous
                logical_key = (dialog_id, str(content.get("contentId") or raw_content_id))
                usage = previous["usages"].setdefault(logical_key, {
                    "table": "SNSDialogTable.json",
                    "dialogId": dialog_id,
                    "contentId": content.get("contentId", raw_content_id),
                    "contentType": 5,
                    "contentTypeName": "Voice",
                    "contentParamIndex": 0,
                    "speaker": content.get("speaker"),
                    "durationSeconds": params[1] if len(params) > 1 else None,
                    "sources": set(),
                })
                usage["sources"].add(display_path(path))
    for event_hash in conflicts:
        candidates.pop(event_hash, None)
    rows: list[dict[str, Any]] = []
    for row in candidates.values():
        usages = []
        for usage in row.pop("usages").values():
            usage["sources"] = sorted(usage["sources"])
            usages.append(usage)
        usages.sort(key=lambda usage: (str(usage["dialogId"]), str(usage["contentId"])))
        row["usages"] = usages
        rows.append(row)
    rows.sort(key=lambda row: (str(row.get("name") or "").casefold(), int(row["eventHash"])))
    return rows

def collect_skill_id_dictionary_wwise_event_aliases(
    export_root: Path,
    wwise_event_inventory: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Recover identity-only Event names from the exact ``skill_id`` map.

    The string must hash to a current type-4 Wwise Event and have a matching
    exported SkillData binary. This proves the authored Event name and its SFX
    naming domain, but deliberately emits no playback/ownership context: the
    dictionary is an identifier map, not an audio consumer.
    """

    event_hashes = {
        int(row.get("eventHash")) & 0xFFFFFFFF
        for row in wwise_event_inventory
        if isinstance(row, dict) and isinstance(row.get("eventHash"), int)
    }
    candidates: dict[int, dict[str, Any]] = {}
    conflicts: set[int] = set()
    for source_root in ("StreamingAssets", "Persistent"):
        table_path = export_root / "structured" / source_root / "Table" / "NumIdStrTable.json"
        payload = load_json_strict(table_path, {})
        skill_map = ((payload.get("skill_id") or {}).get("dic") or {}) if isinstance(payload, dict) else {}
        if not isinstance(skill_map, dict):
            continue
        skill_root = export_root / "structured" / source_root / "Data" / "Json" / "SkillData"
        for raw_numeric_id, raw_name in skill_map.items():
            if not isinstance(raw_name, str) or not raw_name.strip():
                continue
            name = raw_name.strip()
            event_hash = audio_hash_generator_compute(name)
            if event_hash not in event_hashes:
                continue
            skill_path = skill_root / f"{name}.json"
            if not skill_path.is_file():
                continue
            previous = candidates.get(event_hash)
            if previous is not None and str(previous.get("name") or "").casefold() != name.casefold():
                conflicts.add(event_hash)
                continue
            if previous is None:
                previous = {
                    "eventHash": event_hash,
                    "eventHashHex": f"0x{event_hash:08x}",
                    "name": name,
                    "dictionaryKind": "skill_id",
                    "numericSkillIds": set(),
                    "tableSources": set(),
                    "skillDataSources": set(),
                    "evidence": "skillIdDictionaryNameAndSkillDataFileHashEqualsCurrentWwiseEventId",
                    "playbackPlacementStatus": "identityOnlyNoAudioConsumer",
                }
                candidates[event_hash] = previous
            previous["numericSkillIds"].add(str(raw_numeric_id))
            previous["tableSources"].add(display_path(table_path))
            previous["skillDataSources"].add(display_path(skill_path))
    for event_hash in conflicts:
        candidates.pop(event_hash, None)
    rows: list[dict[str, Any]] = []
    for row in candidates.values():
        row["numericSkillIds"] = sorted(row["numericSkillIds"], key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value))
        row["tableSources"] = sorted(row["tableSources"])
        row["skillDataSources"] = sorted(row["skillDataSources"])
        rows.append(row)
    rows.sort(key=lambda row: (str(row.get("name") or "").casefold(), int(row["eventHash"])))
    return rows
