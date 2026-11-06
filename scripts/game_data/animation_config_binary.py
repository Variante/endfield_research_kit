"""Complete selected AnimationConfig operation and independent legacy prefix.

The legacy mask component proves null/empty/one-entry lists and pooled layer names.
It does not admit extraData, montages, Beyond.FAnimationCurve or whole-owner EOF,
including payloads whose unread tail resembles an older fixed empty variant.
"""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import struct
from typing import Any
from scripts.game_data.memorypack.core import MEMORYPACK_NULL_COUNT
from scripts.game_data.animation_masks_native import validate as validate_animation_masks
from scripts.game_data.string_pool import StringPool

ANIMATION_CONFIG_FIELDS = (
    "_fallbackMontages",
    "avatarBlendProfilePath",
    "bakedBindingPath",
    "boneWeightMasks",
    "controllerPath",
    "extraData",
    "montages",
    "npcMontages",
    "optControllerPath",
    "retargetAnimConfigPath",
    "syncGroupAnimationCurves",
    "syncGroupCurves",
    "timeRefCurves",
    "useRotateDirection",
    "useStateVariables",
)
ANIMATION_CONFIG_PREFIX_FIELDS = ANIMATION_CONFIG_FIELDS[:5]
BONE_WEIGHT_MASK_FIELDS = ("layerName", "maskPath")

class AnimationConfigFramingError(ValueError):
    """Raised when the current-corpus prefix cannot be authenticated."""


def decode_animation_config_current_animation(data, *, operation):
    """Explicit whole MC15 opt-in; accept its native receipt only after exit."""
    from scripts.game_data.animation_current_native import prepared_current_animation
    return prepared_current_animation(operation).animation_config(data)


class _CompleteAnimationReader:
    def __init__(self,operation,gameassembly,metadata):
        self.operation=operation;self.active=True
        self.native_sources={'GameAssembly.dll':str(gameassembly),'global-metadata.dat':str(metadata)}
        self.counts=dict(attempted=0,closed=0,failed=0)

    def __call__(self,data):
        if not self.active:raise AnimationConfigFramingError('AnimationConfig complete operation is closed')
        self.counts['attempted']+=1
        try:
            value=self.operation.animation_config(data)
            fields=value.get('fields',[])
            if(value.get('schemaStatus')!='named_exact'or value.get('wholeSchemaExact')is not True
                or value.get('physicalEOF')is not True or value.get('serializedMemberCount')!=15
                or value.get('bytesConsumed')!=len(data)or not isinstance(fields,list)
                or any(not isinstance(r,dict)or not isinstance(r.get('value'),dict)for r in fields)
                or[(r.get('memberIndex'),r.get('fieldName'))for r in fields]!=list(enumerate(ANIMATION_CONFIG_FIELDS))
                or value.get('opaqueRanges')or value.get('unreadFields')):
                raise AnimationConfigFramingError('AnimationConfig complete operation: fifteen named fields and physical EOF required')
            self.counts['closed']+=1;return value
        except ValueError as error:
            self.counts['failed']+=1
            raise AnimationConfigFramingError(str(error))from error

    @property
    def receipt(self):
        proof=self.operation.receipt
        if self.active or proof.get('wholeAnimationConfigAdmitted')is not True:
            raise AnimationConfigFramingError('AnimationConfig complete operation: successful closed native scope required')
        if self.counts['failed']or self.counts['attempted']!=self.counts['closed']:
            raise AnimationConfigFramingError('AnimationConfig complete operation: incomplete owners '+str(self.counts))
        return dict(schema='endfield.complete-animation-config-operation.v1',nativeInputs=proof['nativeInputs'],
            nativeSources=self.native_sources,sourceCounts=dict(self.counts),allAttemptedOwnersClosed=True,
            nativeSourcePoolExitBookendsPassed=proof['nativeSourcePoolExitBookendsPassed'],
            wholeAnimationConfigAdmitted=True,physicalEOFRequired=True,serializedMemberCount=15,
            currentAnimationOperation=proof,runtimeAnimationProved=False)


@contextmanager
def complete_animation_reader(*,strings,game_root=None,gameassembly=None,metadata=None):
    """Fresh complete graph, authoritative selected pair and reloaded pool pages.

    Required consumers retain no result before the native/source/pool exit and
    all attempted owners close. There is no downgrade to the legacy prefix.
    """
    from scripts.common import resolve_installed_native_inputs
    from scripts.game_data.animation_current_native import current_animation
    if(gameassembly is None)!=(metadata is None):
        raise AnimationConfigFramingError('AnimationConfig complete operation: both native paths required')
    if gameassembly is None:
        if game_root is None:gameassembly,metadata=resolve_installed_native_inputs()
        else:
            selected=Path(game_root).resolve();gameassembly=selected.parent/'GameAssembly.dll';metadata=selected/'il2cpp_data/Metadata/global-metadata.dat'
    ga,md=Path(gameassembly).resolve(),Path(metadata).resolve()
    selected=Path(game_root).resolve()if game_root is not None else md.parents[2]
    if ga!=selected.parent/'GameAssembly.dll'or md!=selected/'il2cpp_data/Metadata/global-metadata.dat':
        raise AnimationConfigFramingError('AnimationConfig complete operation: explicit root/native pair disagree')
    if not isinstance(strings,StringPool):raise AnimationConfigFramingError('AnimationConfig complete operation: selected StringPool required')
    # A caller may have resolved an older version of the same pool object.
    # Reopening current pages prevents stale cached strings passing bookends.
    fresh=StringPool(strings.root)
    with current_animation(game_root=selected,strings=fresh,families=('animation-config',))as operation:
        reader=_CompleteAnimationReader(operation,ga,md)
        try:yield reader
        finally:reader.active=False
    reader.receipt


