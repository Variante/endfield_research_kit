"""Provenance and output helpers shared by the installed-corpus gates."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from scripts.common import sha256_file_upper as _sha256_file


def require_equal(
    failures: list[dict[str, Any]],
    *,
    scope: str,
    field: str,
    actual: Any,
    expected: Any,
) -> None:
    if actual != expected:
        failures.append(
            {"scope": scope, "field": field, "expected": expected, "actual": actual}
        )


def validate_provenance(
    summary: dict[str, Any],
    header: dict[str, Any],
    ledger_path: Path,
    expected_input_set_sha256: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    expected = expected_input_set_sha256.upper()
    ledger_sha256 = _sha256_file(ledger_path)
    require_equal(
        failures,
        scope="outer-summary",
        field="inputSetSha256",
        actual=str(summary.get("inputSetSha256", "")).upper(),
        expected=expected,
    )
    require_equal(
        failures,
        scope="outer-summary",
        field="summary.fullAuditPassed",
        actual=(summary.get("summary") or {}).get("fullAuditPassed"),
        expected=True,
    )
    require_equal(
        failures,
        scope="outer-summary",
        field="publication.ledgerSha256",
        actual=str((summary.get("publication") or {}).get("ledgerSha256", "")).upper(),
        expected=ledger_sha256,
    )
    require_equal(
        failures,
        scope="outer-ledger-header",
        field="schemaVersion",
        actual=header.get("schemaVersion"),
        expected=1,
    )
    require_equal(
        failures,
        scope="outer-ledger-header",
        field="inputSetSha256",
        actual=str(header.get("inputSetSha256", "")).upper(),
        expected=expected,
    )
    for field in ("primaryAssets", "fallbackAssets"):
        require_equal(
            failures,
            scope="outer-ledger-header",
            field=field,
            actual=header.get(field),
            expected=summary.get(field),
        )
    return failures, {
        "inputSetSha256": expected,
        "outerSummary": str(summary.get("format", "")),
        "outerLedger": ledger_path.as_posix(),
        "outerLedgerSha256": ledger_sha256,
        "primaryAssets": header.get("primaryAssets"),
        "fallbackAssets": header.get("fallbackAssets"),
    }


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def atomic_write_json(path: Path, value: Any, *, sort_keys: bool = False,
                      skip_unchanged: bool = False) -> None:
    """Stream canonical corpus JSON; never materialize a multi-GB document.

    The completed temporary file replaces its destination atomically. Identical
    canonical bytes preserve the existing file and its cache timestamp.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        digest = hashlib.sha256()
        with os.fdopen(descriptor, "wb") as stream:
            pending = []
            characters = 0
            def write_pending():
                nonlocal characters
                block = "".join(pending).encode("utf-8")
                stream.write(block)
                digest.update(block)
                pending.clear()
                characters = 0
            encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=sort_keys, indent=2)
            for fragment in encoder.iterencode(value):
                pending.append(fragment)
                characters += len(fragment)
                if characters >= 1024 * 1024:
                    write_pending()
            pending.append("\n")
            write_pending()
        if skip_unchanged and path.is_file() and path.stat().st_size == Path(temporary_name).stat().st_size:
            with path.open("rb") as previous:
                if hashlib.file_digest(previous, "sha256").digest() == digest.digest():
                    os.unlink(temporary_name)
                    return
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def is_bounded_diagnostic_output(path: Path, repo_root: Path) -> bool:
    resolved = path.resolve()
    return any(
        resolved == base or base in resolved.parents
        for base in (repo_root / "tmp", repo_root / "scratch")
    )
