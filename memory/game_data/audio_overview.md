# Audio: what the evidence is, and where it stops

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, audio lane.** Start here for audio. It states the scope of the Wwise
evidence and the boundary between an authored link and an observed one, which the
rest of the lane depends on.

## The six layers of audio evidence

Audio recovery separates six layers:

1. physical package/media identity;
2. decoded playable media;
3. Wwise Event/action/media graph;
4. authored game consumer and control parameters;
5. validated runtime request;
6. selected branch, audibility, and final DSP behavior.

Evidence may advance only one layer at a time. A stronger downstream fact does
not retroactively make every upstream candidate unique.

## Per-type structural gates

Stable conclusions:

- `build_audio.py` owns decode, bank/HIRC indexing, relinking, and Gameplay
  sidecars. Shared SFX/music and language voice remain separate physical roots.
- Numeric HIRC type `0x03` Action bodies now have an input-set-bound structural
  cursor gate. It joins verified package hashes/chunks/physical sources to the
  authenticated outer ledger and reconciles per-bank with package totals;
  unsupported bodies stay unsupported. Exact framing does not establish
  operation names, field ownership, targets, runtime execution, selection, or
  audibility. Current corpus details belong in
  [`reports/animestudio/hirc_action_current_latest.md`](../../reports/animestudio/hirc_action_current_latest.md).
- Numeric HIRC type `0x02` source prefixes have a companion current-corpus
  gate. The maintained parser bounds the 14-byte prefix and the optional
  plugin-type-`0x02` parameter range; the gate reconciles object counts and
  prefix-plus-opaque-tail body bytes per bank/package against the authenticated
  outer ledger. The remaining body stays opaque and has no full cursor claim.
  See [`reports/animestudio/hirc_type02_prefix_current_latest.md`](../../reports/animestudio/hirc_type02_prefix_current_latest.md).
- Numeric HIRC type `0x04` bodies have a third current-corpus structural gate.
  It checks an anonymous one-byte-count/32-bit-entry candidate against declared
  body lengths and bank/package totals, preserving short bodies and trailing
  bytes as explicit failures or opaque tails. Its report binds the current CLI
  output-directory manifest and the exact intermediate bytes it parsed,
  separately from the outer audit's apphost fingerprint. Exact framing does not
  identify entry values, fields, Action relationships, runtime execution,
  selection, or audibility. Current corpus detail belongs in
  [`reports/animestudio/hirc_type04_u32_vector_current_latest.md`](../../reports/animestudio/hirc_type04_u32_vector_current_latest.md).
- Numeric HIRC type `0x02` bodies are now consumed **whole** by a fourth
  current-corpus gate, which supersedes the prefix lane's opaque-tail
  statement without retracting it. After the bounded source prefix the
  maintained reader frames nine anonymous groups: two flag/count slot
  vectors, two parallel one-byte-key/value bundles (4- and 8-byte values), a
  selector-directed vector pair, a selector-directed fixed block, a fixed
  six-byte block, a nested property/group/state directory, and a counted
  entry list with counted 12-byte points. Every current body reaches its
  declared end with no trailing bytes. A one-dimension-at-a-time candidate
  sweep pins twelve of fourteen widths uniquely against whole-corpus exact
  closure; two stay unresolved and fail closed instead of guessing: group
  B's element width (no current body carries a nonempty vector) and group
  E's selector predicate (its two low bits never disagree, so bit0-only,
  bit1-only, and both-bits cannot be separated). The group A split between
  a shared mask byte plus 6-byte slots and no mask byte plus 7-byte slots
  rests on one counterexample object plus non-boolean trailing bytes under
  the rejected reading; treat it as the weakest link in the frame. Group
  letters, selector bits, keys, and values stay anonymous: exact
  consumption is not field ownership, source/effect/bus/parent identity,
  cross-object relationships, runtime execution, event selection, or
  audibility. Two things about this gate must not be over-read. The
  constraining checks are that framed body bytes equal the declared object
  bytes minus object ids and that every exact body ends at its declared
  end; the `exactCursorBytes + nonExactBodyBytes = bodyBytes` identity is an
  internal assert that cannot fail, because a short read is never labelled
  exact. And `failed = 0` is partly upstream luck: a malformed source prefix
  throws in the preceding prefix census and aborts the whole package, so it
  never reaches this lane as a counted failure. The lane now enforces its
  own result -- any failed, unsupported, or ambiguous body publishes
  `incomplete` and exits nonzero -- so a future client update that
  introduces a nonempty group B vector stops the gate instead of quietly
  lowering the number. Current corpus detail belongs in
  [`reports/animestudio/hirc_type02_body_current_latest.md`](../../reports/animestudio/hirc_type02_body_current_latest.md).
