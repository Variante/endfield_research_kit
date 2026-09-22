"""Re-pin the contract fingerprints an exporter rebuild invalidates.

``inputSetSha256`` is not a fingerprint of the game's data.  The VFS audit that
produces it hashes the normalized asset roots *plus* `app.info`,
`GameAssembly.dll`, `Endfield.exe`, `global-metadata.dat` and the running
``AnimeStudio.CLI`` binary, so **rebuilding the exporter changes it with the
game data untouched**.  Every corpus gate then reports a mismatch that is
neither a client update nor a regression, and the reviewed contracts carrying
the old value stop matching.

That is correct fail-closed behaviour, and this module is the maintained way
back out of it -- the alternative being hand-edited hashes, which the repo rules
forbid for good reason.  It does two mechanical things and refuses everything
else:

1. replaces ``inputSetSha256`` in every contract that carries it, with the value
   from a *fresh* audit summary;
2. brings the pins that depend on those bytes back to a fixed point: the
   ``dependencies[].sha256`` rows contracts record for each other, and the
   ``CONTRACT_SHA256`` digest each ``*_native.py`` loader pins for its own
   contract.

**The safety gate is what makes this legitimate rather than a way to silence a
gate.**  A re-pin is only sound when the *game build* is the one the contracts
were derived against and only the exporter moved.  So the audit's recorded
`GameAssembly.dll` and `global-metadata.dat` must equal the installed build's,
and must also equal what the contracts themselves record in ``nativeInputs``.
If a client update is what moved the fingerprint, those checks fail and nothing
is written -- because then the contracts' rows really may be stale, and the
answer is to regenerate them against the new build, not to re-pin them.

Editing happens on bytes, never through ``json.dump``.  A contract is pinned by
its exact bytes, 217 of these files are CRLF on disk and three are deliberately
mixed, so a round-trip through a JSON serializer would rewrite line endings and
break every pin with no other visible symptom.  Replacing a 64-character hex
substring leaves every other byte alone.

Reports what it would change and exits non-zero unless ``--write`` is given.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.repo_paths import REPO_ROOT as REPO


DEFAULT_AUDIT = REPO / "reports/animestudio/vfs_understanding_latest.json"
GAME_ASSEMBLY = "GameAssembly.dll"
GLOBAL_METADATA = "global-metadata.dat"
HEX64 = re.compile(r"^[0-9A-Fa-f]{64}$")
CONTRACT_PATH_PATTERN = re.compile(r'CONTRACT_PATH\s*=\s*CONTRACTS_DIR\s*/\s*"([^"]+)"')
CONTRACT_SHA_PATTERN = re.compile(r'(CONTRACT_SHA256\s*=\s*")([0-9A-Fa-f]{64})(")')
# A cascade is a few rounds deep at most; more than this is a cycle, not depth.
MAX_ROUNDS = 12


def sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def audit_build_fingerprints(summary: dict[str, Any]) -> dict[str, str]:
    """The audit's recorded hash for each build input, by file name."""
    found: dict[str, str] = {}
    for row in summary.get("buildFingerprints", []):
        name = str(row.get("path", "")).replace("\\", "/").rsplit("/", 1)[-1]
        if name and row.get("sha256"):
            found[name] = str(row["sha256"]).upper()
    return found


def check_same_game_build(
    summary: dict[str, Any], contracts: dict[Path, dict[str, Any]]
) -> dict[str, Any]:
    """Refuse unless only the exporter moved.

    Three readings of the same two files must agree: what the installed build
    has now, what the audit recorded while producing the new fingerprint, and
    what the contracts recorded when their rows were derived. Any disagreement
    means a client update is in play, and a re-pin would carry stale rows
    forward under a fresh-looking fingerprint.
    """
    gate = check_installed_native_inputs()
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail}
    installed = {
        GAME_ASSEMBLY: (gate.gameassembly_sha256 or "").upper(),
        GLOBAL_METADATA: (gate.metadata_sha256 or "").upper(),
    }
    audited = audit_build_fingerprints(summary)
    disagreements: list[dict[str, str]] = []
    for name, value in installed.items():
        if audited.get(name) != value:
            disagreements.append({
                "input": name, "installed": value,
                "audit": audited.get(name, "<absent>"), "source": "audit",
            })
    for path, contract in contracts.items():
        native = contract.get("nativeInputs") or {}
        for name, value in installed.items():
            recorded = str(native.get(name, "")).upper()
            if recorded and recorded != value:
                disagreements.append({
                    "input": name, "installed": value,
                    "contract": recorded, "source": path.name,
                })
    return {
        "status": "validated" if not disagreements else "different-game-build",
        "installed": installed,
        "audit": {name: audited.get(name) for name in installed},
        "disagreements": disagreements[:20],
    }


