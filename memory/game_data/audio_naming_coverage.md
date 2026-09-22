# What the audio corpus names, and what nothing reaches

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4, audio lane.** The payoff of the lane: which media are named by which
source records, the music subgraph that no named event reaches, how much of the
corpus is actually accounted for, and the promotion rules by which an Event
acquires a name and an owner outside the banks. Changing counts live in the
generated Audio evidence and `reports/story/recovery/audio/`; the figures kept
here are the ones a later session must not re-derive.

## Types `0x02` and `0x0B` share one source record, and it accounts for the media

**The record.** Numeric type `0x02` carries exactly one 14-byte source record at
body offset 0; `0x0B` carries a counted array of the same record after its leading
flag and count. They are the same record: the word at `+0` is a plugin id from a
closed set (`0x0B` uses two values, and 140,121 of `0x02`'s 142,815 bodies open with
one of exactly those two; `0x02` adds five more, so it is a superset), and the word
at `+5` names a declared media id in 4,447 of `0x0B`'s 4,447 records and in none of
them at any other offset. That contrast, not a bare hit rate, is what makes `+5`
the id field.

**The attribution.** Pooled over every package, **61,325 of the 61,333 declared
media ids are named by some source record** -- 60,049 by `0x02`, 1,279 by `0x0B`,
3 by both, 8 by none. The words one byte either side of the id field name 0 and 2.
Before `0x0B` contributed, 1,284 media had no owner; it closed 1,276 of them, which
is exactly the 1,284 - 8 that the two figures otherwise appear to disagree on.

**The 8 media nothing names.** Seven are the Init bank's embedded `DIDX` media in
`default_banks.pck` (`sounds=0`, `externals=0`, exactly 7 entries); six of those
also stream from `default_stream_0.pck` and one (`624424588`) from
`default_stream_2.pck`. The eighth, `1041213772`, is in `default_stream_0.pck`
only and has no bank entry at all, so it is the one media that is genuinely not
Init-bank embedded. None of the 8 is a bank id (the pooled intersection of 20,863
bank ids with the media ids is 0). Externals exist in the corpus but not in the
packages the 8 live in.

## The cross-package join trap

A source record names media that a *different* `.pck` declares, so a join written
inside one package scores near zero and looks like a negative result. It bit three
fields the same way: media ids named by source records (12 of 147,262 package-local
against 61,325 of 61,333 pooled), source ids reached from named events, and plugin
ids named by `INIT` (1 against 973 of 147,262). **When a table and its users are in
separate files, the join belongs in the pass that already unions the files**: the
C# reader collects distinct value sets, the Python audit joins them.

## Nothing reaches the music family from outside it

Two walks are easy to confuse, so their scopes come first. "Named" below means
the `hirc_named_reach` corpus gate's sense: the `0x04` objects named by a shipped
`global-metadata.dat` literal (199 objects from 221 audio-shaped literals).
`build_audio`'s own traversal starts from a much larger pool (tables, gameplay
references, authored payload literals, aliases, grammar preimages) and **does**
reach music-family media through `musicTrack`/`musicTrackSource` from `au_music_*`
Events. That is a different starting set, not a contradiction; do not quote one
walk's reach for the other.

Within the bank format the result is complete, because the relations can be
enumerated:

| relation | edges | any music type at either end? |
| --- | --- | --- |
| main reference graph | 240,898 | no -- sources `04/05/06/07/09`, targets `02/05/06/07/09` |
| parent field (its inverse) | 199,445 | no -- 13 type pairs, all in `02/05/06/07/09` |
| `0x08`/`0x12` forest | 412 | no |
| music hierarchy at `+9`, `0x0C` and `0x0A` counted arrays | 7,084 + 2,980 + 3,903 | internal only (`0A/0C/0D`, `0A->0B`) |
| action target word | 23,455 resolvable | 8 land on `0x0C`; none on `0A`, `0B` or `0D` |
| the four unparsed sections, 32-bit sliding window | 63 hits against 0.59 expected | every one a bus (`0x12` x62, `0x08` x1) inside `STMG` |

- The family is large and internally connected (11,656 objects, 7,305 downward
  edges); every `0x0B` has an incoming edge, so the tracks are owned. Entering it
  from outside there are 5 edges in the corpus, all `action_03 -> type0C` within one
  bank, all landing on roots with no outgoing edge, reaching 0 source ids. So the
  family's **1,279 media are reached by nothing** in the graph, and the 163 media
  the named walk reaches (arriving at `0x03/02/09/05/06/07/04`, never a music type)
  are all owned by `0x02`. Reading `0x0B`'s source records changed the reach by
  exactly nothing: 120 identifiers, 218 source ids, before and after.
- The unaligned window was deliberate: the source id sits at `+5`, and testing only
  aligned words is how that field stayed unidentified for so long.
