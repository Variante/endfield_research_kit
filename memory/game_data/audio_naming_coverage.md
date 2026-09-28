# What the audio corpus names, and what nothing reaches

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4, audio lane.** The payoff of the lane: which media are named by which
source records, the music subgraph that no named event reaches, how much of the
corpus is actually accounted for, and the promotion rules by which an Event
acquires a name and an owner outside the banks. Changing counts live in the
generated Audio evidence and `reports/story/recovery/audio/`; the figures kept
here are the ones a later session must not re-derive. The promotion mechanics
live in the docstrings of the owning `scripts/webui/audio/semantics/` modules
named below.

## Types `0x02` and `0x0B` share one source record, and it accounts for the media

- **The record.** Type `0x02` carries one 14-byte source record at body offset 0;
  `0x0B` carries a counted array of the same record after its leading flag and
  count. The word at `+0` is a plug-in id from a closed set (`0x0B` uses two
  values, `0x02` a superset of seven); the word at `+5` names a declared media id
  in every `0x0B` record and at no other offset. That contrast, not a bare hit
  rate, is what makes `+5` the id field.
- **The attribution.** Pooled over every package, 61,325 of the 61,333 declared
  media ids are named by some source record (`0x02` names most, `0x0B` names the
  music tracks, 3 by both). The words one byte either side of the id field name
  almost nothing.
- **The 8 media nothing names.** Seven are the Init bank's embedded `DIDX` media
  in `default_banks.pck` (`sounds=0`, `externals=0`), which also stream from
  `default_stream_*.pck`. The eighth, `1041213772`, is in `default_stream_0.pck`
  only, with no bank entry, and is the one media genuinely not Init-embedded.
  None is a bank id.
- **One media is reached by no Event at all**, `17778495865568962267`; its uint64
  shape says External Source, so it is an External-Source-route question, not an
  HIRC one.

## The cross-package join trap

A source record names media that a *different* `.pck` declares, so a join written
inside one package scores near zero and looks like a negative result. It bit
three fields the same way: media ids named by source records (12 package-local
against 61,325 of 61,333 pooled), source ids reached from named events, and
plug-in ids named by `INIT`. **When a table and its users are in separate files,
the join belongs in the pass that already unions the files**: the C# reader
collects distinct value sets, the Python audit joins them.

## Nothing reaches the music family from outside it

Two walks are easy to confuse. "Named" here means the `hirc_named_reach` gate's
sense: the `0x04` objects named by a shipped `global-metadata.dat` literal.
`build_audio`'s own traversal starts from a much larger pool (tables, gameplay
references, authored payload literals, aliases, grammar preimages) and **does**
reach music-family media through `musicTrack`/`musicTrackSource` from `au_music_*`
Events. That is a different starting set, not a contradiction; do not quote one
walk's reach for the other.

Within the bank format the result is complete, because the relations can be
enumerated:

| relation | any music type at either end? |
| --- | --- |
| main reference graph (sources `04/05/06/07/09`) | no |
| parent field (its inverse) | no |
| `0x08`/`0x12` bus forest | no |
| music hierarchy at `+9`, `0x0C` and `0x0A` counted arrays | internal only (`0A/0C/0D`, `0A->0B`) |
| action target word | a handful land on `0x0C`; none on `0A`, `0B` or `0D` |
| the four unparsed sections, unaligned 32-bit window | every hit a bus inside `STMG` (63 hits against 0.59 expected) |

- The family is large and internally connected; every `0x0B` has an incoming
  edge, so the tracks are owned. The only edges entering it from outside are
  `action_03 -> type0C` within one bank, landing on roots with no outgoing edge
  and reaching no source id. So the family's media are **reached by nothing** in
  the graph, and everything the named walk reaches is owned by `0x02`.
- The unaligned window was deliberate: the source id sits at `+5`, and testing
  only aligned words is how that field stayed unidentified.
