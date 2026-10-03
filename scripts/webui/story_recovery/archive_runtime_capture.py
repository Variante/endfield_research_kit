"""Retain closed runtime recordings as immutable, checksum-verified local ZIPs.

Saving proves byte preservation, not capture completeness or native ownership.
Keep historical settings, raw streams and diagnostics together; audit separately.
Generated archives and their inventories belong under reports/, outside Git.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import zipfile

if __name__ == "__main__" and not __package__:
    raise SystemExit("run as: python -m scripts.webui.story_recovery.archive_runtime_capture")

from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.runtime-capture-archive.v1"
DEFAULT_ROOT = REPO_ROOT / "reports/audio/captures"
CHUNK_BYTES = 1024 * 1024
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")


def token(value: str) -> str:
    if not TOKEN.fullmatch(value) or value in {".", ".."}:
        raise ValueError(f"invalid archive identifier: {value!r}")
    return value


def fingerprint(path: Path) -> tuple[int, int, int, int]:
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"capture input is not a regular file: {path}")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def digest_file(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(CHUNK_BYTES), b""):
            result.update(block)
    return result.hexdigest()


def input_files(inputs: dict[str, Path]) -> list[tuple[str, Path]]:
    if not inputs:
        raise ValueError("at least one capture input is required")
    files = []
    identities = set()
    for role, supplied in sorted(inputs.items()):
        token(role)
        if supplied.is_symlink():
            raise ValueError(f"symlink capture input is unsupported: {supplied}")
        root = supplied.resolve(strict=True)
        if root.is_dir():
            candidates = sorted(root.rglob("*"))
        else:
            candidates = [root]
        role_count = 0
        for path in candidates:
            if path.is_symlink():
                raise ValueError(f"symlink in capture input: {path}")
            if path.is_dir():
                continue
            fingerprint(path)
            relative = path.relative_to(root).as_posix() if root.is_dir() else path.name
            member = f"inputs/{role}/{relative}"
            identity = fingerprint(path)[:2]
            if identity in identities:
                raise ValueError(f"same file supplied more than once: {path}")
            identities.add(identity)
            files.append((member, path))
            role_count += 1
        if not role_count:
            raise ValueError(f"capture input contains no files: {root}")
    return files


def read_manifest(archive: zipfile.ZipFile) -> dict:
    members = archive.namelist()
    if len(members) != len(set(members)):
        raise ValueError("duplicate archive members")
    info = archive.getinfo("manifest.json")
    if info.file_size > MAX_MANIFEST_BYTES:
        raise ValueError("archive manifest exceeds the bounded inventory limit")
    result = json.loads(archive.read(info))
    if not isinstance(result, dict) or result.get("schema") != SCHEMA:
        raise ValueError("unsupported capture archive schema")
    token(result["sessionId"])
    if not isinstance(result.get("files"), list) or not result["files"]:
        raise ValueError("capture archive has no file inventory")
    inventoried = set()
    for row in result["files"]:
        member = row["member"]
        name = PurePosixPath(member)
        if (not isinstance(member, str) or "\\" in member or name.is_absolute()
                or ".." in name.parts or not member.startswith("inputs/")
                or name.as_posix() != member or member in inventoried):
            raise ValueError(f"unsafe or duplicate inventory member: {member!r}")
        if (type(row["bytes"]) is not int or row["bytes"] < 0
                or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])):
            raise ValueError(f"invalid inventory identity: {member}")
        inventoried.add(member)
    if set(members) != inventoried | {"manifest.json"}:
        raise ValueError("archive members differ from the inventory")
    return result


def verify_archive(path: Path) -> dict:
    """Re-read every saved byte, also checking ZIP CRC and exact membership."""
    with zipfile.ZipFile(path) as archive:
        manifest = read_manifest(archive)
        for row in manifest["files"]:
            info = archive.getinfo(row["member"])
            if info.file_size != row["bytes"]:
                raise ValueError(f"saved length differs: {row['member']}")
            sha = hashlib.sha256()
            size = 0
            with archive.open(info) as source:
                for block in iter(lambda: source.read(CHUNK_BYTES), b""):
                    sha.update(block)
                    size += len(block)
            if size != row["bytes"] or sha.hexdigest() != row["sha256"]:
                raise ValueError(f"saved SHA256 differs: {row['member']}")
    return manifest


def archive_capture(root: Path, session_id: str, kind: str, inputs: dict[str, Path],
                    notes: list[str]) -> Path:
    """Copy inputs without removing originals; never replace an existing archive."""
    token(session_id)
    token(kind)
    files = input_files(inputs)
    root = root.resolve()
    for supplied in inputs.values():
        source = supplied.resolve()
        if source.is_dir() and root.is_relative_to(source):
            raise ValueError("archive output is inside an input directory")
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"{session_id}.zip"
    if destination.exists():
        raise FileExistsError(f"saved capture already exists; verify it or use another ID: {destination}")
    for protected in (destination, root / "index.json", root / "index.md"):
        for _, source in files:
            if source == protected or (protected.exists() and os.path.samefile(source, protected)):
                raise ValueError(f"capture input aliases an archive publication path: {source}")
    before = {path: fingerprint(path) for _, path in files}
    manifest = {
        "schema": SCHEMA, "sessionId": session_id, "kind": kind,
        "savedUtc": datetime.now(timezone.utc).isoformat(),
        "preservationOnly": True,
        "evidenceBoundary": "Checksums prove preservation only. Capture completeness, settings provenance and current-build claims require their own audits.",
        "notes": notes, "files": [],
    }
    handle, temporary_name = tempfile.mkstemp(prefix=f".{session_id}-", suffix=".partial", dir=root)
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as archive:
            for member, path in files:
                sha = hashlib.sha256()
                size = 0
                with path.open("rb") as source, archive.open(member, "w", force_zip64=True) as target:
                    for block in iter(lambda: source.read(CHUNK_BYTES), b""):
                        target.write(block)
                        sha.update(block)
                        size += len(block)
                if fingerprint(path) != before[path] or size != before[path][2]:
                    raise ValueError(f"capture input changed while saving: {path}")
                manifest["files"].append({"member": member, "source": str(path),
                                          "bytes": size, "sha256": sha.hexdigest()})
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        verify_archive(temporary)
        # Re-read the originals too: a mid-copy mutation cannot produce a saved
        # mixture that passes only the archive's self-consistency check.
        for (_, path), row in zip(files, manifest["files"]):
            if (fingerprint(path) != before[path] or digest_file(path) != row["sha256"]
                    or fingerprint(path) != before[path]):
                raise ValueError(f"capture input changed before publication: {path}")
        if input_files(inputs) != files:
            raise ValueError("capture input file set changed while saving")
        # Same-volume hard link atomically publishes without replacing an old ZIP.
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def write_index(root: Path) -> Path:
    """Generate a small browsable catalog; archives remain the source of truth."""
    rows = []
    for path in sorted(root.glob("*.zip")):
        with zipfile.ZipFile(path) as archive:
            manifest = read_manifest(archive)
        rows.append({"sessionId": manifest["sessionId"], "kind": manifest["kind"],
                     "archive": path.name, "archiveBytes": path.stat().st_size,
                     "archiveSha256": digest_file(path), "fileCount": len(manifest["files"]),
                     "rawBytes": sum(row["bytes"] for row in manifest["files"]),
                     "notes": manifest["notes"]})
    lines = ["# Saved runtime captures", "", "Local retained evidence; saving does not validate playback or current-build claims.", "",
             "| Session | Kind | Files | Saved bytes |", "| --- | --- | ---: | ---: |"]
    for row in rows:
        lines.append(f"| [{row['sessionId']}]({row['archive']}) | {row['kind']} | {row['fileCount']} | {row['archiveBytes']:,} |")
    for row in rows:
        lines += ["", f"## {row['sessionId']}", ""] + [f"- {note}" for note in row["notes"]]
    root.mkdir(parents=True, exist_ok=True)
    for name, content in (("index.json", json.dumps({"schema": SCHEMA, "captures": rows}, ensure_ascii=False, indent=2) + "\n"),
                          ("index.md", "\n".join(lines) + "\n")):
        handle, temporary_name = tempfile.mkstemp(prefix=".index-", dir=root)
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as output:
                output.write(content)
            os.replace(temporary_name, root / name)
        finally:
            Path(temporary_name).unlink(missing_ok=True)
    return root / "index.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    save = commands.add_parser("save", help="Copy and verify closed capture inputs, leaving originals in place")
    save.add_argument("--session-id", required=True)
    save.add_argument("--kind", required=True)
    save.add_argument("--input", action="append", required=True, metavar="ROLE=PATH")
    save.add_argument("--note", action="append", default=[])
    save.add_argument("--archive-root", type=Path, default=DEFAULT_ROOT)
    verify = commands.add_parser("verify", help="Recheck every archived file's length, SHA256 and ZIP CRC")
    verify.add_argument("archive", type=Path)
    catalog = commands.add_parser("index", help="Refresh the small generated archive catalog")
    catalog.add_argument("--archive-root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            manifest = verify_archive(args.archive)
            print(f"Preservation verified: {manifest['sessionId']} ({len(manifest['files'])} files)")
        else:
            root = args.archive_root.resolve()
            if not root.is_relative_to(REPO_ROOT / "reports"):
                raise ValueError("generated capture archives must stay under reports/")
            if args.command == "save":
                inputs = {}
                for supplied in args.input:
                    role, separator, source = supplied.partition("=")
                    if not separator or not source or role in inputs:
                        raise ValueError(f"invalid or duplicate input role: {supplied!r}")
                    inputs[token(role)] = Path(source)
                saved = archive_capture(root, args.session_id, args.kind, inputs, args.note)
                print(f"Capture saved and preservation verified: {saved}")
            print(f"Capture catalog: {write_index(root)}")
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(f"Capture archive failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
