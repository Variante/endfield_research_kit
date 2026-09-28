# The shipped HIRC parser, read out of the engine

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, audio lane.** The parser ships with the game, so the object types can be
read from the engine rather than guessed from bytes. The shipped DLL also settles,
in the negative, which types its built-in parser never reads; the SDK's own
libraries supply those layouts.

## Current position

- **Every shipped HIRC type frames byte-exact from the engine's own grammar.**
  Body lanes in [`hirc_action_corpus`](../../scripts/webui/audio/semantics/hirc_action_corpus.py)
  cover `0x02`, `0x05`-`0x07`, `0x09`-`0x0E`, `0x10`, `0x11` and `0x13`-`0x16`;
  the same module censuses the `0x03` Action cursor and the `0x04` id vectors.
  `0x03` (Action) and `0x08`/`0x12` (Bus) are typed in
  [`hirc_v150`](../../scripts/webui/audio/semantics/hirc_v150.py); `0x0F` is framed
  but no object ships, so it is fixture-checked only.
- **The witness is the installed Wwise 2023.1.17 SDK**, the exact engine version the
  shipped `AkSoundEngine.dll` names. Its Profile `AkSoundEngine.lib` and
  `AkMusicEngine.lib` ship with PDBs, so the v150 readers disassemble with their own
  symbol names and their virtual calls resolve through each class's vtable
  relocations. Headers and libraries are Audiokinetic's under their EULA: record
  derived facts, never vendor them. The disassembly is regenerable; its annotated
  dumps are scratch material, not evidence to cite.
- **Where the layouts live.** The full field order per type, the node-frame groups,
  the decision-tree semantics and the reading rules are the module docstring of
  [`hirc_v150.py`](../../scripts/webui/audio/semantics/hirc_v150.py). The AnimeStudio
  reader (`tools/AnimeStudio/AnimeStudio/Endfield/Audio/EndfieldAkpkPackage.cs`)
  carries the same layouts beside each framer, and each lane publishes its `layout`
  string into its report. Enum names are the reviewed contract
  [`wwise_sdk_enums.json`](../../scripts/game_data/contracts/wwise_sdk_enums.json)
  (33 enums, PDB hashes as provenance), loaded through
  [`wwise_enums.py`](../../scripts/webui/audio/semantics/wwise_enums.py).
- **Evidence boundary.** Extents and field order are `exact`; field names taken from
  the SDK reader are `direct`. Nothing here is object identity beyond a same-bank
  join, runtime execution, selection, or audibility.

## Layout index

The group letters are the report keys kept from before the SDK read; the extents the
corpus gates proved did not move by a byte when the names arrived.

| group | SDK reader | what it is |
| --- | --- | --- |
| A | `CAkParameterNode::SetInitialFxParams` | override flag, FX count, bypass bits, six-byte slots |
| B | `SetInitialMetadataParams` | metadata plug-in slots, six bytes; never nonempty in the corpus |
| -- | `SetNodeBaseParams` | `OverrideBusId`, `DirectParentID`, priority/MIDI bit vector |
| C, D | `CAkParameterNode::SetInitialParams` | property bundle and ranged bundle, keys and values as parallel runs |
| E | `SetPositioningParams` | positioning bits; the 3D/automation extension needs both low bits and e3DPositionType 1 or 2 |
| F | `SetAuxParams` | aux bit vector, four conditional user aux ids, reflections aux bus |
| G | `SetAdvSettingsParams` | voice limiting and virtual-voice settings |
| H | `CAkStateAware::ReadStateChunk` | varint-counted state properties and state groups |
| I | `AK::RTPC::ReadRtpcCurves` | RTPC curves of 12-byte points |

