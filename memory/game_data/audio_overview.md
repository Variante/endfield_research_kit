# Audio: what the evidence is, and where it stops

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, audio lane.** Start here for audio. It states the scope of the Wwise
evidence and the boundary between an authored link and an observed one, which the
rest of the lane depends on.

## The six layers of audio evidence

1. physical package/media identity;
2. decoded playable media;
3. Wwise Event/action/media graph;
4. authored game consumer and control parameters;
5. validated runtime request;
6. selected branch, audibility, and final DSP behavior.

Evidence may advance only one layer at a time. A stronger downstream fact does
not retroactively make every upstream candidate unique. Layers 5-6 need a host
process or a bounded capture ([`audio_native_hooks.md`](audio_native_hooks.md)).

Counts change per input set (current `reports/animestudio/hirc_*_current_latest.*`);
this file keeps boundaries, witnessed joins, gaps and corrections. Code owners
under `scripts/webui/audio/`: `build_audio.py`, `semantics/hirc_action_corpus.py`
(lanes, graph), `hirc_named_reach.py` (naming, reach), `hirc_v150.py` (typed
parse), `wwise_enums.py` (SDK enum contract). Layouts: [`audio_hirc_parser.md`](audio_hirc_parser.md);
graph and typed parse: [`audio_hirc_graph.md`](audio_hirc_graph.md); non-HIRC
sections: [`audio_bank_format.md`](audio_bank_format.md).

## The structural lanes

**One proof pattern.** Each numeric HIRC type has a current-corpus lane bound to
the authenticated VFS input set (verified package hashes, chunks and physical
sources joined to the outer ledger, reconciled per bank and per package). Its
grammar is the SDK deserializer's, not a fit. The constraining checks are that
framed body bytes equal declared object bytes minus object ids and that every
exact body ends at its declared end; `exactCursorBytes + nonExactBodyBytes =
bodyBytes` is an internal assert that cannot fail. A failed, unsupported or
ambiguous body publishes `incomplete` and exits nonzero. `failed = 0` is partly
upstream: a malformed `0x02` source prefix aborts its package in the prefix
census before reaching a body lane. **Exact framing never establishes** operation
names, field ownership, targets, execution, selection or audibility unless a
separate gate says so.

| type | what the lane frames | what it does not claim |
| --- | --- | --- |
| `0x03` Action | whole cursor; serialized action type is a 16-bit word | execution; see target-word notes below |
| `0x02` Sound | 14-byte source prefix (plug-in id, source id at `+5`) plus the nine shared node groups to the declared end | source identity beyond the media join, cross-bank relations |
| `0x04` Event | one-byte count plus 32-bit entries | the entries' targets' names |
| `0x07`, `0x05`, `0x06`, `0x09` | shared node frame plus each container tail (child vectors; `0x05` adds an opaque block and an 8-byte record vector with an independent count, `referenceRecordCountMismatch`; `0x06` adds group lists and 14-byte records; `0x09` layers with their own RTPC curves) | ordering, selection, membership semantics |
| every other shipped type | byte-exact from the SDK: `0x08`/`0x12` bus, `0x0A`-`0x0E` (`0x0C` trees walked against `AkDecisionTree::ResolvePath`), `0x10`, `0x11`, `0x13`-`0x16`; `0x0F` unshipped, fixture only | see [`audio_hirc_parser.md`](audio_hirc_parser.md) |

- **The structural lane is closed**; what remains is inside plug-in parameter
  blocks. A refreshed client (the `HotfixAudio` cohort) added objects and closed
  every type and graph reference without a grammar change; the named gate covers
  only its managed-literal identities, so new names from other sources are open.
- When lanes share code, **keep each lane's own layout sentence and non-claims**:
  unifying them once silently dropped `0x02`'s source-identity and cross-bank
  disclaimers, which counts alone could not reveal.

## Corrections the corpus could not force by itself

Durable lessons; each has a published histogram or counter.

- **Group I key is variable-size.** `0x02` spends one byte on every key, so a
  fixed width survived that corpus and would have mis-framed the `0x07` objects
  with wider keys (`groupIKeyWidth_*`). Its five-byte cap and 32-bit range are
  inherited from the `0x03` reader, not proven here.
- **Group H state is variable-length** (`u32 id`, `u16` count, then `count` x
  `u16 AkPropID` and `count` x `u32` value, from
  `CAkStateAware::ReadStateChunk`). A fixed twelve bytes survived three whole
  corpora because every state had one element; `0x09` carries two
  (`groupHStateWidth_*`). **A width a one-dimension sweep calls uniquely
  determined is unique only over the shapes the corpus contains.**
