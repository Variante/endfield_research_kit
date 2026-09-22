"""Current-build BuffData action additions kept outside frozen SkillData readers."""
from __future__ import annotations

import copy
import struct
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_pinned_contract
from scripts.game_data.memorypack.core import CONTRACTS_DIR

from scripts.game_data.memorypack.buff import frame_buff_named_middle as _base_named_middle
from scripts.game_data.memorypack.buff_icon_config import decode_icon_config
from scripts.game_data.memorypack.buff_actions import (
    FrameError,
    Reader as _BaseReader,
    Unsupported,
    root_continuation as _base_root_continuation,
)
from scripts.game_data import buff_frontiers_native as buff_frontiers


CONTRACT_PATH = CONTRACTS_DIR / "buff_residual_actions_native.json"
LABEL = "buffResidualActions"
CONTRACT_SHA256 = "67C1567CF9BC244D8212DA2359BABBF55ABAC02F7A0DEB8AFA63D672AEE39819"


def _contract() -> dict[str, Any]:
    value, _digest = read_pinned_contract(
        CONTRACT_PATH, sha256=CONTRACT_SHA256, schema="endfield.buff-residual-action-native-contract.v1", label=LABEL
    )
    return value


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the supplemental rows against the installed exact build."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    image = open_native_image(gate.gameassembly, gate.metadata)
    validated = []
    for action in contract["actions"]:
        image.validate_dispatcher(action, label=LABEL)
        for row in action["methods"]:
            image.validate_method_row(row, label=LABEL)
        image.check_windows(action["codeWindows"], label=LABEL)
        for context in action.get("nestedContextUsage", []):
            image.nested_usage_cell(context, label=LABEL)
        validated.append(action["unionTag"])
    return {"status": "validated", "unionTags": validated, "nativeInputs": contract["nativeInputs"]}


