"""Exact current-build reader for BuffData's nested ``iconConfig`` field."""
from __future__ import annotations

import struct
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_pinned_contract
from scripts.game_data.memorypack.core import CONTRACTS_DIR


CONTRACT_PATH = CONTRACTS_DIR / "buff_icon_config_native.json"
LABEL = "buffIconConfig"
CONTRACT_SHA256 = "D4984B74DC1D02CC93091EE4130F572AD89CD45F86C19997B3B6D369C9278359"


def _contract() -> dict[str, Any]:
    value, _digest = read_pinned_contract(
        CONTRACT_PATH, sha256=CONTRACT_SHA256, schema="endfield.buff-icon-config-native-contract.v1", label=LABEL
    )
    return value


def validate_current_native_contract() -> dict[str, Any]:
    """Recheck method identities, registered pointers, and exact code extents."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    image = open_native_image(gate.gameassembly, gate.metadata)
    if image.code_registration != contract["codeRegistrationVa"]:
        raise ValueError(f"{LABEL}.native:code-registration={image.code_registration:#x}")
    validated_methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    for wrapper in contract["wrappers"]:
        owner = image.metadata.types[wrapper["typeDefinition"]]
        if image.metadata.type_full_name(owner) != wrapper["typeName"]:
            raise ValueError(f"{LABEL}.native:wrapper-type={wrapper['typeDefinition']}")
        if image.setter_methods(owner, label=LABEL) != wrapper["setterMethods"]:
            raise ValueError(f"{LABEL}.native:setter-order={wrapper['typeName']}")
    return {
        "status": "validated",
        "methodIndices": validated_methods,
        "nativeInputs": contract["nativeInputs"],
        "inputSetSha256": contract["inputSetSha256"],
    }


def decode_icon_config(
    data: bytes,
    start: int,
    limit: int,
    *,
    input_set_sha256: str,
) -> dict[str, Any]:
    """Decode exactly one BuffIconConfig wrapper ending at ``limit``.

    The caller supplies an independently selected following-field boundary.
    Contract and input-set mismatches fail closed before any field is named.
    """
    contract = _contract()
    if input_set_sha256.upper() != contract["inputSetSha256"]:
        raise ValueError("buffIconConfig.input-set:mismatch")
    if type(start) is not int or type(limit) is not int or not 0 <= start < limit <= len(data):
        raise ValueError(f"buffIconConfig.boundary:invalid start={start} limit={limit}")

    offset = start
    member_count = data[offset]
    offset += 1
    if member_count == 0xFF:
        if offset != limit:
            raise ValueError("buffIconConfig.null:trailing-bytes")
        return {
            "status": "exact-null",
            "startOffset": start,
            "consumedEnd": offset,
            "memberCount": None,
            "isNull": True,
            "fields": [],
            "wholeValueExact": True,
        }
    if member_count != 19:
        raise ValueError(f"buffIconConfig.member-count:{member_count}")

    fields: list[dict[str, Any]] = []

    def need(size: int, name: str) -> None:
        if offset + size > limit:
            raise ValueError(f"buffIconConfig.{name}:truncated")

    def field(name: str, field_start: int, value: Any, **extra: Any) -> None:
        fields.append({
            "name": name,
            "start": field_start,
            "end": offset,
            "value": value,
            "boundaryClass": "exact-cursor",
            **extra,
        })

    field_start = offset
    need(12, "orderPriorityConfig")
    use_directory_raw = data[offset]
    if use_directory_raw not in (0, 1):
        raise ValueError(f"buffIconConfig.orderPriorityConfig.useDirectoryValue:{use_directory_raw}")
    reserved = data[offset + 1 : offset + 4]
    priority_value = struct.unpack_from("<i", data, offset + 4)[0]
    priority_enum = struct.unpack_from("<I", data, offset + 8)[0]
    offset += 12
    field(
        "orderPriorityConfig",
        field_start,
        {
            "useDirectoryValue": bool(use_directory_raw),
            "reservedPaddingHex": reserved.hex().upper(),
            "priorityValue": priority_value,
            "priorityEnumRaw": priority_enum,
        },
        representation="direct current reader raw12 native-value layout",
    )

    field_start = offset
    need(4, "spritePath.length")
    string_length = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if string_length == 0xFFFFFFFF:
        sprite_path = None
    else:
        if string_length > 16_384:
            raise ValueError(f"buffIconConfig.spritePath.length:{string_length}")
        need(string_length, "spritePath.bytes")
        try:
            sprite_path = data[offset : offset + string_length].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("buffIconConfig.spritePath:utf8") from exc
        offset += string_length
    field("spritePath", field_start, sprite_path, byteLength=None if sprite_path is None else string_length)

    def read_u32(name: str) -> None:
        nonlocal offset
        field_start = offset
        need(4, name)
        value = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        field(name, field_start, value)

    def read_bool(name: str) -> None:
        nonlocal offset
        field_start = offset
        need(1, name)
        raw = data[offset]
        if raw not in (0, 1):
            raise ValueError(f"buffIconConfig.{name}:bool={raw}")
        offset += 1
        field(name, field_start, bool(raw))

    read_u32("abnormalColorType")
    read_bool("blinkInMainCharHpBar")
    read_u32("charHpBarVfxType")
    read_bool("forceRaiseIconEvent")
    read_bool("hasCharHpBarVfxType")
    read_u32("iconStyleInSquad")
    for name in (
        "onlyShowForMainCharacter",
        "playStrongInAnimation",
        "showDirectlyInHeadBuff",
        "showInHeadBarAttached",
        "showInHeadBarCommon",
        "showInSquadIcon",
        "showProgressInHpBar",
        "showProgressInNormalSkillButton",
        "showProgressInUltimateSkillButton",
        "showWarningBackground",
        "useWeakProgressInNormalSkillButton",
    ):
        read_bool(name)
    if offset != limit:
        raise ValueError(f"buffIconConfig.eof:expected={limit} actual={offset}")
    if [row["name"] for row in fields] != contract["selectedReadOrder"]:
        raise ValueError("buffIconConfig.contract:read-order-mismatch")
    return {
        "status": "exact",
        "startOffset": start,
        "consumedEnd": offset,
        "memberCount": member_count,
        "isNull": False,
        "fields": fields,
        "wholeValueExact": True,
        "fieldOrderSource": "current generated setter order plus selected native source reads",
    }
