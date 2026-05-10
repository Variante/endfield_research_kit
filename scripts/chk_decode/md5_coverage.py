"""Count how many extracted files had file_data_md5 != 0 (i.e. MD5-verified).

Also double-check that the decoder never silently ran past the end of a .chk.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from decode_persistent_vfs import (  # type: ignore
    decrypt_blc, parse_block_main_info, BLOCK_HASHES,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vfs-root", required=True, type=Path,
                    help="Path to <subtree>/VFS")
    args = ap.parse_args()

    verified = 0
    skipped = 0
    total = 0
    chks = 0
    oversize_chks = 0
    files_past_eof = 0

    for block_dir in sorted(p for p in args.vfs_root.iterdir() if p.is_dir()):
        blc = block_dir / f"{block_dir.name}.blc"
        if not blc.exists():
            continue
        try:
            info = parse_block_main_info(decrypt_blc(blc), verify_crc=True)
        except Exception as e:
            print(f"  !! {block_dir.name}: {e}", file=sys.stderr)
            continue

        for chunk in info.chunks:
            chk = block_dir / (chunk.md5_name.to_bytes(16, "little").hex().upper() + ".chk")
            if not chk.exists():
                continue
            chks += 1
            size = chk.stat().st_size
            for fi in chunk.files:
                total += 1
                if fi.file_data_md5 != 0:
                    verified += 1
                else:
                    skipped += 1
                if fi.offset + fi.length > size:
                    files_past_eof += 1

    print(f"subtree: {args.vfs_root}")
    print(f"  .chk files present: {chks}")
    print(f"  files enumerated:   {total}")
    print(f"  MD5-verified:       {verified}")
    print(f"  MD5 zero (skipped): {skipped}")
    print(f"  files past EOF:     {files_past_eof}")


if __name__ == "__main__":
    main()
