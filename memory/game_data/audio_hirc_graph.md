# The HIRC object graph, and the types that are closed

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 3, audio lane.** The first structure above byte layout: the relations, how
they are told apart, and the per-type layouts that are closed byte-exact.

## Current position

- **Every shipped type frames byte-exact from the SDK deserializer** (see
  [`audio_hirc_parser.md`](audio_hirc_parser.md)); the field order per type is the
  module docstring of
  [`hirc_v150.py`](../../scripts/webui/audio/semantics/hirc_v150.py).
- **Two readings of the same bytes coexist.** The typed v150 parse in `hirc_v150`
  names fields. The corpus censuses in the AnimeStudio reader, gated by
  [`hirc_action_corpus`](../../scripts/webui/audio/semantics/hirc_action_corpus.py)
  and [`hirc_named_reach`](../../scripts/webui/audio/semantics/hirc_named_reach.py),
  measure words at corpus offsets and predate the SDK read. They stay as regression
  guards on the bytes; field names belong to the lanes and the typed parse. Each gate
  function's docstring records its measurement, controls and non-claims.
- **What the SDK names in the censuses.** The `0x08`/`0x12` leading word is the
  `CAkBus` parent bus, and a null one is followed by `idDeviceShareset` -- the extra
  word the corpus found on null-reference bodies. The front-offset parent of `0x02`,
  `0x05`, `0x06`, `0x07` and `0x09`, and the music word at offset 9, are the node
  frame's `DirectParentID`. `0x0A`'s counted array is a segment's children list; the
  name hashes near the end of `0x0C` are decision-tree keys; `0x0B`'s closing word
  100 is `iLookAheadTime`; the 14-byte record `0x02` and `0x0B` share is
  `AkBankSourceData`.
- **Evidence boundary.** Everything here is authored serialized structure: relations,
  counts of references, authored values. None of it is runtime DSP, effective
  inheritance, live State/RTPC/modulator values, branch choice, or audibility.
  Changing counts live in the `reports/animestudio/hirc_*_current_latest` reports
  and the generated Audio summary.

## Three relation kinds, told apart by in-degree and symmetry

| relation | direction | what separates it | gates |
| --- | --- | --- | --- |
| main reference graph (`05`->`02`, `07`->`07`, `09`->`05`, `04`->`03`, ...) | owner -> owned | every target named by **exactly one** referrer; same-bank by closure | `reference_graph_is_closed` |
| bus parent (`0x08`/`0x12` leading word) | child -> parent | many children per parent; a forest per bank | `the_shared_hierarchy_is_a_forest`, `almost_every_bank_contributes_one_tree`, `numeric_type_12_is_a_leaf`, `the_hierarchy_runs_opposite_to_the_main_reference_graph` |
| music references (every word offered) | mostly mutual | the reverse edge is present for about three quarters of askable edges; almost all same-bank | `the_music_relation_is_symmetric`, `music_references_resolve_inside_their_own_bank`, `music_bodies_all_carry_references` |

- **Direction is visible in in-degree, not in shape.** Both hierarchies are forests;
  only how often a target is named tells owner->owned from child->parent. The bus
  relation is deliberately **not** in the main reference graph: adding it would break
  that graph's one-referrer-per-target closure.
- **The parent field is the exact inverse of the child lists.** `DirectParentID`
  names the object whose counted child list names the child back, with zero
  disagreements across every checkable case and more than five type pairs
  (`the_parent_field_inverts_the_reference_graph`). Two different byte sources
  agreeing exactly is the strongest cross-check the format allows. `0x04` at offset 1
  looked like a parent and is not: it names a `0x03` in the same direction as the
  graph edge. The music offset-9 word is not part of this test (the main graph
  carries no music type); it is censused separately and forms its own forest below.
- **The music relation cannot be read as parenthood in either direction**, and it is
  not cliques (neighbours of a node are almost never linked). Only edges whose target
  was itself scanned can be asked for a reverse edge; counting the others as one-way
  mixes "not mutual" with "not askable".
