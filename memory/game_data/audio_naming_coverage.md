# What the audio corpus names, and what nothing reaches

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4, audio lane.** The payoff of the lane: which media are named by which
source records, the music subgraph that no named event reaches, and how much of the
corpus is actually accounted for. Also the cross-package join trap, three times.

## Types `0x02` and `0x0B` share one source record, and it accounts for the media

This is the first result in this lane that is about the corpus rather than about a
body layout, so its evidence is stated in full.

**The record.** Numeric type `0x02` carries exactly one 14-byte source record at body
offset 0. Numeric type `0x0B` carries a counted array of the same record after its
leading flag and count. That they are the same record is shown twice:

- **The word at `+0` is a plugin id from a closed set.** `0x0B` uses two values --
  `0x00040001` (3,506 records) and `0x00140001` (941) -- and **140,121 of `0x02`'s
  142,815** bodies open with one of exactly those two. `0x02` uses five more
  (`0x00080001`, `0x00650002`, `0x00640002`, `0x00940002`, `0x01990002`), so it is a
  superset rather than a different field.
- **The word at `+5` names a declared media id in 4,447 of `0x0B`'s 4,447 records,
  and in 0 of them at any other offset in the record.** That contrast is what makes
  `+5` the id field. A bare hit rate would not.

**The attribution.** Pooled over every package, **61,325 of the 61,333 declared media
ids are named by some source record** -- 60,049 by `0x02`, 1,279 by `0x0B`, 3 by both,
and **8 by no record at all**. The words one byte either side of the id field name
**0 and 2**. Before `0x0B` was allowed to contribute, 1,284 media had no owner; it
closed 1,276 of them.

**The join has to cross a file boundary, and that is a trap worth recording.** A
source record names media that a *different* package declares. The first version of
this census joined inside one package and scored **12 of 147,262** -- not a weak
result, a meaningless one. `media_ids_from_audit` already carried the warning in its
own docstring: *"joining inside one package answers a question nobody asked."* The
census is published from C# as distinct value sets and joined in Python, where the
packages are already pooled.

## THE CROSS-PACKAGE JOIN TRAP, THREE TIMES

This has now bitten three separate fields, and the pattern is always the same: a table
and its users live in **different `.pck` files**, so a join written inside the reader
scores near zero and looks like a negative result.

| field | package-local score | pooled score |
| --- | --- | --- |
| media ids named by source records | 12 of 147,262 | **61,325 of 61,333** |
| source ids reached from named events | (pooled from the start) | 163 |
| plugin ids named by `INIT` | **1** of 147,262 | **973** of 147,262 |

`media_ids_from_audit` has carried the warning in its own docstring the whole time:
*"joining inside one package answers a question nobody asked."* I wrote the C# join
twice more anyway. **When a table and its users are in separate files, the join belongs
in the pass that already unions the files** -- the reader collects, the audit joins.

## The 8 media nothing names, explained

- **7 of the 8** are declared by `default_banks.pck`, which has `sounds=0`,
  `externals=0` and **exactly 7 media entries** -- so all 7 come from its `DIDX`
  section (84 bytes = 7 x 12). They are the Init bank's **embedded** media, and the
  same 7 ids are also declared as streamed copies in `default_stream_0.pck`. The 8th is
  in `default_stream_2.pck` only.
- **None of the 8 is a bank id**: pooled over 20,863 bank ids, the intersection with
  the 61,333 media ids is **0**, so they are genuine audio that no HIRC source record
  names rather than banks miscounted as media.
- Externals exist in this corpus -- 28,277 in `default_chinese_stream.pck` and 1 in
  `hotfix_japanese_bD0.pck` -- but not in the packages the 8 live in.

## NOTHING outside HIRC references a music object either

Sliding a 32-bit window over all four unparsed sections -- 10,677 words -- **63 name a
HIRC object against 0.59 expected by chance**, so the references are real. Every one
is a **bus**: numeric type `0x12` 62 times and `0x08` once, all inside `STMG`. `INIT`,
`ENVS` and `PLAT` name nothing at all.

- Unaligned offsets were included deliberately. The source id inside the 14-byte
  source record sits at `+5`, which is not four-byte aligned, and testing only aligned
  words is exactly how that field stayed unidentified for so long.
- **Together with the object graph this closes the question.** Across every byte of
  the bank format -- the reference graph, the parent field, the `0x08`/`0x12` forest,
  every music relation, the action target word, and all four unparsed sections --
  **nothing references a music object from outside the music family.**
- Gated with its expiry in mind: a music type appearing here fails the audit. **That
  failure is the good news.**

