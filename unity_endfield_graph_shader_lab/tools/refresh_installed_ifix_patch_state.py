#!/usr/bin/env python3
"""Refresh the hash-pinned installed IFix patch evidence.

The installed Persistent VFS overlay changes independently of the tracked
source notes.  This tool reads the current DAFE52C9 block, extracts the
Gameplay.Beyond patch, discovers its type/target tables, and rewrites the
ignored evidence report consumed by ``verify_installed_ifix_patch_state.py``.
It never launches the game or contacts the network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from datetime import date
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
DEFAULT_GAME_ROOT = Path(r"D:/Program Files/Endfield Game")
DEFAULT_REPORT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/"
    "CharInfoPresentation/installed_ifix_patch_state.json"
)
DEFAULT_EVIDENCE_ROOT = LAB_ROOT / "scratch/character_recovery/ifix_patch_state"
IFIX_BLOCK = "DAFE52C9"
PATCH_NAME = "Data/IFixPatchOut/Windows/Gameplay.Beyond.patch.bytes"
BRIDGE_MARKER = b"IFix.ILFixInterfaceBridge"


def _decoder_module():
    sys.path.insert(0, str(REPO_ROOT / "scripts/chk_decode"))
    import decode_persistent_vfs as decoder  # type: ignore

    return decoder


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest().upper()


def read_i32(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError(f"truncated int32 at 0x{offset:x}")
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def read_string(data: bytes, offset: int) -> tuple[str, int]:
    length = 0
    shift = 0
    for _ in range(5):
        if offset >= len(data):
            raise ValueError("truncated 7-bit string length")
        value = data[offset]
        offset += 1
        length |= (value & 0x7F) << shift
        if not value & 0x80:
            end = offset + length
            if end > len(data):
                raise ValueError("truncated string payload")
            return data[offset:end].decode("utf-8"), end
        shift += 7
    raise ValueError("invalid 7-bit string length")


def short_type(value: str) -> str:
    return value.split(",", 1)[0]


def find_bridge_offset(data: bytes) -> int:
    marker = data.find(BRIDGE_MARKER)
    if marker < 0:
        raise ValueError("IFix bridge string marker is absent")
    for offset in range(max(0, marker - 5), marker + 1):
        try:
            value, end = read_string(data, offset)
        except ValueError:
            continue
        if marker >= offset and value.startswith("IFix.ILFixInterfaceBridge"):
            return offset
    raise ValueError("could not recover the bridge string offset")


def parse_type_table(data: bytes, bridge_offset: int) -> tuple[str, list[str], int]:
    bridge, offset = read_string(data, bridge_offset)
    if not bridge.startswith("IFix.ILFixInterfaceBridge"):
        raise ValueError(f"unexpected IFix bridge type: {bridge!r}")
    type_count, offset = read_i32(data, offset)
    if not 1 <= type_count <= 4096:
        raise ValueError(f"unreasonable IFix type count: {type_count}")
    types: list[str] = []
    for _ in range(type_count):
        value, offset = read_string(data, offset)
        if not value or not all(char.isprintable() for char in value):
            raise ValueError("type table contains a non-printable/empty identity")
        types.append(value)
    return bridge, types, offset


def parse_target_table(data: bytes, offset: int, types: list[str]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    start = offset
    target_count, offset = read_i32(data, offset)
    if not 1 <= target_count <= 1024:
        raise ValueError(f"unreasonable IFix target count: {target_count}")
    targets: list[dict[str, Any]] = []
    for _ in range(target_count):
        if offset >= len(data):
            raise ValueError("truncated IFix target flags")
        flags = data[offset]
        offset += 1
        if flags != 0:
            raise ValueError(f"unexpected target flags: {flags}")
        type_index, offset = read_i32(data, offset)
        if not 0 <= type_index < len(types):
            raise ValueError("target type index is outside the type table")
        method, offset = read_string(data, offset)
        if not method or len(method) > 256 or not all(char.isprintable() for char in method):
            raise ValueError("target method is empty, oversized, or non-printable")
        parameter_count, offset = read_i32(data, offset)
        if not 0 <= parameter_count <= 64:
            raise ValueError("unreasonable IFix parameter count")
        parameter_indexes: list[int] = []
        for _ in range(parameter_count):
            parameter_index, offset = read_i32(data, offset)
            if not 0 <= parameter_index < len(types):
                raise ValueError("target parameter index is outside the type table")
            parameter_indexes.append(parameter_index)
        implementation_index, offset = read_i32(data, offset)
        if implementation_index < 0:
            raise ValueError("negative IFix implementation index")
        targets.append(
            {
                "type": short_type(types[type_index]),
                "method": method,
                "parameters": [short_type(types[index]) for index in parameter_indexes],
                "implementation_index": implementation_index,
            }
        )
    target_end = offset
    terminal, offset = read_i32(data, offset)
    if terminal != 0 or offset != len(data):
        raise ValueError("IFix target table does not terminate exactly at file end")
    return targets, {
        "target_table_offset": start,
        "target_count": target_count,
        "target_table_end": target_end,
        "terminal_int32": terminal,
        "file_end": offset,
    }


def discover_patch_layout(data: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return the unique self-terminating target table in a patch payload."""

    bridge_offset = find_bridge_offset(data)
    bridge, types, type_end = parse_type_table(data, bridge_offset)
    candidates: list[tuple[list[dict[str, Any]], dict[str, int]]] = []
    for offset in range(type_end, len(data) - 8):
        try:
            targets, details = parse_target_table(data, offset, types)
        except (UnicodeDecodeError, ValueError):
            continue
        candidates.append((targets, details))
    if len(candidates) != 1:
        raise ValueError(
            f"expected exactly one self-terminating IFix target table, found {len(candidates)}"
        )
    targets, details = candidates[0]
    layout: dict[str, Any] = {
        "bridge_string_offset": f"0x{bridge_offset:x}",
        "bridge": bridge,
        "type_count": len(types),
        "type_table_end": f"0x{type_end:x}",
        "target_table_offset": f"0x{details['target_table_offset']:x}",
        "target_count": details["target_count"],
        "target_table_end": f"0x{details['target_table_end']:x}",
        "terminal_int32": details["terminal_int32"],
        "file_end": f"0x{details['file_end']:x}",
        "record_layout": (
            "byte flags; int32 declaring-type index; BinaryReader 7-bit-length UTF-8 "
            "method name; int32 parameter count; int32 parameter type indexes; "
            "int32 interpreter implementation index"
        ),
        "identity_note": (
            "Patch records identify targets by declaring type, method name, and "
            "parameter-type signature. Wrapper gate constants are not on-disk target-table keys."
        ),
    }
    return targets, layout


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def installed_path(path: Path) -> str:
    return path.resolve().as_posix()


