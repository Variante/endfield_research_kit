# Fluffy Dumper Reference

## Paths And Build

Local patched workspace:

```text
tools\fluffy-dumper-src
```

Build:

```bat
cargo build --release --manifest-path tools\fluffy-dumper-src\Cargo.toml
```

Expected binary:

```text
tools\fluffy-dumper-src\target\release\fluffy-dumper.exe
```

The source is a local vendor checkout, not a tracked submodule. The repo setup path can download and overlay the hosted patched source with:

```bat
.\setup_first_time.bat --refresh-fluffy-src
```

The local patch adds `--fallback-assets` to `dump` and `audio`. Confirm the option before using wrapper flows.

## CLI Surface

Top-level:

```text
fluffy-dumper.exe <COMMAND>
```

Commands:

```text
dump
audio
list
help
```

`dump`:

```bat
fluffy-dumper.exe dump --streaming-assets path\to\StreamingAssets --output output_dir --block-type all
```

Aliases and options:

```text
-s, --streaming-assets   Required source root containing VFS.
--fallback-assets        Optional fallback source root containing another VFS.
-o, --output             Output directory, default ./output.
-b, --block-type         all, table, lua, video, bundle, streaming, dynamic-streaming, audio, audio-chinese, audio-english, audio-japanese, audio-korean, and other VFS block names.
```

`audio`:

```bat
fluffy-dumper.exe audio --streaming-assets path\to\StreamingAssets --output output_dir --language chinese --format wav --block all
```

Audio options:

```text
-s, --streaming-assets   Required source root containing VFS.
--fallback-assets        Optional fallback source root containing another VFS.
-o, --output             Output directory, default ./output.
-l, --language           all, chinese, english, japanese, korean.
-f, --format             wem or wav.
-b, --block              all, voice, audio, initial-audio, audit-audio.
```

`list` prints the dumpable VFS block types known by the local binary.

## Wrapper Integration

Structured data in `scripts\export_full_from_game.py`:

```bat
fluffy-dumper.exe dump -s Endfield_Data\StreamingAssets -o export_full\structured\StreamingAssets
fluffy-dumper.exe dump -s Endfield_Data\Persistent -o export_full\structured\Persistent --fallback-assets Endfield_Data\StreamingAssets
```

The wrapper writes command logs under:

```text
reports\StreamingAssets\StreamingAssets_structured_dump.stdout.log
reports\StreamingAssets\StreamingAssets_structured_dump.stderr.log
reports\Persistent\Persistent_structured_dump.stdout.log
reports\Persistent\Persistent_structured_dump.stderr.log
```

Audio in `scripts\build_audio.py`:

```bat
fluffy-dumper.exe audio --streaming-assets <root> --output export_full\structured\Audio\CN --language chinese --format wav --block all
```

`build_audio.py` can pass `--fallback-assets` when configured and post-processes generated conversation JSON with playable `audioSrc` links.

`export_assets.bat --export-from-game` calls `scripts\export_full_from_game.py --skip-structured`, so it bypasses this tool.

## Workspace Crates

Workspace members from `tools\fluffy-dumper-src\Cargo.toml`:

```text
fluffy-dumper  CLI binary and orchestration.
vfs            VFS block loader, block metadata parser, chunk extraction.
sparkbuffer    Binary table parser to JSON.
vgmstream      WEM to WAV conversion wrapper.
usm            USM video conversion to MP4.
chacha20       Stream cipher.
xxhash3        VFS block directory hashing.
xxtea          Lua script decryption.
```

Important files:

```text
fluffy-dumper\src\main.rs
fluffy-dumper\src\cli.rs
fluffy-dumper\src\dumper.rs
fluffy-dumper\src\processors.rs
fluffy-dumper\src\audio\dumper.rs
fluffy-dumper\src\audio\map.rs
vfs\src\loader.rs
vfs\src\parser.rs
vfs\src\types.rs
```

## Code Flow

`main.rs` parses Clap commands and dispatches:

```text
Commands::Dump  -> dumper::run_dump
Commands::Audio -> audio::run_audio_dump
Commands::List  -> BlockType::all_dumpable
```

`dumper::run_dump`:

1. Loads the ChaCha key and Unity hash secret.
2. Creates `VfsLoader::new(streaming_assets, key, secret, fallback_assets)`.
3. Expands `--block-type all` to `BlockType::all_dumpable()`.
4. Loads block info and processes chunk file entries in parallel with Rayon.
5. Logs per-file failures but returns success unless block loading itself fails.

`processors.rs` handles per-file conversion:

```text
Table -> sparkbuffer JSON under output\Table
Lua   -> base64 decode, XXTEA decrypt, normalized .lua under output\Lua
Video -> .usm to .mp4 through usm, otherwise raw write
Other -> raw file path under output
```

`audio::run_audio_dump`:

1. Loads `AudioDialog` from the Table block.
2. Builds language-specific hash-to-path maps.
3. Extracts `.pck` files from selected audio blocks.
4. Writes mapped files as WEM or WAV; unmapped files go under `unmapped\<language>`.

## Fallback Assets

`VfsLoader` stores:

```text
vfs_path = <streaming-assets>\VFS
fallback_vfs_path = <fallback-assets>\VFS if it exists
```

Block metadata is loaded from the primary `vfs_path`. Chunk file resolution checks the primary block directory first and then the fallback block directory. This is why Persistent dumps can use StreamingAssets as a fallback: the manifest stays primary, but missing chunks can still be found.

If `--fallback-assets` is absent or wrong, expect `chunk file not found` errors for cross-source references.

## Output And Failure Semantics

Structured dump output is rooted at:

```text
export_full\structured\StreamingAssets
export_full\structured\Persistent
```

The Python wrapper parses stderr lines matching:

```text
Failed to extract <file>: <reason>
Warning: <count> files failed
```

Actual failures are written to:

```text
export_full\unresolved\failed_to_decode.txt
```

Persistent manifest-only missing references are split into:

```text
export_full\unresolved\manifest_reference_missing.txt
```

For audio, the Rust command prints total extracted, unmapped, and error counts. `build_audio.py` then indexes decoded files, parses Wwise bank event-to-media links, and patches conversation JSON with `audioSrc`.

## Useful Searches

```bat
rg -n "fallback_assets|VfsLoader::new|resolve_chunk_path|ChunkNotFound" tools\fluffy-dumper-src
rg -n "run_dump|process_file|BlockType|all_dumpable" tools\fluffy-dumper-src\fluffy-dumper\src tools\fluffy-dumper-src\vfs\src
rg -n "run_audio_dump|AudioDialog|unmapped|vgmstream" tools\fluffy-dumper-src\fluffy-dumper\src\audio
rg -n "run_fluffy_dumper|failed_to_decode|manifest_reference_missing|structured_dump" scripts\export_full_from_game.py scripts\build_audio.py
```

## Verification Pattern

After Rust changes:

```bat
cargo test --manifest-path tools\fluffy-dumper-src\Cargo.toml
cargo build --release --manifest-path tools\fluffy-dumper-src\Cargo.toml
.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe dump --help
.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe audio --help
```

Targeted data checks:

```bat
.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe dump -s Endfield_Data\StreamingAssets -o tmp\fluffy-table -b table
.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe audio -s Endfield_Data\StreamingAssets -o tmp\fluffy-audio-cn -l chinese -f wem -b voice
```

Use the wrapper logs and `reports\export_full_summary.md` for end-to-end confirmation.