## NOTHING in the HIRC object graph reaches the music family's media

The previous batch asked what addresses the music subgraph. The answer, over every
relation this reader has resolved, is **nothing** -- and the evidence is now complete
rather than suggestive, because the relations can be enumerated.

| relation | edges | any music type at either end? |
| --- | --- | --- |
| main reference graph | 230,247 | **no** -- sources `04/05/06/07`, targets `02/05/06/07/09` |
| parent field (its inverse) | 199,445 | **no** -- 13 type pairs, all in `02/05/06/07/09` |
| `0x08`/`0x12` forest | 412 | no |
| music hierarchy at `+9` | 7,084 | internal only: `0A->0C`, `0A->0D`, `0C->0C`, `0D->0C` |
| `0x0C`'s counted array | 2,980 | internal only: `->0A`, `->0C`, `->0D` |
| `0x0A`'s counted array | 3,903 | internal only: `->0B` |
| **action target word** | 23,455 resolvable | **8 land on `0x0C`; none on `0A`, `0B` or `0D`** |

- **The family is large and well connected internally**: 11,656 objects, 7,305
  downward edges from 4,607 sources, 4,351 objects with no incoming edge (3,764
  `0x0A`, 489 `0x0D`, 98 `0x0C`). **Every `0x0B` has an incoming edge** -- none is a
  root -- so the tracks are owned.
- **Entering it from outside there are 5 edges in the whole corpus**, all
  `action_03 -> type0C`, resolved within the same bank. All 5 land on objects that are
  **roots**, **none of the 5 has an outgoing edge**, and together they reach **0**
  source ids.
- So the family's **1,279 media are reached by nothing**. Extending the named walk to
  read `0x0B`'s source records changed the reach numbers by exactly nothing --
  120 identifiers, 218 source ids, before and after.
- *This is written as a gate, not a note.* If a later reading reaches even one source
  id through the music family, `reachedSourceIdCount` becomes positive and the audit
  fails. **That failure is the good news.** The same pattern retired the `0x0B`
  element-count caveat two batches ago.
- The gate also refuses when the walk has **no edges**, because an empty edge set
  reaches nothing and looks exactly like isolation. *A negative result needs proof
  that the instrument was working.*
- What this does **not** say: that music is unreachable at runtime. It says no
  relation resolved here reaches it, so whatever drives music is **outside the HIRC
  object graph**. That bounds the search rather than ending it.

## The music subgraph is not reachable from any named event

- **Actions almost never address music.** Of the 23,455 action target words that
  resolve to an object in the package, the types are `0x05` 7,709, `0x02` 7,466,
  `0x09` 3,869, `0x06` 3,826, `0x04` 393, `0x07` 126, `0x08` 46, `0x15` 12 -- and
  **`0x0C` 8**. None at all reach `0x0A`, `0x0B` or `0x0D`.
- **The named walk confirms it from the other side.** Starting at the 199 named
  `0x04` objects and following gated reference vectors, the walk arrives at types
  `0x03` (310), `0x02` (225), `0x09` (127), `0x05` (91), `0x06` (18), `0x07` (4) and
  `0x04` (1). **It never arrives at a music type.**
- So the **1,279 media owned by `0x0B` are reached by no named event**, and the 163
  media a named event does reach are all owned by `0x02`. Extending the walk to read
  `0x0B`'s source records changed the reach numbers by **nothing** -- 120 identifiers
  reaching 218 source ids, before and after -- which is itself the measurement.
- What this does **not** say: that music is unreachable at runtime. It says the
  music types are not addressed through the action target word or through any gated
  reference vector, so whatever addresses them is not in this graph.

## How much of the audio corpus is actually named

| | count | share of declared media |
| --- | --- | --- |
| media ids declared by the packages | 61,333 | 100% |
| named by some source record | 61,325 | **99.99%** |
| reachable from a named `0x04` event | 163 | **0.27%** |

The gap is not a defect in the walk. Only **221** audio-shaped literals survive in
`global-metadata.dat`, matching 199 objects; the event names for the rest are not
shipped as managed literals. *Coverage of the structure and coverage of the names are
different numbers, and quoting one for the other would overstate both.*

## Beyond the shipped literals: how an Event acquires a name and an owner

Everything above measures what the *bank corpus* names. The rest of the lane's
naming comes from outside the banks -- managed literals, authored tables,
serialized components and native callsites -- and each route has its own
promotion rule. The rules are the durable part; the row counts they produce
belong to the generated Audio evidence and to
`reports/story/recovery/audio/`. None of these routes upgrades an authored
request to a selected branch, a playback event, or audibility.