- Group E selector `0x01` appears without the extension, disproving a bit-0
  predicate (thin: very few objects); selector `0x02` is unobserved and the
  reader follows the engine. Group B is empty in every shipped body; its
  six-byte element comes from the SDK reader and a fixture.
- **The action type is the whole 16-bit word.** Framing keys on the high byte,
  but that mask had become the published identity (four Stop words all shown as
  `stop`). The contract names all but `0x1B02`/`0x1B03`, which stay unnamed: the
  stock enum stops at `0x1B01` and a low-byte-pattern name would be fitted.
  **A mask chosen because it decides a layout quietly becomes identity.**
- **The RTPC type is `AkGameSyncType`**, not `AkRtpcCurve::OwnerType`
  (`AkRtpcCurveParams.rtpcType` in the PDB; `ReadRtpcCurves` reads the byte into
  it; 5/8 are markers). The corpus exercises `GameParameter` and `Modulator`.
  Naming the field proves no live value or curve activation.

## The reference graph (layer 3 closes, layer 4 opens)

- **The terminal vectors of `0x04`/`0x05`/`0x06`/`0x07`/`0x09` are object
  identities**: every counted reference resolves to exactly one object declared
  in the same bank, with no self reference, no target with two referrers, no
  cycle, and a longest chain of 8 references. Every such number is computed by
  the reader. A few object ids repeat inside a bank; no reference targets one.
- **`0x06` is where the join said no.** Only its child vector resolves
  completely; unmatched group-item and record words are published as
  `candidateWords` and not joined (the first attempt claimed all three vectors
  and the gate failed it). **Believe the counter and narrow the claim.**
- **Correction: action targets cross banks and packages.** The same-bank result
  is a fact about those counted vectors, not the corpus. The `0x03` target word
  names an object in another bank of the same package, or in another package,
  far above the ~1.5 hits chance predicts (~1,460x). Targets outside the reader's
  package are counted as outside, not unresolved, and the gate asserts that the
  crossing is observed so a future zero cannot restore the old claim. The first
  body byte clearly matters (`action_03` carries nearly every in-bank
  resolution, `action_04` resolves for under 1% of its targets) but is
  **reported, not claimed as a decider**: no class is clean the way the plug-in
  partition below is, so a rule would be fitted.
- **Two corpora, one object apart**: the structural gate audits every AKPK
  package, the WebUI bank reader only bank/hotfix packages (missing
  `audit_stream.pck`). Quote which corpus a count came from; see the comment on
  `build_audio.EVENT_BANK_FILE_REGEX`.

## Naming: what the shipped literals reach

- **The test is a computed coincidence rate, not a vocabulary.** A folded
  `AudioHashGenerator` hash of a structural-shape literal hits a type by chance
  with probability `population / 2**32`. `0x04`, `0x08` (bus-shaped names) and
  `0x15` (device-shaped names, 4 of its 5 objects) clear it by three to five
  orders of magnitude -- the shapes describe the strings, not what the types
  do; `0x02` matches at its own coincidence rate, so its
  name-like matches are reported and **not** claimed. The gate applies the bar
  to every type and refuses a pass where nothing clears it. The narrow
  `au_`/`bark_`/`radio_` prefix claim is gated separately.
- **Sixteen types match no literal** (`0x03`, `0x05`-`0x07`, `0x09`, `0x0A`-`0x0E`,
  `0x10`-`0x14`, `0x16`): their anonymity is a property of the data.
- **Bank ids are named; media ids are not** (zero, against an expectation
  under one): the identifier chain ends at an opaque media id, so do not look
  for a filename. No named bank id is also a HIRC object id.
- **The chain is closed: shipped identifier -> media file.** The named walk runs
  package-wide (`walkEdgesLeavingThePackage`; a per-bank walk abandoned
  sibling-bank edges) and includes `0x09` child vectors (layer containers sit
  between many named Events and their sounds). It publishes the reached ids
  with the counts and refuses a count without its list. Matched objects exceed
  identifiers because a few named objects are declared in two packages, which is
  expected. Music containers are not in this walk.