class _ResidualReader(_BaseReader):
    """Add only union routes proved by the adjacent exact-build contract."""

    def gait_multiplier_map(self) -> None:
        """Read SerializeFieldDictionary<GroundedMoveGait, float>."""
        start = self.pos
        if self.peek() == 0xFF:
            self.take(1, "null-gait-multiplier-map")
        else:
            self.header(1)
            for _ in range(self.count(8)):
                self.take(4, "anonymous-grounded-move-gait")
                self.take(4, "anonymous-float32")
        self.records.append({
            "start": start,
            "end": self.pos,
            "kind": "anonymous-gait-multiplier-map",
        })

    def string_list(self, *, reserve: int = 0) -> None:
        """Read a nullable direct List<string> with bounded element payloads."""
        start = self.pos
        count = self.count(4, reserve=reserve, nullable=True)
        for _ in range(max(0, count)):
            self.byte_payload()
        self.records.append({
            "start": start,
            "end": self.pos,
            "kind": "anonymous-string-list",
        })

    def attribute_override_list(self) -> None:
        """Read List<OverrideRawAttributeAction.AttributeOverrideEntry>."""
        start = self.pos
        for _ in range(max(0, self.count(1, nullable=True))):
            if self.peek() == 0xFF:
                self.take(1, "null-attribute-override")
            else:
                self.header(2)
                self.take(4, "anonymous-enum32")
                self.scalar_payload()
        self.records.append({
            "start": start,
            "end": self.pos,
            "kind": "anonymous-attribute-override-list",
        })

    def buff_id_list(self, *, reserve: int = 0) -> None:
        """Read List<BuffId>, retaining the nested one-member wrapper."""
        start = self.pos
        for _ in range(max(0, self.count(1, reserve=reserve, nullable=True))):
            if self.peek() == 0xFF:
                self.take(1, "null-buff-id")
            else:
                self.header(1)
                self.byte_payload()
        self.records.append({
            "start": start,
            "end": self.pos,
            "kind": "anonymous-buff-id-list",
        })

    def teleport_fix_distance_profile(self) -> None:
        start = self.pos
        if self.peek() == 0xFF:
            self.take(1, "null-teleport-fix-distance")
        else:
            self.header(3)
            self.scalar_payload()
            self.take(1, "anonymous-byte")
            self.take(1, "anonymous-byte")
        self.records.append({"start": start, "end": self.pos, "kind": "anonymous-teleport-fix-distance"})

    def teleport_ranged_profile(self) -> None:
        start = self.pos
        if self.peek() == 0xFF:
            self.take(1, "null-teleport-ranged")
        else:
            self.header(1)
            self.scalar_payload()
        self.records.append({"start": start, "end": self.pos, "kind": "anonymous-teleport-ranged"})

    def create_buff_input_profile(self) -> None:
        """Read the five-member CreateBuffActionInput derived wrapper."""
        start = self.pos
        if self.peek() == 0xFF:
            self.take(1, "null-create-buff-input")
        else:
            self.header(5)
            self.take(1, "anonymous-byte")
            for _ in range(max(0, self.count(1, reserve=5, nullable=True))):
                self.assignment_profile()
            self.byte_payload()
            self.byte_payload()
            self.take(1, "anonymous-byte")
        self.records.append({"start": start, "end": self.pos, "kind": "anonymous-create-buff-input"})

    def smart_target_select_profile(self) -> None:
        """Read the four-member SmartTargetSelectSetting value wrapper."""
        start = self.pos
        if self.peek() == 0xFF:
            self.take(1, "null-smart-target-select")
        else:
            self.header(4)
            self.finder_profile()
            self.buff_id_list(reserve=5)
            self.take(4, "anonymous-enum32")
            self.query_profile()
        self.records.append({"start": start, "end": self.pos, "kind": "anonymous-smart-target-select"})

    def blow_off_fields(self) -> None:
        """Read the ten serialized fields inherited by BlowOff-derived actions."""
        self.target_profile()
        self.scalar_payload()
        self.scalar_payload()
        self.take(4, "anonymous-enum32")
        self.direction_profile()
        self.scalar_payload()
        self.take(1, "anonymous-byte")
        self.take(1, "anonymous-byte")
        self.target_profile()
        self.scalar_payload()

    def _action(self, depth: int, tag: int, width: int) -> None:
        frontier9_counts = {
            0x1D: 14, 0x82: 12, 0x97: 17, 0xB5: 12, 0xB8: 9,
            0xBE: 15, 0xC8: 10, 0xD1: 9, 0xDD: 13, 0xE5: 10,
            0xE9: 4, 0x104: 12, 0x108: 6, 0x11B: 7, 0x141: 11,
            0x143: 11, 0x17D: 9, 0x17E: 8, 0x191: 11,
        }
        if tag in frontier9_counts:
            self.take(width, "union-tag")
            if self.peek() == 0xFF:
                self.take(1, "null-wrapper")
                return
            self.header(frontier9_counts[tag])
            self.take(1, "anonymous-nonzero-byte")
            for _ in range(3):
                self.take(4, "anonymous-scalar32")
            if tag == 0x1D:
                self.blow_off_fields()
            elif tag == 0x82:
                self.take(4, "anonymous-enum32")
                self.take(4, "anonymous-enum32")
                self.target_profile(); self.target_profile()
                self.take(4, "anonymous-enum32")
                self.target_profile(); self.target_profile(); self.scalar_payload()
            elif tag in (0x97, 0xBE):
                self.blow_off_fields()
                if tag == 0x97:
                    self.scalar_payload()
                    self.take(1, "anonymous-byte")
                self.take(4, "anonymous-float32")
            elif tag == 0xB5:
                self.target_profile(); self.target_profile(); self.take(1, "anonymous-byte")
                self.scalar_payload(); self.target_profile(); self.take(1, "anonymous-byte")
                self.take(1, "anonymous-byte"); self.query_profile()
            elif tag == 0xB8:
                for _ in range(3):
                    self.take(1, "anonymous-byte")
                self.byte_payload(); self.target_profile()
            elif tag == 0xC8:
                self.take(4, "anonymous-float32"); self.take(4, "anonymous-enum32")
                self.take(4, "anonymous-float32"); self.take(4, "anonymous-float32")
                self.take(4, "anonymous-int32"); self.target_profile()
            elif tag == 0xD1:
                self.take(1, "anonymous-byte"); self.take(4, "anonymous-enum32")
                self.take(8, "anonymous-vector2"); self.target_profile(); self.byte_payload()
            elif tag == 0xDD:
                self.take(4, "anonymous-enum32"); self.scalar_payload(); self.direction_profile()
                self.take(1, "anonymous-byte"); self.take(4, "anonymous-float32")
                self.take(1, "anonymous-byte"); self.take(4, "anonymous-enum32")
                self.target_profile(); self.target_profile()
            elif tag == 0xE5:
                self.take(1, "anonymous-byte"); self.byte_payload(); self.take(1, "anonymous-byte")
                self.take(1, "anonymous-byte"); self.byte_payload(); self.take(1, "anonymous-byte")
            elif tag == 0xE9:
                pass
            elif tag == 0x104:
                self.take(4, "anonymous-enum32"); self.scalar_payload()
                self.take(4, "anonymous-enum32")
                for _ in range(3):
                    self.scalar_payload()
                self.target_profile(); self.target_profile()
            elif tag == 0x108:
                self.attribute_override_list(); self.target_profile()
            elif tag == 0x11B:
                self.buff_id_list(reserve=5); self.take(4, "anonymous-enum32"); self.query_profile()
            elif tag == 0x141:
                self.take(4, "anonymous-enum32"); self.target_profile(); self.target_profile()
                self.take(4, "anonymous-enum32"); self.target_profile(); self.target_profile()
                self.byte_payload()
            elif tag == 0x143:
                self.target_profile(); self.byte_payload(); self.curve_profile(); self.scalar_payload()
                self.take(1, "anonymous-byte"); self.target_profile(); self.take(1, "anonymous-byte")
            elif tag == 0x17D:
                self.byte_payload(); self.teleport_fix_distance_profile(); self.teleport_ranged_profile()
                self.target_profile(); self.take(4, "anonymous-enum32")
            elif tag == 0x17E:
                self.take(1, "anonymous-byte"); self.take(1, "anonymous-byte")
                self.take(4, "anonymous-float32"); self.target_profile()
            elif tag == 0x191:
                self.take(1, "anonymous-byte"); self.scalar_payload(); self.scalar_payload()
                self.create_buff_input_profile(); self.scalar_payload()
                self.smart_target_select_profile(); self.scalar_payload()
            return
        if (tag == 0xFF and width == 1) or tag not in (
            0x21, 0x29, 0x2A, 0x46, 0x6C, 0x9E, 0xD0, 0xD7,
            0xE4, 0xEE, 0xEF, 0xF5, 0x100, 0x10A, 0x111, 0x12F,
            0x130, 0x15F, 0x18D, 0xFF, 0x106, 0x109, 0x149, 0x162,
            0x170, 0x173, 0x195, 0x09, 0x14, 0x1E, 0x2D, 0x4D,
            0x5F, 0xAF, 0xC2, 0xD9, 0x107, 0x10D, 0x114,
        ):
            return super()._action(depth, tag, width)
        self.take(width, "union-tag")
        if self.peek() == 0xFF:
            self.take(1, "null-wrapper")
            return
        self.header(
            4 if tag in (0x1E, 0x10D, 0x21, 0x9E, 0xD0, 0x100, 0x130, 0x15F)
            else 9 if tag == 0x29
            else 16 if tag == 0x10A
            else 6 if tag == 0x6C
            else 6 if tag in (0x09, 0x14, 0xAF, 0xC2, 0xD9, 0x107,
                                  0xFF, 0x106, 0x109, 0x149, 0x162, 0x170, 0x173, 0x195)
            else 5 if tag in (0x2A, 0xD7, 0xE4, 0x111, 0x12F, 0x18D)
            else 7
        )
        self.take(1, "anonymous-nonzero-byte")
        for _ in range(3):
            self.take(4, "anonymous-scalar32")
        if tag in (0x1E, 0x10D):
            pass
        elif tag == 0x09:
            self.string_list(reserve=1)
            self.target_profile()
        elif tag == 0x14:
            self.sequence(depth)
            self.take(1, "anonymous-byte")
        elif tag == 0x2D:
            self.paired_payload()
            self.take(4, "anonymous-enum32")
            self.target_profile()
        elif tag == 0x4D:
            self.scalar_payload()
            self.scalar_payload()
            self.target_profile()
        elif tag == 0x5F:
            self.string_list(reserve=2)
            self.take(1, "anonymous-byte")
            self.take(1, "anonymous-byte")
        elif tag == 0xAF:
            self.target_profile()
            self.finder_profile()
        elif tag == 0xC2:
            self.byte_payload()
            self.take(4, "anonymous-float32")
        elif tag == 0xD9:
            self.sequence(depth)
            self.take(4, "anonymous-int32")
        elif tag == 0x107:
            self.scalar_payload()
            self.target_profile()
        elif tag == 0x114:
            self.byte_payload()
            self.scalar_payload()
            self.target_profile()
        elif tag == 0x29:
            self.gait_multiplier_map()
            self.take(4, "anonymous-float32")
            self.take(1, "anonymous-byte")
            self.gait_multiplier_map()
            self.gait_multiplier_map()
        elif tag == 0x2A:
            self.scalar_payload()
        elif tag == 0x46:
            self.take(4, "anonymous-scalar32")
            self.scalar_payload()
            self.target_profile()
        elif tag == 0x6C:
            self.target_profile()
            self.query_profile()
        elif tag in (0xD7, 0x111):
            self.target_profile()
        elif tag in (0xE4, 0x18D):
            self.take(1, "anonymous-byte")
        elif tag == 0xEE:
            self.scalar_payload()
            self.query_profile()
            self.take(1, "anonymous-byte")
        elif tag == 0xEF:
            self.query_profile()
            self.scalar_payload()
            self.take(1, "anonymous-byte")
        elif tag == 0xF5:
            self.target_profile()
            self.sequence(depth)
            self.scalar_payload()
        elif tag == 0x10A:
            for _ in range(7):
                self.scalar_payload()
            self.target_profile()
            for _ in range(3):
                self.take(1, "anonymous-nonzero-byte")
            self.scalar_payload()
        elif tag == 0x12F:
            self.byte_payload()
        elif tag == 0xFF:
            self.scalar_payload()
            self.target_profile()
        elif tag == 0x106:
            self.buff_input_profile()
            self.take(4, "anonymous-enum32")
        elif tag == 0x109:
            self.byte_payload()
            self.take(4, "anonymous-int32")
        elif tag == 0x149:
            self.take(8, "anonymous-int64")
            self.target_profile()
        elif tag == 0x162:
            self.byte_payload()
            self.byte_payload()
        elif tag == 0x170:
            self.take(4, "anonymous-enum32")
            self.byte_payload()
        elif tag == 0x173:
            self.byte_payload()
            self.target_profile()
        elif tag == 0x195:
            self.target_profile()
            self.byte_payload()


