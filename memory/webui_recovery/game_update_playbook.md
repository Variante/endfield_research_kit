# Game-update playbook

What to do when Endfield updates and you want the WebUI recovery to keep
working. Read this before reaching for any of the IL2CPP tools.

This document is the operational follow-up to
[dialog_id_registry.md](dialog_id_registry.md). Read that if you want the
"why"; this file is the "how".

## TL;DR (the 95% case)

Most game updates are just data changes. Recovery handles them
automatically:

```
.\export.bat
```

That's it. The pipeline re-extracts the new game data, rebuilds
`DialogIdTable` registry, regenerates every conv JSON, refreshes
warnings. **No tool in this playbook needs the game running.**

Then, as a 30-second canary that the dialog system itself isn't
restructured:

```
python tools\endfield-il2cpp\verify_dialog_class_hierarchy.py
```

Pass (exit 0): you're done, business as usual.

Fail (exit 1): jump to "When the canary fails" below.

## What "export.bat" does and why nothing else is usually needed

Order of operations:

1. `scripts/export_full_from_game.py --skip-raw-vfs --skip-source-inventory`
   re-extracts every structured table and asset from the install at
   `D:\Program Files\Endfield Game\Endfield_Data\`. The game does NOT
   need to be running. If the game is open, close it first -- some
   files may be locked.
2. `scripts/recover_dialog_id_registry.py --quiet` re-builds
   `export_full/recovered/dialog_id_table_index.json` from the freshly-
   extracted `DialogIdTable.json`. This is the file
   `scene_order_gap_shared.py` reads to decide whether each scene is
   runtime-registered or unregistered (cut content).
3. `scripts/webui/build_updates.py` rebuilds the per-asset update feed.
4. `scripts/webui/build_story.py --languages CN --default-language CN`
   regenerates every conv JSON and embeds the right warnings. Every
   scene gets re-classified against the new registry.
5. `scripts/webui/build_assets.py` rebuilds the asset index.

After this, the WebUI is consistent with the new game version. Open the
WebUI at `python serve.py` and spot-check.

## When the canary fails

`verify_dialog_class_hierarchy.py` flags drift when:

- An expected class disappears (e.g. `DialogTrunkBehaviour` is renamed
  or removed). Treat as a soft warning: the recovery's behavior is
  unchanged (it still uses `DialogIdTable` and `DialogTextTable`), but
  the comments and reasoning text in
  `scripts/scene_order_gap_shared.py` reference the old class names.
  Plan to refresh the docs.
- A previously-absent "document/letter/memo" UI class appears. This is
  the higher-stakes case: the recovery's `dialogTrunkRowIteration`
  reasoning assumes there is *no* separate loader for document scenes.
  If a new specialised loader exists, scenes loaded by it may have an
  authored line order we're not capturing.

Triage steps:

1. Run the broader catalog scan:

   ```
   python tools\endfield-il2cpp\catalog_dialog_classes.py --topic-cap 100 ^
       --out catalog.json
   ```

   Look at the "DocOrMemo", "Dialog", "Trunk", "Tree" groups for any new
   class names. Compare against the lists in
   [dialog_id_registry.md](dialog_id_registry.md) and
   [scripts/README.md](../../scripts/README.md). New `*Panel` /
   `*Controller` / `*Loader` matches in `DocOrMemo` are the smoking gun.

2. If the recovery genuinely needs to change (new dialog loader class
   confirmed), proceed to "Re-running the IL2CPP investigation" below.

3. If the drift is just renames (e.g. `DialogTrunkBehaviour` is now
   `DialogTrunkBehavior`), update `EXPECTED_PRESENT` in
   `tools/endfield-il2cpp/verify_dialog_class_hierarchy.py` and the
   docstring / comments in `scripts/scene_order_gap_shared.py`. The
   recovery logic doesn't depend on the class names matching.

## Re-running the IL2CPP investigation

This path is for the rare case where you genuinely need updated
information about Endfield's C# code -- e.g. a new dialog loader class
needs to be modeled in the recovery, or you want to push IL2CPP
decompilation further than the existing recovery does.

### Risk reminder

Endfield ships `HGP.dll` (Hypergryph anti-tamper) plus an
`AntiCheatExpert/` directory of additional kernel-mode protections.
Reading the live game's process memory CAN trigger anti-cheat
heuristics. The May 2026 investigation found:

- pe-sieve `/refl` mode works against Endfield with admin + an enabled
  `SeDebugPrivilege` -- the AC kernel driver permits it.
- procdump `-ma -r` works for the same reasons (PSS reflection).
- Direct `OpenProcess(PROCESS_VM_READ)` against the live game **is
  blocked** by the AC kernel driver. Use the reflection-based tools.

**Use an alt account or no account.** Do not log in to the live service
while running these tools. Get the game to the title screen, leave it
there, dump, exit. If a future update tightens AC further (e.g. blocks
`RtlCreateProcessReflection` too), stop -- there is no clean way past
that.

### Prerequisites

- Endfield installed and updated to the version you want to dump.
- An elevated PowerShell.
- `python` and `dotnet` on PATH.
- `ilspycmd` installed once: `dotnet tool install --global ilspycmd`.
- Tools in `tools/` are intact:
  - `tools/Il2CppDumper-src/.../Il2CppDumper.exe` (rebuild from source
    if missing)
  - `tools/Cpp2IL-nightly/Cpp2IL.exe` (rarely useful for this game,
    kept as backup)
  - `tools/pe-sieve/pe-sieve64.exe`
  - `tools/procdump/procdump64.exe`
  - `tools/endfield-il2cpp/*` (this playbook's companion scripts)

### Step 1: get the game to a known state

Launch `Endfield.exe`. Wait for the title / login screen. **Do not log
in.** IL2CPP is fully initialised by this point.

### Step 2: find the PID

In your elevated PowerShell:

```powershell
Get-Process Endfield | Select-Object Id, ProcessName
```

Save the PID.

### Step 3: locate GameAssembly.dll's mapped base + size

pe-sieve will refuse to dump `GameAssembly.dll` by default (it doesn't
classify it as "modified" without scanning IAT hooks). But it will
report the module's mapped base + size if you ask for a full scan
report. Run from any working directory you don't mind getting filled
with files:

```powershell
$work = "D:\fluffy-dump\scratch\update_<yymmdd>"
mkdir $work -Force | Out-Null
cd $work

D:\fluffy-dump\tools\pe-sieve\pe-sieve64.exe /pid <PID> /refl `
    /report 7 /jlvl 2 /ofilter 1 /dir $work\listing
```

`/report 7` reports all scanned modules. `/ofilter 1` suppresses module
dumps but keeps the report. Wait ~90 seconds for the workingset scan
to finish.

Find the GameAssembly entry:

```powershell
Select-String -Path $work\listing\process_<PID>\scan_report.json `
              -Pattern 'GameAssembly' -Context 4,4
```

Pull two values: `module` = base address (hex), `module_size` = size
(hex). On the May 2026 baseline these were `0x7ffc435d0000` and
`0xf1e5000`.

### Step 4: get a dump of GameAssembly.dll

The simplest path is pe-sieve with `/iat 3` -- it'll classify
`GameAssembly.dll` as "modified" because HGP installs IAT hooks, and
dump it as part of the standard pe-sieve flow:

```powershell
D:\fluffy-dump\tools\pe-sieve\pe-sieve64.exe /pid <PID> /refl `
    /dmode V /imp A /iat 3 /data 3 /dir $work\agg
```

The dump lands at `$work\agg\process_<PID>\<base>.GameAssembly.dll`.

If pe-sieve refuses (e.g. a future game version doesn't install IAT
hooks), fall back to direct reflection:

```powershell
D:\fluffy-dump\tools\endfield-il2cpp\dump_module_via_reflection.ps1 `
    -ProcId <PID> -BaseHex 0x<base> -SizeHex 0x<size> `
    -OutPath $work\GameAssembly_dumped.dll
```

### Step 5: take a full memory dump

Needed because HGP relocates `MetadataRegistration` out of
`GameAssembly.dll`'s mapped image. The May 2026 baseline put the real
`MetadataRegistration` at ~`0x1263f3c98` in a separate HGP heap arena;
that address will change every run. We have to scan for it each time.

```powershell
D:\fluffy-dump\tools\procdump\procdump64.exe -accepteula -ma -r `
    <PID> $work\endfield_full.dmp
```

`-ma` = full memory, `-r` = use PSS reflection (lower impact). The
.dmp will be 4-10 GB. Make sure $work is on a drive with enough room.

You can quit the game once procdump prints "Dump 1 complete."

### Step 6: find MetadataRegistration in the full memory dump

```powershell
python D:\fluffy-dump\tools\endfield-il2cpp\find_metadata_in_minidump.py `
    --dump $work\endfield_full.dmp > $work\scan.log
python D:\fluffy-dump\tools\endfield-il2cpp\rerank_candidates.py `
    --log $work\scan.log
```

The first scan typically takes 5-15 minutes and emits thousands of
candidates. The re-ranker filters down to a handful and surfaces
"isolated cluster" hits at the top. The real `MetadataRegistration`
has eight monotonically-increasing pointers spanning a single HGP heap
arena, and eight strictly-distinct counts (not all powers of two; not
sliding-window-uniform).

If the scan returns zero candidates: HGP may have changed the layout
or your filters are too strict. Edit
`tools/endfield-il2cpp/find_metadata_in_minidump.py`'s `is_plausible`
function and relax thresholds one at a time.

### Step 7: feed the addresses to Il2CppDumper

You now have CodeRegistration (from `Il2CppDumper` output earlier --
it finds CodeRegistration even when MetadataRegistration fails) and
MetadataRegistration (from step 6).

```powershell
D:\fluffy-dump\tools\endfield-il2cpp\process_dump.ps1 `
    -DumpedDll $work\agg\process_<PID>\<base>.GameAssembly.dll `
    -ImageBaseHex 0x<base> `
    -WorkDir $work
```

If Il2CppDumper falls into manual-mode prompts (because PlusSearch
can't find MetadataRegistration in the dump alone -- it lives in
another region), you'll need to feed both addresses interactively. The
`process_dump.ps1` script supplies a default via stdin; for an
interactive run, invoke Il2CppDumper directly:

```powershell
D:\fluffy-dump\tools\Il2CppDumper-src\Il2CppDumper\bin\Release\net8.0\Il2CppDumper.exe `
    $work\agg\process_<PID>\<base>.GameAssembly.dll `
    "D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat" `
    $work\dummy_out
```

Note: even with the right addresses, Il2CppDumper requires
MetadataRegistration's pointers to resolve in the same flat binary as
GameAssembly.dll. They don't (they live in HGP heap memory). To get
fully decoded dummy DLLs requires a multi-region binary loader we did
not build. The May 2026 work stopped short of finishing this -- we
proved the C# class hierarchy via `global-metadata.dat` instead.

If you need to finish this path, the merged-region binary loader is
roughly 100 lines of patching `Il2CppDumper.IO.BinaryStream` to consult
a region table (start_va, file_offset, size) instead of subtracting a
single `ImageBase`. The minidump's `Memory64ListStream` (already parsed
by `find_metadata_in_minidump.py`) is exactly that region table.

### Step 8: cleanup

After confirming the new runtime info matches what you need:

- Delete `$work/endfield_full.dmp` (5+ GB, no further use).
- Keep `$work/agg/process_<PID>/<base>.GameAssembly.dll` and
  `$work/scan.log` as provenance for the version you investigated.
- Update `tools/endfield-il2cpp/verify_dialog_class_hierarchy.py`'s
  expected/forbidden class lists if the hierarchy genuinely changed.
- Update `memory/webui_recovery/dialog_id_registry.md` with the new
  findings.

## When the registry is wrong shape

Symptoms: `recover_dialog_id_registry.py --quiet` runs but reports
near-zero entries; many scenes that should be registered come back as
`unregisteredScene`.

Likely cause: the game changed `DialogIdTable.json`'s binary format
(e.g. now encrypted at rest, or now uses numeric IDs instead of string
keys).

Triage:

1. Run the recovery without `--quiet` and inspect the count:
   ```
   python scripts\recover_dialog_id_registry.py
   ```
   Compare to the May 2026 baseline (~4 500 entries). A drop to 0-100
   means the extractor's regex isn't finding identifiers.

2. Inspect the raw bytes:
   ```powershell
   Format-Hex `
     -Path "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\..." `
     -Count 256
   ```
   (Adjust the path -- `export_full_from_game.py` writes a copy under
   `export_full/structured/StreamingAssets/Data/Json/GameplayConfig/DialogIdTable.json`
   which is the actual input.)

3. If you can still see ASCII `dlg_*` strings: the regex in
   `scripts/recover_dialog_id_registry.py` needs widening. If you
   can't see them: the table is now encrypted / serialized
   differently, and you need to identify how the runtime decodes it
   (use `global-metadata.dat` to find the `DialogIdTable`-related
   methods and inspect them via the IL2CPP path above).

## Quick reference

| When | Run | Game running? |
| ---- | --- | ------------- |
| Normal post-update refresh | `.\export.bat` | No (close it) |
| Sanity-check class hierarchy | `tools\endfield-il2cpp\verify_dialog_class_hierarchy.py` | No |
| Broader vocabulary audit | `tools\endfield-il2cpp\catalog_dialog_classes.py` | No |
| Sanity-check the registry | `scripts\recover_dialog_id_registry.py` (no --quiet) | No |
| New IL2CPP investigation | Steps 1-8 in this playbook | **Yes** (alt account!) |
