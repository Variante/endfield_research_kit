"""Build a compact projectile inspector payload from AnimeStudio JSON (game/Unity.sqlite).

The source records are ``data_projectile_*`` MonoBehaviour objects whose
managed references (``ProjectileTemplateData`` and
``ProjectileComponentData``) the local AnimeStudio fork decoded through the
serialized managed-reference TypeTree that ships inside the bundle.  That
TypeTree names every field and the decode consumed the bounded payload
exactly, so field order and values are exact. Its enum integers stay on each
row. An optional selected-native join publishes EffectActionCfg enum names
only when the installed pair, declaring fields, and all published values
validate; it does not infer runtime use.

Any other object shape is skipped and counted.  The retired hand-written
decoders published inferred field names and partial tails; the exporter's
exact-only gate now replaces such a result with the TypeTree decode or leaves
the object out, so a non-TypeTree payload reaching this builder is a pipeline
regression to surface, not data to guess at.

Examples:
    python -m scripts.webui.gameplay.build_gameplay --stage projectiles
    python -m scripts.webui.gameplay.projectiles --pretty
    python -m scripts.webui.gameplay.projectiles --export-root PATH --output PATH
"""

from __future__ import annotations
from scripts.common import EXPORT_LAYOUT, check_installed_native_inputs

import argparse
import json
import sys
from pathlib import Path
from typing import Any


from scripts.game_data.unity_store import UnityObjectStore, open_store_if_present
from scripts.repo_paths import REPO_ROOT
from scripts.source_paths import ExportLayout

if __package__ in {None, ""}:
    raise SystemExit(
        "Run this maintained entry point as: "
        "python -m scripts.webui.gameplay.projectiles"
    )

EXPORT_ROOT = EXPORT_LAYOUT.root
#: The scanned Unity type; its documents are rows of game/Unity.sqlite.
PROJECTILE_UNITY_TYPE = "MonoBehaviour"
PROJECTILE_NAME_GLOB = "*projectile*.json"
DEFAULT_OUTPUT = REPO_ROOT / "webui/data/gameplay/projectiles.json"
SCHEMA_VERSION = 5
SOURCE_LABEL = "AnimeStudio exact managed-reference TypeTree decode"
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
# Reasons a candidate file is left out.  Each is a pipeline condition a reader
# can act on, never a guess about the payload.
SKIP_NOT_JSON = "unreadable_json"
SKIP_NO_PROJECTILE_REFERENCES = "no_projectile_references"
SKIP_NOT_EXACT_TYPETREE = "not_exact_typetree_decode"
SKIP_REGISTRY_NOT_FULLY_DECODED = "registry_not_fully_decoded"