- Those nine groups are **not** type-`0x02`-specific. Numeric HIRC type `0x07`
  reuses them with no source prefix and one terminal counted vector of
  four-byte anonymous references, and all 48,740 current objects / 3,572,927
  body bytes consume exactly. One maintained reader now frames both types, so
  the guards and the fail-closed rules cannot drift apart. Type `0x07` also
  corrected two things the type `0x02` corpus could not. The group I entry
  carries a **variable-size** anonymous key, not a fixed byte: type `0x02`
  bodies spend one byte on all 475 of theirs, so a fixed width survived that
  corpus and would have silently mis-framed exactly the 90 type-`0x07` objects
  that contain a wider key. And group E selector `0x01` appears with no
  extension, which disproves a bit-0 branch predicate — though that rests on
  4 objects out of 48,740, so treat it as thin. Selector `0x02` is still
  unobserved everywhere, so bit-1-only and both-bits-set remain tied and fail
  closed. Say the refactor result precisely: the type `0x02` **counts** are
  unchanged and its report diffs clean, but two **behaviours** changed on paths
  that corpus never exercises, so a fixture now pins a continued key on the
  type `0x02` path too. The key's five-byte cap and 32-bit range are inherited
  from the type `0x03` Action reader, not proven here; both lanes publish a
  `groupIKeyWidth_*` histogram so the widths actually witnessed stay auditable
  (today: only 1 and 2). Group B is still empty in every framed body of both
  types, so its element width stays unresolved, and both lanes now publish the
  same shared-framer residual list rather than each carrying a shorter one.
  Reference targets, container membership, ordering and selection are not
  claimed. See
  [`reports/animestudio/hirc_type07_body_current_latest.md`](../../reports/animestudio/hirc_type07_body_current_latest.md).
- Numeric HIRC type `0x05` is the third type on the shared node frame: node
  groups, then a fixed 24-byte opaque block, one counted vector of four-byte
  anonymous references and one counted vector of eight-byte anonymous records.
  All 30,352 current objects / 3,652,971 body bytes consume exactly. The two
  terminal counts are **independent**: 130,591 references against 130,655
  records, and the reader publishes `referenceRecordCountMismatch` (39) so that
  per-object claim is a measurement in the report rather than prose nobody can
  check. Neither vector is a projection of the other and no relationship between
  them is claimed. When unifying lanes, keep each lane's own layout sentence and
  its own non-claims: collapsing them once silently dropped type `0x02`'s
  source-identity and cross-bank disclaimers and every lane's description of what
  its framer consumes, which the counts alone could not reveal. With three lanes sharing
  one framer, the maintained code now carries one census object, one metrics
  reader, one accumulator, one markdown renderer and one report publisher;
  adding a further type is a lane declaration plus a framer, and the shared
  residual list is published identically by every lane. Corpus detail is in
  [`reports/animestudio/hirc_type05_body_current_latest.md`](../../reports/animestudio/hirc_type05_body_current_latest.md).