### Managed `AU_*` fields: symbol-to-ID and nothing further

A scan of current IL2CPP string fields finds 25 unique `AU_*` symbols whose
`AudioHashGenerator` hashes match current Wwise Event IDs. Each is published
with its declaring type, field token, metadata hash and exact symbol-to-ID
evidence, and the existing name-prefix taxonomy is then used **only** for a
conservative broad category. **This static field identity does not recover the
runtime setter, caller, trigger, selected branch, execution, or audibility.**

### Grammar name recovery, for the Events no shipped string reaches

`scripts/webui/audio/semantics/name_recovery.py` names Events that no shipped string
reaches. Sweeping the whole IL2CPP literal blob and every metadata type/field
name resolves only a handful of hash-only Events, so the module instead mines
head/tail name templates per naming family **from the names already proven by
exact evidence**, regenerates sibling names, and keeps candidates whose
`AudioHashGenerator` hash equals a current hash-only Event id.

- **Because a generated preimage is weaker than a shipped string**, a hash with
  two distinct spellings is dropped, and a name is promoted only when its head
  and tail each recur across other recovered Events at one shared split
  boundary. Uncorroborated hits stay in
  `grammarEventNameRecovery.isolatedEntries` and **never become an Event name**.
- `index.json` publishes the promoted rows as `grammarRecoveredWwiseEventNames`
  plus the candidate, isolated and ambiguous counts and the
  coincidental-preimage expectation.
- Promoted rows set `eventIdentityStatus=grammarHashPreimageNameRecovered` and
  recover **only the owner and category the spelling encodes, never a caller or
  audibility**.
- Grammar-derived `au_` names are projected to an enemy only when the full
  current EnemyTable id prefix plus delimiter matches exactly. That
  `enemyNamespaceAudio` projection is **identity-only and is not a trigger or
  runtime-consumer claim.**

### Broad categories recovered without upgrading status

- Complete final-media leaf-set equivalence recovers a **uniform broad output
  category** for 85 hash-only Events (56 SFX, 21 UI, 6 voice, 2 control),
  **without upgrading their caller, trigger, branch or runtime-purpose status**.
- Weak category-name evidence is retained for 954 named Events from the enemy,
  actor/UI, LevelSequence and Gameplay-SFX families; **exact voice contexts
  override the weak enemy-name category** where the two disagree.
- Media paths that remain under `wwise/unknown` receive a separate semantic
  category from exact evidence: uniform related-Event joins, four
  trigger-context Event categories, and MonoBehaviour audio-field roles. **The
  raw physical category is preserved**, and mixed known-category joins remain
  unclassified rather than resolved by majority.

### Native trigger contexts, and the one that is deliberately not an Event

- 18 exact native `SwitchAudioCustomState` contexts are admitted across
  rotate-platform, crane, electric-fence, ForgeIron, LifterButton and
  MovingPlatform Event rows. The trigger catalog exposes the decoded
  custom-state name, current-build method/callsite evidence and metadata usage
  word **only after an authored `InteractiveData` custom-state join**.
  RotateNormalStart and RotateOverStart remain **separate branch-specific states
  at one native callsite**; branch execution, object ownership and audible
  output remain unobserved.
- The same fingerprint-locked catalog places the pause/resume control Events
  `au_gameplay_pause_spidle` and `au_gameplay_resume_spidle` at their exact
  `SnapshotSystem` `PostEvent` callsites; **the selected action entity and the
  runtime execution branch remain unobserved.**
- The validated native-literal catalog also covers exact anchor-wave hit-state
  routes and 3D-radio narrative selector values. **These are authored callsite
  contexts, not runtime execution or audible-playback evidence.**
- LevelScript `PlayVoice`/`PlayVoiceNarrative` rows are kept as a **separate
  direct path-stem contract**: their constant `_voId` selects an `AudioDialog`
  path and deliberately carries `wwiseEventStatus=notApplicable`. **They are not
  rewritten into Wwise Event identities.**

### LevelScript audio lifecycle, and the dynamic-property boundary

Producer/consumer links are admitted only for an **exact same-LevelScript
source-root and source-path identity**, with one active final serialized slot
and one unique output path. `story_builder.level_bindings` resolves
`ParamSource=200` dynamic string properties **only** through the strict
`LevelScriptBriefData` property formatter; `ParamSource=100` and
unknown/runtime sources remain runtime-unresolved and **cannot become handles**.
This is authored serialized topology, **not runtime handle state, action
execution, branch selection, or audibility**.

RemoteCommon lifecycle fields use an exact Persistent-over-Streaming row
overlay: non-empty `startAudioEvent`/`endAudioEvent` values become separate
authored trigger contexts, while `voiceId` remains a dialogue identity and
runtime execution remains unobserved.