- *Both results are written as gates, not notes.* A music type appearing in the
  unparsed sections, or `reachedSourceIdCount` becoming positive, fails the audit;
  the gate also refuses an empty edge set, because reaching nothing through no edges
  looks exactly like isolation. **That failure would be the good news.**
- What this does **not** say: that music is unreachable at runtime. Whatever drives
  music is outside the HIRC object graph, which bounds the search rather than ending
  it.

## How much of the audio corpus is actually named

| | count | share of declared media |
| --- | --- | --- |
| media ids declared by the packages | 61,333 | 100% |
| named by some source record | 61,325 | 99.99% |
| reachable from a named `0x04` event | 163 | 0.27% |

Coverage of the structure and coverage of the names are different numbers, and
quoting one for the other overstates both. The Event names for the rest are not
shipped as *managed* literals, but they are not all unshipped either: the authored
serialized payloads are a second literal source.

## How an Event acquires a name and an owner outside the banks

Each route below has its own promotion rule. The rules are the durable part;
the row counts they produce belong to the generated Audio evidence. None of these
routes upgrades an authored request to a selected branch, a playback event, or
audibility.

- **Managed `AU_*` fields: symbol-to-ID and nothing further.** IL2CPP string fields
  whose `AudioHashGenerator` hash matches a current Wwise Event id are published with
  declaring type, field token, metadata hash and exact symbol-to-ID evidence; the
  name-prefix taxonomy supplies only a conservative broad category. The static field
  identity recovers no setter, caller, trigger, selected branch, execution or
  audibility.
- **Authored serialized payloads are the second shipped-literal source.** The roots
  `LevelScriptData`, `LevelScriptTemplateData`, `SpawnerConfig`, `Interactive` and
  `LevelData` carry MemoryPack length-prefixed `au_*` literals exactly as `SkillData`
  and `BuffData` do, and treating the metadata blob as the last observed-string
  source is what kept a large block of Events hash-only while their names were in
  the client. `scripts/webui/audio/semantics/authored_payload_event_names.py`
  collects them under two exact constraints, the shipped `au_`/`bark_`/`radio_`
  grammar and the four-byte length prefix that separates a serialized string from
  an incidental ASCII run, and feeds them *before* the HIRC pass, because a name
  added afterwards can only relabel an inventory row, not give the Event-to-media
  links a spelling. Promotion is `exact`: a candidate names an Event exactly when
  its FNV-1 hash equals a current HIRC Event object id. Because the equality is on a
  shipped string, this is the same tier as a managed `AU_*` literal and strictly
  stronger than a grammar preimage; the coincidence expectation is published beside
  the count. The payload root is provenance for the spelling only: the field that
  holds the literal is not identified, so the payload-to-Event relation stays
  `structuralOnly` and is not a consumer, caller, trigger, branch, execution or
  audibility claim. Events spelled `Play_au_*` fall outside the harvested grammar
  and remain a separate, measurable widening.
- **Grammar name recovery, for the Events no shipped string reaches.**
  `scripts/webui/audio/semantics/name_recovery.py` mines head/tail templates per
  naming family from names already proven by exact evidence, regenerates sibling
  names, and keeps candidates whose hash equals a current hash-only Event id.
  Because a generated preimage is weaker than a shipped string, a hash with two
  distinct spellings is dropped and a name is promoted only when its head and tail
  each recur across other recovered Events at one shared split boundary;
  uncorroborated hits stay in `grammarEventNameRecovery.isolatedEntries` and never
  become a name. Promoted rows carry
  `eventIdentityStatus=grammarHashPreimageNameRecovered` and recover only the owner
  and category the spelling encodes. Grammar-derived `au_` names project to an enemy
  only on an exact full current EnemyTable id prefix plus delimiter, as an
  identity-only `enemyNamespaceAudio` claim.
- **Broad categories never upgrade status.** Complete final-media leaf-set
  equivalence recovers a uniform broad output category for hash-only Events without
  touching their caller, trigger, branch or runtime-purpose status; weak
  category-name evidence is retained for named enemy, actor/UI, LevelSequence and
  Gameplay-SFX Events, with exact voice contexts overriding the weak enemy-name
  category. Media paths under `wwise/unknown` keep that **raw physical category**;
  a semantic category comes only from exact evidence (uniform related-Event joins,
  trigger-context Event categories, MonoBehaviour audio-field roles), and mixed
  joins stay unclassified rather than resolved by majority. The `unknown` folder is
  therefore not an "unnamed" flag: most of its media carry a named Event and sit
  there because only six naming prefixes map to a physical folder.
