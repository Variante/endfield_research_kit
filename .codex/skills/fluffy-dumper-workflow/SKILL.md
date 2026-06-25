---
name: fluffy-dumper-workflow
description: Use when working on the local patched tools/fluffy-dumper-src Rust workspace for Endfield structured dumps or audio decoding, including compiling, direct CLI use, Python wrapper integration, fallback-assets behavior, VFS code structure, and export.bat audio or structured-data failures.
---

# Fluffy Dumper Workflow

## When To Use

Use this skill for `fluffy-dumper` tasks in this repo: building the Rust workspace, calling `dump` or `audio`, checking patched `--fallback-assets` behavior, diagnosing structured export failures, or changing VFS/audio/table/video extraction code.

If the task is about the whole WebUI export flow, also use `endfield-webui-workflow`. For command details, code structure, and wrapper integration, read `references/fluffy-dumper.md` before changing code or diagnosing failures.

## Quick Commands

Build the local patched source:

```bat
cargo build --release --manifest-path tools\fluffy-dumper-src\Cargo.toml
```

Expected executable:

```text
tools\fluffy-dumper-src\target\release\fluffy-dumper.exe
```

Check the installed CLI surface:

```bat
.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe --help
.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe dump --help
.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe audio --help
.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe list
```

The `dump` and `audio` help must include `--fallback-assets`. The WebUI wrappers rely on that local patch when a source root references chunks from another source root.

## Wrapper Usage

The normal structured-data path is:

```bat
.\export.bat --export-from-game
```

That calls `scripts\export_full_from_game.py`, which runs:

```bat
fluffy-dumper.exe dump --streaming-assets Endfield_Data\StreamingAssets --output export_full\structured\StreamingAssets
fluffy-dumper.exe dump --streaming-assets Endfield_Data\Persistent --output export_full\structured\Persistent --fallback-assets Endfield_Data\StreamingAssets
```

The normal CN audio path is included at the end of `export.bat`; direct audio maintenance goes through:

```bat
python scripts\build_audio.py
```

`export_assets.bat --export-from-game` passes `--skip-structured`, so it does not need `fluffy-dumper`.

## Direct CLI Shape

Dump all supported VFS blocks:

```bat
.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe dump -s path\to\StreamingAssets -o export_full\structured\StreamingAssets
```

Dump one block:

```bat
.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe dump -s path\to\StreamingAssets -o tmp\fluffy-table -b table
```

Decode audio:

```bat
.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe audio -s path\to\StreamingAssets -o export_full\structured\Audio\CN -l chinese -f wav -b all
```

## Diagnostics

After wrapper runs, start with:

```text
reports\export_full_summary.md
reports\StreamingAssets\StreamingAssets_structured_dump.stdout.log
reports\StreamingAssets\StreamingAssets_structured_dump.stderr.log
reports\Persistent\Persistent_structured_dump.stdout.log
reports\Persistent\Persistent_structured_dump.stderr.log
export_full\unresolved\failed_to_decode.txt
export_full\unresolved\manifest_reference_missing.txt
```

`failed_to_decode.txt` is for actual extraction failures. `manifest_reference_missing.txt` is separated because Persistent manifests can legitimately reference StreamingAssets chunks that require `--fallback-assets`.

For the Rust crate map, API behavior, output layout, and failure interpretation, read `references/fluffy-dumper.md`.