| type | SDK class | read by |
| --- | --- | --- |
| `0x02` | `CAkSound` (source record from `CAkBankMgr::LoadSource`, then the frame) | lane |
| `0x03` | `CAkAction` (header, bundles, per-class params) | cursor census, `hirc_v150` |
| `0x04` | `CAkEvent` (varint action list) | vector census |
| `0x05` | `CAkRanSeqCntr` (24-byte policy block, children, weighted playlist) | lane |
| `0x06` | `CAkSwitchCntr` (ten-byte group head, children, switch groups, params) | lane |
| `0x07` | `CAkActorMixer` (children) | lane |
| `0x08`, `0x12` | `CAkBus` (parent bus, bus params, ducks, then A, B, I, H) | `hirc_v150` |
| `0x09` | `CAkLayerCntr` + `CAkLayer` (children, layers with their own curves) | lane |
| `0x0A`-`0x0D` | music segment, track, switch, random/sequence (`AkMusicEngine`) | lanes |
| `0x0E` | `CAkAttenuation` (cone, 19 curve indices, curves, I) | lane |
| `0x0F` | `CAkDialogueEvent` (decision tree, bundles) | reader, fixture only |
| `0x10`, `0x11` | `CAkFxBase` (fxID, sized params, bank media, I, H, values) | lanes |
| `0x13`, `0x14`, `0x16` | `CAkModulator` (bundles, I) | lanes |
| `0x15` | `CAkAudioDevice` (`CAkFxBase` + owned effect slots) | lane |

The music types open with one flag byte and then the shared node frame, which is why
every offset-0 attempt on them failed; `0x0B` alone puts the frame after its source,
playlist and clip-automation lists. The "sub-list inside the layer header" that once
fenced four `0x09` bodies was each layer's own curve list.

## Corrections the PDB forced

- **The RTPC and state `ParamID` is the `AkPropID`.** The PDB carries no separate RTPC
  id enum, so the older RTPC label table (wwiser's pre-2019 numbering, where 6 meant
  InitialDelay) was wrong for v150 and now aliases the initial-property table.
- **Every varint accumulates most-significant group first**, with no engine width cap.
  The shipped two-byte keys `82 30` and `84 30` decode to `0x130` and `0x230`, effect
  slots 1 and 2 of `AkPropID_BypassFX`; the little-endian reading gave 6146 and 6148
  (`0x1802`, `0x1804`), which name nothing. Group H's counts are varints too; the
  corpus spends one byte on each, so the byte widths were the short form.
- **`numSubTrack` is read only when the music track's playlist is nonempty.**
- **`AkRtpcCurveParams.rtpcType` is `AkGameSyncType`**, by the PDB field list: the
  serialized byte is read into that field before `AddRtpcCurve`, and the five real
  members name stored values 0-4. This is direct field identity, not a runtime value.

The other label tables (curve interpolation, RTPC accumulation, curve scaling, sync
type, bank type, plug-in type, source type, value meaning, initial properties) agree
with the PDB up to spelling.

## The decision tree, walked the way the SDK resolves it

`0x0C` and `0x0F` hand a sized tree to `AkDecisionTree::SetTree`; `ResolvePath`
walks it. The root is a sentinel at positive depth, each branch indexes one
contiguous 12-byte child range that is binary-searched by key, a first child keyed
zero is the fallback, weights are relative and the probability gates a resolved leaf
(sibling probabilities are **not** a sum-to-100 partition, so a sum check would reject
valid trees). The node layout is in the `hirc_v150` docstring.

The reader's `FrameDecisionTreeNodes` applies those rules to every shipped `0x0C`
body, and the lane partitions node bytes, reachability and leaf identity (zero,
unique same-bank declaration, duplicate declaration, absent declaration); the lane
refuses any partition that does not add up. Every shipped `0x0C` body closes, every
stored node is reachable, every child range is in bounds and sorted, and no leaf
probability exceeds 100. Most nonzero leaves join one declaration in their own bank
(music segment, switch and random/sequence types). A leaf with no same-bank
declaration is a local ownership gap, not global absence or an invalid tree. The
tree is authored structure: runtime argument values, fallback or weighted selection,
and audibility are unobserved.

## What the shipped engine parses

The shipped `AkSoundEngine.dll` was read before the SDK symbols were available, and
its structural findings stand; the loader facts and the method routes that failed on
it are recorded in the docstring of
[`wwise_sdk_symbols.py`](../../scripts/game_data/wwise_sdk_symbols.py), which is also
how a later build's addresses are re-derived (addresses are not kept in prose).