- *Both results are gates, not notes.* A music type appearing in the unparsed
  sections, or `reachedSourceIdCount` becoming positive, fails the audit; the
  gate also refuses an empty edge set, because reaching nothing through no edges
  looks exactly like isolation. That failure would be the good news.
- Not claimed: that music is unreachable at runtime. Whatever drives music is
  outside the HIRC object graph (see the skipped-types note in
  [`audio_hirc_parser.md`](audio_hirc_parser.md)).

## How much of the audio corpus is actually named

| | count | share of declared media |
| --- | --- | --- |
| media ids declared by the packages | 61,333 | 100% |
| named by some source record | 61,325 | 99.99% |
| reachable from a metadata-literal-named `0x04` event | 163 | 0.27% |

Coverage of the structure and coverage of the names are different numbers;
quoting one for the other overstates both. The remaining Event names are not
shipped as *managed* literals, but the authored serialized payloads are a second
literal source.

## How an Event acquires a name and an owner outside the banks

Each route has its own promotion rule; none upgrades an authored request to a
selected branch, a playback event, or audibility. The rule text lives in the
owner's docstring; the row counts belong to the generated Audio evidence.

| route | rule, in one line | owner |
| --- | --- | --- |
| managed `AU_*` fields | `AudioHashGenerator` hash equals a current Event id: symbol-to-ID only, no setter/caller/trigger | `mono_behaviour.py` |
| authored payload literals (`LevelScriptData`, `LevelScriptTemplateData`, `SpawnerConfig`, `Interactive`, `LevelData`) | length-prefixed `au_`/`bark_`/`radio_` literal whose FNV-1 equals an Event id: `exact` spelling; the holding field is unidentified, so the payload-to-Event relation is `structuralOnly` | `authored_payload_event_names.py` |
| decoded `_soundEvent` members | member placement offers a candidate; only a selected HIRC Event-object hash promotes it | `decoded_payload_event_names.py` |
| grammar preimages | head/tail recombination plus single-token substitution; promoted only when head and tail are each corroborated; weaker than a shipped string | `name_recovery.py` |
| broad categories | final-media or Play-target equivalence gives a category, never a caller/trigger/status | `purpose.py`, `media_rows.py` |
| native trigger contexts | exact callsite plus authored `InteractiveData` join; LevelScript `PlayVoice` stays an `AudioDialog` path stem | `trigger_contexts.py` |
| LevelScript lifecycle | same-LevelScript exact output path, one active slot, one producer; `ParamSource=100` stays unresolved | `levelscript.py` |
| AudioCue expressions | operand projection only, no evaluation | `table_contexts.py` |
| serialized components | the serialized path is the evidence; `AudioMapData` needs the complete schema | `mono_behaviour.py` |
| scene ownership | exact `Source`+`PathID` containment only; blocked by the exporter's missing prefab identity | `scene_backgrounds.py` |
| character, enemy, NPC owners and animation callbacks | exact table keys; the callback is the edge, never name similarity | `media_ownership.py` |
| projection into other pages | exact namespace Events and playable candidates go to `gameplay/sound_effects.json`, apart from trigger-backed skill and animation audio; playable `AudioDialogCustomEventTable` rows reach a matching conversation only through Audio's `audio/conv/` sidecar, and missing conversation ids stay Audio-only with no lifecycle dispatch inferred | `media_ownership.py`, `dialog_lifecycle.py`, `conversation_sidecar.py` |

**External Source identity (no code owner).** The audit that compared External
Source Event ids against typed voice-table routing aliases and, separately, the
narrower AudioDialog path-hash aliases was removed as unconsumed, so this
conclusion lives only here: the Event route and the per-request
`externalSourceKey` are different identities; the
`overrideWwiseEvent -> AudioDialog.path` and `AudioDialogChannel` joins are
bounded candidate sets (the latter explicitly lower-confidence), never selected
runtime rows. The static cookie identity for External Source records is
recorded in `mono_behaviour.py`; the key's many-to-one relation to files is in
[`audio_native_hooks.md`](audio_native_hooks.md).

