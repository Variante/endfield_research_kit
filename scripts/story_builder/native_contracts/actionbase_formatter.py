"""Load and gate the reviewed ActionBase MemoryPack formatter contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
except ImportError:  # pragma: no cover - package import identity
    from scripts.common import (
        NATIVE_EVIDENCE_VALIDATED,
        check_installed_native_inputs,
    )


SCHEMA = "actionBaseFormatterNativeContract.v1"
AUDIT_SCHEMA = "actionBaseFormatterNameAudit.v1"
DEFAULT_CONTRACT = Path(__file__).with_name("actionbase_formatter.json")
GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)
ACTION_NAMES_SHA256 = (
    "07181E33E997D0B439D66272DBE6366983C928C717087AE0B26101BC0A4C9604"
)
NATIVE_MAPPING_ID = (
    "gameassembly-2026-07-11-cr-0x18b9217d0-actionbase-0x0000-0x0520"
)


def _source_file(path: Path) -> str:
    root = Path(__file__).resolve().parents[3]
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def load_actionbase_formatter_names(
    contract_path: Path = DEFAULT_CONTRACT,
    *,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> tuple[dict[int, str], dict[str, Any]]:
    """Return all formatter names only for the reviewed installed build."""

    path = Path(contract_path)
    source_file = _source_file(path)
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "actionBaseFormatterNativeContract",
            "gate": gate,
            "sourceFile": source_file,
            "expected": expected,
            "actual": actual,
        })

    try:
        raw = path.read_bytes()
        contract = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        reject("read_valid_json", {"readableJsonObject": True}, str(error)[:400])
        return {}, {
            "schema": AUDIT_SCHEMA,
            "status": "validation_failed",
            "sourceFile": source_file,
            "sourceSha256": "",
            "nativeMappingId": NATIVE_MAPPING_ID,
            "summary": {"recoveredTags": 0, "validationFailures": 1},
            "validationFailures": failures,
            "usesOcrOrManualOrder": False,
        }

    source_sha256 = hashlib.sha256(raw).hexdigest().upper()
    if not isinstance(contract, dict):
        reject("contract_object", {"type": "object"}, {
            "type": type(contract).__name__,
        })
        contract = {}
    sources = (
        contract.get("metadata")
        if isinstance(contract.get("metadata"), dict)
        else {}
    )
    target = (
        contract.get("targetMethod")
        if isinstance(contract.get("targetMethod"), dict)
        else {}
    )
    summary = (
        contract.get("summary")
        if isinstance(contract.get("summary"), dict)
        else {}
    )
    exact_gates = (
        ("schema", SCHEMA, contract.get("schema")),
        ("status", "validated", contract.get("status")),
        ("gameassembly_sha256", GAMEASSEMBLY_SHA256, sources.get("gameAssemblySha256")),
        ("metadata_sha256", METADATA_SHA256, sources.get("metadataSha256")),
        ("code_registration", "0x18b9217d0", sources.get("codeRegistration")),
        ("formatter_type_token", "0x02000c1c", target.get("typeToken")),
        ("formatter_method_token", "0x0600488f", target.get("methodToken")),
        ("formatter_method_va", "0x183998700", target.get("methodPointerVa")),
        ("tag_count", 1313, summary.get("tagCount")),
        ("min_tag", 0, summary.get("minTag")),
        ("max_tag", 1312, summary.get("maxTag")),
        ("duplicate_tags", 0, summary.get("duplicateTagCount")),
        ("missing_tags", 0, summary.get("missingTagCountInsideRange")),
        ("unknown_instructions", 0, summary.get("unknownInstructionCount")),
    )
    for gate, expected, actual in exact_gates:
        if actual != expected:
            reject(gate, expected, actual)

    compact_names = contract.get("actionNames")
    if not isinstance(compact_names, list):
        reject("action_names", {"type": "array", "length": 1313}, {
            "type": type(compact_names).__name__,
        })
        compact_names = []
    names: dict[int, str] = {}
    for tag, action_name in enumerate(compact_names):
        if not isinstance(action_name, str) or not action_name:
            reject("nonempty_action_name", {"tag": tag, "nonempty": True}, {
                "actionName": action_name,
            })
            continue
        names[tag] = action_name
    if len(compact_names) != 1313:
        reject("action_name_count", 1313, len(compact_names))
    names_sha256 = hashlib.sha256(
        "\0".join(str(value) for value in compact_names).encode("utf-8")
    ).hexdigest().upper()
    if names_sha256 != ACTION_NAMES_SHA256:
        reject("action_names_sha256", ACTION_NAMES_SHA256, names_sha256)

    native = check_installed_native_inputs(
        GAMEASSEMBLY_SHA256,
        METADATA_SHA256,
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        reject(
            "installed_native_inputs",
            {"status": NATIVE_EVIDENCE_VALIDATED},
            {"status": native.status, "detail": native.detail},
        )
    if failures:
        names = {}
    status = (
        NATIVE_EVIDENCE_VALIDATED
        if not failures
        else native.status
        if native.status != NATIVE_EVIDENCE_VALIDATED
        else "validation_failed"
    )
    return names, {
        "schema": AUDIT_SCHEMA,
        "status": status,
        "sourceFile": source_file,
        "sourceSha256": source_sha256,
        "nativeMappingId": NATIVE_MAPPING_ID,
        "summary": {
            "recoveredTags": len(names),
            "validationFailures": len(failures),
        },
        "validationFailures": failures,
        "usesOcrOrManualOrder": False,
    }


__all__ = [
    "ACTION_NAMES_SHA256",
    "AUDIT_SCHEMA",
    "DEFAULT_CONTRACT",
    "GAMEASSEMBLY_SHA256",
    "METADATA_SHA256",
    "NATIVE_MAPPING_ID",
    "SCHEMA",
    "load_actionbase_formatter_names",
]
