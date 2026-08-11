"""Build a compact projectile inspector payload from AnimeStudio JSON.

The source records are exact-consumption MonoBehaviour decodes produced by the
local AnimeStudio fork.  This builder intentionally keeps authored numeric
values and blackboard keys separate from display labels: enum/hash meanings
that have not been independently recovered stay numeric.

Examples:
    python scripts/build_projectile_data.py
    python scripts/build_projectile_data.py --pretty
    python scripts/build_projectile_data.py --input-root PATH --output PATH
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUTS = (
    REPO_ROOT / "export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/MonoBehaviour",
    REPO_ROOT / "export_full/recovered/AnimeStudio-cli/Persistent/json_by_type/MonoBehaviour",
)
DEFAULT_OUTPUT = REPO_ROOT / "webui/data/gameplay/projectiles.json"
DEFAULT_AUDIO_INDEX = REPO_ROOT / "export_full/structured/Audio/CN/index.json"
PROJECTILE_EVENT_PREFIX = "projectile-event:"
EFFECT_LIST_FIELDS = (
    ("main", "mainEffects"),
    ("launch", "launchEffects"),
    ("reach", "reachEffects"),
    ("hit", "hitEffects"),
    ("block", "blockEffects"),
    ("finish", "finishEffects"),
)
SOUND_FIELDS = (
    "launchSound",
    "loopSound",
    "reachSound",
    "hitSound",
    "blockSound",
    "finishedSound",
    "sizzleSound",
)

AUDIO_LINK_FIELDS = (
    "src", "mediaId", "format", "bytes", "audioScope", "audioCategory",
    "audioCategoryDetail", "sourceBlock", "sourceBlockLabel", "sourceBank",
    "bankId", "bank",
)


def compact_dict(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def enum_value(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    return compact_dict(
        value=value.get("value"),
        name=value.get("name"),
        hex=value.get("hex"),
        enumType=value.get("enumType"),
    )


def hydrate_audio_links(entries: list[dict[str, Any]], audio_index_path: Path) -> dict[str, Any] | None:
    """Reuse the current canonical HIRC mapping without rescanning game banks."""

    try:
        audio_index = json.loads(audio_index_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    requested_hashes = {
        int(value) & 0xFFFFFFFF
        for value in (audio_index.get("projectileEventHashes") or [])
        if isinstance(value, int)
    }
    if not requested_hashes:
        return None
    found_hashes = {
        int(row.get("eventHash")) & 0xFFFFFFFF
        for row in (audio_index.get("eventEvidence") or [])
        if isinstance(row, dict)
        and isinstance(row.get("eventHash"), int)
    }
    event_ids_by_hash: dict[int, set[str]] = {}
    for row in audio_index.get("eventEvidence") or []:
        if not isinstance(row, dict) or not isinstance(row.get("eventHash"), int):
            continue
        event_id = str(row.get("eventId") or "").strip()
        if event_id:
            event_ids_by_hash.setdefault(int(row["eventHash"]) & 0xFFFFFFFF, set()).add(event_id)
    audio_by_hash: dict[int, list[dict[str, Any]]] = {}
    for row in audio_index.get("events") or []:
        if not isinstance(row, dict):
            continue
        try:
            event_hash = int(row.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            continue
        if not row.get("src"):
            continue
        audio_by_hash.setdefault(event_hash, []).append({
            key: row[key]
            for key in AUDIO_LINK_FIELDS
            if row.get(key) is not None
        })

    refs = 0
    linked_refs = 0
    candidate_count = 0
    resolved_hashes: set[int] = set()
    for entry in entries:
        sounds = entry.get("sounds") or {}
        for field in SOUND_FIELDS:
            value = sounds.get(field)
            raw = value.get("value") if isinstance(value, dict) else value
            if not isinstance(value, dict) or not isinstance(raw, int) or not raw:
                continue
            refs += 1
            event_hash = raw & 0xFFFFFFFF
            if event_hash not in requested_hashes:
                continue
            media: list[dict[str, Any]] = []
            seen: set[tuple[str, str]] = set()
            for audio in audio_by_hash.get(event_hash, []):
                key = (str(audio.get("src") or ""), str(audio.get("mediaId") or ""))
                if not key[0] or key in seen:
                    continue
                seen.add(key)
                media.append(audio)
            event_found = event_hash in found_hashes
            resolved_hashes.update([event_hash] if event_found else [])
            if media:
                linked_refs += 1
                candidate_count += len(media)
            value["event"] = {
                "hash": event_hash,
                "hex": f"0x{event_hash:08x}",
                "foundInWwise": event_found,
                "playableCandidates": len(media),
                "source": "wwiseHirc" if event_found else "unresolved",
                "runtimeSelection": "unresolved" if len(media) > 1 else "singleCandidate" if media else "none",
                "canonicalEventIds": sorted(event_ids_by_hash.get(event_hash) or {f"{PROJECTILE_EVENT_PREFIX}0x{event_hash:08x}"}),
            }
            if media:
                value["audio"] = media
    return {
        "projectileSoundRefs": refs,
        "projectileSoundEvents": len(resolved_hashes),
        "projectileSoundRefsLinked": linked_refs,
        "projectileAudioCandidates": candidate_count,
        "source": "Wwise HIRC event traversal (reused from current audio index)",
        "note": "Playable files are event media candidates; runtime switch/container selection is not recovered.",
    }


def blackboard_scalar(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    result = compact_dict(
        useBlackboardKey=value.get("useBlackboardKey"),
        value=value.get("value"),
        blackboardKey=value.get("blackboardKey"),
        valueFloatCandidate=value.get("valueFloatCandidate"),
        valueIntCandidate=value.get("valueIntCandidate"),
    )
    if isinstance(value.get("rawWords"), list):
        result["rawWords"] = [enum_value(word) for word in value["rawWords"]]
    return result


def blackboard_vector(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    result = {axis: blackboard_scalar(value.get(axis)) for axis in ("x", "y", "z") if axis in value}
    if isinstance(value.get("valueCandidate"), dict):
        result["valueCandidate"] = value["valueCandidate"]
    return result


def blackboard_range(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    result = compact_dict(
        min=blackboard_scalar(value.get("min")),
        max=blackboard_scalar(value.get("max")),
        valueCandidate=value.get("valueCandidate"),
    )
    return result


def curve(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    keyframes = []
    for row in value.get("keyframes") or []:
        if not isinstance(row, dict):
            continue
        keyframes.append(
            compact_dict(
                time=row.get("time"),
                value=row.get("value"),
                inSlope=row.get("inSlope"),
                outSlope=row.get("outSlope"),
                weightedMode=enum_value(row.get("weightedMode")),
                inWeight=row.get("inWeight"),
                outWeight=row.get("outWeight"),
            )
        )
    return compact_dict(
        keyframes=keyframes,
        preInfinity=enum_value(value.get("preInfinity")),
        postInfinity=enum_value(value.get("postInfinity")),
        rotationOrder=enum_value(value.get("rotationOrder")),
    )


def bezier_point(value: Any, status: Any) -> Any:
    if not isinstance(value, dict):
        return compact_dict(status=status)
    return compact_dict(
        status=status or value.get("decodeStatus"),
        usePresetPoint=value.get("usePresetPoint"),
        presetPointKey=value.get("presetPointKey"),
        xRatioRange=blackboard_range(value.get("xRatioRange")),
        yzAngleRange=blackboard_range(value.get("yzAngleRange")),
        yzRadiusRange=blackboard_range(value.get("yzRadiusRange")),
        scaledYzRadius=value.get("scaledYzRadius"),
    )


def shape_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return compact_dict(
        shapeType=enum_value(value.get("shapeType")),
        radius=blackboard_scalar(value.get("radius")),
        center=blackboard_vector(value.get("center")),
        extent=blackboard_vector(value.get("extent")),
        initOuterRadius=blackboard_scalar(value.get("initOuterRadius")),
        initInnerRadius=blackboard_scalar(value.get("initInnerRadius")),
        outerRadiusIncreaseSpeed=blackboard_scalar(value.get("outerRadiusIncreaseSpeed")),
        innerRadiusIncreaseSpeed=blackboard_scalar(value.get("innerRadiusIncreaseSpeed")),
        height=blackboard_scalar(value.get("height")),
        isSector=value.get("isSector"),
        sectorDirection=enum_value(value.get("sectorDirection")),
        sectorAngle=blackboard_scalar(value.get("sectorAngle")),
    )


def target_filter_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    query = value.get("tagQuery") if isinstance(value.get("tagQuery"), dict) else {}
    return compact_dict(
        serializedLayout=value.get("serializedLayout"),
        tagEntryLayout=value.get("tagEntryLayout"),
        checkAlive=value.get("checkAlive"),
        autoSetTargetFaction=value.get("autoSetTargetFaction"),
        factionTarget=enum_value(value.get("factionTarget")),
        targetFactionType=enum_value(value.get("targetFactionType")),
        filterObjectType=value.get("filterObjectType"),
        objectType=enum_value(value.get("objectType")),
        filterSlot=value.get("filterSlot"),
        slotIndex=value.get("slotIndex"),
        filterGameplayTag=value.get("filterGameplayTag"),
        tagQuery=compact_dict(queryType=enum_value(query.get("queryType")), tags=query.get("tags") or []),
    )


def move_mode_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return compact_dict(
        key=value.get("key"),
        traceType=enum_value(value.get("traceType")),
        traceTime=blackboard_scalar(value.get("traceTime")),
        traceUntilDistance=blackboard_scalar(value.get("traceUntilDistance")),
        moveType=enum_value(value.get("moveType")),
        parabolaDef=enum_value(value.get("parabolaDef")),
        speed=blackboard_scalar(value.get("speed")),
        speedCurve=curve(value.get("speedCurve")),
        useSpeedScaleWithDistance=value.get("useSpeedScaleWithDistance"),
        speedScaleWithDistance=curve(value.get("speedScaleWithDistance")),
        lockVelocityToXZ=value.get("lockVelocityToXZ"),
        groundedMove=value.get("groundedMove"),
        limitAngularSpeed=value.get("limitAngularSpeed"),
        angularSpeed=blackboard_scalar(value.get("angularSpeed")),
        angularSpeedCurve=curve(value.get("angularSpeedCurve")),
        travelDuration=blackboard_scalar(value.get("travelDuration")),
        vertexYOffset=blackboard_scalar(value.get("vertexYOffset")),
        gravity=blackboard_scalar(value.get("gravity")),
        bezierMidPoint1=bezier_point(value.get("bezierMidPoint1"), value.get("bezierMidPoint1Status")),
        bezierMidPoint2=bezier_point(value.get("bezierMidPoint2"), value.get("bezierMidPoint2Status")),
        surroundCenterKey=value.get("surroundCenterKey"),
        surroundLineSpeed=blackboard_scalar(value.get("surroundLineSpeed")),
        surroundLineSpeedCurve=curve(value.get("surroundLineSpeedCurve")),
        surroundCentrifugalSpeed=blackboard_scalar(value.get("surroundCentrifugalSpeed")),
        surroundCentrifugalSpeedCurve=curve(value.get("surroundCentrifugalSpeedCurve")),
        surroundMaxCentrifugalRadius=blackboard_scalar(value.get("surroundMaxCentrifugalRadius")),
        reachOnMaxCentrifugalRadius=value.get("reachOnMaxCentrifugalRadius"),
        surroundAxialSpeed=blackboard_scalar(value.get("surroundAxialSpeed")),
        surroundAxialSpeedCurve=curve(value.get("surroundAxialSpeedCurve")),
        surroundMaxAxialHeight=blackboard_scalar(value.get("surroundMaxAxialHeight")),
        reachOnMaxAxialHeight=value.get("reachOnMaxAxialHeight"),
        surroundAxisRotation=blackboard_vector(value.get("surroundAxisRotation")),
        confidence={
            "structure": "exact",
            "semantics": "qualified",
            "note": "Field order and record boundary are byte-proven; numeric movement enum names remain withheld when the exporter has no independently validated member name.",
        },
    )


def effect_tail_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    scalar_keys = (
        "isShowInDialog", "isLimitEffectCount", "limitCount", "protectTime", "limitTime", "limitKey",
        "assetOnlyAffectModelRoot", "isUltimateShow", "visibleWithEntity", "grounded", "followGrounded",
        "ignoreEntityDither", "useCameraViewportAnchor", "cameraAnchorDistance", "cameraReferenceFov",
        "cameraReferenceAspect", "followGroundedMaxDistance", "lerpToTargetTrans", "lerpDuration",
        "followHideTarget", "visibleWhenHideTarget", "slotIndex",
        "useWeaponMountPoint", "useAccurateMp", "isClothMountPoint", "weaponIndex", "showHideWithWeapon",
        "offsetDirRevert", "usePositionOffsetBB", "useTargetRotation", "scaleWithTargetSize", "fxSize",
        "unpackPosDelayFrame", "unpackFollowTargetOnRelease", "rotUseWeaponMountPoint", "rotWeaponIndex",
        "revertDir", "useSelfRotationBB", "lockYRotation", "unpackRotDelayFrame",
        "unpackFollowTargetRotOnRelease", "weaponVfxKey", "weaponVfxIndex", "weaponVfxPersistent",
        "animateAlert", "alertAnimateDuration", "isAlertAnimateReverse", "angle", "hollow", "value",
    )
    result = {key: value[key] for key in scalar_keys if key in value}
    for key in (
        "visibleWithEntityType", "moveType", "cameraScreenSizeScaleMode", "positionRef", "mountPoint", "weaponMountPoint", "offsetDir",
        "rotType", "rotRef", "directionRef", "rotMountPoint", "rotWeaponMountPoint", "alertType", "modifyType",
    ):
        if key in value:
            result[key] = enum_value(value[key])
    for key in ("cameraViewportPosition", "positionOffset", "selfRotation"):
        if key in value:
            result[key] = value[key]
    for key in ("positionOffsetBB", "selfRotationBB"):
        if key in value:
            result[key] = blackboard_vector(value[key])
    return result


def effect_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    terrain = value.get("effectPosData") if isinstance(value.get("effectPosData"), dict) else {}
    return compact_dict(
        fxType=enum_value(value.get("fxType")),
        effectName=value.get("effectName"),
        guardEffect=value.get("guardEffect"),
        forceGuardEffect=value.get("forceGuardEffect"),
        isCenterChangeLod=value.get("isCenterChangeLod"),
        scale=value.get("scale"),
        scaleBB=blackboard_vector(value.get("scaleBB")),
        useLengthBB=value.get("useLengthBB"),
        lengthBB=blackboard_scalar(value.get("lengthBB")),
        useDurationScaleBB=value.get("useDurationScaleBB"),
        durationScaleBB=blackboard_scalar(value.get("durationScaleBB")),
        releaseByAction=value.get("releaseByAction"),
        ignoreOwnerTimeScale=value.get("ignoreOwnerTimeScale"),
        interruptTime=value.get("interruptTime"),
        terrainPrefab=value.get("terrainPrefab"),
        terrainEffectCount=terrain.get("count"),
        behavior=effect_tail_payload(value.get("effectActionTail")),
        confidence={
            "structure": "exact",
            "semantics": "qualified",
            "note": "The observed projectile effect body is byte-complete. Some wrapper internals and enum labels remain inferred or unnamed.",
        },
    )


def effect_list_payload(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []
    return [effect_payload(item) for item in value.get("entries") or [] if isinstance(item, dict)]


def source_label(path: Path) -> str:
    for part in reversed(path.parts):
        if part in {"StreamingAssets", "Persistent"}:
            return part
    return path.name or "unknown"


def relative_vfs_path(original: Any, source: str) -> str:
    if not original:
        return ""
    normalized = str(original).replace("\\", "/")
    marker = f"/{source}/"
    index = normalized.lower().find(marker.lower())
    return normalized[index + 1 :] if index >= 0 else Path(normalized).name


def find_reference(payload: dict[str, Any], class_name: str) -> dict[str, Any] | None:
    refs = (payload.get("references") or {}).get("RefIds") or []
    for ref in refs:
        if isinstance(ref, dict) and ((ref.get("type") or {}).get("class") == class_name):
            return ref
    return None


def build_entry(path: Path, root: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    template_ref = find_reference(payload, "ProjectileTemplateData")
    component_ref = find_reference(payload, "ProjectileComponentData")
    if not template_ref or not component_ref:
        return None
    template = template_ref.get("data") or {}
    component = component_ref.get("data") or {}
    tail = component.get("tail") or {}
    remaining = tail.get("structuredRemainingTail") or {}
    move_dict = tail.get("moveModeDict") or {}
    metadata = payload.get("$animestudio") or {}
    source = source_label(root)
    projectile_id = str(component.get("id") or template.get("id") or metadata.get("name") or path.stem)
    path_id = str(metadata.get("pathId") or "")
    exact = bool(
        component.get("$decoded")
        and remaining.get("structuredDecodeStatus") == "decoded"
        and int(tail.get("remainingRawWordCount") or 0) == 0
        and int(remaining.get("remainingRawWordCount") or 0) == 0
        and remaining.get("consumedWordCount") == remaining.get("wordCount")
    )
    effects = {label: effect_list_payload(remaining.get(field)) for label, field in EFFECT_LIST_FIELDS}
    sounds = remaining.get("postAlertEffectSoundTail") or {}
    sound_payload = {key: enum_value(sounds.get(key)) for key in SOUND_FIELDS}
    sound_payload.update(
        compact_dict(
            sizzleSoundTriggerDistance=sounds.get("sizzleSoundTriggerDistance"),
            ringProjectileSoundSmoothFactor=sounds.get("ringProjectileSoundSmoothFactor"),
        )
    )
    segments = []
    for row in component.get("moveSegments") or []:
        if not isinstance(row, dict):
            continue
        segments.append(
            compact_dict(
                startPointKey=row.get("startPointKey"),
                moveModeId=row.get("moveModeId"),
                endPointKey=row.get("endPointKey"),
                earlyNextByDuration=row.get("earlyNextByDuration"),
                segmentDuration=blackboard_scalar(row.get("segmentDuration")),
                skipHitAndBlockDetection=row.get("skipHitAndBlockDetection"),
                speedLerpTime=blackboard_scalar(row.get("speedLerpTime")),
            )
        )
    base = template.get("baseTemplate") or {}
    entity = template.get("entityTemplate") or {}
    skills = template.get("skillDataBundle") or {}
    result = {
        "key": f"{source}:{projectile_id}:{path_id}",
        "id": projectile_id,
        "source": compact_dict(
            root=source,
            assetName=metadata.get("name") or payload.get("m_Name"),
            pathId=path_id,
            sourceFile=metadata.get("sourceFile"),
            sourceOffset=metadata.get("sourceOffset"),
            vfsPath=relative_vfs_path(metadata.get("sourceOriginalPath"), source),
            byteSize=metadata.get("byteSize"),
            rawDataSha256=metadata.get("rawDataSha256"),
            typeTreeSource=metadata.get("typeTreeSource"),
            jsonPath=path.relative_to(REPO_ROOT).as_posix() if path.is_relative_to(REPO_ROOT) else path.name,
        ),
        "template": compact_dict(
            name=base.get("name"),
            factionIndex=enum_value(base.get("factionIndex")),
            bornTag=enum_value(entity.get("bornTag")),
            delayToRecycleTime=entity.get("delayToRecycleTime"),
            delayRecyclePerformTime=entity.get("delayRecyclePerformTime"),
            sendDieEvent=entity.get("sendDieEvent"),
            useWeaponEmitMountPoint=template.get("useWeaponEmitMountPoint"),
            emitMountPoint=enum_value(template.get("emitMountPoint")),
            weaponIndex=template.get("weaponIndex"),
            weaponMountPoint=enum_value(template.get("weaponMountPoint")),
            hitMountPoint=enum_value(template.get("hitMountPoint")),
            activeSkillIds=skills.get("allActiveSkillId") or [],
            passiveSkillIds=skills.get("allPassiveSkillId") or [],
            normalAttackIds=skills.get("allNormalAttackId") or [],
            normalAttackList=skills.get("normalAttackList") or [],
            enabledBreakingNormalAttacks=skills.get("enabledBreakingNormalAttacks") or [],
            enabledPassiveSkills=skills.get("enabledPassiveSkills") or [],
            normalSkillId=skills.get("normalSkillId"),
            ultimateSkillId=skills.get("ultimateSkillId"),
            plungingAttackStartId=skills.get("plungingAttackStartId"),
            plungingAttackEndId=skills.get("plungingAttackEndId"),
            dodgeSkillId=skills.get("dodgeSkillId"),
            comboSkillPriorityType=enum_value(skills.get("comboSkillPriorityType")),
            enableComboSkillBlackboard=skills.get("enableComboSkillBlackboard"),
            comboSkillBlackboard=skills.get("comboSkillBlackboard"),
            comboSkillId=skills.get("comboSkillId"),
            comboSkillSpecialNodeName=skills.get("comboSkillSpecialNodeName"),
            hudPanelName=skills.get("hudPanelName"),
            activeSkillTypeOverrides=skills.get("activeSkillTypeOverrides"),
        ),
        "lifetime": compact_dict(
            finishDuration=blackboard_scalar(component.get("finishDuration")),
            finishDistance=blackboard_scalar(component.get("finishDistance")),
            finishOnReach=component.get("finishOnReach"),
            hitOnReach=component.get("hitOnReach"),
            keepMoveOnReach=component.get("keepMoveOnReach"),
            mainEffectFinishType=enum_value(tail.get("mainEffectFinishType")),
            mainEffectFinishTypeSerialized=enum_value(tail.get("mainEffectFinishTypeSerialized")),
            mainEffectFinishDistance=blackboard_scalar(tail.get("mainEffectFinishDistance")),
        ),
        "collision": shape_payload(component.get("colliderShapeData")),
        "targeting": compact_dict(
            blockLayerDef=enum_value(component.get("blockLayerDef")),
            blockLayer=enum_value(component.get("blockLayer")),
            targetFilter=target_filter_payload(component.get("targetFilter")),
            ignoreImmuneLevel=enum_value(component.get("ignoreImmuneLevel")),
            maxHitCount=blackboard_scalar(component.get("maxHitCount")),
            allowHitSameTarget=component.get("allowHitSameTarget"),
            hitIntervalPerTarget=component.get("hitIntervalPerTarget"),
            collisionDetectTiming=enum_value(component.get("collisionDetectTiming")),
            hitAndBlockDetectDelayTime=blackboard_scalar(component.get("hitAndBlockDetectDelayTime")),
            hitAndBlockDetectDelayDistance=blackboard_scalar(component.get("hitAndBlockDetectDelayDistance")),
            canTraceTargetAfterReach=component.get("canTraceTargetAfterReach"),
        ),
        "movement": {
            "presetPointKeys": component.get("presetPointKeys") or [],
            "useSegmentMove": component.get("useSegmentMove"),
            "segments": segments,
            "modes": [move_mode_payload(row) for row in move_dict.get("values") or [] if isinstance(row, dict)],
        },
        "effects": compact_dict(
            lists=effects,
            showReachEffectOnlyWithTarget=remaining.get("showReachEffectOnlyWithTarget"),
            showFinishEffectOnlyWhenUnblockAndNotHit=remaining.get("showFinishEffectOnlyWhenUnblockAndNotHit"),
            showAlertEffect=remaining.get("showAlertEffect"),
            alert=effect_payload(remaining.get("alertEffect")),
        ),
        "sounds": sound_payload,
        "confidence": {
            "structure": "exact" if exact else "incomplete",
            "semantics": "mixed",
            "byteComplete": exact,
            "qualifiers": [
                "ProjectileComponentData boundaries and exact tail consumption are validated for the current installed-game export.",
                "Authored numeric values and blackboard keys are preserved; the WebUI does not evaluate runtime blackboards.",
                "Exporter-provided enum member names are shown where validated; otherwise the numeric value and enum type are retained.",
                "The seven sound fields preserve authored Wwise event hashes; build_audio.py may attach exact HIRC event-to-media candidates when decoded audio is current.",
                "Effect bodies are byte-complete for observed projectile variants while some wrapper semantics remain inferred.",
            ],
        },
    }
    return result


def candidate_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return ()
    return sorted(root.rglob("*projectile*.json"), key=lambda item: item.as_posix().lower())


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build compact WebUI projectile data from exact AnimeStudio MonoBehaviour JSON.",
    )
    parser.add_argument(
        "--input-root",
        action="append",
        type=Path,
        help="MonoBehaviour JSON directory to scan; repeat for multiple source roots. Defaults to StreamingAssets and Persistent.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help=f"Output JSON path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--audio-index", type=Path, default=DEFAULT_AUDIO_INDEX, help=f"Current decoded audio index used to reuse projectile HIRC links (default: {DEFAULT_AUDIO_INDEX})")
    parser.add_argument("--skip-audio-links", action="store_true", help="Do not hydrate projectile sound links from the current decoded audio index.")
    parser.add_argument("--pretty", action="store_true", help="Write indented JSON for inspection instead of compact JSON.")
    parser.add_argument("--require-exact", action="store_true", help="Fail if any emitted projectile lacks exact tail consumption.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    roots = tuple(path.resolve() for path in (args.input_root or DEFAULT_INPUTS))
    entries: list[dict[str, Any]] = []
    scanned = 0
    missing = []
    for root in roots:
        if not root.exists():
            missing.append(str(root))
            continue
        for path in candidate_files(root):
            scanned += 1
            entry = build_entry(path, root)
            if entry:
                entries.append(entry)
    entries.sort(key=lambda row: (str(row.get("id") or ""), str(row.get("source", {}).get("root") or ""), str(row.get("source", {}).get("pathId") or "")))
    incomplete = sum(1 for row in entries if not row["confidence"]["byteComplete"])
    source_counts: dict[str, int] = {}
    for row in entries:
        source = row["source"]["root"]
        source_counts[source] = source_counts.get(source, 0) + 1
    authored_skill_refs: list[str] = []
    movement_modes = 0
    effect_actions = 0
    id_only_tag_filters = 0
    character_projectiles = 0
    enemy_projectiles = 0
    for row in entries:
        projectile_id = str(row.get("id") or "").lower()
        character_projectiles += int("projectile_chr_" in projectile_id)
        enemy_projectiles += int("projectile_eny_" in projectile_id)
        template = row.get("template") or {}
        for key in (
            "activeSkillIds", "passiveSkillIds", "normalAttackIds", "normalAttackList",
            "enabledBreakingNormalAttacks", "enabledPassiveSkills",
        ):
            authored_skill_refs.extend(str(value) for value in (template.get(key) or []) if value)
        for key in (
            "normalSkillId", "ultimateSkillId", "plungingAttackStartId", "plungingAttackEndId",
            "dodgeSkillId", "comboSkillId",
        ):
            if template.get(key):
                authored_skill_refs.append(str(template[key]))
        movement_modes += len((row.get("movement") or {}).get("modes") or [])
        effect_actions += sum(len(values or []) for values in ((row.get("effects") or {}).get("lists") or {}).values())
        id_only_tag_filters += int((((row.get("targeting") or {}).get("targetFilter") or {}).get("tagEntryLayout") == "idOnly"))
    output = {
        "schemaVersion": 2,
        "source": "AnimeStudio exact MonoBehaviour projectile decode",
        "sourceRoots": [source_label(root) for root in roots],
        "counts": {
            "projectiles": len(entries),
            "byteComplete": len(entries) - incomplete,
            "incomplete": incomplete,
            "bySource": dict(sorted(source_counts.items())),
            "characterProjectiles": character_projectiles,
            "enemyProjectiles": enemy_projectiles,
            "otherProjectiles": len(entries) - character_projectiles - enemy_projectiles,
            "movementModes": movement_modes,
            "effectActions": effect_actions,
            "authoredSkillRefs": len(authored_skill_refs),
            "uniqueAuthoredSkills": len(set(authored_skill_refs)),
            "idOnlyTagFilters": id_only_tag_filters,
        },
        "confidence": {
            "structure": "exact" if entries and incomplete == 0 else "mixed",
            "semantics": "qualified",
            "note": "Structural completeness does not imply recovered runtime enum/hash meanings or evaluated blackboard values.",
        },
        "entries": entries,
    }
    audio_links = None if args.skip_audio_links else hydrate_audio_links(entries, args.audio_index.resolve())
    if audio_links is not None:
        output["audioLinks"] = audio_links
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None, separators=None if args.pretty else (",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"Projectile data: {len(entries)} entries ({len(entries) - incomplete} byte-complete, {incomplete} incomplete)")
    print(f"Scanned candidate JSON: {scanned}")
    print(f"Sources: {', '.join(f'{key}={value}' for key, value in sorted(source_counts.items())) or 'none'}")
    if missing:
        print(f"Missing input roots (skipped): {len(missing)}")
        for path in missing:
            print(f"  {path}")
    print(f"Wrote: {args.output}")
    if args.require_exact and incomplete:
        print("ERROR: --require-exact rejected incomplete projectile records")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
