"""Selected BuffData timeline-list ownership and null/empty suffix receipt.

The positive list still needs independent element boundaries.  This reader
only joins an empty or null list count to the following exact trigger tail.

Ownership comes entirely from the re-derived root contract
(``buff_root_no_positive_native``), validated first: its field 26 is the
``ReadPackable<List<TimelineActionData>>`` call (generic context, call target
and store into ``BuffData.timelineActions``), and the immediately following
members 27-29 are the ``BlackboardDouble`` ``triggerInterval`` read and the
two bool reads. This contract names those root members and the
BlackboardDouble child contract; it records no address of its own. The
validator requires the members to be adjacent and of the expected kinds and
types, and requires the BlackboardDouble contract to validate on the same
build.

On the empty branch the list consumes exactly its four-byte ``-1``/``0``
count; the trigger tail is then a pooled BlackboardDouble, two bytes and EOF.
The receipt removes the suffix-fallback blocker only when both native gates
and the cursor joins validate (``conditional``). Positive timeline bodies
keep a structural endpoint and their fallback-ownership blocker.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import TYPE_CHECKING, Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import native_validation_failure, read_reviewed_contract
from scripts.game_data.memorypack import buff_blackboard_double_native
from scripts.game_data.memorypack.core import CONTRACTS_DIR

if TYPE_CHECKING:
    from scripts.game_data.string_pool import StringPool


LABEL = "buffTimelineEmpty"
SCHEMA = "endfield.buff-timeline-empty-native-contract.v2"
CONTRACT_PATH = CONTRACTS_DIR / "buff_timeline_empty_native.json"
ROOT_CONTRACT_PATH = CONTRACTS_DIR / "buff_root_no_positive_native.json"
CHILD_CONTRACT_PATH = buff_blackboard_double_native.CONTRACT_PATH
TAIL_KINDS = ("list", "object", "bool", "bool")


def _contract() -> dict[str, Any]:
    value = read_reviewed_contract(
        CONTRACT_PATH, schema=SCHEMA, status="exact-current-build", label=LABEL
    )[0]
    if value.get("reviewedDependencies") != [ROOT_CONTRACT_PATH.name, CHILD_CONTRACT_PATH.name]:
        raise ValueError(f"{LABEL}.contract:dependency-list")
    return value


def _check_root_tail(contract: dict[str, Any], root: dict[str, Any],
                     child: dict[str, Any]) -> None:
    """Require timeline, trigger and the two bools to be the root's last four members."""
    names = [contract["timelineField"], contract["followingField"], *contract["tailBoolFields"]]
    tail = root["fields"][-4:]
    if (root["ownerType"] != contract["ownerType"] or len(root["fields"]) != root["rootMemberCount"]
            or [row["name"] for row in tail] != names
            or [row["source"]["kind"] for row in tail] != list(TAIL_KINDS)):
        raise ValueError(f"{LABEL}.native:root-tail-members")
    timeline, trigger = tail[0], tail[1]
    if (timeline["declaredType"] != contract["timelineFieldType"]
            or timeline["source"]["context"]["argumentType"] != contract["timelineFieldType"]):
        raise ValueError(f"{LABEL}.native:timeline-type")
    if (trigger["declaredType"] != contract["followingFieldType"]
            or trigger["source"]["context"]["argumentType"] != contract["followingFieldType"]
            or child["wrappedType"] != contract["followingFieldType"]):
        raise ValueError(f"{LABEL}.native:trigger-type")
    if {k: v.upper() for k, v in root["nativeInputs"].items()} != \
            {k: v.upper() for k, v in contract["nativeInputs"].items()} or \
            {k: v.upper() for k, v in child["nativeInputs"].items()} != \
            {k: v.upper() for k, v in contract["nativeInputs"].items()}:
        raise ValueError(f"{LABEL}.native:dependency-native-inputs")


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                     metadata: Path | None = None) -> dict[str, Any]:
    """Validate the root and BlackboardDouble contracts, then the tail-member join."""
    from scripts.game_data.memorypack import buff_root_no_positive_native
    try:
        contract = _contract()
        expected = contract["nativeInputs"]
        gate = check_installed_native_inputs(
            expected["GameAssembly.dll"], expected["global-metadata.dat"],
            gameassembly=gameassembly, metadata=metadata,
        )
        if gate.status != "validated":
            return {"status": gate.status, "nativeStatus": gate.status, "detail": gate.detail,
                    "evidenceBoundary": "No named timeline list on missing or changed native inputs."}
        for name, module in (("root", buff_root_no_positive_native),
                             ("blackboardDouble", buff_blackboard_double_native)):
            result = module.validate_current_native_contract(
                gameassembly=gate.gameassembly, metadata=gate.metadata)
            if result.get("status") != "validated":
                return {"status": result.get("status", "invalid"),
                        "nativeStatus": result.get("status"), "detail": f"{name}: {result.get('detail')}"}
        _check_root_tail(contract, buff_root_no_positive_native._contract(),
                         buff_blackboard_double_native._contract())
        return {"status": "validated", "nativeStatus": "validated",
                "nativeInputs": expected, "field": contract["timelineField"],
                "evidenceBoundary": contract["evidenceBoundary"]}
    except (ValueError, KeyError, IndexError, TypeError, OSError) as error:
        return native_validation_failure(error, label=LABEL, source_path=CONTRACT_PATH)


def _bool(data: bytes, offset: int, name: str) -> dict[str, Any]:
    if offset >= len(data):
        raise ValueError(f"{LABEL}.{name}:truncated")
    if data[offset] not in (0, 1):
        raise ValueError(f"{LABEL}.{name}:invalid-bool={data[offset]}")
    return {"name": name, "start": offset, "end": offset + 1, "value": bool(data[offset])}


def decode_empty_timeline_suffix(
    data: bytes, count_start: int, *, native_validation: dict[str, Any],
    strings: "StringPool | None" = None,
) -> dict[str, Any]:
    """Require a null/zero list and the immediate exact pooled trigger tail to EOF."""
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:unvalidated")
    if type(count_start) is not int or not 0 <= count_start <= len(data) - 4:
        raise ValueError(f"{LABEL}.boundary:invalid-count-start={count_start!r}")
    count = struct.unpack_from("<i", data, count_start)[0]
    if count not in (-1, 0):
        raise ValueError(f"{LABEL}.count:positive-or-invalid={count}")
    trigger_start = count_start + 4
    trigger = buff_blackboard_double_native.decode_blackboard_double(
        data, trigger_start, strings=strings, label=f"{LABEL}.triggerInterval")
    use_time_dilation = _bool(data, trigger["consumedEnd"], "useTimeDilationDt")
    wait_first = _bool(data, use_time_dilation["end"], "waitFirstTriggerInterval")
    end = wait_first["end"]
    if end != len(data):
        raise ValueError(f"{LABEL}.tail-not-exact={end:#x}")
    return {
        "status": "exact-null-or-empty-list-to-eof",
        "startOffset": count_start, "consumedEnd": trigger_start,
        "count": count, "representation": "null" if count == -1 else "empty",
        "followingField": "triggerInterval",
        "followingStart": trigger_start,
        "followingEnd": end,
        "triggerInterval": trigger,
        "useTimeDilationDt": use_time_dilation["value"],
        "waitFirstTriggerInterval": wait_first["value"],
        "wholeTimelineListExact": True,
        "positiveTimelineInteriorExact": False,
    }