- The shared node frame's group H **state is variable-length**: a four-byte key
  plus its own `u16`-counted vector of six-byte elements. A fixed twelve bytes
  survived three whole corpora because every one of their 1,546 states carries
  exactly one element; type `0x09` bodies carry two and disprove it. This is the
  second latent fixed width of the same class, after the group I variable-size
  key. Within the field family `{key, count at +4, count elements, fixed tail}`
  the six-byte element is forced, not fitted: a `u32` count would make the
  two-element sample declare 65,538 elements, and widths 3, 4 or 12 contradict
  the count the one-element sample carries. That uniqueness is only inside that
  family -- a fixed twelve-byte state followed by a separately gated six-byte
  structure is **not** excluded, which is precisely the failure mode being
  corrected, so the census carries it as a residual. Note also that the shipped
  reports alone cannot settle this: every state they publish is one element wide,
  and the only non-degenerate witness is type `0x09`, which is not a shipped
  lane. Take the pattern seriously: a width that a
  one-dimension sweep reports as
  *uniquely determined* can still be a degenerate case, because uniqueness is
  only ever over the shapes the corpus happens to contain. Both lanes now publish
  `groupHStateWidth_*` and `groupIKeyWidth_*` histograms so the degenerate case
  is visible rather than inferred, and the gate requires each histogram to match
  both its count and its byte total. Type `0x02`, `0x05` and `0x07` still close
  exactly after the correction, so no published count changed.
- Numeric HIRC type `0x09` is **not** a closed lane and is deliberately not
  shipped as one. Its bodies are the shared node frame, a counted four-byte
  reference vector, a counted layer vector and one trailing byte, where a layer
  is a fifteen-byte header plus a counted list of per-reference twelve-byte graph
  points. That frames 5,154 of 5,158 current objects. The other 4 carry a
  nonempty `u16`-counted sub-list inside the layer header that the rest never
  exercise, and its element width cannot be separated from the surrounding
  fields without guessing, so the grammar stays unresolved rather than being
  fitted to four samples. Do not publish a type `0x09` lane until those four
  parse; the gate would refuse it anyway.
- **That 5,154 grammar is documented here but not implemented anywhere, and this
  prose is not enough to rebuild it.** A later attempt re-derived type `0x09` from
  scratch with a validated node-frame mirror and reached only 4,982 bodies at
  best, after sweeping 48 layer-grammar variants (header widths 8..23 against
  fixed, single-counted and per-reference point lists). None reproduced 5,154. If
  the layer grammar is revisited, **write it down as field widths and offsets or
  as code**, not as a sentence -- a number in a note that nobody can reproduce is
  worse than no number.
- What that attempt did confirm independently: the shared node frame opens **all
  5,158** type `0x09` bodies, and after it come a counted run of four-byte
  entries and a second count. Where the second count is zero, one further byte
  closes the body exactly -- 4,973 bodies, 308,489 of 344,190 bytes, now gated and
  tested in the reader. The other 185 are fenced. **This shipped census is
  deliberately weaker than the 5,154 recorded above**; it is what is verified in
  code, not the best reading anyone has had.
- **Layer 4 opens for audio.** The anonymous four-byte values inside the exactly
  framed terminal vectors of numeric types `0x04`, `0x05`, `0x06` and `0x07` are object
  identities. All 230,247 of them resolve, every one to exactly one HIRC object
  declared by the **same bank**: zero unresolved, zero crossing a bank or package
  boundary, zero self references, zero targets carrying more than one referrer,
  zero framed entries that never reached the census, and zero nodes on or feeding
  a cycle, at a longest traversed chain of 7 references (8 objects). Every one of
  those numbers is computed and published by the maintained reader; none is prose.
  Numeric edge counts and a per-type referenced-versus-population table are in
  [`reports/animestudio/hirc_reference_graph_current_latest.md`](../../reports/animestudio/hirc_reference_graph_current_latest.md).
  Seventeen object ids repeat inside a bank, 17 distinct ids over 17 repeat
  occurrences, so each appears exactly twice; **no reference targets a duplicated
  id**, so that ambiguity does not touch the claim.