- **HIRC `0x0A`-`0x0D` are not parsed by the engine's own parser; it skips them.**
  The HIRC jump table covers `0x02`-`0x16` exactly, and the four music types share one
  arm that calls an optional registered hook and otherwise advances the stream by the
  item's declared size, checking only that the skip was not short. The game DLL
  carries no music-engine strings. So no built-in parser exists for them; a
  registered handler (the SDK's `AkMusicBank::LoadBankItem`) could read them at
  runtime, and whether the game registers one is a runtime question.
- **Two independent lines point the same way**: the built-in reader does not parse
  the music family, and nothing in the object graph or the non-HIRC sections enters
  it (`the_music_family_is_not_entered_from_the_object_graph` and
  `the_unparsed_sections_name_only_buses` in
  [`hirc_named_reach`](../../scripts/webui/audio/semantics/hirc_named_reach.py)).
  Unreachable and unparsed are different claims from different evidence; neither
  says music cannot play.
- **Bank-embedded media need no HIRC owner.** The `DIDX`/`DATA` path registers media
  by id straight from the chunk. A media no source record names is therefore not a
  dangling reference; all but one of those are the Init bank's embedded media.
- **The item header is `u8 type, u32 size`**, the framing this project's reader uses.
- **The in-house build moves the node-block vtable slots** 0x28 bytes later than
  the stock SDK without changing the bytes they read.

## Eliminated routes, so they are not retried

- **Engine-side naming of music fields.** No engine code reads them, so no
  disassembly of the game DLL can name them; that route is closed, not unexplored.
  Their layouts come only from `AkMusicEngine.lib`.
- **Corpus-only framing of the music types.** The fitted `0x0B` census (`type11*`, the
  former `audio_hirc_curves.md`), the `0x0A` head rule and end anchors, the `0x0C`
  region grid and the `0x0D` length rule were all fits: every "entry header",
  "element", "trailer" and "step-back" was a playlist item, a clip automation, the
  node frame or the switch block seen through a wrong stride. *A corpus-only fit
  cannot tell right from wrong without the reader that wrote the bytes.*
- **The `0x0B` `+12`/`+20` entry words.** Pooled over every package they were floats
  in a bounded band, usually equal and otherwise a symmetric range, against controls
  near zero. No shipped table could name them: STMG, bank, media and object tables
  are all identifier-keyed and a float does not join an id table; the decoded audit
  intermediate holds per-package summaries and BNK section headers, not bodies or
  media sizes (it is generated with media verification skipped). They sit inside
  the 44-byte playlist item the SDK names.
- **A runtime observation of the music path** is an account-affecting action on a
  client that ships `AntiCheatExpert`. It is the user's call and is not taken
  without an explicit request.
- **The `0x11` "21 versus 27" width tie.** Both widths consumed every flagged body
  and the flag never exceeded 1, so no body could separate them. The engine reads
  the effect id and a parameter size and hands the block to the plug-in the id
  selects; the tie was two plug-ins, not two readings. The `CAkFxBase` layout closes
  every `0x10` and `0x11` body, and the named fences (`tiedOptionalBlockWidth`,
  `type10_variant7F`) are retired. *A tie that will not break under more corpus is
  often one the format never had a side in.*
- **Ten corpus-only models of `0x12`**, each tested and refused before the SDK read:
  the `0x10`/`0x11` grammar (fails at offset 4 on every body), the `0x16` shape,
  chained counted blocks after a four-byte lead (8 of 251), a fixed 21-byte tail
  (two samples agreed, 100 of 251 did), fixed trailers of 0-39 bytes (best 143 of
  251), group I near the end (coincidence at two offsets), TLV records (84 of 251),
  flag-predicted optional parts (26% against 100% for `0x0E`'s flag), and size
  fields at any offset or after any chain (at most 33%, clustered exactly on the
  body-length histogram). `0x12` is `CAkBus` and closes in `hirc_v150`. *Check a
  candidate field's hit distribution against the length histogram before believing
  it; two samples agreeing on an offset is not evidence.*
- **Witness counts for the smallest types.** `0x13`, `0x14` and `0x15` ship a
  handful of bodies each. Their layouts rest on the SDK reader, not on those
  bodies; the modulator ranged bundle is empty in every shipped object and its
  nine-byte entry is pinned by fixture.
- **"The obstacle is a licence."** The SDK-only types were blocked on having the
  SDK, never on analysis; the installed SDK closed them.

## Open

- Runtime selection: decision-tree argument values, fallback and weighted choice,
  and which music hook (if any) the game registers need a runtime witness, which is
  the user's call.
- Fixture-only paths: `0x0F` ships no object; group B is never nonempty; group H
  multi-byte varints and some group E selector branches (one rests on a single
  object) are rare or absent in the corpus.
- The lanes consume `AkPropID` keys and group I parameter ids by extent; names are
  joined in `hirc_v150`, not in the lanes.
- Media: of the few media no source record names, the one that is not Init-bank
  embedded, and what (if anything) distinguishes it.
