"""Produce a per-.chk decode report for all .chk files under Endfield_Data.

Reads the JSON logs from `decode_persistent_vfs.py` and cross-references
each `.chk` on disk with the `.blc` manifest that references it.

Output:
  - <out_dir>/chk_status.json
  - <out_dir>/chk_status.md
  - <out_dir>/chk_undecoded.txt
  - <out_dir>/referenced_missing_chunks.json
  - <out_dir>/referenced_missing_chunks.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

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


def build_report(log_paths: dict[str, Path], vfs_roots: dict[str, Path], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    disk_chks: dict[str, list[dict[str, object]]] = {}
    for label, root in vfs_roots.items():
        entries: list[dict[str, object]] = []
        for block_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            for file_path in sorted(block_dir.iterdir()):
                if file_path.suffix.lower() != ".chk":
                    continue
                entries.append(
                    {
                        "block": block_dir.name,
                        "block_name": BLOCK_HASHES.get(block_dir.name),
                        "chk": file_path.name,
                        "size": file_path.stat().st_size,
                    }
                )
        disk_chks[label] = entries

    status: list[dict[str, object]] = []
    referenced_missing_chunks: list[dict[str, object]] = []
    for label, entries in disk_chks.items():
        log = json.loads(log_paths[label].read_text(encoding="utf-8"))
        idx: dict[tuple[str, str], dict[str, object]] = {}
        for block in log["blocks"]:
            for chunk in block["chunks"]:
                idx[(block["dir"], chunk["chk"])] = chunk
                if not chunk["present"]:
                    referenced_missing_chunks.append(
                        {
                            "subtree": label,
                            "block": block["dir"],
                            "block_name": block.get("known_as"),
                            "chk": chunk["chk"],
                            "file_count": chunk["file_count"],
                            "ok_count": chunk["ok_count"],
                            "fail_count": chunk["fail_count"],
                            "reason": "referenced by .blc but missing on disk",
                        }
                    )

        for entry in entries:
            key = (entry["block"], entry["chk"])
            chunk = idx.get(key)
            if chunk is None:
                status.append(
                    {
                        "subtree": label,
                        "block": entry["block"],
                        "block_name": entry["block_name"],
                        "chk": entry["chk"],
                        "size_bytes": entry["size"],
                        "referenced": False,
                        "file_count": None,
                        "ok_count": None,
                        "fail_count": None,
                        "decoded": False,
                        "reason": "orphan: no chunk in .blc references this file",
                    }
                )
                continue

            decoded = chunk["fail_count"] == 0 and chunk["present"]
            status.append(
                {
                    "subtree": label,
                    "block": entry["block"],
                    "block_name": entry["block_name"],
                    "chk": entry["chk"],
                    "size_bytes": entry["size"],
                    "referenced": True,
                    "file_count": chunk["file_count"],
                    "ok_count": chunk["ok_count"],
                    "fail_count": chunk["fail_count"],
                    "decoded": decoded,
                    "reason": None if decoded else f"{chunk['fail_count']} file(s) failed extraction",
                }
            )

    (out_dir / "chk_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")

    md = ["# Per-.chk decode status\n"]
    md.append(
        f"Generated over {sum(len(v) for v in disk_chks.values())} .chk files "
        f"across {len(disk_chks)} subtrees.\n"
    )
    total = len(status)
    ok = sum(1 for row in status if row["decoded"])
    bad = total - ok
    md.append(f"- Decoded fully: **{ok}/{total}**")
    md.append(f"- Not decoded: **{bad}**")
    md.append(
        "- Referenced missing chunks in manifests (not physical .chk files on disk): "
        f"**{len(referenced_missing_chunks)}**\n"
    )

    by_subtree: dict[str, list[dict[str, object]]] = {}
    for row in status:
        by_subtree.setdefault(str(row["subtree"]), []).append(row)
    for label, rows in by_subtree.items():
        md.append(f"## {label}  (n={len(rows)})")
        md.append("")
        md.append("| block | type | chk | size | files | ok | fail | decoded |")
        md.append("| --- | --- | --- | ---: | ---: | ---: | ---: | :---: |")
        for row in rows:
            md.append(
                "| {block} | {type} | `{chk}` | {size} | {file_count} | {ok_count} | {fail_count} | {decoded} |".format(
                    block=row["block"],
                    type=row["block_name"] or "?",
                    chk=row["chk"],
                    size=f"{row['size_bytes']:,}",
                    file_count=row["file_count"] if row["file_count"] is not None else "-",
                    ok_count=row["ok_count"] if row["ok_count"] is not None else "-",
                    fail_count=row["fail_count"] if row["fail_count"] is not None else "-",
                    decoded="yes" if row["decoded"] else "NO",
                )
            )
        md.append("")
    (out_dir / "chk_status.md").write_text("\n".join(md), encoding="utf-8")

    undecoded = [row for row in status if not row["decoded"]]
    undecoded_lines = []
    if undecoded:
        undecoded_lines.append("# Undecoded .chk files\n")
        for row in undecoded:
            undecoded_lines.append(
                f"- `{row['subtree']}/{row['block']}/{row['chk']}`  "
                f"({row['size_bytes']:,} bytes)  \u2192 {row['reason']}"
            )
    else:
        undecoded_lines.append(
            "# Undecoded .chk files\n\n"
            "None - every physical .chk under Endfield_Data decoded successfully.\n"
        )
    (out_dir / "chk_undecoded.txt").write_text("\n".join(undecoded_lines), encoding="utf-8")

    (out_dir / "referenced_missing_chunks.json").write_text(
        json.dumps(referenced_missing_chunks, indent=2),
        encoding="utf-8",
    )

    missing_md = ["# Referenced Missing Chunks\n"]
    missing_md.append(
        "These entries are listed in a `.blc` manifest but the corresponding `.chk` file is not present on disk.\n"
    )
    missing_md.append(f"- Missing referenced chunks: **{len(referenced_missing_chunks)}**\n")
    if referenced_missing_chunks:
        missing_md.append("| subtree | block | type | chk | files | fail | reason |")
        missing_md.append("| --- | --- | --- | --- | ---: | ---: | --- |")
        for row in referenced_missing_chunks:
            missing_md.append(
                "| {subtree} | {block} | {block_name} | `{chk}` | {file_count} | {fail_count} | {reason} |".format(
                    subtree=row["subtree"],
                    block=row["block"],
                    block_name=row["block_name"] or "?",
                    chk=row["chk"],
                    file_count=row["file_count"],
                    fail_count=row["fail_count"],
                    reason=row["reason"],
                )
            )
    else:
        missing_md.append("None.\n")
    (out_dir / "referenced_missing_chunks.md").write_text("\n".join(missing_md), encoding="utf-8")

    print(f"Total .chk files: {total}")
    print(f"  Decoded OK    : {ok}")
    print(f"  Undecoded     : {bad}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-root", required=True, type=Path, help="Path to Endfield_Data")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--persistent-log", required=True, type=Path)
    parser.add_argument("--streaming-log", required=True, type=Path)
    args = parser.parse_args()
    build_report(
        log_paths={
            "Persistent": args.persistent_log,
            "StreamingAssets": args.streaming_log,
        },
        vfs_roots={
            "Persistent": args.game_root / "Persistent" / "VFS",
            "StreamingAssets": args.game_root / "StreamingAssets" / "VFS",
        },
        out_dir=args.out,
    )


if __name__ == "__main__":
    main()