- Numeric HIRC type `0x06` is the fourth type on the shared node frame: node
  groups, a fixed ten-byte opaque header, one counted four-byte reference vector,
  one counted group list where each group carries a four-byte key and its own
  counted vector, and one counted vector of fourteen-byte records. All 4,573
  current objects / 1,334,519 body bytes consume exactly, and every suffix width
  is uniquely determined by whole-corpus closure.
- Type `0x06` is also where the reference join first had to say no. Only its
  child vector resolves completely (20,290/20,290). Of the other framed words,
  432 of 22,234 group items and 573 of 20,863 record leading words match no
  object in their bank, so those words are **not** established as identities and
  are not joined. Excluding them silently would have been cherry-picking -- a 98%
  rate reported as 100% -- so the census publishes them as `candidateWords` with
  the number that do match, and the gate requires that count to cover every
  framed word held out. The gate caught this: the first attempt claimed all three
  vectors as references and failed with 1,005 unresolved. Believe the counter and
  narrow the claim, never the reverse.

## Naming: what the shipped literals actually reach

- **Bank ids are named too, and media ids are not -- both measured.** Applying the
  same coincidence arithmetic to id populations other than HIRC objects: 175 of
  20,873 bank ids are named by shipped literals (1,448x chance), while **0 of
  61,333 media ids** are, against an expectation of 0.36. So the identifier chain
  ends at an opaque media id and does **not** continue into a filename; do not go
  looking for one.
- None of the named bank ids is also a HIRC object id, so bank names and event
  names are different strings rather than one name reused across both.
- **Sixteen HIRC types match no literal at all**, and that zero is now measured
  rather than assumed: `0x03`, `0x05`, `0x06`, `0x07`, `0x09`, `0x0A`-`0x0E`,
  `0x10`-`0x14`, `0x16`. Their ids are not hashes of any string this build ships,
  so their anonymity is a property of the data, not a gap in the search. Only
  `0x04`, `0x08` and `0x15` carry names.
- **Naming now extends past type `0x04`, and the test is a computed coincidence
  rate rather than a vocabulary.** The prefix filter (`au_`/`bark_`/`radio_`/`vo_`)
  exists because unfiltered literals resolve generic words by chance -- sound
  reasoning that cannot be checked from inside the filter. Dropping the vocabulary,
  keeping a structural identifier shape, and using the shipped folded hash
  (`AudioHashGenerator`, which lowercases A-Z) gives 24,868 literals and a
  measurable answer.
- Because the hash is 32 bits, chance is computable: a literal hits a type by
  chance with probability `population / 2**32`. Observed against expected:
  `type15` 4 matches on 5 objects (**138,000x** chance), `type08` 3 on 161
  (**3,218x**), `type04` 204 on 22,910 (**1,538x**), `type02` 2 on 142,815
  (**2.4x** -- its own coincidence rate).
- So type `0x02` is reported and **not** claimed, which is the point of the test:
  its two matches read like names (`on_threst_timer_finish`) and are noise. The
  gate requires the bar to be applied to every type, not just the convenient ones,
  and refuses a pass where nothing clears it.
- Concretely gained: type `0x04` goes from 151 to **204** named objects, and two
  new types get names -- `type08` (`Character`, `Effect`, `object`) and `type15`
  (`SYSTEM`, `System_3D`, `Controller_Speaker`, `Wwise_Motion`), the latter naming
  **4 of its 5 objects**. The type `0x15` names are device-shaped and the `0x08`
  names bus-shaped, but that is an observation about the strings, not a claim
  about what either type does.
- The narrow prefix claim is untouched and still gated separately, so widening the
  filter cannot weaken it.

## Stale non-claims, and the audit that found them

