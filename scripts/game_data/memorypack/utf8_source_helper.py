"""Selected native proof and bounded decoding of stored UTF-8 string spans.

This reader accepts null, empty and valid UTF-8 payloads only. Native invalid
byte replacement, execution, source loading and evaluated keys are outside
its evidence boundary. Callers separately prove their field's source call.
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.core import CONTRACTS_DIR

LABEL = "memorypackUtf8SourceHelper"
CONTRACT_PATH = CONTRACTS_DIR / "memorypack_utf8_source_helper_native.json"


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema="endfield.memorypack-utf8-source-helper-native.v1",
        status="exact-current-build", label=LABEL)
    if (value.get("wireEncoding") != "nullable-int32-byte-length-valid-utf8"
            or not value.get("sourceHelpers") or not value.get("codeWindows")
            or not value.get("instructionWindows") or not value.get("methods")
            or not value.get("calls") or value.get("emptyLiteral", {}).get("value") != ""):
        raise ValueError(f"{LABEL}.contract:shape")
    return value


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    contract = _contract(); pins = contract["nativeInputs"]
    gate = check_installed_native_inputs(pins["GameAssembly.dll"], pins["global-metadata.dat"],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail, "nativeInputs": pins}
    unity = Path(gate.gameassembly).parent / "UnityPlayer.dll"

    def unity_matches() -> bool:
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins["UnityPlayer.dll"]

    if not unity_matches():
        return {"status": "mismatch", "detail": "UnityPlayer.dll missing or mismatched", "nativeInputs": pins}
    image = open_native_image(gate.gameassembly, gate.metadata)
    for method in contract["methods"]:
        image.validate_method_row(method, label=LABEL)
    image.check_windows(contract["codeWindows"], label=LABEL)
    image.check_instruction_windows(contract["instructionWindows"], label=LABEL)
    for call in contract["calls"]:
        raw = image.pe.bytes_at_va(image.pe.image_base + call["rva"], 5)
        target = call["rva"] + 5 + struct.unpack_from("<i", raw, 1)[0]
        method = image.metadata.methods[call["methodIndex"]]
        if (raw[0] != (0xE9 if call["kind"] == "tail-jump" else 0xE8)
                or target != call["targetRva"]
                or image.method_pointer_va(method) != image.pe.image_base + target):
            raise ValueError(f"{LABEL}.native:callee-identity")
    literal = contract["emptyLiteral"]
    word = image.pe.u64_at_va(image.pe.image_base + literal["usageCellRva"])
    section = image.metadata.sections["stringLiteral"]
    data_section = image.metadata.sections["stringLiteralData"]
    index = (word >> 1) & 0x0FFFFFFF
    if (word > 0xFFFFFFFF or not word & 1 or word >> 29 != 5
            or index >= section.size // 8):
        raise ValueError(f"{LABEL}.native:empty-literal-usage")
    length, start = struct.unpack_from("<ii", image.metadata.buf, section.offset + index * 8)
    if length != 0 or not 0 <= start <= data_section.size:
        raise ValueError(f"{LABEL}.native:empty-literal-value")
    after = check_installed_native_inputs(pins["GameAssembly.dll"], pins["global-metadata.dat"],
        gameassembly=gameassembly, metadata=metadata)
    if after.status != "validated" or not unity_matches():
        return {"status": "mismatch", "detail": "native inputs changed during validation", "nativeInputs": pins}
    return {"status": "validated", "nativeInputs": pins,
        "sourceHelpers": contract["sourceHelpers"], "wireEncoding": contract["wireEncoding"],
        "evidenceBoundary": contract["evidenceBoundary"]}


def decode_source_string(data: bytes, *, source: str, digest: str, start: int, end: int,
                         source_helper_rva: int, native_validation: dict[str, Any]) -> dict[str, Any]:
    """Decode one original field span whose independently proved call uses this helper."""
    contract = _contract()
    if (native_validation.get("status") != "validated"
            or native_validation.get("nativeInputs") != contract["nativeInputs"]
            or native_validation.get("sourceHelpers") != contract["sourceHelpers"]
            or native_validation.get("wireEncoding") != contract["wireEncoding"]
            or source_helper_rva not in contract["sourceHelpers"]
            or not isinstance(data, bytes) or not source or not isinstance(digest, str)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    if end - start < 4:
        raise ValueError(f"{LABEL}.decode:short-length")
    count = struct.unpack_from("<i", data, start)[0]
    if count < -1 or end != start + 4 + max(count, 0):
        raise ValueError(f"{LABEL}.decode:length-or-eof")
    try:
        value = None if count == -1 else data[start + 4:end].decode("utf-8", "strict")
    except UnicodeDecodeError as error:
        raise ValueError(f"{LABEL}.decode:invalid-utf8") from error
    return {"schema": "endfield.memorypack-source-string-receipt.v1",
        "source": source, "logicalSha256": digest.upper(), "start": start, "end": end,
        "rawHex": data[start:end].hex().upper(), "byteLength": count, "value": value,
        "sourceHelperRva": source_helper_rva, "nativeStatus": "validated",
        "wholeStoredSpanExact": True, "storedStringValueExact": True,
        "runtimeMeaningExact": False}
