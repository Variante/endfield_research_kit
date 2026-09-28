# The bank's sections outside HIRC

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, audio lane.** The container level of the audio lane: the bank sections
that are not the object graph. `STMG`, `ENVS` and `INIT` are framed byte-exact, and
`ENVS` reuses the same point record the curve type does.

## The bank version is 150, measured, and two external anchors exist

- **`BKHD`'s first `u32` is the bank version and reads 150 in every bank** of
  `init_banks.pck`. The typed reader's `v150` name is a measurement, not an
  assertion. It matters because both external anchors gate on it: wwiser's
  definitions branch at `<= 150` and `<= 152`, and one version either side changes
  which fields exist.
- **The Wwise SDK is installed locally** at `Wwise_2023.1.17.8841`, the exact engine
  version (see [`audio_overview.md`](audio_overview.md)). Its headers give enum and
  codec tables and built-in plug-in parameter layouts; its Profile static libraries
  and PDBs carry the bank deserializers as named object code, which is what frames
  the HIRC node types ([`audio_hirc_parser.md`](audio_hirc_parser.md)). Headers and
  libraries are Audiokinetic's under their EULA: record derived facts, never vendor
  them.
- **wwiser** is the only third-party anchor for the music hierarchy's version-specific
  definitions. A local checkout lives under disposable `tmp/`, so a conclusion drawn
  from it must be re-derived against bytes before it is recorded -- cite the bytes,
  not the path. The SDK's `AkMusicEngine.lib` has since superseded it for layouts.
- **A bounded probe reproduces all of the above**: `AnimeStudio.CLI dump
  --streaming-assets <SA> --output tmp/audio/<task> --block-type initial-audio`, then
  read `BKHD` and walk `hirc_v150.parse_hirc_objects` over each bank payload. InitAudio
  is two small files, so this needs no full audio export.

## The section census

A section census costs nothing and should be the first thing done to a container
format. Every bank carries `BKHD` and `HIRC`; exactly one bank carries the others.

| tag | instances | framed |
| --- | --- | --- |
| `BKHD` | every bank | version field |
| `HIRC` | every bank | every shipped type, see [`audio_hirc_parser.md`](audio_hirc_parser.md) |
| `DIDX` | 1 | 12-byte media entries |
| `DATA` | 1 | addressed by `DIDX` |
| `STMG` | 1 | byte-exact |
| `INIT` | 1 | byte-exact |
| `ENVS` | 1 | byte-exact |
| `PLAT` | 1 | one NUL-terminated name, `Windows` |

The layouts are the module docstring of
[`hirc_named_reach.py`](../../scripts/webui/audio/semantics/hirc_named_reach.py),
which pools the AnimeStudio reader's census and gates each section; the reader's
framers carry the same layouts in `EndfieldAkpkPackage.cs`. Per-build sizes and
record counts belong to the `hirc_named_reach` report.

## `STMG`: three blocks, each located by different evidence

A section that occurs once offers no closure evidence across instances, so each block
needed its own discriminator, and each had a different one available.

- **Leading block: a forward count and a discriminated stride.** At a 12-byte stride
  every record id is distinct; at every other stride from 8 to 20 they collapse, and
  only at 12 is the next word a small count opening a further block. Record values
  are almost all 1000 (`the_stmg_record_stride_beats_its_rivals`).
- **Trailing block: framed backward, located by its count.** The block before it is
  variable-length, so its start cannot be computed forward. Walking back while the
  record's zero bytes hold overshoots by one record, because the bytes happen to be
  zero one record early; over every run length from 1 to 480, exactly one has a
  preceding word equal to itself. All ids are distinct and every rival stride fails
  both the distinctness and zero-byte tests; every float is finite and bounded
  (`the_stmg_tail_run_is_located_by_its_count`). *A shape test that overshoots by one
  is not a boundary; a count that agrees with the run length is.*
- **Middle block: bounded on both sides, then exhausted.** With a known start and end,
  a candidate shape had to consume it byte-exactly in exactly its declared entries;
  of about 745,000 shapes of the form "head with a count inside, then records, then a
  tail", exactly one does. The content agrees independently of the search: entry ids
  are all distinct and the marker byte is 9 in every record
  (`the_stmg_section_closes_byte_exactly`). *A shape found by exhaustion needs content
  the exhaustion did not select for.*
- **Correction that cost a batch**: the middle block was once called blocked on
  having one sample. One `STMG`, but many entries inside the block -- the sample size
  for an entry shape is the entry count, not the section count.
- **What it references**: a 32-bit window over all non-HIRC sections names HIRC
  objects far above chance, every one a bus (`0x08` or `0x12`) and every one in
  `STMG`; nothing names a music object (`the_unparsed_sections_name_only_buses`).

## `ENVS` shares the curve point

`ENVS` has no count of its own -- its run of curves ends when the bytes do -- so
byte-exact closure is what makes the walk a frame rather than a scan. Three shapes
close it with every curve non-empty; the content separated them: only the 4-byte
curve head with a 12-byte `(x, y, interpolation)` point gives interpolation codes in
0..9 for every point and rising x in every curve
(`the_envs_curves_carry_interpolation_codes`). *Closure found three candidates;
content picked one.* The point is the same record RTPC, layer, attenuation and clip
automation curves use, and the codes are the same vocabulary.

## `INIT` names the plug-in classes

- **`INIT` is a plug-in name table** (count, then encoded type/company, plug-in id and
  a NUL-terminated name per entry) and closes byte-exactly; a wrong field order would
  not land on the section end, which is the whole check for a section that appears
  once.
- **The class-id word of the 14-byte source record is
  `(plugin << 16) | (company << 4) | type`**, with the type in the low nibble; the
  reviewed `AkPluginType` enum names `2` Source and `7` Sink. `INIT` names
  `0x01990002` (Source 409) and `0x01FB0007` (Sink 507) **AkMotion**, and the source
  classes `0x00640002` AkSineTone, `0x00650002` AkSilenceGenerator and `0x00940002`
  AkSynthOne. A fresh targeted dump of the installed `init_banks.pck` consumed the
  sole `INIT` section through every entry and read both AkMotion names. This is
  authored plug-in identity, not proof that either class was registered,
  instantiated, or produced output.
- **The unnamed source ids have low word `0x0001`**: type Codec with company zero, not
  company 1. `INIT` lists plug-in classes, not the built-in codec set, so the gate
  requires every unnamed source class to have exactly that low word
  (`the_init_table_names_the_plugins_the_records_use`); an unknown Source class cannot
  pass as a codec.
- The join is a corpus union: `INIT` lives in `init_banks.pck` and the source records
  in other packages, so a package-local join scores almost nothing. Source-record
  counts and distributions belong to the authenticated corpus report.

## Media sections

`DIDX` and `DATA` carry the Init bank's embedded media. The engine registers them by
id straight from the chunk without consulting HIRC
([`audio_hirc_parser.md`](audio_hirc_parser.md)), so an embedded media that no source
record names is expected, not a dangling reference.