def root_continuation(
    data: bytes,
    *,
    source: str,
    start: int,
    input_set_sha256: str,
    limit: int | None = None,
) -> dict[str, Any]:
    """Retry the frozen root continuation with authenticated residual actions."""
    base = _base_root_continuation(data, source=source, start=start, limit=limit)
    contract = _contract()
    frontier_contracts = [buff_frontiers.reviewed_contract(name) for name in buff_frontiers.FRONTIERS]
    if (
        base.get("status") != "unsupported"
        or input_set_sha256.upper() != contract["inputSetSha256"]
        or any(
            input_set_sha256.upper() != frontier_contract["inputSetSha256"]
            for frontier_contract in frontier_contracts
        )
    ):
        return base

    reader = _ResidualReader(data, source, limit)
    if type(start) is not int or not 1 <= start <= reader.limit:
        raise FrameError(source, 0, "first-collection endpoint within read limit", start, "start-bounds")
    reader.pos = start
    status = "supported-prefix"
    diagnostic = None
    named_fields = []
    try:
        for index, name, read_field in (
            (1, "addingCooldown", reader.scalar_payload),
            (2, "applyTags", reader.raw_dword_array),
            (3, "attributeModifier", reader.modifier_collection_profile),
            (4, "blackboard", reader.data_pair_collection_profile),
            (5, "buffEventAction", reader.buff_action_map_collection_profile),
        ):
            field_start = reader.pos
            read_field()
            named_fields.append({
                "index": index,
                "name": name,
                "start": field_start,
                "end": reader.pos,
                "boundaryClass": "exact-cursor",
            })
    except Unsupported as exc:
        status, diagnostic = "unsupported", exc.diagnostic
    except FrameError as exc:
        status, diagnostic = "failed", exc.diagnostic
    cursor = start
    for span in reader.ranges:
        if span["start"] != cursor or not cursor < span["end"] <= reader.limit:
            raise FrameError(source, cursor, "contiguous bounded scalar ranges", span, "internal-range")
        cursor = span["end"]
    if cursor != reader.pos:
        raise FrameError(source, cursor, reader.pos, cursor, "internal-range")
    return {
        "status": status,
        "diagnostic": diagnostic,
        "startOffset": start,
        "consumedEnd": reader.pos,
        "readLimit": reader.limit,
        "ranges": reader.ranges,
        "completedRecords": reader.records,
        "namedFields": named_fields,
        "fieldOrderSource": "current generated BuffDataForMemoryPack setter order",
        "opaqueRemainderRange": [reader.pos, len(data)],
        "wholeSchemaExact": False,
        "evidenceLevel": "structural-only",
        "nativeResidualActionTags": [
            0x21, 0x29, 0x2A, 0x46, 0x6C, 0x9E, 0xD0, 0xD7,
            0xE4, 0xEE, 0xEF, 0xF5, 0x100, 0x10A, 0x111, 0x12F,
            0x130, 0x15F, 0x18D, 0xFF, 0x106, 0x109, 0x149, 0x162,
            0x170, 0x173, 0x195, 0x09, 0x14, 0x1E, 0x2D, 0x4D,
            0x5F, 0xAF, 0xC2, 0xD9, 0x107, 0x10D, 0x114,
            0x1D, 0x82, 0x97, 0xB5, 0xB8, 0xBE, 0xC8, 0xD1,
            0xDD, 0xE5, 0xE9, 0x104, 0x108, 0x11B, 0x141, 0x143,
            0x17D, 0x17E, 0x191,
        ],
        "nativeResidualContract": CONTRACT_PATH.name,
        "nativeFrontierContracts": {name: spec.file for name, spec in buff_frontiers.FRONTIERS.items()},
        "boundary": (
            "Selected root members 2-6 after the independently supported first collection. "
            "Supplemental action routes require the exact input-set contract; later bytes remain opaque."
        ),
    }