def _replace_hex(raw: bytes, field: str, new: str) -> tuple[bytes, str | None]:
    """Swap one JSON string field's 64-hex value, leaving every other byte.

    Returns the bytes and the value replaced, or None when the field is absent
    or already current.
    """
    pattern = re.compile(
        b'("' + field.encode("ascii") + rb'"\s*:\s*")([0-9A-Fa-f]{64})(")')
    match = pattern.search(raw)
    if match is None:
        return raw, None
    previous = match.group(2).decode("ascii")
    if previous.upper() == new.upper():
        return raw, None
    return pattern.sub(match.group(1) + new.encode("ascii") + match.group(3), raw, count=1), previous


def _refresh_dependency_rows(path: Path, contracts_dir: Path) -> list[dict[str, str]]:
    """Bring one contract's ``dependencies[]`` hashes to the files on disk."""
    raw = path.read_bytes()
    try:
        contract = json.loads(raw)
    except ValueError:
        return []
    changes: list[dict[str, str]] = []
    for row in contract.get("dependencies", []):
        target = contracts_dir / row["path"]
        if not target.exists():
            continue
        actual = sha256_bytes(target)
        recorded = str(row.get("sha256", "")).upper()
        if actual == recorded:
            continue
        pattern = re.compile(
            rb'("' + re.escape(recorded.encode("ascii")) + rb'")', re.IGNORECASE)
        updated, count = pattern.subn(b'"' + actual.encode("ascii") + b'"', raw, count=1)
        if count:
            raw = updated
            changes.append({"contract": path.name, "dependency": row["path"],
                            "from": recorded, "to": actual})
    if changes:
        path.write_bytes(raw)
    return changes


def _tabled_pins(text: str, contracts_dir: Path) -> list[tuple[str, str]]:
    """``(contract file, pinned digest)`` pairs a module records in a table.

    Some modules pin one contract through ``CONTRACT_PATH`` /
    ``CONTRACT_SHA256`` declared far apart; others pin several at once in a
    table of records, where the file name and its digest sit side by side --
    ``buff_frontiers_native.FRONTIERS`` is the case that matters. Reading the
    second shape from the syntax tree finds those pairs without a regex having
    to guess how the literals are spaced, and a node that holds both a known
    contract name and a 64-hex string is unambiguous.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    pairs: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Call, ast.Tuple, ast.List)):
            continue
        parts = list(node.args) if isinstance(node, ast.Call) else list(node.elts)
        literals = [item.value for item in parts
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)]
        files = [value for value in literals
                 if value.endswith(".json") and (contracts_dir / value).exists()]
        digests = [value for value in literals if HEX64.match(value)]
        if len(files) == 1 and len(digests) == 1:
            pairs.append((files[0], digests[0]))
    return pairs


def _refresh_module_pins(contracts_dir: Path) -> list[dict[str, str]]:
    """Bring every digest a module pins for a contract to that file's bytes."""
    changes: list[dict[str, str]] = []
    for module in sorted((REPO / "scripts/game_data").rglob("*.py")):
        if module.name == "contracts_repin.py":
            continue
        text = module.read_text(encoding="utf-8")
        updated = text
        for name, recorded in _tabled_pins(text, contracts_dir):
            actual = sha256_bytes(contracts_dir / name)
            if recorded.upper() == actual:
                continue
            # Keep the module's own case convention; the loader compares
            # case-insensitively, and a needless case flip is noise in review.
            replacement = actual.lower() if recorded.islower() else actual
            updated = updated.replace(f'"{recorded}"', f'"{replacement}"')
            changes.append({"module": module.name, "contract": name,
                            "from": recorded.upper(), "to": actual})
        if updated != text:
            module.write_text(updated, encoding="utf-8")
    for module in sorted((REPO / "scripts/game_data").rglob("*.py")):
        text = module.read_text(encoding="utf-8")
        names = CONTRACT_PATH_PATTERN.findall(text)
        pins = [match[1] for match in CONTRACT_SHA_PATTERN.findall(text)]
        if len(names) != 1 or len(pins) != 1:
            continue
        target = contracts_dir / names[0]
        if not target.exists():
            continue
        actual = sha256_bytes(target)
        if pins[0].upper() == actual:
            continue
        module.write_text(
            CONTRACT_SHA_PATTERN.sub(lambda m: m.group(1) + actual + m.group(3), text, count=1),
            encoding="utf-8")
        changes.append({"module": module.name, "contract": names[0],
                        "from": pins[0].upper(), "to": actual})
    return changes