- **Scope decides what a relation is.** The bus forest is built per bank. On
  deduplicated ids it merges unconnected trees into a few and looks far tidier. An
  object with no parent is a root; one naming a parent outside its bank is a root only
  of that bank's fragment -- and those are all `0x12`, whose parent usually lives in
  another bank. Almost every bank contributes one tree.

## The bus forest

- `0x08` sits above and `0x12` below; every parentless object is a `0x08`. `0x12`
  mostly names a `0x08`, `0x08` also nests in itself, a few name the audio device
  (`0x15`), and neither names a music type.
- The typed `CAkBus` parse in `hirc_v150` consumes every published bus exactly and
  resolves each to a parent bus or an explicit root; its layout (the property bundle,
  positioning, aux, limits and ducks **before** InitialFX, then InitialRTPC **before**
  StateChunk) is why byte scanners mistook duck and state data for effect counts.
- The pre-SDK corpus framer for `0x08`/`0x12` (reference, bundle, sized second list,
  nine-byte field, counted runs, a tail block of units and 12-byte records) is
  superseded by that parse. Its gates remain: `type08_head_words_are_null_or_resolve`,
  `type08_tail_head_names_one_object_type`, the tail-record and partial-body gates,
  and the shared-constant rival gates.
- **`0x08`'s tail-head first word names a `0x12` object**, against a control word in
  the same head that resolves zero times. The same words in `0x12`'s tail resolve
  zero times, control included: sharing a layout does not make a field mean the same
  thing, so the finding is not carried across.
- **Music segments reach buses in other packages.** `0x0A`'s word at offset 5 (where
  the SDK frame puts `OverrideBusId`) never resolves inside its own package; corpus-wide
  every value resolves, to `0x08` objects apart from one variant
  (`the_type0a_word_five_points_outside_its_package`).

## The music family

These are corpus measurements; the lanes frame the same bytes by name.

- **One authored bank shipped twice.** One bank appears byte-identical in
  `audit_banks.pck` and `hotfix_main_b75.pck` and holds nearly all music objects, so
  music totals are about double the distinct population. Closure rates are
  unaffected; sample sizes are not. `the_corpus_reports_its_duplication` publishes
  the distinct count beside every total.
- **`DirectParentID` forms a forest** chaining `0x0A` -> `0x0D` -> `0x0C` -> `0x0C`
  (with `0x0A` -> `0x0C` directly): acyclic per bank, deep, many children per parent
  -- the same shape as the bus relation in an unrelated family
  (`the_type0c_parent_relation_repeats_the_same_shape`). The typed parse reads it
  through the whole node base (`hirc_v150.hirc_object_parent_id`). The C# census's
  head word is `DirectParentID` only when body byte 2, the FX count, is zero
  (offset 9); in the nonzero branch its offset-5 word is the first FX slot's
  `fxID`, and the parent sits at `10 + 6 x uNumFx`. Those bodies' head words are FX
  references that happen to resolve in the same bank, not parents. Five `0x0C`
  bodies with first byte 6 follow neither branch and are counted, not dropped; a
  fourth byte-2 value must fail closed (`music_head_references_are_closed`).
- **Every `0x0B` is a child of exactly one `0x0A`** -- as many distinct targets as the
  type declares, none twice, none missed (`the_music_partition_edge_is_one_to_one`).
  The word before the first child is a count that is right in every body that carries
  one (`the_type0a_reference_is_a_counted_array`); the segments without a track are a
  whole population four bytes shorter, not anomalies.
- **`0x0A` and `0x0D` place their references in fields, `0x0C` in lists**: edges per
  distinct end distance separate them by an order of magnitude with an empty middle
  (`the_music_types_split_into_located_and_scattered_references`). A handful of
  `0x0C` bodies carry over half its references, so quote its median, not its mean.
  The `0x0A` -> `0x0B` edge alone is 4-byte aligned to the body end
  (`the_type0a_to_type0b_edge_is_aligned_to_the_body_end`). `0x0C`'s first counted
  array sits at `32 + 5 * body[14]` against rival bases that find nothing, and a flag
  inside the fixed region after it places the next block
  (`the_type0c_reference_array_is_located`, `..._region_flag_places_the_next_block`).