### The AudioCue expression tree is an operand projection

The projection retains the complete validated tree with cue/handler scope,
expression side, source path, parent/depth, `exprType`, four serialized scalar
fields, child paths, node class and bounded diagnostics, **without evaluating
serialized expressions**.

- Non-empty behavior `exprType=3` leaves are **authored Event requests**;
  non-empty `exprType=8` leaves are `runtimeCueVariable` evidence; non-empty
  child lists are `compositeOpaque`; **all other nodes remain opaque**.
- `childrenLimit` rejects the parent before child projection.
- Enum and operator names are published only for a validated exact native
  contract; missing or mismatched native inputs keep those names absent.
- **The AST is a static request/operand projection, never condition truth,
  variable value, branch execution, or playback evidence.**

### Serialized components: the path is the evidence

- For MonoBehaviour `monoBehaviourAudioIdField` contexts the **serialized path
  remains the evidence**. The narrow `component*` role is an authored static
  field label, while `componentLayout`, raw field/path values and exact
  GameObject placement stay separately searchable. **Component or callback
  execution, Event posting, Wwise selection and audibility remain unobserved.**
- Complete serialized `AudioMapData` schemas admit their exact trigger
  enter/exit, level lifecycle and outdoor-room-tone `uint32` Event fields. **The
  schema gate rejects incomplete lookalikes before a numeric Wwise match becomes
  a context.**

### Scene ownership: what promotes it, and the prefab-identity gap that blocks it

The scene-background catalog consumes each validated AnimeStudio AssetMap object
root in one bounded streaming pass, using exact AssetMap `Source` + `PathID`
identities.

- **Prefab-local and scene-asset containment candidates remain separate**, and
  only an authoritative scene ID with unique scene containment promotes scene
  ownership.
- Missing, malformed or unreadable sources are excluded with explicit
  diagnostics while independently validated sources remain publishable; **no
  cross-source edge is inferred.**
- It resolves `AudioMapData` and scene emitters by script type, and joins exact
  `AudioLevel` rows plus `MissionRuntimeAsset.acceptMode.levelId`.
- **Scene activation, State/RTPC values, selector branches, listener state,
  playback and audibility remain runtime evidence; source prefab definitions do
  not prove level-instance placement.**
- Scene-emitter Event rows publish compact containment and prefab-identity
  status sets. **The current valid negative contract is a
  prefab-local/static-authored emitter with unresolved scene and unavailable
  prefab identity**; only exact SceneAsset/Level containment, or an exact prefab
  `Source`+`PathID` evidence row joined to one level, may publish
  `sceneEmitterSceneIds`. Candidate paths, sidecar `levelId`, names, positions
  and mixed exact attributions **fail closed**.
- Scene-global Event rows receive a compact attribution **only after** the
  merged scene-background catalog validates every direct context: the complete
  scene-id and original semantic-role sets are retained, while malformed,
  partial, non-direct, truncated or out-of-catalog contexts remain unavailable
  with bounded diagnostics. This is authored definition evidence; `foundInWwise`,
  category, runtime activation, branch choice, playback and audibility are
  unchanged.

**The blocking gap is exporter-side.** `recover_map_streaming_instances.py`
publishes the validated `InitChunkData` entity/name/transform and the raw ECS
columns under a versioned prefab identity contract, and **the current validated
columns expose no known prefab `Source`+`PathID`/hash field in the observed
schema**. So no instance is promoted by basename, entity name, position, Mesh,
or similarity. If a future sidecar carries an exact numeric identity, it may
resolve through one unique full AssetMap container path (or an explicit
component identity) before the Audio page attaches a level; ambiguous and
missing relations stay unresolved. If the explicit component-identity and exact
prefab-path identity routes disagree, reconciliation fails closed with
`conflictingPrefabInstanceIdentityJoins`. **The remaining gap is
exporter/sidecar production of exact prefab identity**, not analysis of the
current columns.

### Coarse media ownership, and what it may fill in

Scene roles plus exact Event-context and external-path evidence are projected
into coarse decoded-media ownership such as scene environment, animation,
authored component, interaction, or mission narration. It **may** fill an
otherwise unknown semantic category only for unambiguous roles such as outdoor
room tone or an authored ambient emitter; **ownership never upgrades runtime
playback or audibility status.**

### Character, enemy and NPC ownership rules

These are the promotion rules, each stated with what it refuses:

- **Character namespaces.** Current `CharacterTable` keys assign authored
  `chr_*`/`au_chr_*` Event namespaces, leading `au_actor_<token>_*` Events, and
  Event-leading internal character tokens such as `lastrite_*` to a character
  **only** through a delimited full key, a unique four-digit character-id
  prefix, or a uniquely owned exact token. That owner set propagates to possible
  media, **retaining every owner when a Wwise leaf is shared**. Generic
  character templates, display-name similarity, actions, runtime requests,
  selected leaves and playback positions are **not** inferred. Endministrator
  gender variants continue to use the existing synthetic-item alias rather than
  inventing a new WebUI owner.
- **Enemy namespaces.** A leading `au_monster_<token>_*` Event is accepted only
  when that token maps to **one** exact current `EnemyTable` id; it remains
  separate from full `au_eny_<id>_*` matches and is **identity-only**. Explicit
  enemy response candidates from ResponsiveDialog, skill and animation contexts
  are published separately when their owner field **exactly equals** a current
  EnemyTable id, and native-covered Events stay in the stronger native group.
  Native voice-response callsites are published separately when their exact
  AudioDialog Event has one longest delimited current EnemyTable prefix; they
  retain response role and media candidates **without claiming live selection or
  playback**.
- **NPC owners.** An NPC owner is admitted only when one valid `NpcInfoTable`
  row has matching non-empty `voActor`/`wwiseId` fields **and** its
  `NpcTemplateGroupTable` `npcNameId`/`templateId` row agrees. Exact actor tokens
  must also have one exact current `AudioDialogChannel` key whose typed
  narrating and radio Event suffixes agree with that token; only then do they
  publish `ownerKind=npc`, the `npcId`, the template id and the actor token.
  Rows with duplicate tokens, overlay conflicts, malformed layers or template
  mismatches remain unresolved, and **generic archetypes are never promoted by
  name**.
- **Table overlays are authoritative or suppressed, never stale.** In the
  CharacterTable/EnemyTable/EnemyTemplateTable animation identity overlay,
  Persistent rows are authoritative, and **a malformed Persistent layer
  suppresses that table's identity surface instead of silently falling back to a
  stale base**.
- **Resolved is separate from candidate.** Each supported serialized
  AnimationClip callback keeps per-Clip resolved entity IDs separate from
  candidate IDs: exact Character, Enemy or EnemyTemplate matches may resolve,
  while unique-token and multi-match possibilities remain candidate/ambiguous.
  Shared callback owners remain shared; missing, malformed or unsupported
  evidence stays unresolved/fail-closed; **candidate IDs never become resolved
  ownership.** Mixed Events retain an identity only on their callback
  occurrence/Clip rows, **not as a single Event owner**, and none of this proves
  CharacterTable identity, Animator execution, playback or audibility.

### Animation callbacks: the callback is the edge, not the name

- Every supported serialized AnimationClip `PostAudioEvent` context is projected
  as an explicit Event/media callback link with its clip, owner, function,
  reachability and AnimatorController names when available. **This callback link
  does not require the Event and clip names to match and does not promote an
  unknown category.**
- An AnimationClip action name and a Wwise Event id are recognized as the same
  thing **only** when their normalized names match exactly *inside an existing
  `PostAudioEvent` callback context*. That promotes the Event and its possible
  media to action SFX while retaining the clip, actor, callback and
  runtime-selection boundary. **Name similarity without the callback never
  creates a trigger or ownership edge.**

### External Source identity: three alias families, kept apart

`externalSourceEventIdentityAudit` compares External Source Event ids separately
against typed voice-table routing aliases and the narrower AudioDialog
path-hash aliases, **preserving the Event-route versus per-request
`externalSourceKey` boundary**.

- When the structured AudioDialog tables are available, the audit adds a typed
  `overrideWwiseEvent -> AudioDialog.path` candidate join producing bounded
  route/path candidate sets. **Shared route Events remain candidate sets, not
  selected runtime rows.**
- Typed `AudioDialogChannel` narrating/radio fields add a broader candidate join
  for channel-selection candidates. **This is explicitly lower-confidence
  evidence** and is reported separately from the path-hash audit.
- The changing candidate counts for both live in their own reports under
  `reports/story/recovery/audio/`.

### Playable-media projection into other pages

- The compact Gameplay projection of exact namespace Events and playable
  candidates is published into the language-specific `gameplay/sound_effects.json`
  sidecar and **remains separate from trigger-backed skill and animation
  audio**.
- Playable `AudioDialogCustomEventTable` preload/post-enter rows are projected
  onto matching `conv/<dialogId>.json` records. **Missing conversation IDs
  remain Audio-only and lifecycle dispatch is not inferred.**