def repin(
    *, audit_summary: Path = DEFAULT_AUDIT, contracts_dir: Path = CONTRACTS_DIR,
    write: bool = False,
) -> dict[str, Any]:
    """Re-pin the exporter fingerprint and settle every hash that depends on it."""
    if not audit_summary.is_file():
        return {"status": "missing-audit", "detail": str(audit_summary)}
    summary = json.loads(audit_summary.read_bytes())
    fingerprint = str(summary.get("inputSetSha256", "")).upper()
    if not HEX64.match(fingerprint):
        return {"status": "unusable-audit", "detail": "no inputSetSha256"}

    contracts = {}
    for path in sorted(contracts_dir.glob("*.json")):
        try:
            value = json.loads(path.read_bytes())
        except ValueError:
            continue
        if isinstance(value, dict) and value.get("inputSetSha256"):
            contracts[path] = value

    gate = check_same_game_build(summary, contracts)
    if gate["status"] != "validated":
        return {"status": gate["status"], "gate": gate,
                "detail": "refusing to re-pin: this is not an exporter-only change"}

    planned = [
        {"contract": path.name,
         "from": str(value["inputSetSha256"]).upper(), "to": fingerprint}
        for path, value in contracts.items()
        if str(value["inputSetSha256"]).upper() != fingerprint
    ]
    result: dict[str, Any] = {
        "status": "validated",
        "auditSummary": str(audit_summary),
        "inputSetSha256": fingerprint,
        "gate": gate,
        "contractsCarryingFingerprint": len(contracts),
        "fingerprintUpdates": planned,
        "dependencyUpdates": [],
        "modulePinUpdates": [],
        "rounds": 0,
    }
    if not write:
        result["status"] = "dry-run" if planned else "already-current"
        return result

    for path in contracts:
        raw, previous = _replace_hex(path.read_bytes(), "inputSetSha256", fingerprint)
        if previous is not None:
            path.write_bytes(raw)

    # Changing a contract's bytes invalidates every hash recorded for it, and
    # that fix changes those files in turn. Iterate until nothing moves.
    for round_number in range(1, MAX_ROUNDS + 1):
        moved: list[dict[str, str]] = []
        for path in sorted(contracts_dir.glob("*.json")):
            moved.extend(_refresh_dependency_rows(path, contracts_dir))
        pins = _refresh_module_pins(contracts_dir)
        result["dependencyUpdates"].extend(moved)
        result["modulePinUpdates"].extend(pins)
        result["rounds"] = round_number
        if not moved and not pins:
            break
    else:
        result["status"] = "unsettled"
    return result


def verify(contracts_dir: Path = CONTRACTS_DIR) -> dict[str, Any]:
    """Re-check every dependency row and loader pin against the files on disk."""
    stale_rows: list[dict[str, str]] = []
    checked_rows = 0
    for path in sorted(contracts_dir.glob("*.json")):
        try:
            contract = json.loads(path.read_bytes())
        except ValueError:
            continue
        for row in contract.get("dependencies", []):
            target = contracts_dir / row["path"]
            if not target.exists():
                stale_rows.append({"contract": path.name, "dependency": row["path"],
                                   "reason": "missing"})
                continue
            checked_rows += 1
            if sha256_bytes(target) != str(row.get("sha256", "")).upper():
                stale_rows.append({"contract": path.name, "dependency": row["path"],
                                   "reason": "sha256"})
    stale_pins: list[dict[str, str]] = []
    checked_pins = 0
    for module in sorted((REPO / "scripts/game_data").rglob("*.py")):
        text = module.read_text(encoding="utf-8")
        names = CONTRACT_PATH_PATTERN.findall(text)
        pins = [match[1] for match in CONTRACT_SHA_PATTERN.findall(text)]
        if len(names) != 1 or len(pins) != 1:
            continue
        target = contracts_dir / names[0]
        if not target.exists():
            continue
        checked_pins += 1
        if pins[0].upper() != sha256_bytes(target):
            stale_pins.append({"module": module.name, "contract": names[0]})
    return {
        "status": "validated" if not stale_rows and not stale_pins else "stale",
        "dependencyRowsChecked": checked_rows,
        "staleDependencyRows": stale_rows,
        "modulePinsChecked": checked_pins,
        "staleModulePins": stale_pins,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-summary", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--write", action="store_true",
                        help="apply the re-pin; without it nothing is written")
    parser.add_argument("--verify", action="store_true",
                        help="only re-check every dependency row and loader pin")
    args = parser.parse_args()
    try:
        if args.verify:
            result = verify()
        else:
            result = repin(audit_summary=args.audit_summary, write=args.write)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "failed", "detail": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
    return 0 if result["status"] in ("validated", "already-current") else 2


if __name__ == "__main__":
    raise SystemExit(main())
