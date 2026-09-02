#!/usr/bin/env python3
"""Verify an inventoried, session-scoped Endminf M27 mip-bias receipt."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


RECEIPT_RELATIVE_PATH = (
    "graphics/endminf_m27_global_mip_bias_receipt.json"
)
RUNTIME_RELATIVE_PATH = "private/EndfieldCapture.dll"
RESULT_SCHEMA = (
    "endfield.endminf-m27-global-mip-bias-session-verification.v1"
)
MAX_DIAGNOSTIC_CHARS = 512


class SessionReceiptError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SessionReceiptError(message)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    _require(path.is_file(), f"missing {label}: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SessionReceiptError(f"invalid {label}: {exc}") from exc
    _require(isinstance(value, dict), f"{label} must be an object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_result(path: Path, result: dict[str, Any]) -> None:
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized, encoding="utf-8")


def _load_receipt_verifier() -> Any:
    path = Path(__file__).with_name(
        "verify_endminf_m27_global_mip_bias_receipt.py"
    )
    spec = importlib.util.spec_from_file_location("m27_receipt_verifier", path)
    if spec is None or spec.loader is None:
        raise SessionReceiptError(f"unable to load receipt verifier: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def verify_inventory_binding(
    session_root: Path, receipt: dict[str, Any]
) -> dict[str, str]:
    session = _load_json(session_root / "session.json", "session descriptor")
    inventory_path = session_root / "collected" / "inventory.json"
    inventory = _load_json(inventory_path, "collection inventory")
    _require(
        inventory.get("schema") == "endfieldCapture.collection.v1",
        "collection inventory schema mismatch",
    )
    session_id = session.get("sessionId")
    numeric_session_id = session.get("numericSessionId")
    _require(
        session.get("schema") == "endfieldCapture.session.v1",
        "session descriptor schema mismatch",
    )
    _require(isinstance(session_id, str) and session_id, "invalid sessionId")
    _require(
        type(numeric_session_id) is int and numeric_session_id > 0,
        "invalid numericSessionId",
    )
    _require(inventory.get("session") == session_id, "inventory session mismatch")
    _require(session.get("providers") == 1, "session provider mask is not graphics-only")
    _require(session.get("graphicsProfile") == "full", "session is not Full")
    _require(
        session.get("evidenceLabel") == "forced-d3d11",
        "session evidence label mismatch",
    )

    receipt_session = receipt.get("session")
    _require(isinstance(receipt_session, dict), "receipt session scope is missing")
    _require(receipt_session.get("sessionId") == session_id, "receipt session mismatch")
    _require(
        receipt_session.get("numericSessionId") == numeric_session_id,
        "receipt numeric session mismatch",
    )
    _require(
        receipt_session.get("providerMask") == session.get("providers"),
        "receipt provider mask mismatch",
    )
    _require(receipt_session.get("graphicsProfile") == "full", "receipt is not Full")
    _require(
        receipt_session.get("runtimeKind") == "general",
        "receipt is not from the general runtime",
    )
    _require(
        receipt_session.get("runtimePackage") == RUNTIME_RELATIVE_PATH,
        "receipt runtime package path mismatch",
    )

    artifacts = inventory.get("artifacts")
    _require(isinstance(artifacts, list), "inventory artifacts are missing")
    by_path: dict[str, dict[str, Any]] = {}
    for row in artifacts:
        _require(isinstance(row, dict), "inventory artifact row is invalid")
        relative = row.get("path")
        _require(isinstance(relative, str) and relative, "artifact path is invalid")
        _require(relative not in by_path, f"duplicate inventory artifact: {relative}")
        by_path[relative] = row
    _require(inventory.get("files") == len(artifacts), "inventory file count mismatch")

    result: dict[str, str] = {}
    for relative in (RECEIPT_RELATIVE_PATH, RUNTIME_RELATIVE_PATH):
        row = by_path.get(relative)
        _require(row is not None, f"inventory omits required artifact: {relative}")
        path = session_root / Path(relative)
        _require(path.is_file(), f"inventoried artifact is missing: {relative}")
        size = path.stat().st_size
        digest = _sha256(path)
        _require(row.get("bytes") == size, f"inventory size mismatch: {relative}")
        _require(row.get("sha256") == digest, f"inventory hash mismatch: {relative}")
        result[relative] = digest
    runtime_path = (session_root / RUNTIME_RELATIVE_PATH).resolve()
    staged_path = session.get("runtimeStagedPath")
    _require(isinstance(staged_path, str) and staged_path, "runtimeStagedPath is missing")
    _require(
        Path(staged_path).resolve() == runtime_path,
        "runtimeStagedPath does not identify the session runtime package",
    )
    _require(
        session.get("runtimeBytes") == runtime_path.stat().st_size,
        "session runtimeBytes mismatch",
    )
    _require(
        session.get("runtimeSha256") == result[RUNTIME_RELATIVE_PATH],
        "session runtimeSha256 mismatch",
    )
    return result


def verify_session(
    session_root: Path,
    *,
    contract: Path | None = None,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    """Return the admitted session result after every inventory/source gate."""
    receipt_path = session_root / RECEIPT_RELATIVE_PATH
    receipt = _load_json(receipt_path, "M27 mip-bias receipt")
    hashes = verify_inventory_binding(session_root, receipt)
    verifier = _load_receipt_verifier()
    contract_args: dict[str, Any] = {}
    if contract is not None:
        contract_args["contract_path"] = contract
    if gameassembly is not None:
        contract_args["gameassembly"] = gameassembly
    if metadata is not None:
        contract_args["metadata"] = metadata
    _contract, contract_sha256 = verifier.load_validated_contract(
        **contract_args
    )
    source_result = verifier.verify_receipt(receipt, contract_sha256)
    return {
        "schema": RESULT_SCHEMA,
        "status": "inventoried_source_receipt_admitted",
        "session": receipt["session"]["sessionId"],
        "receiptSha256": hashes[RECEIPT_RELATIVE_PATH],
        "runtimePackageSha256": hashes[RUNTIME_RELATIVE_PATH],
        "sourceVerification": source_result,
        "presentationAuthority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_root", type=Path)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = verify_session(
            args.session_root,
            contract=args.contract,
            gameassembly=args.gameassembly,
            metadata=args.metadata,
        )
    except (
        OSError,
        KeyError,
        TypeError,
        ValueError,
        SessionReceiptError,
        getattr(sys.modules.get("m27_receipt_verifier"), "ReceiptError", RuntimeError),
    ) as exc:
        reason = str(exc).replace("\r", " ").replace("\n", " ")
        reason = reason[:MAX_DIAGNOSTIC_CHARS]
        message = f"Endminf M27 mip-bias session receipt failed: {reason}"
        print(message, file=sys.stderr)
        if args.output:
            rejected = {
                "schema": RESULT_SCHEMA,
                "status": "rejected",
                "validator": "verify_endminf_m27_global_mip_bias_session",
                "failedGate": "session_receipt_validation",
                "reason": reason,
                "presentationAuthority": False,
            }
            try:
                _write_result(args.output, rejected)
            except OSError as output_exc:
                print(
                    "Endminf M27 mip-bias session receipt failed to write "
                    f"rejection report: {output_exc}",
                    file=sys.stderr,
                )
        return 1
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        _write_result(args.output, result)
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