- A second audit pass found a **stale non-claim**, which is the opposite failure
  and just as misleading. The type `0x02` prefix report listed "physical media
  placement" among the things it does not identify. That was true when written and
  is now false: the source id inside that prefix joins to the media the corpus
  ships, gated in the reference-graph report. Saying it is unidentified reads as
  caution while actually being wrong.
- **Non-claims go stale too, and nothing makes them fail.** A wrong positive claim
  eventually contradicts a number somewhere; a wrong "we do not know this" just
  sits there looking responsible. When a new join lands, re-read the non-claims of
  every report that touches the same bytes.
- Sweeping the remaining reports found two more. The type `0x03` action report
  said it does not establish **target resolution** -- which the reference-graph
  report had just gated (21,956 same-bank, 1,499 other-bank). The type `0x04`
  vector report said **entry values remain unnamed** and that no **Action
  relationship** is established, while the reference graph publishes this type's
  edges into type `0x03` and the named-reach report names 203 of the objects
  holding those vectors. Both are now scoped: the entry *targets* are still
  unnamed, which is narrower and still true.
- That is four stale non-claims across four reports, all written correctly and all
  falsified later by a different lane. **The pattern is structural, not careless**:
  each report is gated on what it claims, so nothing in the build can notice when a
  sibling lane makes one of its non-claims obsolete. Treat "this does not establish
  X" as a dated statement and re-read it whenever X lands somewhere else.
- **An audit of the published wording found the over-generalisation had spread.**
  After correcting the cross-bank claim in these notes, the same claim was still
  sitting in two published reports, and one of them contradicted a table twenty
  lines above it. Both are now scoped: the reference-graph report says its
  same-bank result is a fact about *those counted vectors*, not the corpus, and
  says plainly that names do exist for some endpoints. The named-reach report says
  its "all on type `0x04`" result is a fact about *those literals*, not the format,
  since the broad pass in the same module names `0x08` and `0x15`.
- **When a conclusion is corrected, grep for where else it was asserted.** A
  correction recorded only in memory leaves the wrong sentence in every report and
  docstring that repeated it, and those are what a future reader actually reads.
  The tests now pin the scoping rather than the old absolute sentence.
- One cross-check passed and is worth recording as passing: the five reached source
  ids that name no shipped media all come from plug-in ids the media partition says
  never name media (`00080001`, `00640002`, `00650002`). The media join and the
  identifier chain agree.
- **Correction: this corpus DOES contain cross-bank references.** The numeric type
  `0x03` target word leaves its bank routinely -- of 28,379 targets, 21,956 name an
  object in the same bank, **1,499 name one in another bank of the same package**,
  4,907 name nothing the package declares, and 17 are null. A Python probe that can
  see every package classifies 739 of those 4,907 as objects in a *different
  package*, so the relation crosses package boundaries too.
- This is not marginal and not a coincidence: a random 32-bit word lands on one of
  the 231,693 declared object ids about **1.53 times** across all 28,379 targets,
  against 2,238 observed crossings -- roughly 1,463x chance.
- **What was wrong was the generalisation, not the measurement.** The gated
  reference vectors of types `0x04`/`0x05`/`0x06`/`0x07` really are all same-bank,
  and that is still true. Recording it as "this corpus has no cross-bank evidence"
  extended a fact about those vectors to the whole corpus, and several notes in
  this file repeated it. Actions are a different relation and behave differently.
- The first body byte clearly matters -- `action_03` resolves 21,894 times in-bank
  while `action_04` resolves 17 times in 3,578 -- but it is **reported and not
  claimed as a decider**, because no class is clean the way the type `0x02`
  plug-in partition is. A rule here would be fitted rather than found.
- Targets outside the package are counted as outside rather than unresolved: the
  reader sees one package and cannot speak for the others. The gate asserts that
  the crossing is *observed*, so a future reader reporting zero cannot quietly
  restore the old conclusion.

## The named-reach walk, and reaching shipped media

