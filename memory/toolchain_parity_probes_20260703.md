# Toolchain Parity Probes - 2026-07-03

## AnimeStudio vs Fluffy-Dumper VFS Index

Compared AnimeStudio's integrated VFS `vfs-index` command against the local
`fluffy-dumper` binary for the WebUI table block.

Commands:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe vfs-index -s "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" --fallback-assets "D:\Program Files\Endfield Game\Endfield_Data\Persistent" -b table -o tmp\tool_parity_vfs_table_20260703\as_table.json

.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe vfs-index -s "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" --fallback-assets "D:\Program Files\Endfield Game\Endfield_Data\Persistent" -b table -o tmp\tool_parity_vfs_table_20260703\fd_table.json
```

Result:

- Both commands exited `0`.
- Both indexed `629` table files across `42` chunks.
- Both summaries reported `161,084,549` bytes, `1` block, `0` missing blocks,
  and `0` missing chunks.
- The two JSON files were byte-identical:
  `sha256 2000461bdda6aa026d610e177a4d0653707865cc832d1130fb66111b64776e49`.
- Normalized file entries had no differences by name, offset, length, MD5,
  chunk, or block.

Conclusion: the integrated AnimeStudio VFS index path matches the older
fluffy-dumper table-index behavior for this WebUI-critical source block.

## ScriptFirst MonoBehaviour Probe

Ran a focused ScriptFirst TypeTree priority export for chunk
`68B3B9B8EB82E88FBFE6A313E6B18FB6.chk` using the existing timeline filter data.

Command:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\scriptfirst_68b3_20260703 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --filter_data export_full\recovered\AnimeStudio-cli\timeline_extract\68B3B9B8EB82E88FBFE6A313E6B18FB6\filter_data.json --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --mono_behaviour_type_tree_priority ScriptFirst
```

Input filter:

- `44,036` total filter rows.
- `32,607` MonoBehaviour filter rows.

Result:

- Command exited `0`.
- Output contained `32,638` MonoBehaviour JSON files.
- All emitted files still reported `typeTreeSource: serializedType`.
- No `$partial`, `$unparsed`, `$heuristic`, `decodeError`, or
  `partialTypeTreeDecode` markers appeared in the output.
- For the `20,742` filename-matched filtered records that also exist in the
  current export, top-level JSON field sets matched the current serialized-first
  export.

Conclusion: on this focused chunk, `ScriptFirst` does not currently recover
additional script-derived MonoBehaviour fields beyond the serialized TypeTree
path. It is useful as a validation probe, not an immediate recovery win.

## Next Toolchain Leads

- Keep using AnimeStudio as the production VFS extractor for table/json-data
  blocks; the table-index parity probe supports that path.
- Use ScriptFirst only for targeted regressions or specific MonoBehaviour
  classes where serialized TypeTree is absent or known incomplete.
- The next likely higher-value decoder target is the narrow
  `Beyond.Gameplay.InteractiveEvent` action family, not broad ScriptFirst export.