def _shift_offsets(value: Any, *, pivot: int, delta: int, key: str = "") -> Any:
    if isinstance(value, dict):
        return {k: _shift_offsets(v, pivot=pivot, delta=delta, key=k) for k, v in value.items()}
    if isinstance(value, list):
        return [_shift_offsets(v, pivot=pivot, delta=delta, key=key) for v in value]
    offset_keys = {"start", "end", "startOffset", "endOffset", "hardLimit", "consumedEnd", "readLimit"}
    if key in offset_keys and isinstance(value, int) and value >= pivot:
        return value + delta
    if key == "offset" and isinstance(value, str) and value.startswith("0x"):
        number = int(value, 16)
        return hex(number + delta) if number >= pivot else value
    return value


def frame_buff_named_middle(
    data: bytes,
    start: int,
    id_marker_offset: int,
    *,
    input_set_sha256: str,
) -> dict[str, Any]:
    """Close a middle containing an authenticated residual condition action."""
    base = _base_named_middle(data, start, id_marker_offset)
    if base.get("status") == "named-through-iconConfig":
        return _close_icon_config(
            base,
            data=data,
            id_marker_offset=id_marker_offset,
            input_set_sha256=input_set_sha256,
        )
    contracts = (
        (_contract(), CONTRACT_PATH.name),
        *((buff_frontiers.reviewed_contract(name), spec.file) for name, spec in buff_frontiers.FRONTIERS.items()),
    )
    expected_input = input_set_sha256.upper()
    if any(expected_input != contract["inputSetSha256"] for contract, _ in contracts):
        return base
    authenticated_tags = {
        action["unionTag"]
        for contract, _ in contracts
        for action in contract.get("actions", [])
    }

    reader = _ResidualReader(data, "BuffData.damageModifier", id_marker_offset)
    reader.pos = start
    try:
        count = reader.damage_modifier_collection_profile()
    except (ValueError, IndexError, struct.error):
        return base
    reached_residual_tags = sorted({
        row["tag"]
        for row in reader.records
        if row.get("kind") == "union" and row.get("tag") in authenticated_tags
    })
    if not reached_residual_tags:
        return base
    damage_end = reader.pos

    replacement = struct.pack("<i", 0)
    synthetic = data[:start] + replacement + data[damage_end:]
    synthetic_id = id_marker_offset - (damage_end - start) + len(replacement)
    framed = _base_named_middle(synthetic, start, synthetic_id)
    if framed.get("status") != "named-through-iconConfig" or framed.get("consumedEnd") != synthetic_id:
        return base

    delta = damage_end - start - len(replacement)
    recovered = _shift_offsets(copy.deepcopy(framed), pivot=start + len(replacement), delta=delta)
    fields = recovered.get("namedFields", [])
    if not fields or fields[0].get("name") != "damageModifier":
        return base
    fields[0].update({"start": start, "end": damage_end, "count": count, "isNull": count == -1})
    recovered.update({
        "consumedEnd": id_marker_offset,
        "hardLimit": id_marker_offset,
        "nativeResidualActionTags": reached_residual_tags,
        "nativeResidualContract": CONTRACT_PATH.name,
        "nativeResidualContracts": [name for _, name in contracts],
    })
    return _close_icon_config(
        recovered,
        data=data,
        id_marker_offset=id_marker_offset,
        input_set_sha256=input_set_sha256,
    )


def _close_icon_config(
    framed: dict[str, Any],
    *,
    data: bytes,
    id_marker_offset: int,
    input_set_sha256: str,
) -> dict[str, Any]:
    """Replace the old named opaque icon range with its exact nested cursor."""
    fields = framed.get("namedFields")
    if not isinstance(fields, list) or not fields or fields[-1].get("name") != "iconConfig":
        raise ValueError("buffIconConfig.integration:missing-field-14")
    icon_field = fields[-1]
    decoded = decode_icon_config(
        data,
        icon_field["start"],
        id_marker_offset,
        input_set_sha256=input_set_sha256,
    )
    icon_field.update({
        "end": decoded["consumedEnd"],
        "boundaryClass": "exact-cursor",
        "memberCount": decoded["memberCount"],
        "isNull": decoded["isNull"],
        "decoded": decoded,
    })
    framed["opaqueNestedRanges"] = []
    framed["iconConfigStatus"] = "exact"
    framed["iconConfigContract"] = "buff_icon_config_native.json"
    framed["boundary"] = (
        "Fields 6-14 advance exact cursors under the current generated wrapper order; "
        "the exact iconConfig cursor ends at the independently accepted id marker."
    )
    return framed