- **The plug-in id decides whether a source names shipped media.** Joining the
  `0x02` source id to AKPK media ids, `0x00040001` and `0x00140001` always name
  shipped media; `0x00080001`, `0x00640002`, `0x00650002`, `0x00940002` and
  `0x01990002` never do; no plug-in id is split and the gate enforces that. The
  low nibble does not explain it (`0x00080001` is type 1 and never resolves).
  **Compute this across the whole corpus, never per package** (the
  cross-package trap in [`audio_naming_coverage.md`](audio_naming_coverage.md)).
  `hirc_v150.HIRC_SOURCE_PLUGIN_LABELS` names them (Vorbis, Opus; External
  Source, Sine, Silence, Motion Source, Synth One): class identity, not proof
  that a generator or external source runs. Every reached source id with no
  shipped media comes from a never-media plug-in id.

## Non-claims go stale, and nothing makes them fail

Four report non-claims ("media placement unidentified", "target resolution not
established", "entry values unnamed", ...) were right when written and later
falsified by a sibling lane; each report is gated only on what it claims. Treat
"this does not establish X" as dated, and when a conclusion is corrected, grep
every report and docstring that repeated it. Tests pin the scoping.

## The SDK witness

- **The shipped `AkSoundEngine.dll` is Wwise 2023.1.17** with in-house changes:
  its only version string is `wwise_v2023.1.17`, and its assert paths name a
  stock build root and a vendored `RM42.Beyond` tree, so every stock-SDK layout
  must meet the bank bytes (the corpus gates check that; every layout has
  passed). Its hash is pinned in `contracts/wwise_effect_parameters_native.json`.
- The DLL is unpacked (no `.tvm0`), RTTI-stripped and names only the chunk
  tags: **do not string-mine it** for layouts.
- **The witness is the SDK's Profile static libraries and PDBs** (exact version
  2023.1.17.8841): named v150 deserializers that disassemble with `dumpbin`,
  vtable slots resolving from relocation tables, PDB type records for the enum
  contract; `scripts/game_data/wwise_sdk_symbols.py` matches shipped functions
  to them. They are Audiokinetic's under EULA: record derived facts, never
  vendor them, and gate the SDK inputs afresh on each machine.
- **The shipped DLL cannot be profiled** (no communication layer).
- `INIT` names `0x01990002` (source 409) and `0x01FB0007` (sink 507)
  **AkMotion** ([`audio_bank_format.md`](audio_bank_format.md)): authored class
  identity, not registration, instantiation or output.

## Recovery queue

Closed and not to reopen: shared SDK enum naming (unsupported values stay
numeric), bus vocabulary in the typed v150 projection, and the structural
`0x0C` decision-tree walk (child ranges, strict sibling-key order, reachable
nodes, same-bank leaf joins; `+8` is a relative weight and `+10` a
selected-leaf probability gate, so siblings need not sum to 100). Open inside
them: plug-in-specific value tables, leaves with no same-bank declaration,
runtime bus and leaf selection.

1. **Plug-in parameter blocks.** Convolution Reverb and Mastering Suite have a
   direct registration -> factory -> vtable -> `SetParamsBlock` join but stay
   opaque (an older unchecked DLL pin once let stale native labels onto the
   page; the effect contract now binds the selected hashes). The next witness is
   plug-in-specific parameter definitions or exact native consumers
   ([`audio_hirc_graph.md`](audio_hirc_graph.md)); never fit names from
   corpus correlation.
2. **Layers 5 and 6 need a host, not a reader**: link the SDK Profile libraries,
   load the game's `.pck` files through the sample file-package I/O, register
   the plug-ins the game compiles in, and use the Query API and output capture
   under chosen switch/state/RTPC values. Treat its output as a strong prior and
   cross-check the native path in [`audio_native_hooks.md`](audio_native_hooks.md).
3. **Music containers in the main graph** collide with the music-reach edge
   tables and change every published count: one gated step, then rerun the
   named-reach gate.

## Do not repeat

- Corpus-only stride sweeps for any HIRC type: the reader that wrote the bytes is on disk.
- String-mining the game DLL, or re-deriving what these notes already record: read memory first.
- Little-endian varint decoding of HIRC fields.
- Per-package joins for anything that can land in two `.pck` files.
- Reconciling the two corpora by widening the bank regex.
- Reading the stream packages whole through the CLI JSONL stream (out of memory).

## Recipes

The SDK reading workflow (dumpbin on extracted objects, relocation-table vtable
slots, `pdb_enums.py`) lives with its dumps under
`scratch/reverse_engineering/wwise_sdk/`. The corpus gates are
`python -m scripts.webui.audio.semantics.hirc_action_corpus
--expected-input-set-sha256 <current inputSetSha256>`, then
`python -m scripts.webui.audio.semantics.hirc_named_reach`, about four minutes
each, after `scripts\game_data\extraction\animestudio\rebuild.bat -Target CLI`.