- **`0x0C` names**: the words 12 and 24 bytes from the end match FNV hashes of shipped
  literals far above chance (`High`, `Low`, `Loop`, `WIN`, `Start`, `NONE`, ...);
  they are decision-tree keys. `music_tail_words_are_named` skips rather than passes
  when no names were supplied.
- **Authored values in `0x0A`, recorded as observations**: a float that is whole in
  almost every body, 55-190 with modes 120, 130, 110, 90 (tempo-like; `AkMeterInfo`
  carries `f32 fTempo`); a 32-bit fixed-point fraction of one beside it; a bounded
  whole float with a -96 floor in the head; the constant `0x408F4000` shared by
  `0x0A`, `0x0C` and `0x0D` and almost absent from `0x0B`. What each measures is not
  claimed by the gates.
- **Nothing outside the family enters it.** The main graph and the parent field carry
  no music type; five action-target words land on `0x0C` roots with no outgoing edge
  and reach no source id (`the_music_family_is_not_entered_from_the_object_graph`);
  the non-HIRC sections name only buses. This says no resolved relation reaches
  music, not that music cannot play at runtime.

## Source records, media and names

- **`0x02` and `0x0B` share the 14-byte `AkBankSourceData` record**, and their
  plug-in ids are built-in codec ids: `0x00040001` Vorbis and `0x00140001` Opus in
  WEM, company 0, type Codec. No third-party or premium plug-in is referenced, so the
  base SDK is sufficient.
- **The source id names shipped media, across packages.** Essentially all declared
  media are named by some record (`0x02` for most, `0x0B` for the music media), and
  the words one byte either side name almost none (`media_attribution_is_discriminated`);
  the plug-in id alone decides whether a source id names shipped media
  (`media_join_is_decided_by_the_plugin_id`). A bank's media usually live in another
  package, so every join is a corpus union.
- **Action targets cross banks** (`type03_targets_cross_bank_boundaries`); the gated
  reference vectors do not.
- **Type `0x04` is the object managed code addresses by name.** Every match between a
  metadata literal hashed with the shipped `AudioHashGenerator` (FNV-1 over UTF-16
  with ASCII case folding) and a HIRC id lands on a `0x04` and on no other type; the
  walk from it to media is in `hirc_named_reach`.
- **The 12-byte point `{f32, f32, u32 interpolation 0..9}`** is one record in RTPC
  curves, layer and clip-automation curves, attenuation curves and `ENVS`. Its code
  alphabet is dominated by 9 and 4 everywhere.

## The typed v150 parse

Detail lives in the owning modules; this is the boundary.

- **Effects.** NodeBase effect slots, output-bus ids and effect definitions (PCK and
  bank scope, class id, parameter hash) are exact. Typed built-in parameter values
  need the selected-build gate in
  [`wwise_effect_native.py`](../../scripts/webui/audio/semantics/wwise_effect_native.py)
  over [`wwise_effect_parameters_native.json`](../../scripts/game_data/contracts/wwise_effect_parameters_native.json).
  Convolution Reverb and Mastering Suite are joined to their methods structurally,
  with contiguous read spans and no field meanings; RoomVerb keeps eleven unnamed
  floats. Slot flags are authored, not runtime DSP.
- **Buses and NodeBase tail.** The bus forest is typed and complete. The NodeBase
  tail yields AuxParams (user-defined aux slots reach aux buses; no populated
  early-reflections target), AdvSettings, State groups and RTPC curves, checked by an
  independent unique-payload audit. Game-defined aux ids, listeners and send levels
  are runtime inputs.
- **Properties.** Initial AkPropID bundles keep raw u32 and float forms; initial
  BypassFX/BypassAllFX ids do not occur; unnamed ids stay numeric.
- **Controls.** Non-playback Action tails are typed exactly or published as
  `failedClosed` with an offset and a reason. Six `AU_RTPC_*` GameParameter names are
  symbol-to-id evidence only
  ([`rtpc_alignment.py`](../../scripts/webui/audio/semantics/rtpc_alignment.py)).
  Type-6 selector packages join media only through exact same-bank evidence
  (`event_projection.selector_branch_projection`).
