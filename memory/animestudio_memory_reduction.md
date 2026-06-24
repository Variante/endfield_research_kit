# AnimeStudio Memory Reduction Notes

Date: 2026-06-23

## Goal

Reduce peak RAM per AnimeStudio CLI worker so `export_assets.bat --export-from-game`
and `export.bat --export-from-game` can safely run more per-type workers through
`--animestudio-jobs N`.

## Diagnosis

The first risk was untrusted count and byte-size fields being used before
validation. Examples included `ReadInt32()` followed by array/list allocation,
`ReadBytes(count)` allocating a `List<byte>(count)`, type-tree array/map sizes,
packed animation vector item counts, mesh vertex/channel multiplications, VFS
block counts, bundle block counts, and external resource offset/size casts.

The larger practical worker peak came from valid Endfield data, not only corrupt
counts. One TextAsset JSON worker over installed StreamingAssets completed but
peaked at 18.7 GB. The main cause was large decompressed VFS/bundle block streams
remaining in memory and large-object-heap growth across per-file processing.

## Implemented Changes

- Added central `EndianBinaryReader` guards for readable byte counts and element
  counts, and changed `ReadBytes` to exact-read into one final byte array.
- Made `ObjectReader.Remaining` object-relative, so object parsers validate
  against the current Unity object rather than the whole file.
- Guarded TypeTree array/map/TypelessData sizes before loops or byte reads.
- Guarded common allocation-heavy object parsers: AnimationClip packed vectors
  and bindings, AnimatorController masks/bindings, Avatar lists, Mesh index and
  vertex data, NapAssetBundleIndexAsset lists, ResourceReader external ranges,
  SerializedFile metadata counts, VFS counts, and Bundle counts.
- Removed a hard-coded Endfield AnimatorController dump path under `scratch`.
- Spilled decompressed VFS/bundle block streams above 64 MiB to delete-on-close
  temp files instead of keeping them in memory.
- Spilled individual VFS/bundle node streams above 64 MiB to delete-on-close
  temp files as well. The previous block-stream spill still left large
  per-node `MemoryStream` allocations in `BundleFile.ReadFiles` and
  `VFSFile.ReadFiles`.
- Re-enabled compacting GC in `AssetsManager.Clear()` only when managed heap
  usage is at least 512 MiB, reducing large-object-heap pressure after large
  files without forcing a full blocking collection after every small file.
- Kept AnimeStudio stages type-sliced even when `--animestudio-jobs 1`, so
  serial mode still runs one type per process instead of a broad multi-type
  process.
- Set the default AnimeStudio job count to 1 for safer first-run memory, while
  documenting `--animestudio-jobs N` in `export.bat` and `export_assets.bat`.
- Made `scripts/export_full_from_game.py` return nonzero after any tool command
  returns nonzero, while still writing the JSON/Markdown summary first. Before
  this, failed type-sliced AnimeStudio subprocesses were logged in the summary
  but the Python wrapper still returned `0`.
- Capped Story timeline recovery's full `json_by_type/MonoBehaviour` scan at
  200,000 JSON files and forced filtered extraction to skip the full scan
  entirely. This avoids a multi-hour Story builder stall on the current
  Endfield export.
- Guarded `AnimationClip.FindRoots()` casts so a generic `AnimeStudio.Object`
  with `ClassIDType.Animator` or `ClassIDType.Animation` does not abort
  animation conversion.

## Verification

Build:

```bat
dotnet build tools\AnimeStudio\AnimeStudio.CLI\AnimeStudio.CLI.csproj -c Release -f net9.0-windows --no-restore
```

Result: passed with existing warnings. A multi-target build still hit a local
`obj\Release\net8.0` write permission issue, so verification used the net9 CLI
target used by `scripts/export_full_from_game.py`.

Endfield smoke command shape:

```bat
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" scratch\...\json_by_type --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types TextAsset:Both
```

Results:

| Build | Peak working set | Duration | Output files |
| --- | ---: | ---: | ---: |
| after count guards | 18.7 GB | 262 s | 6,757 |
| after 256 MiB block-stream spill | 16.1 GB | 238 s | 6,757 |
| after 64 MiB spill + compacting GC | 12.3 GB | 253 s | 6,757 |

Asset conversion smoke:

```bat
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\Persistent" scratch\...\convert_by_type --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type Convert --types Mesh:Both
```

Result: passed. The first run was 8.3 s, 1.1 GB peak working set, 195 output
files. After review fixes, a repeat run was 8.0 s, 1.14 GB peak working set,
195 output files.

