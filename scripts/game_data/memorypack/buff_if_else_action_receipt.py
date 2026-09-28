"""Selected-build named wrapper receipt for BuffData IfElseAction (tag C9).

The Buff reader already closes this physical action anonymously. This adapter
attaches generated wrapper setter names to its eight source-ordered spans only
after authenticating the selected dispatcher, reader, generic child provider,
installed native build, logical file hash, and exact action end.

The selected dispatcher, complete source reader and three identical
``SequenceActionData`` MethodSpec callsites fix an eight-member read order
(``IF_ELSE_ACTION_READ_KINDS`` in ``buff_actions``); the generated wrapper
setters name the inherited action prefix, ``alwaysNext``,
``conditionAction``, ``failActions`` and ``succeedActions``. For each
authenticated corpus union span the adapter requires the selected
candidate's certified child union ranges, rechecks the three
SequenceActionData headers, counts and terminal booleans, and rejoins the
exact outer action end.

The standalone anonymous action reader stops at a reached ``0x0082`` child,
so it cannot independently replay every current ``0x00C9`` record; the
adapter therefore fails closed when a certified child range is absent or
mismatched. Nested union bodies stay at the corpus's existing structural or
derived tier. Neither this receipt nor the child ranges prove an evaluated
condition or runtime branch selection, and whole BuffData stays open.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import (
    IF_ELSE_ACTION_MEMBER_COUNT, IF_ELSE_ACTION_READ_KINDS,
    IF_ELSE_ACTION_TAG, SEQUENCE_RECURSION_LIMIT, Reader,
)
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "buffIfElseActionReceipt"
CONTRACT_PATH = CONTRACTS_DIR / "buff_if_else_action_receipt_native.json"
SCHEMA = "endfield.buff-if-else-action-receipt.v1"
TAG = IF_ELSE_ACTION_TAG


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.buff-if-else-action-receipt-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    return contract


@lru_cache(maxsize=1)
def _dependencies() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    contract = _contract()
    source = json.loads((CONTRACTS_DIR / contract["sourceContract"]).read_bytes())
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    provider = source[contract["sourceProvider"]]
    route = catalog["families"]["AbilityActionData"][TAG]
    wrapper = contract["wrapper"]
    reads = provider.get("orderedSourceReads")
    kinds = tuple(row.get("kind") for row in reads) if isinstance(reads, list) else ()
    setters = wrapper["inheritedSetterMethods"] + wrapper["setterMethods"]
    native_inputs = contract["nativeInputs"]
    if (
        source.get("schema") != "endfield.skill-timeline-shared-sequence-native-contract.v2"
        or source.get("status") != "exact-current-build-composite"
        or source.get("nativeInputs") != {
            "gameassemblySha256": native_inputs["GameAssembly.dll"],
            "globalMetadataSha256": native_inputs["global-metadata.dat"],
            "unityplayerSha256": native_inputs["UnityPlayer.dll"],
        }
        or provider.get("status") != "authenticated-static-provider-chain-with-exact-corpus-cursor"
        or provider.get("physicalTag") != "0x00C9"
        or provider.get("serializedMemberCount") != IF_ELSE_ACTION_MEMBER_COUNT
        or provider.get("wrapperName") != wrapper["typeName"]
        or provider.get("recursionLimit") != SEQUENCE_RECURSION_LIMIT
        or [row.get("memberIndex") for row in reads or []]
        != list(range(IF_ELSE_ACTION_MEMBER_COUNT))
        or kinds != IF_ELSE_ACTION_READ_KINDS
        or len(setters) != wrapper["serializedMemberCount"]
        or any(
            (kind == "anonymous-nonzero-byte" and setter[2] != "System.Boolean")
            or (kind == "anonymous-scalar32" and setter[2] not in (
                "System.Int32", "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority"))
            or (kind == "SequenceActionData" and setter[2]
                != "Beyond.Gameplay.Core.SequenceActionData")
            for setter, kind in zip(setters, kinds)
        )
        or catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or catalog["nativeInputs"]["gameAssemblySha256"] != native_inputs["GameAssembly.dll"]
        or catalog["nativeInputs"]["metadataSha256"] != native_inputs["global-metadata.dat"]
        or route["tag"] != TAG
        or route["wrapperName"] != wrapper["typeName"]
        or route["memberCount"] != wrapper["serializedMemberCount"]
        or route["wrappedType"] != "Beyond.Gameplay.Core.IfElseAction+IfElseActionData"
        or catalog["switches"]["AbilityActionData"]["entryCount"]
        != len(catalog["families"]["AbilityActionData"])
    ):
        raise ValueError(f"{LABEL}.contract:dependency-shape")
    return source, catalog, provider


def validate_current_native_contract() -> dict[str, Any]:
    """Prove one current selected dispatcher, wrapper, and nested provider."""
    contract = _contract()
    _source, _catalog, provider = _dependencies()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if (
        not unityplayer.is_file()
        or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper()
        != expected["UnityPlayer.dll"]
    ):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    source_route = provider["dispatcherRoute"]
    dispatcher = {
        **source_route,
        "usageCellRva": int(source_route["usageCellRva"], 16),
        "routeWindow": contract["routeWindow"],
    }
    image.validate_dispatcher(dispatcher, label=LABEL)
    for method in provider["methods"]:
        image.validate_method_row(method, label=LABEL)
    image.check_windows(provider["codeWindows"], label=LABEL)
    image.check_instruction_windows(provider["instructionWindows"], label=LABEL)

    method_spec = provider["nestedMethodSpec"]
    index = method_spec["index"]
    if not 0 <= index < image.registration["methodSpecsCount"]:
        raise ValueError(f"{LABEL}.native:method-spec-index")
    raw = image.pe.bytes_at_va(int(image.registration["methodSpecs"], 16) + index * 12, 12)
    if raw.hex().upper() != method_spec["rawHex"].upper():
        raise ValueError(f"{LABEL}.native:method-spec-raw")
    instantiation = image.instantiations.resolve(method_spec["methodInstantiationIndex"])
    if (
        image.type_name(method_spec["typeDefinition"]) != method_spec["typeName"]
        or len(instantiation.arguments) != 1
        or instantiation.arguments[0].raw_type_record_hex.upper()
        != method_spec["argumentTypeRawHex"].upper()
    ):
        raise ValueError(f"{LABEL}.native:sequence-instantiation")
    load_windows = {
        rva: instruction for rva, instruction in provider["instructionWindows"]
        if rva in method_spec["callsiteRvas"]
    }
    if set(load_windows) != set(method_spec["callsiteRvas"]):
        raise ValueError(f"{LABEL}.contract:sequence-callsites")
    for rva in method_spec["callsiteRvas"]:
        cell, usage = image.nested_usage_cell({
            "instructionRva": rva,
            "instructionHex": load_windows[rva],
            "cellRva": int(method_spec["usageCellRva"], 16),
            "usageRawHex": method_spec["usageRawHex"],
        }, label=LABEL)
        if method_spec_usage_index(
            usage, image.registration["methodSpecsCount"],
            source=str(gate.gameassembly), offset=cell,
        ) != index:
            raise ValueError(f"{LABEL}.native:sequence-method-spec")

    wrapper = contract["wrapper"]
    owner = image.check_wrapper_inheritance(wrapper, label=LABEL)
    parent = image.metadata.types[wrapper["parentTypeDefinition"]]
    if (
        image.setter_methods(parent, parameter="typeName", label=LABEL)
        != wrapper["inheritedSetterMethods"]
        or image.setter_methods(owner, parameter="typeName", label=LABEL)
        != wrapper["setterMethods"]
    ):
        raise ValueError(f"{LABEL}.native:setter-order")
    return {
        "status": "validated",
        "unionTag": TAG,
        "nativeInputs": expected,
        "memberCount": wrapper["serializedMemberCount"],
    }


def _field_name(setter: list[Any]) -> str:
    name = setter[1]
    if not name.startswith("set___") or not name.endswith("__"):
        raise ValueError(f"{LABEL}.contract:setter-name={name}")
    return name.removeprefix("set___").removesuffix("__")


def _read_sequence(
    reader: Reader,
    child_spans: dict[int, dict[str, int]],
) -> None:
    """Reparse one child envelope using independently closed union spans."""
    if reader.peek() != 3:
        raise ValueError(f"{LABEL}:sequence-member-count={reader.peek()}")
    reader.take(1, "sequence-header")
    count_start = reader.pos
    count = struct.unpack("<i", reader.take(4, "sequence-count"))[0]
    if not 0 <= count <= SEQUENCE_RECURSION_LIMIT:
        raise ValueError(f"{LABEL}:sequence-count={count}; offset={count_start}")
    for _ in range(count):
        child_start = reader.pos
        row = child_spans.get(child_start)
        if row is None:
            raise ValueError(f"{LABEL}:missing-certified-child={child_start}")
        child_end, tag = row["end"], row["tag"]
        if not child_start < child_end <= reader.limit:
            raise ValueError(f"{LABEL}:child-range={child_start},{child_end}")
        first = reader.data[child_start]
        width = 3 if first == 0xFA else 1
        if child_end - child_start < width:
            raise ValueError(f"{LABEL}:child-tag-truncated={child_start}")
        actual_tag = (
            struct.unpack_from("<H", reader.data, child_start + 1)[0]
            if width == 3 else first
        )
        if actual_tag != tag:
            raise ValueError(f"{LABEL}:child-tag={child_start}")
        reader.pos = child_end
    for name in ("onlyExecuteWhenSourceIsGuard", "onlyExecuteWhenSourceIsMainChar"):
        value = reader.take(1, name)[0]
        if value not in (0, 1):
            raise ValueError(f"{LABEL}:{name}={value}")


def decode_if_else_action_receipt(
    data: bytes,
    *,
    source: str,
    logical_sha256: str,
    start: int,
    end: int,
    native_validation: dict[str, Any],
    certified_action_spans: list[dict[str, int]],
) -> dict[str, Any]:
    """Name one authenticated C9 span using certified nested action ends."""
    contract = _contract()
    _source, _catalog, provider = _dependencies()
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("unionTag") != TAG
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("memberCount") != contract["wrapper"]["serializedMemberCount"]
    ):
        raise ValueError(f"{LABEL}:native-not-validated")
    if (
        not isinstance(logical_sha256, str)
        or len(logical_sha256) != 64
        or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()
    ):
        raise ValueError(f"{LABEL}:logical-sha256-mismatch")
    if not source or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data):
        raise ValueError(f"{LABEL}:invalid-action-range")
    if not isinstance(certified_action_spans, list):
        raise ValueError(f"{LABEL}:missing-certified-action-spans")
    child_spans: dict[int, dict[str, int]] = {}
    ordered: list[tuple[int, int]] = []
    for row in certified_action_spans:
        if not isinstance(row, dict):
            raise ValueError(f"{LABEL}:invalid-certified-action-span")
        child_start, child_end, tag = row.get("start"), row.get("end"), row.get("tag")
        if (
            type(child_start) is not int or type(child_end) is not int or type(tag) is not int
            or not 0 <= child_start < child_end <= len(data)
            or child_start in child_spans
        ):
            raise ValueError(f"{LABEL}:invalid-certified-action-span")
        child_spans[child_start] = {"end": child_end, "tag": tag}
        ordered.append((child_start, child_end))
    # Nested union spans may contain other spans, but partial crossings are
    # impossible for a serialized tree and would let a supplied child swallow
    # bytes belonging to its sibling or parent.
    stack: list[int] = []
    for child_start, child_end in sorted(ordered, key=lambda item: (item[0], -item[1])):
        while stack and child_start >= stack[-1]:
            stack.pop()
        if stack and child_end > stack[-1]:
            raise ValueError(f"{LABEL}:crossing-certified-action-spans")
        stack.append(child_end)
    if child_spans.get(start) != {"end": end, "tag": TAG}:
        raise ValueError(f"{LABEL}:enclosing-action-not-certified")

    reader = Reader(data, source, end)
    reader.pos = start
    if reader.take(1, "union-tag")[0] != TAG:
        raise ValueError(f"{LABEL}:union-tag")
    reader.header(contract["wrapper"]["serializedMemberCount"])
    fields: list[dict[str, Any]] = []
    setters = contract["wrapper"]["inheritedSetterMethods"] + contract["wrapper"]["setterMethods"]
    for setter, read in zip(setters, provider["orderedSourceReads"], strict=True):
        field_start = reader.pos
        kind = read["kind"]
        if kind == "anonymous-nonzero-byte":
            if reader.take(1, kind)[0] not in (0, 1):
                raise ValueError(f"{LABEL}:invalid-boolean={field_start}")
        elif kind == "anonymous-scalar32":
            reader.take(4, kind)
        elif kind == "SequenceActionData":
            _read_sequence(reader, child_spans)
        else:
            raise ValueError(f"{LABEL}.contract:unsupported-read-kind={kind}")
        if reader.pos <= field_start:
            raise ValueError(f"{LABEL}:field-no-progress")
        fields.append({"fieldName": _field_name(setter), "kind": kind,
                       "start": field_start, "end": reader.pos})
    if reader.pos != end or fields[0]["start"] != start + 2 or any(
        left["end"] != right["start"] for left, right in zip(fields, fields[1:])
    ):
        raise ValueError(f"{LABEL}:action-end={reader.pos}; expected={end}")
    return {
        "schema": SCHEMA,
        "source": source,
        "logicalSha256": logical_sha256.upper(),
        "status": "named-wrapper-exact-span",
        "tag": TAG,
        "typeName": "Beyond.Gameplay.Core.IfElseAction+IfElseActionData",
        "memberCount": len(fields),
        "start": start,
        "end": end,
        "namedFields": fields,
        "wholeActionByteSpanExact": True,
        "recursiveNamedSchemaExact": False,
        "wholeBuffDataExact": False,
        "nestedStructuralFields": ["conditionAction", "failActions", "succeedActions"],
        "evidenceBoundary": (
            "The selected native route and generated setters name eight IfElseAction "
            "wrapper members. The authenticated logical bytes and independently "
            "certified child action ends close three SequenceActionData envelopes "
            "to the physical action end. The adapter does not reparse nested action "
            "bodies or evaluate the condition, branch selection, or enclosing BuffData."
        ),
    }
