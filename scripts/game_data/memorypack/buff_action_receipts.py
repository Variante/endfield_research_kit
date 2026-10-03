"""Shared selected-native gates and exact-span Buff action receipt replay.

The action adapters own their reviewed read/setter layouts. This module selects
those adapters and authenticates the explicitly selected installed inputs; it
does not publish a corpus or promote nested profiles to a complete Buff schema.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
from typing import Any

from scripts.common import GLOBAL_METADATA_REL, resolve_installed_native_inputs, sha256_file_upper
from scripts.game_data.memorypack import (
    buff_compare_float_action_receipt as compare_float,
    buff_create_buff_action_receipt as create_buff,
    buff_effect_action_receipt as effect_action,
    buff_finish_buff_advanced_action_receipt as finish_buff,
    buff_if_else_action_receipt as if_else,
    buff_modify_dynamic_blackboard_action_receipt as modify_blackboard,
    buff_raise_train_level_event_receipt as raise_train,
    buff_set_super_armor_action_receipt as set_super_armor,
)


ACTION_DECODERS = {
    compare_float.TAG: compare_float.decode_compare_float_action_receipt,
    create_buff.TAG: create_buff.decode_create_buff_action_receipt,
    effect_action.TAG: effect_action.decode_effect_action_receipt,
    finish_buff.TAG: finish_buff.decode_finish_buff_advanced_action_receipt,
    if_else.TAG: if_else.decode_if_else_action_receipt,
    modify_blackboard.TAG: modify_blackboard.decode_modify_dynamic_blackboard_action_receipt,
    raise_train.TAG: raise_train.decode_raise_train_level_event_receipt,
    set_super_armor.TAG: set_super_armor.decode_set_super_armor_action_receipt,
}
_NATIVE_VALIDATORS = {
    module.TAG: module.validate_current_native_contract
    for module in (compare_float, create_buff, effect_action, finish_buff,
                   if_else, modify_blackboard, raise_train, set_super_armor)
}


def _fail(check: str, *, source: str = "", detail: str = "") -> None:
    raise ValueError(f"buffActionReceipts:{check}:source={source}; {detail}")


@contextmanager
def _selected_game_root(game_root: Path):
    root = Path(game_root).resolve()
    assembly = root.parent / "GameAssembly.dll"
    metadata = root / GLOBAL_METADATA_REL
    unityplayer = root.parent / "UnityPlayer.dll"
    if not all(path.is_file() for path in (assembly, metadata, unityplayer)):
        _fail("selected-native-input-missing", detail=str(root))
    old = os.environ.get("ENDFIELD_GAME_ROOT")
    # Existing domain validators resolve their inputs through the common gate.
    # Bind that resolver to this selection and verify its paths before any call.
    os.environ["ENDFIELD_GAME_ROOT"] = str(root)
    try:
        actual_assembly, actual_metadata = resolve_installed_native_inputs()
        if actual_assembly.resolve() != assembly or actual_metadata.resolve() != metadata:
            _fail("selected-native-path-drift", detail=str(root))
        yield {"GameAssembly.dll": assembly, "global-metadata.dat": metadata,
               "UnityPlayer.dll": unityplayer}
    finally:
        if old is None:
            os.environ.pop("ENDFIELD_GAME_ROOT", None)
        else:
            os.environ["ENDFIELD_GAME_ROOT"] = old


def validate_selected_native(game_root: Path) -> dict[int, dict[str, Any]]:
    """Run every domain gate and recheck each pin against the selected paths.

    Each adapter retains its own pin shape: some prove the IL2CPP pair, while
    others also pin UnityPlayer. No shared catalog substitutes for a route gate.
    """
    with _selected_game_root(game_root) as paths:
        validations = {tag: validator() for tag, validator in _NATIVE_VALIDATORS.items()}
        for tag, validation in validations.items():
            if validation.get("status") != "validated" or validation.get("unionTag") != tag:
                _fail("native-gate", detail=f"tag=0x{tag:04X}")
            inputs = validation.get("nativeInputs")
            if not isinstance(inputs, dict) or not {
                "GameAssembly.dll", "global-metadata.dat",
            }.issubset(inputs):
                _fail("native-input-shape", detail=f"tag=0x{tag:04X}")
            for name, expected in inputs.items():
                if name not in paths or sha256_file_upper(paths[name]) != expected:
                    _fail("selected-native-hash-drift", detail=f"tag=0x{tag:04X} {name}")
        return validations


def selected_candidate(row: dict[str, Any], source: str) -> dict[str, Any]:
    """Require the unique corpus candidate whose reader reached physical EOF."""
    candidates = row.get("candidates")
    selected = [candidate for candidate in candidates or []
                if candidate.get("readerAcceptedThroughEof") is True]
    if row.get("candidateCount") != 1 or len(selected) != 1:
        _fail("candidate-identity", source=source, detail="requires one accepted EOF candidate")
    return selected[0]


def certified_action_spans(
    candidate: dict[str, Any], *, source: str, length: int,
) -> list[dict[str, int]]:
    """Retain exact union intervals from the authenticated corpus candidate."""
    records: list[dict[str, int]] = []
    seen: set[tuple[int, int, int]] = set()
    for profile_name in ("currentEventPrefix", "currentRootContinuation"):
        profile = candidate[profile_name]
        for row in profile.get("completedRecords", []):
            if row.get("kind") != "union":
                continue
            start, end, tag = row.get("start"), row.get("end"), row.get("tag")
            if (
                type(start) is not int or type(end) is not int or type(tag) is not int
                or not 0 <= start < end <= length
            ):
                _fail("union-range", source=source, detail=str((start, end, tag)))
            identity = (start, end, tag)
            if identity in seen:
                _fail("duplicate-union", source=source, detail=str(identity))
            seen.add(identity)
            records.append({"start": start, "end": end, "tag": tag})
    return sorted(records, key=lambda row: (row["start"], row["end"], row["tag"]))


def replay_action_receipt(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    tag: int, native_validation: dict[str, Any],
    certified_spans: list[dict[str, int]],
) -> dict[str, Any]:
    """Replay one selected action; supplied certification never names its fields."""
    if type(tag) is not int:
        _fail("unsupported-action", source=source, detail=str(tag))
    decoder = ACTION_DECODERS.get(tag)
    if decoder is None:
        _fail("unsupported-action", source=source, detail=str(tag))
    if {"start": start, "end": end, "tag": tag} not in certified_spans:
        _fail("action-not-certified", source=source, detail=str((start, end, tag)))
    kwargs = {"certified_action_spans": certified_spans} if tag == if_else.TAG else {}
    return decoder(
        data, source=source, logical_sha256=logical_sha256, start=start, end=end,
        native_validation=native_validation, **kwargs,
    )
