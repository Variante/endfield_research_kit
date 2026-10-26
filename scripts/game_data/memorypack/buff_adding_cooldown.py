"""Selected-build ownership and bounded child spans for BuffData field one.

The selected root contract (``buff_root_no_positive_native.json``) proves
that the root reader's ``ReadValue`` call with the
``Beyond.Blackboard+BlackboardDouble`` method-spec context stores its result
in ``BuffData.addingCooldown`` (``exact`` source-to-field join). The child's
own reader is proved by ``buff_blackboard_double_native``: a one-byte member
header (``FF`` null or ``03``), the ``blackboardKey`` pooled Int32 index, the
``useBlackboardKey`` byte and four ``value`` Single bytes, in the generated
base-wrapper setter order. This module joins the two and names the spans;
both owning contracts are validated on the selected build, so the
ownership contract carries no native address of its own.

The same child decoder is reused for ``duration``, ``triggerInterval`` and
by ``buff_blackboard_double_child_receipt``. The boolean byte and value bits
stay raw: no live provider choice, blackboard lookup or evaluated cooldown
is proved; a key resolves to text only when the caller passes the export's
own ``StringPool``.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import native_validation_failure, read_reviewed_contract
from scripts.game_data.memorypack import buff_blackboard_double_native

if TYPE_CHECKING:
    from scripts.game_data.string_pool import StringPool


CONTRACT_PATH = CONTRACTS_DIR / "buff_adding_cooldown_ownership_native.json"
ROOT_CONTRACT_PATH = CONTRACTS_DIR / "buff_root_no_positive_native.json"
CHILD_CONTRACT_PATH = buff_blackboard_double_native.CONTRACT_PATH
SCHEMA = "endfield.buff-adding-cooldown-ownership-native-contract.v2"
LABEL = "buffAddingCooldown"


def _contract() -> dict[str, Any]:
    value, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema=SCHEMA, status="exact-current-build", label=LABEL
    )
    if value.get("reviewedDependencies") != [ROOT_CONTRACT_PATH.name, CHILD_CONTRACT_PATH.name]:
        raise ValueError(f"{LABEL}.contract:dependency-list")
    return value


def _same_inputs(left: dict[str, str], right: dict[str, str]) -> bool:
    return {k: v.upper() for k, v in left.items()} == {k: v.upper() for k, v in right.items()}


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                     metadata: Path | None = None) -> dict[str, Any]:
    """Join the root field store to the separately proved BlackboardDouble reader."""
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
                    "evidenceBoundary": "No named child fields on missing or mismatched native inputs."}
        root = buff_root_no_positive_native.validate_current_native_contract(
            gameassembly=gate.gameassembly, metadata=gate.metadata)
        child = buff_blackboard_double_native.validate_current_native_contract(
            gameassembly=gate.gameassembly, metadata=gate.metadata)
        for name, result in (("root", root), ("blackboardDouble", child)):
            if result.get("status") != "validated":
                return {"status": result.get("status", "invalid"), "nativeStatus": result.get("status"),
                        "detail": f"{name}: {result.get('detail')}"}
        root_contract = buff_root_no_positive_native._contract()
        child_contract = buff_blackboard_double_native._contract()
        if not all(_same_inputs(other["nativeInputs"], expected)
                   for other in (root_contract, child_contract)):
            raise ValueError(f"{LABEL}.native:dependency-native-inputs")
        field = root_contract["fields"][contract["rootFieldIndex"]]
        owner, _, owner_field = contract["destinationField"].partition("::")
        if (owner != root_contract["ownerType"] or field["name"] != owner_field
                or field["source"]["kind"] != "object"
                or field["source"]["context"]["argumentType"] != contract["rootContextType"]
                or contract["rootContextType"] != child_contract["wrappedType"]):
            raise ValueError(f"{LABEL}.native:root-field-join")
        order = [row[1].removeprefix("set___").removesuffix("__")
                 for row in child_contract["setterMethods"]]
        if order != contract["selectedReadOrder"]:
            raise ValueError(f"{LABEL}.native:child-read-order")
        return {
            "status": "validated",
            "nativeStatus": "validated",
            "sourceStoreValidated": True,
            "rootField": contract["destinationField"],
            "selectedReadOrder": contract["selectedReadOrder"],
            "wire": child_contract["wire"],
            "evidenceBoundary": contract["evidenceBoundary"],
        }
    except (ValueError, KeyError, IndexError, TypeError, OSError) as error:
        return native_validation_failure(error, label=LABEL, source_path=CONTRACT_PATH)


def decode_adding_cooldown(
    data: bytes, start: int, end: int, *, native_validation: dict[str, Any],
    strings: "StringPool | None" = None,
) -> dict[str, Any]:
    """Name child spans while preserving raw values and nullable wire states."""
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:unvalidated")
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data):
        raise ValueError(f"{LABEL}.boundary:invalid")
    child = buff_blackboard_double_native.decode_blackboard_double(
        data, start, end, strings=strings, label=LABEL)
    child["fieldOrderSource"] = "selected native BlackboardDouble reader joined to the root field store"
    return child