- **Media rows** project all of this per possible leaf; the contract, including
  `noExplicitOutputBusSerialized`, is the module docstring of
  [`media_rows.py`](../../scripts/webui/audio/semantics/media_rows.py).

## Rules this file taught

- Check a structural test against the degenerate input that passes it for free -- a
  run of zeros, a count of zero, a one-element list -- before reading its hit rate.
- A constant fitted by closure is established only if rivals scored the same way lose;
  score only the bodies that exercise it and reduce on corpus totals.
- Count bodies, not entries: one body can carry a whole total, and a 100% rate over
  optional structure is an average of claims.
- A field that is 0 in almost every body and small elsewhere is a count; a
  single-element counted run is indistinguishable from a fixed head.
- Measure locality from both ends of a variable-length body. Resolve ids in the
  right scope: per bank for a forest, corpus-wide before calling a word "resolves
  nowhere".
- A one-to-one claim needs distinct targets equal to the population, no repeats, and
  the edge total equal to both; an edge total alone supplies none of them.
- A neighbouring offset is a control only if it is not itself part of the structure.
- Never re-implement a hash the repo already mirrors: a duplicate FNV without the
  case fold once lost every literal with capitals.
- When rules accumulate around a field, suspect the field's shape; when a walk
  desynchronises, look for the next occurrence of something already parsed; when
  words look misaligned, find where a known sentinel sits to recover the grid.
- When a type will not frame, offer every word: sparse 32-bit ids let the id space
  discriminate. When a small type resists, look for a structure another type closes.
- Before presenting a located field as new, grep the reader for its offset; print a
  sigil, not a count, for varying positions in a byte table.

## Eliminated readings

- **Corpus-only framing of the music types** (head rules, end anchors, region grids,
  the `0x0D` `165 + 34a + 5b` length rule, the `0x0B` fixed 88-byte entries): fits
  retired by the SDK read. The length rule is a regularity of lengths only; the
  length groups do not align to one repeated block.
- **A second counted array in `0x0C`**: every "count" before it was 1, which any word
  holding 1 satisfies.
- **The music heads as a fixed skeleton**: only a few front positions are constant;
  the node frame parses at many offsets, so "it parsed" carries no information there.
- **The `0x08`/`0x12` tail in the music types**: the tail block fits almost nothing,
  and the apparent entry-run matches were all count-zero bodies.
- **The 12-byte curve record in `0x0A`/`0x0C`/`0x0D`**: chance fits; the unconstrained
  scan's near-total hits on `0x0D` were runs of zero bytes.
- **Curve propagation along bus edges**: untestable here -- too few edges with curves
  at both ends, and a shared-code statistic that scores the same on shuffled pairs.
- **`0x08` tail-head words as names**: none matches an FNV hash of any metadata string
  literal; the head's word at offset 10 is not a reference.
- **A head byte that sizes `0x0A`'s tail, or a byte inside the tail that counts its
  extension**: neither exists; the four-byte insertion sits right after the child
  reference.
- **The "fixed 9-byte signature" in `0x08`/`0x12`**: a field that varies in one 32-bit
  slot, not a magic.
- **A hand-read "zero-unit" tail layout**: invented from two samples, closed 1 of 10.
- **A misplaced entry run as the cause of the remaining fenced tails**: no run length
  from 0 to 63 frames them.
- **A `0x11` classification of the two edges into it**: too few references to place
  them on either side of an empty-middle discriminator.

## Open

- Convolution Reverb and Mastering Suite parameter meanings need plug-in-specific
  definitions or exact native consumers. Do not fit names or runtime roles from
  corpus correlations.
- The AnimeStudio music head census should read `DirectParentID` after the FX and
  metadata groups instead of taking offset 5 when the FX count is nonzero; until
  then its nonzero-branch rows are FX references.
- Several lane residual strings still describe SDK-named fields as opaque (the
  `0x05` policy block, the `0x06` group head, the `0x0E` head); the names are in
  `hirc_v150`, the lanes do not publish them yet.
- Runtime: game-defined aux sends, live RTPC and State values, selector and decision
  tree choice, duck activation, effective inheritance, and audibility.