def build_index(info: Any, chunk: Any, chunk_path: Path, persistent_root: Path) -> dict[str, Any]:
    chunk_name = chunk.chk_file_name()
    files: list[dict[str, Any]] = []
    for file_info in chunk.files:
        files.append(
            {
                "blockType": "IFixPatchOut",
                "chunkMd5": file_info.file_chunk_md5.to_bytes(16, "little").hex().upper(),
                "dataMd5": file_info.file_data_md5.to_bytes(16, "little").hex().upper(),
                "encrypted": file_info.use_encrypt,
                "ivSeed": file_info.iv_seed,
                "length": file_info.length,
                "name": file_info.file_name,
                "nameHash": file_info.file_name_hash,
                "offset": file_info.offset,
                "tag": "None" if file_info.file_tag == 0 else file_info.file_tag,
            }
        )
    chunk_record = {
        "absolutePath": installed_path(chunk_path),
        "blockType": "IFixPatchOut",
        "byteCount": chunk.length,
        "chunkCount": 1,
        "contentMd5": chunk.content_md5.to_bytes(16, "little").hex().upper(),
        "exists": chunk_path.is_file(),
        "fileCount": len(files),
        "fileName": chunk_name,
        "files": files,
        "length": chunk.length,
        "md5Name": chunk.md5_name.to_bytes(16, "little").hex().upper(),
        "relativePath": f"{IFIX_BLOCK}/{chunk_name}",
        "source": "primary",
        "tag": "None",
    }
    block = {
        "blockType": "IFixPatchOut",
        "byteCount": chunk.length,
        "chunkCount": 1,
        "chunks": [chunk_record],
        "codeVersion": info.code_version,
        "declaredChunkBytes": info.group_chunks_length,
        "declaredFileCount": info.group_file_info_num,
        "fileCount": len(files),
        "groupConfigHashName": info.group_cfg_hash_name,
        "groupConfigName": info.group_cfg_name,
        "hashDirectory": IFIX_BLOCK,
        "missingChunkCount": 0,
        "name": info.group_cfg_name,
        "version": info.version,
    }
    return {
        "blockFilter": "IFixPatchOut",
        "blocks": [block],
        "fallbackAssets": installed_path(persistent_root),
        "files": [
            {
                **files[index],
                "blockName": "IFixPatchOut",
                "chunkAbsolutePath": installed_path(chunk_path),
                "chunkContentMd5": chunk_record["contentMd5"],
                "chunkExists": chunk_path.is_file(),
                "chunkFile": chunk_name,
                "chunkLength": chunk.length,
                "chunkMd5Name": chunk_record["md5Name"],
                "chunkRelativePath": f"{IFIX_BLOCK}/{chunk_name}",
                "chunkSource": "primary",
                "fileBlockType": "IFixPatchOut",
                "fileChunkMd5": files[index]["chunkMd5"],
                "fileDataMd5": files[index]["dataMd5"],
                "fileName": files[index]["name"],
                "fileNameHash": files[index]["nameHash"],
                "fileTag": files[index]["tag"],
                "hashDirectory": IFIX_BLOCK,
                "ivSeed": files[index]["ivSeed"],
                "length": files[index]["length"],
                "offset": files[index]["offset"],
            }
            for index in range(len(files))
        ],
        "generatedAtEpoch": 0,
        "missingBlocks": [],
        "schemaVersion": 1,
        "streamingAssets": installed_path(persistent_root),
        "summary": {
            "blockCount": 1,
            "byteCount": chunk.length,
            "chunkCount": 1,
            "fileCount": len(files),
            "missingBlockCount": 0,
            "missingChunkCount": 0,
        },
    }