The smoke output was written under `scratch/animestudio_memory_smoke*`.

Wrapper and worker benchmark:

| Command | Jobs | Result | Duration | Peak working set |
| --- | ---: | --- | ---: | ---: |
| Story JSON slice, StreamingAssets | 1 | exit 0, 980,462 JSON files | 2,316.5 s | 12.1 GiB |
| Story JSON slice, StreamingAssets | 2 | exit 0, 980,462 JSON files | 1,830.2 s | 23.2 GiB |
| `export.bat --export-from-game` export phase | 2 | 10 tool commands, all exit 0 | 6,470 s before Story builder stop | 23.5 GiB |
| `export.bat` finish run after timeline fix | n/a | exit 0 | 1,558.0 s | 3.1 GiB |
| `export_assets.bat --export-from-game` | 2 | exit 0 | about 16,802 s | observed 27.2 GiB |

The `jobs=2` Story JSON slice was about 21% faster than `jobs=1`, but used
nearly double the memory. On this 64 GiB machine, `--animestudio-jobs 2` is the
best tested setting. `jobs=3` is not recommended for this checkout because the
asset run overlapped a high-memory `AnimationClip` worker with other workers
and already reached 27.2 GiB observed process-tree working set.

`export.bat --export-from-game --animestudio-jobs 2` refreshed `export_full/`
successfully before the Story builder hit the old full-MonoBehaviour timeline
scan path. After the timeline scan-limit fix, rerunning `export.bat` from the
fresh `export_full/` completed successfully. Story export had:

- structured failures: 0 for StreamingAssets and Persistent
- tool command failures: 0
- unresolved `failed_to_decode.txt` entries: 0
- unresolved manifest missing entries: 0
- JSON output: 980,462 StreamingAssets files and 60,656 Persistent files
- metadata-only MonoBehaviour fallbacks: 2,433 StreamingAssets and 238
  Persistent

The metadata-only fallbacks are the expected bounded behavior for objects whose
schema read reaches impossible string/count values, for example a
`ReadAlignedString` length much larger than the remaining object bytes. Old
code could turn those bad fields into large allocations; current code logs the
issue and writes metadata-only JSON for that object instead of treating it as a
full wrapper failure.

`export_assets.bat --export-from-game --animestudio-jobs 2` completed with exit
0 and wrote:

- `webui/data/assets/index.json`: 254,597 assets
- images: 131,300
- models: 53,368
- videos: 928
- JSON files: 69,001
- Story media lookup: 1,320 images from 5,292 ids and 235 videos from 237 refs

The asset run had no nonzero AnimeStudio subprocesses and no unresolved
`failed_to_decode.txt` entries, but it did log per-asset conversion errors:
349 under StreamingAssets and 209 under Persistent. The common examples were
shader conversion reads with impossible string lengths. One story-like
AnimationClip error was the `AnimeStudio.Object` to `Animator` cast fixed after
the run and included in the rebuilt CLI. These are skipped converted asset
outputs, not a failed wrapper export.

Validation after the final patches:

```bat
python -m py_compile scripts\export_full_from_game.py scripts\story_builder\timeline_recovery.py
python scripts\story_builder\timeline_recovery.py --extract-timeline-assets --parse-only --full-monobehaviour-scan-limit 1 --limit-chks 1 --extract-dir scratch\timeline_recovery_smoke_extract --out scratch\timeline_recovery_smoke_orders.json
python scripts\export_full_from_game.py --game-root scratch\fake_game_root --output scratch\fake_export_failure --skip-structured --sources StreamingAssets --animestudio-scope story --animestudio-stages maps --animestudio <python.exe>
dotnet build tools\AnimeStudio\AnimeStudio.CLI\AnimeStudio.CLI.csproj -c Release -f net9.0-windows --no-restore
```

Results:

- `py_compile`: passed.
- timeline smoke: exit 0 and logged `filtered timeline extraction requested;
  skipped full MonoBehaviour parse`.
- fake AnimeStudio failure: wrapper wrote a summary and exited 1 with
  `command_failure_count=1`.
- AnimeStudio CLI build: passed for `net9.0-windows` with existing warnings.

## Remaining Notes

The TextAsset JSON worker still peaks around 12 GB because it legitimately
materializes and exports many large TextAssets as JSON. The current changes
allow `--animestudio-jobs 2` on this 64 GiB workstation, but the default should
remain 1 for first-time and low-RAM runs. Further reductions would require a
streaming export path that exports matching objects while reading a file instead
of holding every parsed object until the file-level export pass.
