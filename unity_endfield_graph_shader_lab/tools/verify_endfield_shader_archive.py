#!/usr/bin/env python3
"""Validate EndfieldCapture's bounded session-end D3D11 shader archive."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


class VerificationError(RuntimeError):
    pass


def build_report(session: Path) -> dict[str, Any]:
    archive = session / "graphics" / "shaders"
    manifest_path = archive / "manifest.json"
    if not manifest_path.is_file():
        raise VerificationError(f"shader archive manifest is absent: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "endfieldCapture.shaderArchive.v1":
        raise VerificationError("shader archive schema is unsupported")
    registrations = manifest.get("registrations")
    if not isinstance(registrations, list):
        raise VerificationError("shader archive registrations are absent")

    errors: list[str] = []
    files: dict[str, dict[str, Any]] = {}
    for index, registration in enumerate(registrations):
        if not isinstance(registration, dict):
            errors.append(f"registration {index} is not an object")
            continue
        filename = registration.get("file")
        digest = registration.get("sha256")
        if not isinstance(filename, str) or not filename.endswith(".dxbc"):
            errors.append(f"registration {index} has an invalid payload filename")
            continue
        if not isinstance(digest, str) or len(digest) != 64:
            errors.append(f"registration {index} has an invalid SHA-256")
            continue
        path = archive / filename
        row = files.setdefault(filename, {
            "file": filename,
            "path": str(path.resolve()),
            "sha256": digest,
            "registrationCount": 0,
        })
        row["registrationCount"] += 1
        expected_identity = int(digest[:16], 16)
        if int(registration.get("identityHash", -1)) != expected_identity:
            errors.append(
                f"registration {index} identityHash does not match its SHA-256 prefix"
            )
        if int(registration.get("bytecodeSize", -1)) <= 0:
            errors.append(f"registration {index} has no bytecode size")

    unique_bytes = 0
    for filename, row in files.items():
        path = archive / filename
        if not path.is_file():
            errors.append(f"shader payload is absent: {filename}")
            continue
        payload = path.read_bytes()
        actual = hashlib.sha256(payload).hexdigest()
        row["byteSize"] = len(payload)
        row["actualSha256"] = actual
        unique_bytes += len(payload)
        if actual != row["sha256"]:
            errors.append(f"shader payload hash mismatch: {filename}")

    if manifest.get("complete") is not True:
        errors.append("shader archive manifest is not complete")
    if int(manifest.get("registrationCount", -1)) != len(registrations):
        errors.append("shader archive registrationCount is inconsistent")
    if int(manifest.get("uniqueFileCount", -1)) != len(files):
        errors.append("shader archive uniqueFileCount is inconsistent")
    if int(manifest.get("uniqueBytes", -1)) != unique_bytes:
        errors.append("shader archive uniqueBytes is inconsistent")
    if not registrations:
        errors.append("shader archive contains no registrations")

    return {
        "schema": "endfield.shader-bytecode-archive-verification.v1",
        "status": "validated" if not errors else "rejected",
        "session": str(session.resolve()),
        "manifest": str(manifest_path.resolve()),
        "registrationCount": len(registrations),
        "uniqueFileCount": len(files),
        "uniqueBytes": unique_bytes,
        "files": sorted(files.values(), key=lambda row: row["file"]),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = build_report(args.session.resolve())
    except (OSError, ValueError, VerificationError) as exc:
        print(f"ERROR: {exc}")
        return 2
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(args.output)
    else:
        print(text, end="")
    for error in report["errors"]:
        print(f"ERROR: {error}")
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
