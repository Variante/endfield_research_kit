"""Authenticate reviewed Wwise effect parameter layouts on selected inputs.

The contract ``wwise_effect_parameters_native.json`` records, for the selected
``GameAssembly.dll``, ``global-metadata.dat`` and ``AkSoundEngine.dll``, which
built-in plug-in classes have a reviewed ``SetParamsBlock`` layout. Each
reviewed method body in the shipped DLL matches the named Wwise 2023.1.17 SDK
COFF method outside relocation operands; ``check_effect_parameter_native_inputs``
re-hashes every body on the selected build before any typed value is published.
Missing, drifted or pending evidence keeps the class id, parameter length and
SHA-256 and the plug-in media prefix, and withholds names and values.

Reviewed layouts (``hirc_v150.decode_hirc_v150_effect_parameters``) decode the
authored base settings of Gain, Delay, Compressor, Expander, three-band
Parametric EQ, Meter, Matrix Reverb, Pitch Shifter, Harmonizer, Stereo Delay,
Guitar Distortion (three pre-EQ and three post-EQ bands, distortion type,
drive, tone, rectification, output gain, wet/dry) and RoomVerb. RoomVerb
exposes its public controls and 31 ER pattern names; eleven further floats
keep exact offsets and values but no current public name or runtime role.

Registration witnesses join a class id to its method without a public SDK
layout. The DLL holds four-word static effect registrations -- plug-in type,
plug-in id, effect factory, parameter factory -- and each parameter factory
installs a vtable whose ``+0x28`` slot is ``SetParamsBlock``. Gain and RoomVerb
are ``slotControl`` witnesses (their slots are independently SDK-named);
Convolution Reverb and Mastering Suite are ``structuralOnly``: the contract
proves the registration, factory and constructor bodies, vtable target, slot
and method body, and an exact partition of the method's input reads. The
page may show anonymous load offsets, widths and raw bits. Scalar loads may
add a float32 representation view, which proves no control name, unit,
processed value, forwarding role or DSP behavior.
Neither method checks the supplied length, so a span is a direct read, not a ``uSize`` acceptance rule,
and the shipped ``uSize`` distribution is not proved by this contract.
Convolution's impulse-response media ids stay exact bank data and never become
playable WEM leaves.

Claims from an older ``AkSoundEngine.dll`` (private SetParam ids, consumer or
forwarding roles) are withheld until re-derived on the selected build: a
constant that pinned an older DLL without checking the pin had no current
native basis. Authored slot flags and parameters are not runtime DSP,
execution or audibility.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR


CONTRACT_PATH = CONTRACTS_DIR / "wwise_effect_parameters_native.json"


@lru_cache(maxsize=1)
def load_effect_parameter_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("schema") != "endfield.wwise-effect-parameters-native.v3":
        raise ValueError("unsupported Wwise effect parameter contract")
    return contract


def effect_parameter_schema(plugin_class_id: int) -> dict[str, Any] | None:
    contract = load_effect_parameter_contract()
    if contract.get("status") != "reviewedCurrentBuild":
        return None
    row = contract["parameterSchemas"].get(f"0x{plugin_class_id:08x}")
    return row if row and row.get("status") == "reviewed" else None


def effect_parameter_structural_schema(plugin_class_id: int) -> dict[str, Any] | None:
    """Return a reviewed read span without promoting anonymous bytes to settings."""
    contract = load_effect_parameter_contract()
    if contract.get("status") != "reviewedCurrentBuild":
        return None
    row = contract.get("structuralSchemas", {}).get(f"0x{plugin_class_id:08x}")
    return row if row and row.get("status") == "structuralOnly" else None


class EffectReadLayoutError(ValueError):
    """A bounded diagnostic for a reviewed anonymous read partition."""

    def __init__(self, class_id: str, check: str, offset: int | None, expected: Any, actual: Any):
        self.diagnostic = {
            "failedCheck": check,
            "failedClassId": class_id,
            "failedSerializedOffset": offset,
            "expected": str(expected)[:160],
            "actual": str(actual)[:160],
        }
        super().__init__(
            f"{class_id} {check} at serialized offset {offset}: "
            f"expected {self.diagnostic['expected']}; actual {self.diagnostic['actual']}"
        )


def validate_structural_input_reads(
    class_id: str, schema: dict[str, Any], body: bytes | None = None,
) -> None:
    """Check a complete anonymous partition and its bounded native witnesses.

    The reviewed contract owns addressing and load identities; method hashing
    binds those facts to the selected DLL. These checks refuse overlaps, gaps,
    incompatible widths and native instruction witnesses outside that method.
    A scalar load is a representation witness, never a public parameter name.
    """
    def fail(check: str, offset: int | None, expected: Any, actual: Any) -> None:
        raise EffectReadLayoutError(class_id, check, offset, expected, actual)

    span = schema.get("contiguousInputReadBytes")
    if type(span) is not int or span <= 0:
        fail("nativeReadSpan", None, "positive integer", span)
    rows = schema.get("inputReads")
    if not isinstance(rows, list) or not rows:
        fail("nativeInputReads", None, "nonempty read list", type(rows).__name__)
    widths = {"word32Copy": 4, "scalar32Load": 4, "byteZeroTest": 1, "byteZeroExtend": 1}
    cursor = 0
    method_size = schema["setParamsBlock"]["bodyLength"]
    if type(method_size) is not int or method_size <= 0:
        fail("nativeMethodSpan", None, "positive integer", method_size)
    bases = schema.get("inputBaseWitnesses")
    if not isinstance(bases, list) or not bases:
        fail("nativeInputBases", None, "nonempty base witness list", type(bases).__name__)
    for row in [*bases, *rows]:
        if not isinstance(row, dict):
            fail("nativeReadRecord", cursor, "object", type(row).__name__)
        at = row.get("bodyOffset")
        encoded = row.get("instructionHex")
        try:
            witness = bytes.fromhex(encoded) if isinstance(encoded, str) else b""
        except ValueError:
            witness = b""
        if type(at) is not int or not witness or at < 0 or at + len(witness) > method_size:
            fail("nativeReadInstructionExtent", row.get("serializedOffset"),
                 f"nonempty instruction inside {method_size}-byte method", f"{at}+{len(witness)}")
        if body is not None and body[at:at + len(witness)] != witness:
            fail("nativeReadInstructionBytes", row.get("serializedOffset"),
                 witness.hex(), body[at:at + len(witness)].hex())
    for row in rows:
        offset = row.get("serializedOffset")
        width = row.get("byteWidth")
        kind = row.get("readKind")
        if type(offset) is not int or offset != cursor:
            fail("nativeReadPartitionOffset", cursor, cursor, offset)
        if kind not in widths or type(width) is not int or width != widths[kind]:
            fail("nativeReadWidth", cursor, widths.get(kind, "supported read kind"), f"{kind}/{width}")
        cursor += width
        if cursor > span:
            fail("nativeReadPartitionOverrun", offset, span, cursor)
    if cursor != span:
        fail("nativeReadPartitionEnd", cursor, span, cursor)


def decode_effect_parameter_native_reads(
    plugin_class_id: int, parameter_data: bytes, *, native_evidence_validated: bool = False,
) -> dict[str, Any] | None:
    """Project raw serialized values at reviewed anonymous native read offsets.

    The caller must supply its selected-build gate result. No named settings or
    transformed native values are produced, and a short block yields no rows.
    Longer blocks retain an explicit unread suffix rather than fitting a size.
    """
    if not native_evidence_validated:
        return None
    schema = effect_parameter_structural_schema(plugin_class_id)
    if schema is None:
        return None
    class_id = f"0x{plugin_class_id:08x}"
    try:
        validate_structural_input_reads(class_id, schema)
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "parameterNativeReadParserStatus": "failedClosed",
            "parameterNativeReadDiagnostic": getattr(exc, "diagnostic", {
                "failedCheck": "nativeInputReadContract", "failedClassId": class_id,
                "detail": str(exc)[:240],
            }),
        }
    span = schema["contiguousInputReadBytes"]
    if len(parameter_data) < span:
        return {
            "parameterNativeReadParserStatus": "failedClosed",
            "parameterNativeReadDiagnostic": {
                "failedCheck": "serializedBlockCoversNativeReads", "failedClassId": class_id,
                "expectedMinimumBytes": span, "actualBytes": len(parameter_data),
                "sourceSha256": hashlib.sha256(parameter_data).hexdigest(),
            },
        }
    rows = []
    for read in schema["inputReads"]:
        offset, width = read["serializedOffset"], read["byteWidth"]
        raw = parameter_data[offset:offset + width]
        row = {
            "serializedOffset": offset, "byteWidth": width, "readKind": read["readKind"],
            "rawHex": raw.hex(), "rawUnsigned": int.from_bytes(raw, "little"),
            "evidenceBoundary": "structuralOnly",
        }
        if read["readKind"] == "scalar32Load":
            value = struct.unpack("<f", raw)[0]
            row["float32View"] = value if math.isfinite(value) else None
        rows.append(row)
    return {
        "parameterNativeReadParserStatus": "exactNativeReadPartition",
        "parameterNativeReads": rows,
        "parameterNativeUnreadByteLength": len(parameter_data) - span,
        "parameterNativeReadEvidenceBoundary": "structuralOnly",
        "parameterNativeReadSemanticBoundary": schema["meaningBoundary"],
    }


def _pe_body(image: bytes, rva: int, length: int) -> bytes:
    """Read a bounded RVA window from one PE image without another dependency."""
    if len(image) < 0x40 or image[:2] != b"MZ":
        raise ValueError("invalid PE DOS header")
    pe_offset = struct.unpack_from("<I", image, 0x3C)[0]
    if pe_offset + 24 > len(image) or image[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ValueError("invalid PE header")
    section_count = struct.unpack_from("<H", image, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", image, pe_offset + 20)[0]
    section_offset = pe_offset + 24 + optional_size
    if not 0 < section_count <= 96 or section_offset + section_count * 40 > len(image):
        raise ValueError("invalid PE section table")
    for index in range(section_count):
        at = section_offset + index * 40
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
            "<IIII", image, at + 8
        )
        if virtual_address <= rva and rva + length <= virtual_address + min(virtual_size, raw_size):
            start = raw_offset + rva - virtual_address
            if start + length <= len(image):
                return image[start:start + length]
    raise ValueError(f"RVA window 0x{rva:x}+{length} outside mapped PE bytes")


def _pe_image_base(image: bytes) -> int:
    if len(image) < 0x40 or image[:2] != b"MZ":
        raise ValueError("invalid PE DOS header")
    pe_offset = struct.unpack_from("<I", image, 0x3C)[0]
    optional = pe_offset + 24
    if optional + 32 > len(image) or image[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ValueError("invalid PE header")
    if struct.unpack_from("<H", image, optional)[0] != 0x20B:
        raise ValueError("AkSoundEngine.dll is not PE32+")
    return struct.unpack_from("<Q", image, optional + 24)[0]


def _validate_registration_witness(
    image: bytes, image_base: int, class_id: str, witness: dict[str, Any], method_rva: int
) -> None:
    """Join a plug-in registration to its parameter factory and vtable slot."""
    registration = struct.unpack(
        "<QQQQ", _pe_body(image, int(witness["registrationRva"], 16), 32)
    )
    expected = (
        witness["pluginType"],
        witness["pluginId"],
        image_base + int(witness["factoryRva"], 16),
        image_base + int(witness["parameterFactoryRva"], 16),
    )
    if registration != expected or int(class_id, 16) != (expected[1] << 16) | expected[0]:
        raise ValueError(f"effect registration mismatch for {class_id}")
    factory = _pe_body(
        image, int(witness["parameterFactoryRva"], 16), witness["parameterFactoryBodyLength"]
    )
    if hashlib.sha256(factory).hexdigest() != witness["parameterFactoryBodySha256"]:
        raise ValueError(f"parameter factory body mismatch for {class_id}")
    if "parameterConstructorRva" in witness:
        constructor_rva = int(witness["parameterConstructorRva"], 16)
        jump_rva = int(witness["constructorJumpRva"], 16)
        jump = _pe_body(image, jump_rva, 5)
        if jump[0] != 0xE9 or jump_rva + 5 + struct.unpack_from("<i", jump, 1)[0] != constructor_rva:
            raise ValueError(f"parameter constructor jump mismatch for {class_id}")
        constructor = _pe_body(image, constructor_rva, witness["parameterConstructorBodyLength"])
        if hashlib.sha256(constructor).hexdigest() != witness["parameterConstructorBodySha256"]:
            raise ValueError(f"parameter constructor body mismatch for {class_id}")
    lea_rva = int(witness["vtableLeaRva"], 16)
    lea = _pe_body(image, lea_rva, 7)
    if lea[:3].hex() != witness["vtableLeaPrefixHex"]:
        raise ValueError(f"parameter vtable LEA mismatch for {class_id}")
    if lea_rva + 7 + struct.unpack_from("<i", lea, 3)[0] != int(witness["vtableRva"], 16):
        raise ValueError(f"parameter vtable target mismatch for {class_id}")
    slot = struct.unpack(
        "<Q", _pe_body(image, int(witness["vtableRva"], 16) + witness["setParamsBlockSlot"], 8)
    )[0]
    if witness["setParamsBlockSlot"] != 40 or slot != image_base + method_rva:
        raise ValueError(f"SetParamsBlock vtable slot mismatch for {class_id}")


def check_effect_parameter_native_inputs(game_root: Path) -> dict[str, Any]:
    """Validate the selected native triplet, method bodies, and registration joins."""
    contract = load_effect_parameter_contract()
    expected = contract["nativeInputs"]
    selected = Path(game_root)
    native = check_installed_native_inputs(
        expected_gameassembly_sha256=expected["gameAssemblySha256"],
        expected_metadata_sha256=expected["globalMetadataSha256"],
        gameassembly=selected.parent / "GameAssembly.dll",
        metadata=selected / "il2cpp_data" / "Metadata" / "global-metadata.dat",
    )
    ak_path = selected / "Plugins" / "x86_64" / "AkSoundEngine.dll"
    result: dict[str, Any] = {
        "status": native.status,
        "detail": native.detail,
        "contractSchema": contract["schema"],
        "selectedGameRoot": str(selected),
        "gameAssemblySha256": native.gameassembly_sha256,
        "globalMetadataSha256": native.metadata_sha256,
        "akSoundEnginePath": str(ak_path),
        "akSoundEngineSha256": "",
        "expectedAkSoundEngineSha256": expected["akSoundEngineSha256"],
        "expectedAkSoundEngineSize": expected["akSoundEngineFileSize"],
        "validatedClassIds": [],
        "validatedStructuralClassIds": [],
    }
    if contract.get("status") != "reviewedCurrentBuild":
        result.update(status="mismatched", detail="Wwise effect parameter contract is not reviewed")
        return result
    if native.status != "validated":
        return result
    if not ak_path.is_file():
        result.update(status="missing", detail=f"selected AkSoundEngine.dll not found at {ak_path}")
        return result
    actual_size = ak_path.stat().st_size
    actual_sha256 = sha256_file(ak_path)
    result["akSoundEngineSize"] = actual_size
    result["akSoundEngineSha256"] = actual_sha256
    if actual_size != expected["akSoundEngineFileSize"] or actual_sha256.casefold() != expected["akSoundEngineSha256"].casefold():
        result.update(
            status="mismatched",
            detail=(
                "selected AkSoundEngine.dll differs from the reviewed effect layout: "
                f"size={actual_size} sha256={actual_sha256[:12]}, "
                f"expected size={expected['akSoundEngineFileSize']} "
                f"sha256={expected['akSoundEngineSha256'][:12]}"
            ),
        )
        return result
    image = ak_path.read_bytes()
    try:
        image_base = _pe_image_base(image) if contract.get("registrationWitnesses") else 0
        validated_class_ids = []
        for class_id, row in contract["parameterSchemas"].items():
            if row.get("status") != "reviewed":
                continue
            method = row["setParamsBlock"]
            body = _pe_body(image, int(method["rva"], 16), method["bodyLength"])
            if hashlib.sha256(body).hexdigest().casefold() != method["bodySha256"].casefold():
                raise ValueError(f"SetParamsBlock body mismatch for {class_id}")
            validated_class_ids.append(class_id)
        validated_structural_class_ids = []
        structural_rows = contract.get("structuralSchemas", {})
        witnesses = contract.get("registrationWitnesses", {})
        if {k for k, v in witnesses.items() if v["role"] == "structuralOnly"} != set(structural_rows):
            raise ValueError("structural effect registration witness set differs from schemas")
        for class_id, row in structural_rows.items():
            if row["status"] != "structuralOnly":
                raise ValueError(f"structural effect status mismatch for {class_id}")
            method = row["setParamsBlock"]
            body = _pe_body(image, int(method["rva"], 16), method["bodyLength"])
            if hashlib.sha256(body).hexdigest().casefold() != method["bodySha256"].casefold():
                raise ValueError(f"structural SetParamsBlock body mismatch for {class_id}")
            validate_structural_input_reads(class_id, row, body)
            validated_structural_class_ids.append(class_id)
        for class_id, witness in witnesses.items():
            if witness["role"] == "slotControl":
                if class_id not in validated_class_ids:
                    raise ValueError(f"unreviewed effect slot control {class_id}")
                method = contract["parameterSchemas"][class_id]["setParamsBlock"]
            elif witness["role"] == "structuralOnly":
                method = structural_rows[class_id]["setParamsBlock"]
            else:
                raise ValueError(f"unknown effect registration role for {class_id}")
            _validate_registration_witness(image, image_base, class_id, witness, int(method["rva"], 16))
    except (KeyError, TypeError, ValueError, struct.error) as exc:
        result.update(status="mismatched", detail=str(exc))
        if isinstance(exc, EffectReadLayoutError):
            result["diagnostic"] = exc.diagnostic
        return result
    result["validatedClassIds"] = sorted(validated_class_ids)
    result["validatedStructuralClassIds"] = sorted(validated_structural_class_ids)
    return result
