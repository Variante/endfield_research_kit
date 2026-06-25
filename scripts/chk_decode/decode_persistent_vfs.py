"""Decode every .chk file under <game>/Endfield_Data/Persistent/VFS.

Mirrors the integrated AnimeStudio VFS loader logic so we can iterate
on failures quickly without rebuilding the CLI.

Outputs:
  - <out_dir>/files/...                : extracted files (path taken from .blc)
  - <out_dir>/chk_decode_log.json      : per-file status (ok/error)
  - <out_dir>/chk_decode_failures.md   : human-readable failure summary
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import struct
import sys
import traceback
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


# --- keys (mirrors integrated AnimeStudio VFS keys) ---------------------------

CHACHA_KEY_B64 = "6VsxesT4KFadI6hr8nHctT6Eb6dckk1nHbqOOPTKUuE="
CHACHA_KEY = base64.b64decode(CHACHA_KEY_B64)
assert len(CHACHA_KEY) == 32

VFS_PROTO_VERSION = 3
BLOCK_HEAD_LEN = 12


# --- known block hashes (mirrors README table) --------------------------------

BLOCK_HASHES = {
    "07A1BB91": "InitialAudio",
    "0CE8FA57": "InitialBundle",
    "3C9D9D2D": "InitialExtendData",
    "1CDDBF1F": "BundleManifest",
    "DAFE52C9": "IFixPatch",
    "6432320A": "AuditStreaming",
    "B9358E30": "AuditDynamicStreaming",
    "06223FE2": "AuditIV",
    "1EBAF5C6": "AuditAudio",
    "2E6CE44D": "AuditVideo",
    "7064D8E2": "Bundle",
    "24ED34CF": "Audio",
    "55FC21C6": "Video",
    "A63D7E6A": "IV",
    "C3442D43": "Streaming",
    "23D53F5D": "DynamicStreaming",
    "19E3AE45": "Lua",
    "42A8FCA6": "Table",
    "775A31D1": "JsonData",
    "D6E622F7": "ExtendData",
    "F151B649": "HotfixAudio",
    "E1E7D7CE": "AudioChinese",
    "A31457D0": "AudioEnglish",
    "F668D4EE": "AudioJapanese",
    "E9D31017": "AudioKorean",
}


# --- ChaCha20 helper ----------------------------------------------------------

def chacha20_apply(key: bytes, nonce12: bytes, counter: int, data: bytes) -> bytes:
    """Apply ChaCha20 keystream starting at `counter` with IETF 12-byte nonce.

    The cryptography library treats the first 4 bytes of its 16-byte ChaCha20 nonce
    as the counter (little endian) and the remaining 12 bytes as the IETF nonce.
    """
    full_nonce = counter.to_bytes(4, "little") + nonce12
    algo = algorithms.ChaCha20(key, full_nonce)
    cipher = Cipher(algo, mode=None)
    enc = cipher.encryptor()
    return enc.update(data) + enc.finalize()


# --- .blc parser --------------------------------------------------------------

@dataclass
class FileInfo:
    file_name: str
    file_name_hash: int
    file_chunk_md5: int
    file_data_md5: int
    offset: int
    length: int
    block_type: int
    use_encrypt: bool
    iv_seed: int
    file_tag: int


@dataclass
class ChunkInfo:
    md5_name: int
    content_md5: int
    length: int
    block_type: int
    main_tag: int
    files: list[FileInfo] = field(default_factory=list)

    def chk_file_name(self) -> str:
        return self.md5_name.to_bytes(16, "little").hex().upper() + ".chk"


@dataclass
class BlockMainInfo:
    version: int
    group_cfg_name: str
    group_cfg_hash_name: int
    group_file_info_num: int
    group_chunks_length: int
    block_type: int
    code_version: int
    chunks: list[ChunkInfo] = field(default_factory=list)


class _R:
    def __init__(self, data: bytes):
        self.buf = data
        self.pos = 0

    def _take(self, n: int) -> bytes:
        if self.pos + n > len(self.buf):
            raise ValueError(f"short read at {self.pos}: want {n}, have {len(self.buf) - self.pos}")
        out = self.buf[self.pos:self.pos + n]
        self.pos += n
        return out

    def u8(self) -> int: return self._take(1)[0]
    def u16(self) -> int: return struct.unpack("<H", self._take(2))[0]
    def i32(self) -> int: return struct.unpack("<i", self._take(4))[0]
    def i64(self) -> int: return struct.unpack("<q", self._take(8))[0]
    def u128(self) -> int: return int.from_bytes(self._take(16), "little")

    def s(self, n: int) -> str:
        return self._take(n).decode("utf-8", errors="replace")


def parse_block_main_info(decrypted: bytes, verify_crc: bool = True) -> BlockMainInfo:
    if len(decrypted) < 4:
        raise ValueError("decrypted .blc too short")

    if verify_crc:
        body = decrypted[:-4]
        expected_crc = struct.unpack("<i", decrypted[-4:])[0] & 0xFFFFFFFF
        actual_crc = zlib.crc32(body) & 0xFFFFFFFF
        if expected_crc != actual_crc:
            raise ValueError(f"CRC mismatch: expected 0x{expected_crc:08X} actual 0x{actual_crc:08X}")

    r = _R(decrypted)
    raw_version = r.i32()
    if raw_version < 11:
        code_version = raw_version
        version = r.i32()
    else:
        code_version = 3
        version = raw_version

    group_cfg_name_len = r.u16()
    group_cfg_name = r.s(group_cfg_name_len)
    group_cfg_hash_name = r.i64()
    group_file_info_num = r.i32()
    group_chunks_length = r.i64()
    block_type = r.u8()
    chunk_count = r.i32()

    info = BlockMainInfo(
        version=version,
        group_cfg_name=group_cfg_name,
        group_cfg_hash_name=group_cfg_hash_name,
        group_file_info_num=group_file_info_num,
        group_chunks_length=group_chunks_length,
        block_type=block_type,
        code_version=code_version,
    )

    for _ in range(chunk_count):
        md5_name = r.u128()
        content_md5 = r.u128()
        length = r.i64()
        chunk_block_type = r.u8()
        if code_version > 3:
            main_tag = r.i32() & 0xFF
        else:
            main_tag = 0
        file_count = r.i32()

        chunk = ChunkInfo(
            md5_name=md5_name,
            content_md5=content_md5,
            length=length,
            block_type=chunk_block_type,
            main_tag=main_tag,
        )

        for _f in range(file_count):
            name_len = r.u16()
            file_name = r.s(name_len)
            file_name_hash = r.i64()
            file_chunk_md5 = r.u128()
            file_data_md5 = r.u128()
            offset = r.i64()
            length2 = r.i64()
            file_block_type = r.u8()
            use_encrypt = r.u8() != 0
            iv_seed = r.i64() if use_encrypt else 0
            file_tag = r.i32() & 0xFF if code_version > 3 else 0

            chunk.files.append(FileInfo(
                file_name=file_name,
                file_name_hash=file_name_hash,
                file_chunk_md5=file_chunk_md5,
                file_data_md5=file_data_md5,
                offset=offset,
                length=length2,
                block_type=file_block_type,
                use_encrypt=use_encrypt,
                iv_seed=iv_seed,
                file_tag=file_tag,
            ))

        info.chunks.append(chunk)

    return info


def decrypt_blc(blc_path: Path) -> bytes:
    raw = blc_path.read_bytes()
    if len(raw) < BLOCK_HEAD_LEN:
        raise ValueError("blc file too short")
    nonce = raw[:BLOCK_HEAD_LEN]
    body = raw[BLOCK_HEAD_LEN:]
    return chacha20_apply(CHACHA_KEY, nonce, 1, body)


# --- chk extraction -----------------------------------------------------------

def extract_file(chk_path: Path, fi: FileInfo) -> bytes:
    with chk_path.open("rb") as fh:
        fh.seek(fi.offset)
        data = fh.read(fi.length)
    if len(data) != fi.length:
        raise ValueError(f"short chk read: want {fi.length}, got {len(data)} at offset {fi.offset}")

    if fi.use_encrypt:
        nonce = struct.pack("<i", VFS_PROTO_VERSION) + struct.pack("<q", fi.iv_seed)
        assert len(nonce) == 12
        data = chacha20_apply(CHACHA_KEY, nonce, 1, data)

    return data


# --- main workflow ------------------------------------------------------------

def safe_join(root: Path, rel: str) -> Path:
    # Strip drive letters / leading slashes, normalize separators
    rel = rel.replace("\\", "/").lstrip("/")
    parts = [p for p in rel.split("/") if p not in ("", ".", "..")]
    return root.joinpath(*parts)


def md5_hex(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def run(persistent_root: Path, out_dir: Path, dry_run: bool = False) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    files_out = out_dir / "files"
    log_path = out_dir / "chk_decode_log.json"
    failures_md = out_dir / "chk_decode_failures.md"

    vfs_dir = persistent_root / "VFS"
    if not vfs_dir.is_dir():
        raise SystemExit(f"VFS dir not found: {vfs_dir}")

    log: dict[str, Any] = {
        "root": str(persistent_root),
        "blocks": [],
        "summary": {},
    }
    total_files = 0
    ok_files = 0
    fail_files = 0
    skipped_dirs = 0

    block_dirs = sorted([p for p in vfs_dir.iterdir() if p.is_dir()])

    for bdir in block_dirs:
        block_entry: dict[str, Any] = {
            "dir": bdir.name,
            "known_as": BLOCK_HASHES.get(bdir.name),
            "blc_ok": False,
            "blc_error": None,
            "chunks": [],
            "file_count": 0,
            "ok_count": 0,
            "fail_count": 0,
            "orphan_chks": [],
        }

        blc_path = bdir / f"{bdir.name}.blc"
        if not blc_path.exists():
            block_entry["blc_error"] = "missing .blc"
            log["blocks"].append(block_entry)
            skipped_dirs += 1
            continue

        try:
            decrypted = decrypt_blc(blc_path)
            info = parse_block_main_info(decrypted, verify_crc=True)
            block_entry["blc_ok"] = True
            block_entry["block_type_id"] = info.block_type
            block_entry["code_version"] = info.code_version
            block_entry["version"] = info.version
            block_entry["group_cfg_name"] = info.group_cfg_name
        except Exception as e:
            block_entry["blc_error"] = f"{type(e).__name__}: {e}"
            log["blocks"].append(block_entry)
            continue

        referenced_chks: set[str] = set()

        for chunk in info.chunks:
            chk_name = chunk.chk_file_name()
            chk_path = bdir / chk_name
            referenced_chks.add(chk_name)
            chunk_entry: dict[str, Any] = {
                "chk": chk_name,
                "present": chk_path.exists(),
                "file_count": len(chunk.files),
                "ok_count": 0,
                "fail_count": 0,
                "errors": [],
            }

            if not chk_path.exists():
                chunk_entry["errors"].append({
                    "file": None,
                    "reason": "chk file missing on disk (listed in .blc but not present)",
                })
                # All files in this chunk are missing
                for fi in chunk.files:
                    total_files += 1
                    fail_files += 1
                    chunk_entry["fail_count"] += 1
                    chunk_entry["errors"].append({
                        "file": fi.file_name,
                        "reason": "chunk missing",
                    })
                block_entry["chunks"].append(chunk_entry)
                continue

            for fi in chunk.files:
                total_files += 1
                try:
                    data = extract_file(chk_path, fi)
                    if not dry_run and fi.file_name:
                        dest = safe_join(files_out / bdir.name, fi.file_name)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(data)
                    # Verify MD5 of payload if non-zero
                    if fi.file_data_md5 != 0:
                        expected = fi.file_data_md5.to_bytes(16, "little").hex()
                        actual = md5_hex(data)
                        if expected != actual:
                            raise ValueError(f"md5 mismatch expected={expected} actual={actual}")
                    ok_files += 1
                    chunk_entry["ok_count"] += 1
                except Exception as e:
                    fail_files += 1
                    chunk_entry["fail_count"] += 1
                    chunk_entry["errors"].append({
                        "file": fi.file_name,
                        "reason": f"{type(e).__name__}: {e}",
                        "offset": fi.offset,
                        "length": fi.length,
                        "use_encrypt": fi.use_encrypt,
                        "iv_seed": fi.iv_seed,
                    })

            block_entry["chunks"].append(chunk_entry)
            block_entry["file_count"] += chunk_entry["file_count"]
            block_entry["ok_count"] += chunk_entry["ok_count"]
            block_entry["fail_count"] += chunk_entry["fail_count"]

        # Orphan chks: .chk files on disk not referenced by any chunk
        for entry in bdir.iterdir():
            if entry.suffix.lower() == ".chk" and entry.name not in referenced_chks:
                block_entry["orphan_chks"].append(entry.name)

        log["blocks"].append(block_entry)

    log["summary"] = {
        "total_files": total_files,
        "ok_files": ok_files,
        "fail_files": fail_files,
        "block_dirs": len(block_dirs),
        "skipped_dirs": skipped_dirs,
    }

    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")

    # Human-readable failure report
    lines = ["# Persistent VFS decode failures\n"]
    lines.append(f"- Total files listed in .blc: **{total_files}**")
    lines.append(f"- Extracted OK: **{ok_files}**")
    lines.append(f"- Failed: **{fail_files}**\n")

    for be in log["blocks"]:
        if be["blc_error"] or be["fail_count"] > 0 or be["orphan_chks"]:
            lines.append(f"## {be['dir']} ({be.get('known_as') or 'unknown'})")
            if be["blc_error"]:
                lines.append(f"- .blc error: `{be['blc_error']}`")
            if be["orphan_chks"]:
                lines.append(f"- Orphan .chk files on disk: {be['orphan_chks']}")
            for ch in be["chunks"]:
                if ch["fail_count"] > 0 or not ch["present"]:
                    lines.append(f"### chunk {ch['chk']} (present={ch['present']}, fails={ch['fail_count']})")
                    for err in ch["errors"][:30]:
                        lines.append(f"  - `{err.get('file')}` -> {err['reason']}")
            lines.append("")
    failures_md.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(log["summary"], indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--persistent", required=True, type=Path,
                    help="Path to <game>/Endfield_Data/Persistent")
    ap.add_argument("--out", required=True, type=Path, help="Output directory")
    ap.add_argument("--dry-run", action="store_true", help="Do not write extracted files")
    args = ap.parse_args()
    run(args.persistent, args.out, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
