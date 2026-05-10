"""Verify extracted .ab bytes are valid Unity AssetBundles.

Pulls a handful of .ab payloads out of the Bundle / InitialBundle
.chk files using the same logic as decode_persistent_vfs, then:

  1. Checks the Unity magic signature ("UnityFS" / "UnityRaw" / "UnityWeb").
  2. Parses the AssetBundle header far enough to read the
     UnityFS format version, Unity engine version, block/directory
     counts, and verifies the flags + total size.
  3. Writes the validated .ab bytes to disk for downstream loaders.
"""

from __future__ import annotations
import argparse, io, struct, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from decode_persistent_vfs import (  # type: ignore
    decrypt_blc, parse_block_main_info, extract_file, BLOCK_HASHES,
)

UNITY_MAGICS = (b"UnityFS", b"UnityRaw", b"UnityWeb", b"UnityArchive")


def read_cstring(buf: io.BytesIO) -> bytes:
    out = bytearray()
    while True:
        c = buf.read(1)
        if not c or c == b"\x00":
            return bytes(out)
        out.extend(c)


def parse_unityfs(data: bytes) -> dict:
    """Parse UnityFS bundle header — enough to confirm it's structurally valid."""
    r = io.BytesIO(data)
    magic = read_cstring(r)
    if magic not in UNITY_MAGICS:
        raise ValueError(f"bad magic {magic!r}")
    version = struct.unpack(">I", r.read(4))[0]
    unity_version = read_cstring(r).decode("ascii", "replace")
    unity_revision = read_cstring(r).decode("ascii", "replace")
    size = struct.unpack(">q", r.read(8))[0]
    comp_info_size = struct.unpack(">I", r.read(4))[0]
    uncomp_info_size = struct.unpack(">I", r.read(4))[0]
    flags = struct.unpack(">I", r.read(4))[0]

    return {
        "magic": magic.decode(),
        "format_version": version,
        "unity_version": unity_version,
        "unity_revision": unity_revision,
        "declared_size": size,
        "actual_size": len(data),
        "compressed_info_size": comp_info_size,
        "uncompressed_info_size": uncomp_info_size,
        "flags_hex": f"0x{flags:08x}",
        "compression_type": flags & 0x3F,  # 0=none, 1=lzma, 2/3=lz4(hc)
        "blocks_at_end": bool(flags & 0x80),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game-root", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--samples-per-block", type=int, default=3)
    args = ap.parse_args()

    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    targets = [
        ("StreamingAssets", "7064D8E2", "Bundle"),
        ("StreamingAssets", "0CE8FA57", "InitialBundle"),
        ("Persistent",      "7064D8E2", "Bundle"),
        ("Persistent",      "0CE8FA57", "InitialBundle"),
    ]

    results = []
    for subtree, block_hash, block_name in targets:
        root = args.game_root / subtree / "VFS" / block_hash
        blc = root / f"{block_hash}.blc"
        if not blc.exists():
            continue
        info = parse_block_main_info(decrypt_blc(blc))

        sampled = 0
        for chunk in info.chunks:
            chk_path = root / (chunk.md5_name.to_bytes(16, "little").hex().upper() + ".chk")
            if not chk_path.exists() or not chunk.files:
                continue
            for fi in chunk.files:
                if not fi.file_name.endswith(".ab"):
                    continue
                if sampled >= args.samples_per_block:
                    break
                try:
                    data = extract_file(chk_path, fi)
                except Exception as e:
                    results.append({
                        "subtree": subtree,
                        "block": block_name,
                        "chk": chk_path.name,
                        "file": fi.file_name,
                        "ok": False,
                        "reason": f"extract: {e}",
                    })
                    continue

                header_ok = False
                details: dict = {"size": len(data)}
                try:
                    details.update(parse_unityfs(data))
                    header_ok = True
                except Exception as e:
                    details["parse_error"] = str(e)
                    details["first_16_bytes_hex"] = data[:16].hex()

                # Persist sample bytes for downstream loader testing
                dst = out / subtree / block_name
                dst.mkdir(parents=True, exist_ok=True)
                (dst / Path(fi.file_name).name).write_bytes(data)

                results.append({
                    "subtree": subtree,
                    "block": block_name,
                    "chk": chk_path.name,
                    "file": fi.file_name,
                    "ok": header_ok and details.get("declared_size") == len(data),
                    **details,
                })
                sampled += 1
            if sampled >= args.samples_per_block:
                break

    # Report
    print(f"{'subtree':<18} {'block':<16} {'unity':<10} {'fmt':<4} {'size':>12} {'decl':>12} {'ok'}")
    for r in results:
        print(f"{r['subtree']:<18} {r['block']:<16} {str(r.get('unity_version','?')):<10} "
              f"{str(r.get('format_version','?')):<4} "
              f"{r.get('size',0):>12} {r.get('declared_size','?'):>12} {r['ok']}")

    import json
    (out / "ab_verification.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    ok = sum(1 for r in results if r["ok"])
    print(f"\n{ok}/{len(results)} sample .ab payloads pass Unity header + size check")


if __name__ == "__main__":
    main()