- **Native trigger contexts.** Exact `SwitchAudioCustomState` contexts (rotate
  platform, crane, electric fence, ForgeIron, LifterButton, MovingPlatform) expose
  the decoded custom-state name, current-build method/callsite and metadata usage
  word only after an authored `InteractiveData` custom-state join; branch-specific
  states at one callsite stay separate. The pause/resume control Events sit at their
  exact `SnapshotSystem` `PostEvent` callsites, and the validated native-literal
  catalog covers anchor-wave hit-state routes and 3D-radio narrative selectors.
  These are authored callsite contexts, not execution or audible playback.
  LevelScript `PlayVoice`/`PlayVoiceNarrative` rows are a separate direct path-stem
  contract: their constant `_voId` selects an `AudioDialog` path and carries
  `wwiseEventStatus=notApplicable`; they are never rewritten into Wwise identities.
- **LevelScript audio lifecycle.** Producer/consumer links are admitted only for an
  exact same-LevelScript source-root and source-path identity with one active final
  serialized slot and one unique output path. `scripts.webui.story.level_bindings`
  resolves `ParamSource=200` dynamic string properties only through the strict
  `LevelScriptBriefData` property formatter; `ParamSource=100` and unknown sources
  stay runtime-unresolved and cannot become handles. RemoteCommon lifecycle fields
  use an exact Persistent-over-Streaming row overlay; non-empty
  `startAudioEvent`/`endAudioEvent` become separate authored trigger contexts while
  `voiceId` stays a dialogue identity. All of it is authored topology, not runtime
  handle state, branch selection or audibility.
- **The AudioCue expression tree is an operand projection.** The complete validated
  tree is retained (scope, side, source path, parent/depth, `exprType`, scalar
  fields, child paths, node class, bounded diagnostics) without evaluation: behavior
  `exprType=3` leaves are authored Event requests, `exprType=8` leaves are
  `runtimeCueVariable` evidence, non-empty child lists are `compositeOpaque`, all
  else opaque; `childrenLimit` rejects the parent first; enum and operator names
  appear only under a validated native contract. Never condition truth, variable
  value, branch execution or playback.
- **Serialized components: the path is the evidence.** For MonoBehaviour
  `monoBehaviourAudioIdField` contexts the serialized path is the evidence; the
  `component*` role is a static field label, with layout, raw values and exact
  GameObject placement searchable separately. Complete `AudioMapData` schemas admit
  their exact trigger enter/exit, level lifecycle and outdoor-room-tone `uint32`
  Event fields, and the schema gate rejects incomplete lookalikes before a numeric
  match becomes a context.
- **Scene ownership, and the prefab-identity gap that blocks it.** The
  scene-background catalog consumes each validated AssetMap object root in one
  bounded pass by exact `Source` + `PathID`. Prefab-local and scene-asset containment
  candidates stay separate; only an authoritative scene id with unique containment
  promotes scene ownership; no cross-source edge is inferred. Scene-emitter rows
  publish `sceneEmitterSceneIds` only from exact SceneAsset/Level containment or an
  exact prefab `Source`+`PathID` row joined to one level; candidate paths, sidecar
  `levelId`, names, positions and mixed attributions fail closed. Scene-global rows
  are attributed only after the merged catalog validates every direct context.
  **The blocking gap is exporter-side:** the validated `InitChunkData` columns from
  `recover_map_streaming_instances.py` expose no prefab `Source`+`PathID`/hash field,
  so no instance is promoted by basename, entity name, position, Mesh or
  similarity. A future sidecar with an exact numeric identity may resolve through
  one unique full AssetMap container path or an explicit component identity;
  disagreement between those routes fails closed with
  `conflictingPrefabInstanceIdentityJoins`.
- **Coarse media ownership** (scene environment, animation, authored component,
  interaction, mission narration) may fill an otherwise unknown semantic category
  only for unambiguous roles such as outdoor room tone or an authored ambient
  emitter; it never upgrades playback or audibility status.
- **Character, enemy and NPC owners.** A character owns `chr_*`/`au_chr_*`
  namespaces, leading `au_actor_<token>_*` Events and Event-leading internal tokens
  only through a delimited full `CharacterTable` key, a unique four-digit id prefix,
  or a uniquely owned exact token; the owner set propagates to possible media and
  retains every owner when a Wwise leaf is shared; Endministrator gender variants
  keep the existing synthetic alias. A leading `au_monster_<token>_*` Event is
  accepted only when the token maps to one exact `EnemyTable` id, separately from
  full `au_eny_<id>_*` matches and identity-only; explicit enemy response candidates
  publish only on an exact owner-field equality, native-covered Events staying in
  the native group, and native voice-response callsites need one longest delimited
  EnemyTable prefix. An NPC owner needs one valid `NpcInfoTable` row with non-empty
  `voActor`/`wwiseId`, an agreeing `NpcTemplateGroupTable` row, and for exact actor
  tokens one `AudioDialogChannel` key whose narrating and radio suffixes agree;
  generic archetypes are never promoted by name. Table overlays are authoritative or
  suppressed, never stale: a malformed Persistent layer suppresses that table's
  identity surface instead of falling back to the base. Resolved is separate from
  candidate: per-Clip resolved entity ids never absorb unique-token or multi-match
  candidates, shared callback owners stay shared, and none of it proves
  CharacterTable identity, Animator execution, playback or audibility.
