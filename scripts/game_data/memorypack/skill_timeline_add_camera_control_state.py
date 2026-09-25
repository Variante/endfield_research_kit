"""Current-build SkillData action 0x019E using the reviewed BuffData reader.

The Buff reader already owns this exact 23-member framing.  This module only
admits its selected union route to SkillData after checking that both the
route identity and the existing reader's source contract still describe the
installed native image.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineAddCameraControlState"
TAG = 0x019E
MEMBER_COUNT = 23
WRAPPER_NAME = (
    "Beyond.MemoryPack.Beyond_Gameplay_View_AddCameraControlStateAction_"
    "AddCameraControlStateActionDataForMemoryPack"
)
SOURCE_PATH = CONTRACTS_DIR / "buff_19e_native.json"
SHARED_PATH = CONTRACTS_DIR / "skill_timeline_shared_sequence_native.json"
READ_ORDER = (
    "byte", "scalar32", "scalar32", "scalar32", "curve-profile",
    "scalar32", "raw4", "curve-profile", "scalar32", "raw4", "raw4",
    "raw4", "byte-payload", "byte", "byte", "byte-payload",
    "nullable-byte-payload-list", "byte", "byte", "byte", "byte", "byte",
    "byte",
)


def _source_contract() -> dict[str, Any]:
    source = json.loads(SOURCE_PATH.read_bytes())
    methods = source.get("methods")
    if (
        source.get("schemaVersion") != 1
        or tuple(source.get("anonymousReadOrder", {}).get("member23", ()))
        != READ_ORDER
        or not isinstance(methods, list)
        or len(methods) != 2
        or not any(row[1] == WRAPPER_NAME and row[2] == "Deserialize" for row in methods)
        or not any(row[1] == WRAPPER_NAME + "+" + WRAPPER_NAME.rsplit(".", 1)[-1] + "Formatter"
                   and row[2] == "Deserialize" for row in methods)
        or not isinstance(source.get("codeWindows"), list)
        or len(source["codeWindows"]) < 2
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return source


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the selected dispatcher and complete existing read body."""
    source = _source_contract()
    shared = json.loads(SHARED_PATH.read_bytes())
    expected = shared.get("nativeInputs", {})
    if (
        shared.get("schema") != "endfield.skill-timeline-shared-sequence-native-contract.v2"
        or not all(expected.get(key) for key in (
            "gameassemblySha256", "globalMetadataSha256", "unityplayerSha256"
        ))
    ):
        raise ValueError(f"{LABEL}.contract:selected-build")
    gate = check_installed_native_inputs(
        expected["gameassemblySha256"], expected["globalMetadataSha256"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if (
        not unityplayer.is_file()
        or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper()
        != expected["unityplayerSha256"]
    ):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    method_indices = [image.validate_method_row(row, label=LABEL) for row in source["methods"]]
    image.check_windows(source["codeWindows"], label=LABEL)
    from scripts.game_data.memorypack.derived_schema import resolve_routes

    routes, _resolver, audit = resolve_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata
    )
    route = routes.get(TAG, {})
    if (
        audit.get("status") != "validated"
        or route.get("status") != "determined"
        or route.get("evidenceTier") != "direct"
        or route.get("wrapperName") != WRAPPER_NAME
    ):
        raise ValueError(f"{LABEL}.native:dispatcher-route-drift")
    return {
        "status": "validated", "unionTag": TAG, "memberCount": MEMBER_COUNT,
        "sourceContract": SOURCE_PATH.name, "nativeInputs": expected,
        "methodIndices": method_indices,
    }


def decode_add_camera_control_state_action(
    reader: Reader, depth: int, tag: int, width: int
) -> None:
    """Consume one selected Skill action through the already finite Buff reader."""
    _source_contract()
    if tag != TAG or width != 3:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    # The base reader owns all nested bounds, null markers and the 23-member
    # source order.  A new Skill-local copy would weaken that single owner.
    Reader._action(reader, depth, tag, width)