- **The chain is closed end to end: shipped identifier -> media file.** 97 of the
  194 named identifiers reach at least one media file this corpus ships, reaching
  163 distinct files between them. The report lists them per identifier,
  so `au_int_erosion_sludge_recover_loop` resolves to 6 files, `au_int_box_touch`
  to 5, and so on.
- **The named-reach walk crosses banks now, and that was worth 14 identifiers.**
  It used to run once per bank, so any edge pointing at a sibling bank was counted
  as leaving and abandoned -- the same over-generalisation the type `0x03`
  classification exposed, except compiled in rather than written down. Walking the
  whole package at once takes reaching-a-source from 109 to 120, source ids from
  181 to 218, identifiers reaching media from 83 to 97, and distinct media from
  150 to 163. Abandoned edges drop from 102 to 47, so more than half of them were
  sibling-bank all along.
- The counter is now `walkEdgesLeavingThePackage`, not `...TheBank`. Renaming it
  mattered: a package-wide walk reporting "edges leaving the bank" would have
  described itself in the vocabulary of the bug it just fixed.
- Matched objects (199) exceed distinct identifiers (194) because 5 named objects
  are declared in two packages each. That is expected, not a defect -- the gate
  checks identities never exceed instances, which is the direction that would
  indicate one.
- Five reached source ids name **no** shipped media, and that is reported per
  identifier rather than dropped, because the plug-in partition establishes that
  some source ids never name media at all. A reached id missing from the media
  table is an expected outcome here, not a defect.
- The named-reach walk now publishes the reached ids themselves, not just how many,
  and the gate requires the id lists and the counts to describe the same walk: a
  count with no list, or a list shorter than its count, stops publication.
- **The audio chain now reaches shipped media, and the plug-in id decides whether
  it does.** Joining the source id in a numeric type `0x02` bounded prefix against
  the media ids in the AKPK bank and sound sectors: 60,049 of 60,997 distinct
  source ids name a file this corpus ships, and 1,284 of 61,333 media files are
  never named.
- **Read the partition, not the 98% rate.** The outcome is decided entirely by the
  plug-in id, with no exceptions anywhere: `0x00040001` (51,889) and `0x00140001`
  (8,160) name shipped media in **every** case, and `0x00080001`, `0x00640002`,
  `0x00650002`, `0x00940002` and `0x01990002` name it in **none** (948 together).
  No plug-in id appears on both sides. The gate enforces that no plug-in id is
  split and that both sides are non-empty; a rate would have hidden the structure
  entirely.
- The low nibble does not explain it: `0x00080001` is type 1 like the two that
  always resolve, and never resolves. It is the whole 32-bit plug-in id that
  decides, so do not simplify this to "type 1 has media, type 2 does not".
- **Compute this join across the whole corpus, never per package.** A bank's media
  almost always lives in a *different* package: the same join done inside one
  package matches 12 of 75,958. The reader therefore reports the two id sets and
  the gate unions them, which is also why the reader carries no verdict here.
- Not claimed: what any plug-in id is, what the five that name no media do instead
  (generation and out-of-corpus media are both consistent with these bytes), or
  that any of it is ever decoded or played.

## The serializer is on disk: Wwise SDK v2023.1.17

- **The serializer is on disk, and it is Wwise SDK v2023.1.17.** The shipped
  `Endfield_Data/Plugins/x86_64/AkSoundEngine.dll` (3,586,536 bytes, SHA-256
  `FD75D48813DC5B6497F0FD18B1AEE1912B8383FFA0AC229AD45A147A7ED052C6`) carries
  compiled-in assert paths naming its build tree. The string `wwise_v2023.1.17`
  occurs 28 times and is the **only** version string in the binary, so the
  identification is not an inference from bank version 150 -- it comes from the
  reader itself.
- Two build roots appear: stock `C:\Jenkins\ws\wwise_v2023.1.17\Wwise\SDK\...`
  and a vendored tree at `E:\Engine\RM42.Beyond\Audio\Wwise\SDK\...`. So the
  engine is Wwise 2023.1.17 with in-house modifications, and a stock-SDK layout
  should be treated as a strong prior rather than ground truth.