## The SetAudioCueVar boundary

LevelScript `SetAudioCueVar` stores LEVEL-scoped BOOL variable names, some of
which exactly equal `exprType=8` operand strings in the current `AudioCueTable`;
others stay unmatched. Its stored route is authenticated by
`scripts.game_data.levelscript_audio_cue_native`. The build-independent claims
contract
[`scripts/game_data/contracts/levelscript_audio_cue_execute_claims.json`](../../scripts/game_data/contracts/levelscript_audio_cue_execute_claims.json),
validated by `python -m scripts.game_data.levelscript_audio_cue_execute_native`
against the selected installed client, proves that `SetAudioCueVar.Execute` reads
all seven authored parameter fields and holds ordered call sites for the iFix
state check, the string/float/int/bool cue-variable setters, and the patch
lookup. It does **not** prove live branch selection, a setter execution, or an
AudioCueTable selection; neither does the authored name join.

## Reading the serialized payloads exactly

- **A regex bounded recovery, not the sources.** The byte scan once let the
  `au_`/`bark_`/`radio_` pattern find its own end and checked the length prefix
  afterwards; a greedy class runs past a string followed by a word character
  (`Au_Chr_0035_Liino_Skill_Pop` then `d`), so the candidate was dropped.
  Driving the scan from the length prefix is stricter per candidate and added
  over a thousand Event names a current Event object claims, a third of them to
  Events with no other name (`gameplay_audio.length_prefixed_matches`). A source
  counts as exhausted only once its reader is known to consume it exactly.
- **The member is a better handle than the spelling, but not proof.** Events
  such as `eny_0125_fdcentur_lance_skill_01_a_hit` never match the byte grammar,
  and the grammar must not be widened on a suffix. The decoded-member source
  admits them by member placement plus the HIRC hash gate. One decoded
  `_soundEvent` holds a Chinese sound-design note, which corrected the earlier
  claim that placement alone proves an Event reference.
- **Trailing whitespace is data.** Two `eny_0080_reaper` sound strings end in a
  space; the game's default PlaySound routes hash them untrimmed, and only the
  hypothetical trimmed id is an Event object in the scanned CN set. See
  [`audio_native_hooks.md`](audio_native_hooks.md) and
  `native_play_sound_string.py`.
- **Two hash domains.** The builder hashes UTF-8 candidates; the game hashes
  UTF-16 code units. They agree for ASCII only (`identifiers.py`).
- **Typed PlaySound actions are broader than the local envelope.** Exact
  whole-record SkillData/BuffData plans place PlaySound under multi-item
  timelines, nested conditional/channeling actions and Buff/Ability event
  actions, so the old local reader is a strict subset. The action path, frame
  window, event slot and `targetSettings` are authored context, not an executed
  branch or a selected target; only HIRC-matched actions join Event contexts
  (`play_sound_actions.py`, `play_sound_action_corpus.py`).

## Eliminated readings

- A per-package join as evidence that a table's ids are unused (cross-package trap).
- A `+0`/`+4` or aligned-only search for the source record's media id.
- "Every observed-string source is exhausted" while one scanner misread its source.
- Member placement alone as proof of an Event (the prose `_soundEvent`).
- Trimming a PlaySound string, or treating every typed member as an Event.
- Widening the `au_`/`bark_`/`radio_` grammar to catch `eny_*` or `Play_au_*`.
- Counting page-only Event identities as HIRC objects when promoting candidates.
- Name similarity (clip, entity, basename, position) as an ownership edge.
- Majority vote over mixed category joins.

## What still needs new evidence

The remaining hash-only Events, and the media reached only by them, need a
captured `PostEvent` argument or a native callsite that carries the string. The
shipped capture hooks cannot supply the spelling (see
[`audio_native_hooks.md`](audio_native_hooks.md)). Payload roots outside the
supported decoders need a measured reader, not a prefix guess.