def decode_animation_config_complete_frame(data,*,strings,game_root=None,gameassembly=None,metadata=None):
    with complete_animation_reader(strings=strings,game_root=game_root,gameassembly=gameassembly,metadata=metadata)as decode:
        value=decode(data)
    return value

def _require(data: bytes, offset: int, size: int, field: str) -> int:
    if size < 0 or offset < 0 or offset + size > len(data):
        raise AnimationConfigFramingError(
            f"{field}:truncated offset={offset} need={size} "
            f"remaining={max(0, len(data) - offset)}"
        )
    return offset + size

def _read_i64(data: bytes, offset: int, field: str) -> tuple[int, int]:
    end = _require(data, offset, 8, field)
    return struct.unpack_from("<q", data, offset)[0], end

def _read_u32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    end = _require(data, offset, 4, field)
    return struct.unpack_from("<I", data, offset)[0], end

def _decode_named_prefix(data: bytes, *, strings: StringPool | None, game_root=None) -> dict[str, Any]:
    """Decode the generated wrapper's first five members at a real cursor."""
    if len(data) < 30:
        raise AnimationConfigFramingError(
            f"truncated AnimationConfig named prefix: expected>=30 actual={len(data)}"
        )
    if data[1] != 0xFF:
        raise AnimationConfigFramingError(
            "AnimationConfig _fallbackMontages supports only the current null variant: "
            f"actual={data[1]}"
        )

    avatar_blend_profile_path, cursor = _read_i64(
        data, 2, "avatarBlendProfilePath"
    )
    baked_binding_path, cursor = _read_i64(data, cursor, "bakedBindingPath")
    raw_count, cursor = _read_u32(data, cursor, "boneWeightMasks.count")
    if raw_count == MEMORYPACK_NULL_COUNT:
        mask_count: int | None = None
    elif raw_count in (0, 1):
        mask_count = raw_count
    else:
        raise AnimationConfigFramingError(
            f"boneWeightMasks:invalid-count={raw_count}"
        )

    if mask_count and strings is None:
        raise AnimationConfigFramingError("boneWeightMasks: matching current StringPool required")
    native = validate_animation_masks(game_root=game_root)
    if native.get("status") != "validated":
        raise AnimationConfigFramingError("AnimationConfig prefix: native source " + str(native)[:800])
    masks: list[dict[str, Any]] = []
    for index in range(mask_count or 0):
        start = cursor
        cursor = _require(data, cursor, 1, f"boneWeightMasks[{index}].memberCount")
        member_count = data[start]
        if member_count != 2:
            raise AnimationConfigFramingError(
                f"boneWeightMasks[{index}].memberCount:expected=2 actual={member_count}"
            )
        _require(data, cursor, 4, f"boneWeightMasks[{index}].layerName")
        pool_index = struct.unpack_from("<i", data, cursor)[0]
        layer_name = strings.resolve(pool_index)
        cursor += 4
        mask_path, cursor = _read_i64(
            data, cursor, f"boneWeightMasks[{index}].maskPath"
        )
        masks.append({
            "memberCount": member_count,
            "fieldOrder": list(BONE_WEIGHT_MASK_FIELDS),
            "layerName": layer_name,
            "layerNamePoolIndex": pool_index,
            "maskPath": mask_path,
            "startOffset": start,
            "endOffset": cursor,
        })

    controller_path, cursor = _read_i64(data, cursor, "controllerPath")
    return {
        "startOffset": 1,
        "endOffset": cursor,
        "fieldOrder": list(ANIMATION_CONFIG_PREFIX_FIELDS),
        "maskNativeInputs": native["nativeInputs"],
        "fields": {
            "_fallbackMontages": None,
            "avatarBlendProfilePath": avatar_blend_profile_path,
            "bakedBindingPath": baked_binding_path,
            "boneWeightMasks": {
                "status": "null" if mask_count is None else "present",
                "count": mask_count,
                "rows": masks,
            },
            "controllerPath": controller_path,
        },
    }


def frame_animation_config(data: bytes, *, strings: StringPool | None = None, game_root=None) -> dict[str, Any]:
    """Stop at the current native-proved controllerPath boundary for every profile."""
    if not data or data[0] != 15:
        raise AnimationConfigFramingError("AnimationConfig member count: expected=15 actual=" + str(data[0] if data else None))
    prefix = _decode_named_prefix(data, strings=strings, game_root=game_root)
    end = prefix["endOffset"]
    return {
        "status": "partial_named_animation_config_frame", "schemaStatus": "partial",
        "serializedMemberCount": 15, "bytesConsumed": end, "prefix": prefix,
        "ranges": [{"startOffset": 0, "endOffset": end, "fields": list(ANIMATION_CONFIG_PREFIX_FIELDS)}],
        "opaqueRanges": [{"startOffset": end, "endOffset": len(data), "length": len(data)-end,
                          "reason": "remaining AnimationConfig fields require independent current source proof"}],
        "unreadFields": list(ANIMATION_CONFIG_FIELDS[5:]),
        "evidenceBoundary": "Conditional current native first-five-field prefix and pooled mask component only. The remaining bytes are opaque; montage/curve counts, whole schema, runtime selection and playback are unproved.",
    }
