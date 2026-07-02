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

## Interpretation

HotfixAudio contains recoverable Wwise media. The current dialog table does not
map these media IDs, so the next useful recovery step is event-bank/HIRC mapping
from HotfixAudio bank metadata to determine whether the files are SFX, music,
UI, or story/cutscene audio before adding it to default audio export behavior.

## Next Steps

1. Keep HotfixAudio decode explicit until its media IDs are categorized.
2. Use the existing Wwise event-bank metadata path to map HotfixAudio media IDs
   to event names or prove they are standalone/unreferenced.
3. Separate the local fluffy-dumper checkout's pre-existing VFS index work from
   the `AudioBlockType::HotfixAudio` patch before committing upstream there.