- **This retires the claim that the stuck cases are undecidable.** They are
  undecidable *from the bank bytes alone* -- that part stands, and the reasoning
  for each still holds -- but the deciding witness exists and is now named: the
  Wwise 2023.1.17 SDK headers define every HIRC struct exactly, which would settle
  `0x11`'s 21-versus-27 tie, `0x09`'s second run, `0x10`'s `0x7F` variant and
  `0x12` outright. That SDK is licensed from Audiokinetic and is not in this repo;
  obtaining it is a decision for the project owner, not something to work around.
- The DLL does **not** name the bank structures directly: its only chunk-tag
  strings are `BKHD`, `DIDX`, `DATA`, `HIRC`, `STID`, `STMG`, and it carries no
  `AkBankMgr`/`AkMusic*`/`AkParameterNode` source paths, so the asserts that would
  have named them are not compiled in. Do not expect to recover layouts by
  string-mining this binary; the version is what it gives you.
- **The DLL is not packed, and that now matters.** Measured sections: `.text`
  2,662,400 B at entropy **6.39**, `.rdata` 652,288 at 6.61, and **no `.tvm0`**
  section at all. Set against `EndfieldBase.dll` (79% `.tvm0` at 7.60) and
  `HGP.dll` (92% at 7.56), the Wwise reader is in the *readable* half of this
  game's binaries. Its RTTI is stripped -- only **12** `.?AV` type descriptors,
  every one a `std::` exception class -- so no `CAk*` names, consistent with the
  string-mining warning above.
- The six chunk-tag constants sit clustered in **`0xf4b74`-`0xf67a0`**, which is
  the section-dispatch region of the bank parser.
- ***So the blocker is weaker than recorded.*** The note above says the deciding
  witness is the licensed SDK and that obtaining it is the owner's call. That
  stands as the *cheap* route, but it is not the only one: the same structs are
  compiled into an unpacked 2.66 MB `.text` that ships with the game, with the
  parser's entry region located. **"Blocked on a licence" and "blocked on
  disassembly effort" are different states**, and only the second is true here.
- **The licence route is now taken: the SDK is installed, at 2023.1.19.8928.** The
  owner installed `Wwise_2023.1.19.8928` with its SDK component, so the cheap route
  is open and the "not in this repo" blocker is retired. Two caveats attach to it.
  **The version is not exact** -- the engine is 2023.1.**17** by its own DLL
  strings, the SDK is 2023.1.**19** -- so a struct read from these headers is a
  strong prior for this build, not the byte-for-byte witness the paragraph above
  describes; serialization is stable across a patch line in practice, and that is a
  prior, not a proof. And the vendored `E:\Engine\RM42.Beyond\Audio\Wwise` tree
  means in-house modification is possible regardless of version, so a stock-SDK
  struct still needs to meet the bytes.
- **What it settled immediately, and what it cannot.** It named the source-record
  fields and the codec ids -- see
  [`audio_hirc_graph.md`](audio_hirc_graph.md) -- and it confirmed the fade-curve
  table already in `hirc_v150.py` matches `AkCurveInterpolation` on all ten values.
  It gives nothing for `0x0A`-`0x0D`, because the bank *format* is not a public API
  and no header carries a layout; those need wwiser, which is a separate anchor.
  Headers are Audiokinetic's under their EULA: record derived facts, never vendor
  the headers into this repo.

  *A process note, since it cost a batch.* This DLL was already identified in these
  notes, with its SHA-256 and version string, **and with an explicit warning not to
  string-mine it** -- which is exactly what I then did. The recovery memory is the
  index of what is already known; **reading it first is cheaper than re-deriving
  it**, and the only reason this batch was not pure waste is that entropy and RTTI
  were questions the earlier pass had not asked.