def dynamic_file_record(path: Path) -> dict[str, Any]:
    return {
        "path_at_recovery": installed_path(path),
        "size": path.stat().st_size,
        "sha256": sha256(path),
    }


def refresh(game_root: Path, report_path: Path, evidence_root: Path) -> dict[str, Any]:
    decoder = _decoder_module()
    persistent_root = game_root / "Endfield_Data/Persistent"
    block_dir = persistent_root / "VFS" / IFIX_BLOCK
    blc_path = block_dir / f"{IFIX_BLOCK}.blc"
    if not blc_path.is_file():
        raise FileNotFoundError(f"IFix VFS block catalog not found: {blc_path}")
    info = decoder.parse_block_main_info(decoder.decrypt_blc(blc_path), verify_crc=True)
    if info.group_cfg_name != "IFixPatchOut" or not info.chunks:
        raise ValueError(f"unexpected IFix block catalog: {info.group_cfg_name!r}")
    patch_chunk = None
    patch_file = None
    for chunk in info.chunks:
        for file_info in chunk.files:
            if file_info.file_name == PATCH_NAME:
                patch_chunk, patch_file = chunk, file_info
                break
        if patch_file is not None:
            break
    if patch_chunk is None or patch_file is None:
        raise ValueError(f"IFix block does not contain {PATCH_NAME}")
    chunk_path = block_dir / patch_chunk.chk_file_name()
    if not chunk_path.is_file():
        raise FileNotFoundError(f"IFix VFS chunk not found: {chunk_path}")
    patch_bytes = decoder.extract_file(chunk_path, patch_file)
    expected_md5 = patch_file.file_data_md5.to_bytes(16, "little").hex().upper()
    if md5(patch_bytes) != expected_md5:
        raise ValueError(f"IFix patch MD5 mismatch: {md5(patch_bytes)} != {expected_md5}")
    targets, patch_format = discover_patch_layout(patch_bytes)

    evidence_root.mkdir(parents=True, exist_ok=True)
    index_path = evidence_root / "persistent_primary_ifix_vfs_index.json"
    index_payload = build_index(info, patch_chunk, chunk_path, persistent_root)
    index_payload["generatedAtEpoch"] = int(date.today().strftime("%Y%m%d"))
    index_path.write_text(json.dumps(index_payload, indent=2) + "\n", encoding="utf-8")
    patch_path = evidence_root / "dump" / Path(PATCH_NAME)
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path.write_bytes(patch_bytes)

    if not report_path.is_file():
        raise FileNotFoundError(f"existing IFix report is required as a static-loader template: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    source_build = report.setdefault("source_build", {})
    source_build["game_assembly"] = dynamic_file_record(game_root / "GameAssembly.dll")
    source_build["global_metadata"] = dynamic_file_record(
        game_root / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat"
    )

    vfs = report.setdefault("vfs_state", {})
    persistent = vfs.setdefault("persistent_overlay", {})
    persistent["index"] = {
        "repo_path": repo_path(index_path),
        "size": index_path.stat().st_size,
        "sha256": sha256(index_path),
    }
    persistent["block_version"] = info.version
    persistent["code_version"] = info.code_version
    persistent["file_count"] = info.group_file_info_num
    persistent["chunk_count"] = len(info.chunks)
    persistent["byte_count"] = info.group_chunks_length
    persistent["file"] = {
        "vfs_name": PATCH_NAME,
        "data_md5": expected_md5,
        "encrypted_in_vfs": patch_file.use_encrypt,
        "extracted_repo_path": repo_path(patch_path),
        "size": len(patch_bytes),
        "sha256": sha256(patch_path),
    }
    persistent["chunk"] = {
        "path_at_recovery": installed_path(chunk_path),
        "content_md5": md5(chunk_path.read_bytes()),
        "size": chunk_path.stat().st_size,
        "sha256": sha256(chunk_path),
    }
    persistent["block_catalog"] = dynamic_file_record(blc_path)

    launcher = vfs.setdefault("launcher_manifests", {})
    for name, filename in (
        ("verify_files_json", "verify_files.json"),
        ("game_files", "game_files"),
        ("package_files", "package_files"),
    ):
        launcher[name] = dynamic_file_record(game_root / filename)
    installed_hashes = vfs.setdefault("installed_index_hashes", {})
    for key, path in (
        ("persistent_index_initial", persistent_root / "index_initial.json"),
        ("persistent_index_main", persistent_root / "index_main.json"),
        ("persistent_pref_initial", persistent_root / "pref_initial.json"),
        ("persistent_pref_main", persistent_root / "pref_main.json"),
        ("streaming_index_initial", game_root / "Endfield_Data/StreamingAssets/index_initial.json"),
        ("streaming_index_main", game_root / "Endfield_Data/StreamingAssets/index_main.json"),
    ):
        installed_hashes[key] = sha256(path)

    report["recovered_at"] = date.today().isoformat()
    report["scope"] = (
        "Current files already present on this machine only. The game was not launched "
        "and no network request was made for this refresh."
    )
    report["outcome"] = (
        f"The current Persistent IFixPatchOut overlay contains one encrypted "
        f"Gameplay.Beyond patch with {len(targets)} signature records. "
        "The protected Character Info/render target audit remains empty; "
        "remote or future payloads remain outside this snapshot."
    )
    report["patch_format"] = patch_format
    report["patch_format"]["type_table_end"] = patch_format["type_table_end"]
    report["targets"] = targets
    report["refresh"] = {
        "tool": "unity_endfield_graph_shader_lab/tools/refresh_installed_ifix_patch_state.py",
        "target_discovery": "unique self-terminating table at file end",
        "source_block": IFIX_BLOCK,
        "source_chunk": patch_chunk.chk_file_name(),
        "source_patch_sha256": sha256(patch_path),
        "source_patch_size": len(patch_bytes),
        "evidence_boundary": (
            "The refreshed report proves only the currently installed local IFix target table; "
            "runtime slot ownership and remote/downloaded payloads remain capture-only."
        ),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return {
        "report": str(report_path),
        "patch": str(patch_path),
        "chunk": str(chunk_path),
        "block_version": info.version,
        "patch_size": len(patch_bytes),
        "patch_sha256": sha256(patch_path),
        "target_count": len(targets),
        "target_table_offset": patch_format["target_table_offset"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    args = parser.parse_args()
    result = refresh(args.game_root, args.report, args.evidence_root)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