- **Animation callbacks: the callback is the edge, not the name.** Every supported
  serialized AnimationClip `PostAudioEvent` context is an explicit Event/media
  callback link with clip, owner, function, reachability and AnimatorController
  names; it does not require the names to match and promotes no category. An
  AnimationClip action name and a Wwise Event are the same thing only when their
  normalized names match exactly *inside* such a callback, which promotes the Event
  and its media to action SFX while keeping the runtime-selection boundary. Name
  similarity without the callback creates nothing.
- **External Source identity: three alias families, kept apart.**
  `externalSourceEventIdentityAudit` compares External Source Event ids separately
  against typed voice-table routing aliases and the narrower AudioDialog path-hash
  aliases, preserving the Event-route versus per-request `externalSourceKey`
  boundary; the `overrideWwiseEvent -> AudioDialog.path` and `AudioDialogChannel`
  candidate joins are bounded candidate sets, the latter explicitly
  lower-confidence, never selected runtime rows. One media, `17778495865568962267`,
  is reached by no Event at all; its uint64 shape says External Source, so it is an
  External-Source-route question rather than an HIRC one.
- **Playable-media projection into other pages.** The compact Gameplay projection of
  exact namespace Events and playable candidates lands in the language-specific
  `gameplay/sound_effects.json` sidecar, separate from trigger-backed skill and
  animation audio; playable `AudioDialogCustomEventTable` rows are projected onto
  matching `conv/<dialogId>.json` records, and missing conversation ids stay
  Audio-only with no lifecycle dispatch inferred.

## The serialized payloads were not exhausted, and the reason was a regex

The claim below that every observed-string source was exhausted held for the
sources, not for the *reading* of one of them. `length_prefixed_matches` found
candidates by letting the `au_`/`bark_`/`radio_` pattern locate its own
boundaries and then checking the four-byte length afterwards. A greedy
`[A-Za-z0-9_]` class runs past the string's end whenever the following byte is
a word character, and the length then disagrees, so the candidate is dropped.
`Au_Chr_0035_Liino_Skill_Pop` is a shipped instance: 27 bytes, followed by a
`d`.

Driving the scan from the length prefix instead -- the pattern still locates a
start, but the *slice the prefix names* must match entirely -- is a stricter
per-candidate test, not a wider one, and the FNV-1 promotion gate is unchanged.
Over SkillData and BuffData it raises candidates from 2,537 to 3,925 and adds
**1,372 Event names that a current Event object claims by hash, 533 of them
Events with no recovered name at all**. Accepting both spellings adds a further
18, and on its own would have added nothing.

*The general point is worth keeping.* "Every source is exhausted" was a claim
about where names live, and what actually bounded recovery was how one scanner
read them. The check that exposed it came from outside the lane: decoding
SkillData and BuffData whole gave 4,091 strings sitting in members literally
named `_soundEvent`, of which 4,072 hash to a current Event -- so the schema
position said "Event" where the spelling grammar had to guess.

## The member is a better handle than the spelling

Fixing the scanner leaves a bound that no scanner can pass. A byte scan can
only find names that *look* like Event names, and the corpus is full of Events
that do not: `eny_0125_fdcentur_lance_skill_01_a_hit` is an Event and begins
`eny_`, which the `au_`/`bark_`/`radio_` grammar will never accept and should
not be widened to accept, because widening it on a suffix is the failure mode
this lane exists to avoid.

`decoded_payload_event_names` uses the member instead. A string in a member the
generated wrapper calls `_soundEvent` is an Event reference because of where it
sits, and the promotion gate is unchanged -- FNV-1 equality with a current
Event object id. Over the decodable families it offers 4,090 candidates, of
which 4,071 are claimed by a current Event against a coincidence expectation of
0.024, and **197 of those are names the byte scan cannot reach at all**.

Two constraints keep it from being a different guess. The member names are an
explicit list of members that were read and found to hold Event references, not
a pattern over member names -- admitting anything containing `sound` would move
the guess up one level rather than remove it. And a decoded value counts only
when its record consumed to EOF exactly, so a drifted cursor contributes
nothing.

The module is a standalone source with its own report and is **not yet wired
into `build_audio`**; wiring it is the remaining step, and it would make the
Audio build depend on the installed-build gate, which it currently does not.

## What still needs new evidence

The remaining hash-only Events, and the media reached only by them, still need
a captured `PostEvent` argument or a native callsite that carries the string.
That is now a statement about the Events left after the fix above, and the
lesson from it is that a source counts as exhausted only once its reader is
known to consume it exactly.