def compact_dict(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def hash32(value: Any) -> Any:
    """Publish an authored int32 hash as its signed value plus uint32 hex.

    Wwise event ids are serialized as ``{"_id": int32}``; consumers mask the
    signed value back to uint32.  Both views are kept so a reader can match
    either the serialized word or the Wwise id without re-deriving it.
    """
    if isinstance(value, dict):
        value = value.get("_id")
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    return {"value": value, "hex": f"0x{value & 0xFFFFFFFF:08x}"}


def layer_mask(value: Any) -> Any:
    if isinstance(value, dict) and "m_Bits" in value:
        return {"bits": value.get("m_Bits")}
    return value


def blackboard_scalar(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    return compact_dict(
        useBlackboardKey=value.get("useBlackboardKey"),
        value=value.get("value"),
        blackboardKey=value.get("blackboardKey"),
    )


def blackboard_vector(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    return {axis: blackboard_scalar(value.get(axis)) for axis in ("x", "y", "z") if axis in value}


def blackboard_pair(value: Any) -> Any:
    """A two-component blackboard vector; the TypeTree names the axes x and y.

    The retired decoder labelled these ``min``/``max``.  That reading is not
    carried by the serialized data, so the axis names are kept as authored.
    """
    if not isinstance(value, dict):
        return value
    return {axis: blackboard_scalar(value.get(axis)) for axis in ("x", "y") if axis in value}


def curve(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    keyframes = []
    for row in value.get("m_Curve") or []:
        if not isinstance(row, dict):
            continue
        keyframes.append(
            compact_dict(
                time=row.get("time"),
                value=row.get("value"),
                inSlope=row.get("inSlope"),
                outSlope=row.get("outSlope"),
                weightedMode=row.get("weightedMode"),
                inWeight=row.get("inWeight"),
                outWeight=row.get("outWeight"),
            )
        )
    return compact_dict(
        keyframes=keyframes,
        preInfinity=value.get("m_PreInfinity"),
        postInfinity=value.get("m_PostInfinity"),
        rotationOrder=value.get("m_RotationOrder"),
    )


def bezier_point(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    return compact_dict(
        usePresetPoint=value.get("usePresetPoint"),
        presetPointKey=value.get("presetPointKey"),
        xRatioRange=blackboard_pair(value.get("xRatioRange")),
        yzAngleRange=blackboard_pair(value.get("yzAngleRange")),
        yzRadiusRange=blackboard_pair(value.get("yzRadiusRange")),
        scaledYzRadius=value.get("scaledYzRadius"),
    )


def shape_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return compact_dict(
        shapeType=value.get("shapeType"),
        radius=blackboard_scalar(value.get("radius")),
        center=blackboard_vector(value.get("center")),
        extent=blackboard_vector(value.get("extent")),
        initOuterRadius=blackboard_scalar(value.get("initOuterRadius")),
        initInnerRadius=blackboard_scalar(value.get("initInnerRadius")),
        outerRadiusIncreaseSpeed=blackboard_scalar(value.get("outerRadiusIncreaseSpeed")),
        innerRadiusIncreaseSpeed=blackboard_scalar(value.get("innerRadiusIncreaseSpeed")),
        height=blackboard_scalar(value.get("height")),
        isSector=value.get("isSector"),
        sectorDirection=value.get("sectorDirection"),
        sectorAngle=blackboard_scalar(value.get("sectorAngle")),
    )


def target_filter_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    query = value.get("tagQuery") if isinstance(value.get("tagQuery"), dict) else {}
    return compact_dict(
        checkAlive=value.get("checkAlive"),
        autoSetTargetFaction=value.get("autoSetTargetFaction"),
        factionTarget=value.get("factionTarget"),
        targetFactionType=value.get("targetFactionType"),
        filterObjectType=value.get("filterObjectType"),
        objectType=value.get("objectType"),
        filterSlot=value.get("filterSlot"),
        slotIndex=value.get("slotIndex"),
        filterGameplayTag=value.get("filterGameplayTag"),
        tagQuery=compact_dict(queryType=query.get("queryType"), tags=query.get("tags") or []),
    )


def move_mode_payload(key: Any, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return compact_dict(
        key=key,
        traceType=value.get("traceType"),
        traceTime=blackboard_scalar(value.get("traceTime")),
        traceUntilDistance=blackboard_scalar(value.get("traceUntilDistance")),
        moveType=value.get("moveType"),
        parabolaDef=value.get("parabolaDef"),
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
        bezierMidPoint1=bezier_point(value.get("bezierMidPoint1")),
        bezierMidPoint2=bezier_point(value.get("bezierMidPoint2")),
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
            "note": "Field order and values come from the serialized managed-reference TypeTree; movement enum members are numeric because no validated member name exists.",
        },
    )


def move_modes(value: Any) -> list[dict[str, Any]]:
    """``Dictionary<string, MoveModeData>`` serializes as parallel key/value arrays."""
    if not isinstance(value, dict):
        return []
    keys = value.get("_keyData") or []
    values = value.get("_valueData") or []
    return [
        move_mode_payload(key, row)
        for key, row in zip(keys, values)
        if isinstance(row, dict)
    ]


def effect_behavior_payload(value: dict[str, Any]) -> dict[str, Any]:
    scalar_keys = (
        "isShowInDialog", "isLimitEffectCount", "limitCount", "protectTime", "limitTime", "limitKey",
        "assetOnlyAffectModelRoot", "isUltimateShow", "visibleWithEntity", "visibleWithEntityType",
        "moveType", "grounded", "followGrounded", "ignoreEntityDither", "useCameraViewportAnchor",
        "cameraViewportPosition", "cameraAnchorDistance", "cameraScreenSizeScaleMode",
        "cameraReferenceFov", "cameraReferenceAspect", "positionRef", "followGroundedMaxDistance",
        "lerpToTargetTrans", "lerpDuration", "followHideTarget", "visibleWhenHideTarget", "slotIndex",
        "useWeaponMountPoint", "mountPoint", "useAccurateMp", "isClothMountPoint", "weaponIndex",
        "weaponMountPoint", "showHideWithWeapon", "offsetDir", "offsetDirRevert", "usePositionOffsetBB",
        "positionOffset", "useTargetRotation", "scaleWithTargetSize", "fxSize", "unpackPosDelayFrame",
        "unpackFollowTargetOnRelease", "rotType", "rotRef", "directionRef", "rotUseWeaponMountPoint",
        "rotMountPoint", "rotWeaponIndex", "rotWeaponMountPoint", "revertDir", "useSelfRotationBB",
        "selfRotation", "lockYRotation", "unpackRotDelayFrame", "unpackFollowTargetRotOnRelease",
        "weaponVfxKey", "weaponVfxIndex", "weaponVfxPersistent", "alertType", "animateAlert",
        "alertAnimateDuration", "isAlertAnimateReverse", "angle", "hollow", "modifyType", "value",
    )
    result = {key: value[key] for key in scalar_keys if key in value}
    for key in ("positionOffsetBB", "selfRotationBB"):
        if key in value:
            result[key] = blackboard_vector(value[key])
    return result


def effect_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    terrain = value.get("effectPosData")
    return compact_dict(
        fxType=value.get("fxType"),
        effectName=value.get("effectName"),
        guardEffect=value.get("guardEffect"),
        isCenterChangeLod=value.get("isCenterChangeLod"),
        useScaleBB=value.get("useScaleBB"),
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
        terrainEffectCount=len(terrain) if isinstance(terrain, list) else None,
        terrainEffects=[
            compact_dict(tag=row.get("tag"), effectName=row.get("effectName"))
            for row in (terrain if isinstance(terrain, list) else [])
            if isinstance(row, dict)
        ] or None,
        behavior=effect_behavior_payload(value),
        confidence={
            "structure": "exact",
            "semantics": "qualified",
            "note": "EffectActionCfg fields come from the serialized managed-reference TypeTree; selected enum names are optional top-level enrichment and stored ids remain numeric.",
        },
    )


def effect_list_payload(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [effect_payload(item) for item in value if isinstance(item, dict)]


def load_effect_config_enums() -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    """Resolve selected EffectActionCfg field enums without changing raw rows."""
    gate = check_installed_native_inputs()
    evidence: dict[str, Any] = {
        "status": gate.status,
        "detail": gate.detail,
        "source": "selected GameAssembly.dll + global-metadata.dat",
    }
    if not gate.validated:
        return {}, evidence
    try:
        from scripts.game_data.il2cpp.native_image import NativeImage
        from scripts.game_data.memorypack.derived_plans import load_registry
        from scripts.game_data.memorypack.effect_config_corpus import (
            EFFECT_TYPE, ENUM_FIELDS, effect_definition,
        )
        from scripts.game_data.memorypack.target_settings_corpus import selected_enum_fields

        registry, plan_gate = load_registry(
            gameassembly=gate.gameassembly, metadata=gate.metadata,
        )
        if plan_gate.get("status") != "validated":
            raise ValueError(f"selected EffectActionCfg plan unavailable: {plan_gate.get('status')}")
        names, _audit = selected_enum_fields(
            NativeImage(gate.gameassembly, gate.metadata, label="projectile-effect-config"),
            registry, effect_definition(registry),
            owner_type=EFFECT_TYPE, enum_fields=ENUM_FIELDS,
        )
        evidence.update({
            "status": "validated",
            "nativeInputs": {
                "GameAssembly.dll": gate.gameassembly_sha256,
                "global-metadata.dat": gate.metadata_sha256,
            },
            "boundary": (
                "selected native field-to-enum types and serialized plan; "
                "names describe authored EffectActionCfg values, not spawned or active effects"
            ),
        })
        return {
            field: {str(value): name for value, name in members.items()}
            for field, members in names.items()
        }, evidence
    except Exception as error:
        evidence.update({
            "status": "unavailable",
            "detail": f"{type(error).__name__}: {error}",
        })
        return {}, evidence


def validate_effect_config_enums(
    entries: list[dict[str, Any]], enums: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Require every exported effect value to have a selected enum member."""
    if not enums:
        return {"status": "incomplete", "checkedConfigs": 0,
                "failureCount": 1, "failureExamples": [{"gate": "empty-enum-fields"}]}
    checked = 0
    failure_count = 0
    failures: list[dict[str, Any]] = []

    def check(entry: dict[str, Any], slot: str, index: int, effect: dict[str, Any]) -> None:
        nonlocal checked, failure_count
        checked += 1
        for field, members in enums.items():
            value = effect.get(field) if field == "fxType" else (effect.get("behavior") or {}).get(field)
            if type(value) is int and str(value) in members:
                continue
            failure_count += 1
            if len(failures) < 12:
                source = entry.get("source") or {}
                failures.append({
                    "gate": "selected-effect-enum-member",
                    "projectile": entry.get("id"),
                    "source": source.get("jsonPath"),
                    "sourceSha256": source.get("rawDataSha256"),
                    "slot": slot, "index": index, "field": field,
                    "expectedCount": len(members),
                    "expectedFirst": sorted(members, key=int)[:8],
                    "actual": value,
                })

    for entry in entries:
        effects = entry.get("effects") or {}
        for slot, values in (effects.get("lists") or {}).items():
            for index, effect in enumerate(values or []):
                if not isinstance(effect, dict) or not effect:
                    continue
                check(entry, slot, index, effect)
        alert = effects.get("alert")
        if isinstance(alert, dict) and alert:
            check(entry, "alert", 0, alert)
    return {"status": "validated" if checked and not failure_count else "incomplete",
            "checkedConfigs": checked, "failureCount": failure_count,
            "failureExamples": failures}


def source_label(path: Path) -> str:
    for part in reversed(path.parts):
        if part in {"StreamingAssets", "Persistent"}:
            return part
    return path.name or "unknown"


INSTALLED_LAYERS = ("StreamingAssets", "Persistent")


def installed_layer(original: Any) -> str | None:
    """The installed layer named in an AnimeStudio source path, if any."""
    normalized = str(original or "").replace("\\", "/").lower()
    for layer in INSTALLED_LAYERS:
        if f"/{layer.lower()}/" in normalized:
            return layer
    return None


def relative_vfs_path(original: Any) -> str:
    """The source path from its installed layer down, e.g. ``Persistent/VFS/…``."""
    if not original:
        return ""
    normalized = str(original).replace("\\", "/")
    layer = installed_layer(normalized)
    if layer is None:
        return Path(normalized).name
    index = normalized.lower().find(f"/{layer.lower()}/")
    return normalized[index + 1 :]


def find_reference(payload: dict[str, Any], class_name: str) -> dict[str, Any] | None:
    refs = (payload.get("references") or {}).get("RefIds") or []
    for ref in refs:
        if isinstance(ref, dict) and ((ref.get("type") or {}).get("class") == class_name):
            return ref
    return None


def is_exact_typetree_decode(data: Any) -> bool:
    return (
        isinstance(data, dict)
        and data.get("$decoded") is True
        and data.get("exactTypeTreeDecoded") is True
        and data.get("serializedLayoutSource") == "managed-reference TypeTree"
    )


def registry_fully_decoded(payload: dict[str, Any]) -> bool:
    metadata = payload.get("$animestudio") or {}
    references = payload.get("references") or {}
    return (
        metadata.get("managedReferencesRegistryFullyDecoded") is True
        and references.get("$decoded") is True
        and not references.get("$partial")
        and not references.get("$heuristic")
    )


def build_entry(path: Path, root: Path, data: bytes) -> tuple[dict[str, Any] | None, str | None]:
    """Return ``(entry, None)`` or ``(None, skip_reason)``.

    ``path`` is the document's logical ``game/Unity/<Type>/<name>`` path under
    the export root and ``data`` its exact bytes from the object store.
    """
    try:
        payload = json.loads(data.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError):
        return None, SKIP_NOT_JSON
    if not isinstance(payload, dict):
        return None, SKIP_NOT_JSON
    template_ref = find_reference(payload, "ProjectileTemplateData")
    component_ref = find_reference(payload, "ProjectileComponentData")
    if not template_ref or not component_ref:
        return None, SKIP_NO_PROJECTILE_REFERENCES
    template = template_ref.get("data") or {}
    component = component_ref.get("data") or {}
    if not (is_exact_typetree_decode(template) and is_exact_typetree_decode(component)):
        return None, SKIP_NOT_EXACT_TYPETREE
    if not registry_fully_decoded(payload):
        return None, SKIP_REGISTRY_NOT_FULLY_DECODED

    metadata = payload.get("$animestudio") or {}
    source = source_label(root)
    projectile_id = str(component.get("id") or template.get("id") or metadata.get("name") or path.stem)
    path_id = str(metadata.get("pathId") or "")
    effects = {label: effect_list_payload(component.get(field)) for label, field in EFFECT_LIST_FIELDS}
    sound_payload: dict[str, Any] = {key: hash32(component.get(key)) for key in SOUND_FIELDS}
    sound_payload.update(
        compact_dict(
            sizzleSoundTriggerDistance=component.get("sizzleSoundTriggerDistance"),
            ringProjectileSoundSmoothFactor=component.get("ringProjectileSoundSmoothFactor"),
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
            layer=installed_layer(metadata.get("sourceOriginalPath")),
            vfsPath=relative_vfs_path(metadata.get("sourceOriginalPath")),
            byteSize=metadata.get("byteSize"),
            rawDataSha256=metadata.get("rawDataSha256"),
            typeTreeSource=metadata.get("typeTreeSource"),
            templateTypeTreeNodeCount=template.get("serializedTypeTreeNodeCount"),
            componentTypeTreeNodeCount=component.get("serializedTypeTreeNodeCount"),
            jsonPath=path.relative_to(REPO_ROOT).as_posix() if path.is_relative_to(REPO_ROOT) else path.name,
        ),
        "template": compact_dict(
            name=template.get("name"),
            factionIndex=template.get("factionIndex"),
            bornTag=template.get("bornTag"),
            delayToRecycleTime=template.get("delayToRecycleTime"),
            delayRecyclePerformTime=template.get("delayRecyclePerformTime"),
            sendDieEvent=template.get("sendDieEvent"),
            useWeaponEmitMountPoint=template.get("useWeaponEmitMountPoint"),
            emitMountPoint=template.get("emitMountPoint"),
            weaponIndex=template.get("weaponIndex"),
            weaponMountPoint=template.get("weaponMountPoint"),
            hitMountPoint=template.get("hitMountPoint"),
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
            comboSkillPriorityType=skills.get("comboSkillPriorityType"),
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
            finishOnBlock=component.get("finishOnBlock"),
            allowRepeatBlock=component.get("allowRepeatBlock"),
            useHitBlockReachOrder=component.get("useHitBlockReachOrder"),
            hitOnReach=component.get("hitOnReach"),
            keepMoveOnReach=component.get("keepMoveOnReach"),
            mainEffectFinishType=component.get("mainEffectFinishType"),
            mainEffectFinishDistance=blackboard_scalar(component.get("mainEffectFinishDistance")),
        ),
        "collision": compact_dict(
            **shape_payload(component.get("colliderShapeData")),
            separateHitAndBlockCollider=component.get("separateHitAndBlockCollider"),
            blockCollider=shape_payload(component.get("blockColliderShapeData")) or None,
            zAxisRotationAngle=blackboard_scalar(component.get("zAxisRotationAngle")),
        ),
        "targeting": compact_dict(
            blockLayerDef=component.get("blockLayerDef"),
            blockLayer=layer_mask(component.get("blockLayer")),
            targetFilter=target_filter_payload(component.get("targetFilter")),
            ignoreImmuneLevel=component.get("ignoreImmuneLevel"),
            maxHitCount=blackboard_scalar(component.get("maxHitCount")),
            allowHitSameTarget=component.get("allowHitSameTarget"),
            hitIntervalPerTarget=component.get("hitIntervalPerTarget"),
            collisionDetectTiming=component.get("collisionDetectTiming"),
            hitAndBlockDetectDelayTime=blackboard_scalar(component.get("hitAndBlockDetectDelayTime")),
            hitAndBlockDetectDelayDistance=blackboard_scalar(component.get("hitAndBlockDetectDelayDistance")),
            canTraceTargetAfterReach=component.get("canTraceTargetAfterReach"),
        ),
        "movement": {
            "presetPointKeys": component.get("presetPointKeys") or [],
            "useSegmentMove": component.get("useSegmentMove"),
            "segments": segments,
            "modes": move_modes(component.get("moveModeDict")),
        },
        "effects": compact_dict(
            lists=effects,
            showReachEffectOnlyWithTarget=component.get("showReachEffectOnlyWithTarget"),
            showFinishEffectOnlyWhenUnblockAndNotHit=component.get("showFinishEffectOnlyWhenUnblockAndNotHit"),
            showAlertEffect=component.get("showAlertEffect"),
            alert=effect_payload(component.get("alertEffect")),
        ),
        "sounds": sound_payload,
        "confidence": {
            "structure": "exact",
            "semantics": "qualified",
            "byteComplete": True,
            "qualifiers": [
                "ProjectileTemplateData and ProjectileComponentData are decoded from the serialized managed-reference TypeTree, which the exporter consumed to the exact payload length.",
                "Authored numeric values and blackboard keys are preserved; the WebUI does not evaluate runtime blackboards.",
                "Enum members, mount-point ids, and layer masks are published as their serialized integers; no member name is inferred.",
                "The seven sound fields preserve authored Wwise event hashes; playable media is published separately by build_audio.py.",
            ],
        },
    }
    return result, None


def candidate_names(store: UnityObjectStore) -> list[str]:
    """Projectile candidate document names; a names-only pass, bytes are read per match."""
    return sorted(store.names(PROJECTILE_UNITY_TYPE, PROJECTILE_NAME_GLOB), key=str.lower)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build compact WebUI projectile data from exact AnimeStudio MonoBehaviour JSON.",
    )
    parser.add_argument(
        "--export-root",
        type=Path,
        default=EXPORT_ROOT,
        help=(
            "Export root whose game/Unity.sqlite object store holds the "
            f"*projectile*.json MonoBehaviour documents (default: {EXPORT_ROOT})."
        ),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help=f"Output JSON path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--pretty", action="store_true", help="Write indented JSON for inspection instead of compact JSON.")
    parser.add_argument(
        "--require-exact",
        action="store_true",
        help="Fail if any projectile candidate was skipped as a non-exact or partial decode.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    export_root = args.export_root.resolve()
    layout = ExportLayout(export_root)
    root = layout.unity_type_dir(PROJECTILE_UNITY_TYPE)
    roots = (root,)
    entries: list[dict[str, Any]] = []
    scanned = 0
    missing = []
    skipped: dict[str, list[str]] = {}
    store = open_store_if_present(export_root)
    if store is None:
        missing.append(str(layout.unity_store_path))
    else:
        for name in candidate_names(store):
            scanned += 1
            entry, reason = build_entry(root / name, root, store.read_bytes(PROJECTILE_UNITY_TYPE, name))
            if entry:
                entries.append(entry)
            elif reason:
                skipped.setdefault(reason, []).append(name)
    entries.sort(key=lambda row: (str(row.get("id") or ""), str(row.get("source", {}).get("root") or ""), str(row.get("source", {}).get("pathId") or "")))
    source_counts: dict[str, int] = {}
    for row in entries:
        source = row["source"]["root"]
        source_counts[source] = source_counts.get(source, 0) + 1
    authored_skill_refs: list[str] = []
    movement_modes = 0
    effect_actions = 0
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
    # Only decode-quality skips count against exactness.  A ProjectileTable or
    # an unrelated file matching the name glob is not a projectile candidate.
    non_exact_skips = {
        reason: names
        for reason, names in skipped.items()
        if reason in (SKIP_NOT_EXACT_TYPETREE, SKIP_REGISTRY_NOT_FULLY_DECODED)
    }
    effect_enums, effect_enum_evidence = load_effect_config_enums()
    if effect_enum_evidence["status"] == "validated":
        checked = validate_effect_config_enums(entries, effect_enums)
        effect_enum_evidence.update(checked)
        if checked["status"] != "validated":
            effect_enums = {}
            first = (checked.get("failureExamples") or [{}])[0]
            effect_enum_evidence["detail"] = (
                f"projectile EffectActionCfg enum audit failed: "
                f"{checked['failureCount']} field values; first {first}"
            )
    output = {
        "schemaVersion": SCHEMA_VERSION,
        "source": SOURCE_LABEL,
        "sourceRoots": [source_label(root) for root in roots],
        "counts": {
            "projectiles": len(entries),
            "byteComplete": len(entries),
            "scannedCandidates": scanned,
            "skipped": {reason: len(names) for reason, names in sorted(skipped.items())},
            "bySource": dict(sorted(source_counts.items())),
            "characterProjectiles": character_projectiles,
            "enemyProjectiles": enemy_projectiles,
            "otherProjectiles": len(entries) - character_projectiles - enemy_projectiles,
            "movementModes": movement_modes,
            "effectActions": effect_actions,
            "authoredSkillRefs": len(authored_skill_refs),
            "uniqueAuthoredSkills": len(set(authored_skill_refs)),
        },
        "skippedFiles": {reason: sorted(names) for reason, names in sorted(non_exact_skips.items())},
        "effectConfigEnums": effect_enums,
        "effectConfigEnumEvidence": effect_enum_evidence,
        "confidence": {
            "structure": "exact" if entries and not non_exact_skips else ("mixed" if entries else "empty"),
            "semantics": "qualified",
            "note": "Every published entry is an exact managed-reference TypeTree decode. Selected EffectActionCfg enum names are optional and describe stored values; runtime effect behavior, event hashes, and evaluated blackboard values remain unresolved.",
        },
        "entries": entries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None, separators=None if args.pretty else (",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        f"projectiles: {len(entries)} entries from {scanned} candidate files "
        f"({', '.join(f'{reason}={len(names)}' for reason, names in sorted(skipped.items())) or 'no skips'}); "
        f"effect-enums={effect_enum_evidence['status']}; wrote {args.output}",
    )
    if effect_enum_evidence["status"] == "incomplete":
        print(f"[projectiles.effect-config-enums] {effect_enum_evidence['detail']}", file=sys.stderr)
    if missing:
        print(f"missing Unity object store: {', '.join(missing)}")
    if args.require_exact and non_exact_skips:
        for reason, names in sorted(non_exact_skips.items()):
            print(f"non-exact skip {reason}: {', '.join(sorted(names)[:5])}{' ...' if len(names) > 5 else ''}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
