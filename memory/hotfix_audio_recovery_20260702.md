# HotfixAudio Decode Recovery - 2026-07-02

## Context

Skipped-block audits showed a Persistent-only `HotfixAudio` VFS block. VFS dump
and stream selectors already recognized the block, but audio decode selectors
did not expose it as an audio block.

## Code Changes

- `scripts/build_audio.py` accepts `--block hotfix-audio`, treats it as shared
  audio storage, and keeps it out of `--block all` for now.
- AnimeStudio submodule commit `aad1379` adds `hotfix-audio` to the audio CLI
  parser, block dispatch, and help text.
- Local `tools/fluffy-dumper-src/fluffy-dumper/src/cli.rs` was patched to add
  `AudioBlockType::HotfixAudio`; that checkout already has unrelated local
  `VfsIndex` work, so the patch is not cleanly committed in the parent repo.

## Verification

Commands run:

```bat
python -B -m py_compile scripts\build_audio.py
cargo check -p fluffy-dumper
cargo build -p fluffy-dumper --release
dotnet build tools\AnimeStudio\AnimeStudio.CLI\AnimeStudio.CLI.csproj -c Release --no-restore
.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe audio -s "D:\Program Files\Endfield Game\Endfield_Data\Persistent" --fallback-assets "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" -o tmp\hotfix_audio_probe -l chinese -f wem -b hotfix-audio
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe audio -s "D:\Program Files\Endfield Game\Endfield_Data\Persistent" --fallback-assets "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" -o tmp\hotfix_audio_probe_animestudio -l chinese -f wem -b hotfix-audio
```

Both decode paths found one PCK,
`Data/Audio/PCK/Windows/Hotfix/hotfix_main.pck`, and extracted `23/23` WEM
entries with `0` errors. Both output trees contain `23` files totaling
`33,354,305` bytes. All entries are currently unmapped by `AudioDialog.json`.

`build_hotfix_audio_event_audit.py` then streamed `hotfix_main.pck` directly
from VFS and parsed embedded Wwise HIRC metadata. It found `59` embedded banks,
linked all `23` media ids to `4` Wwise event hashes, tested `548` known
event-name candidates from current Story/export tables, and found `0` matches. Event
hash `0x0fe31eb5` owns `18` media ids; `0x6f74a1f3` owns `1`; `0x8c9d6ae4`
owns `1`; `0xb7d20b57` owns `3`. A follow-up Wwise section probe did not
find useful `STID` event-name strings in the embedded HotfixAudio banks;
printable HIRC fragments were byte noise rather than stable labels.

## Interpretation

HotfixAudio contains recoverable Wwise media. The current dialog table does not
map these media IDs, so the next useful recovery step is event-bank/HIRC mapping
from HotfixAudio bank metadata to determine whether the files are SFX, music,
UI, or story/cutscene audio before adding it to default audio export behavior.

## Next Steps

1. Keep HotfixAudio decode explicit until its media IDs are categorized.
2. Search for a name source for event hashes `0x0fe31eb5`, `0x6f74a1f3`,
   `0x8c9d6ae4`, and `0xb7d20b57`; current Story/export event-name sources do
   not contain matching FNV hashes.
3. Separate the local fluffy-dumper checkout's pre-existing VFS index work from
   the `AudioBlockType::HotfixAudio` patch before committing upstream there.

## 2026-07-03 Tool Parity Recheck

Rechecked `Persistent` HotfixAudio with `StreamingAssets` fallback:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe vfs-index -s "D:\Program Files\Endfield Game\Endfield_Data\Persistent" --fallback-assets "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" -b hotfix-audio -o tmp\hotfix_audio_probe\Persistent_hotfix_audio_animestudio.json
.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe vfs-index -s "D:\Program Files\Endfield Game\Endfield_Data\Persistent" --fallback-assets "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" -b hotfix-audio -o tmp\hotfix_audio_probe\Persistent_hotfix_audio_fluffy.json
```

The two index JSON files were byte-identical. Both identify one PCK:
`Data/Audio/PCK/Windows/Hotfix/hotfix_main.pck`, length `34,412,094`, chunk
`Persistent/VFS/F151B649/DFF4A9F3294DB6C8A98BFADE8768298D.chk`, data MD5
`20418F4C17B0F919BF0149DC5963A2E1`.

Fresh WEM decode parity:

- AnimeStudio: `23` WEM files, `33,354,305` bytes, `0` errors, output under
  `unmapped/hotfix/`.
- fluffy-dumper: `23` WEM files, `33,354,305` bytes, `0` errors, output under
  `unmapped/chinese/`.
- Normalized by filename/media ID, all `23` files have identical byte sizes and
  SHA-256 hashes.

Re-ran:

```bat
python scripts\story_recovery\build_hotfix_audio_event_audit.py --decoded-root tmp\hotfix_audio_probe\animestudio_wem
```

Result: `23` media IDs, `4` event hashes, `0` known named media, and `0`
unresolved media. This keeps the prior interpretation: HotfixAudio is fully
extractable but still lacks a stable event-name source, so it should remain an
explicit recovery block instead of joining default `--block all`.
