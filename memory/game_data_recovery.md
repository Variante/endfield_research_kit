# Game-data recovery

## Current status

The project can read the current exported tables, MemoryPack/FlatBuffer payloads,
selected Unity objects, Wwise banks, Lua, IL2CPP metadata, and bounded native
code paths. These sources feed Story, Characters, Gameplay, Audio, Assets, and
the local evidence graph.

The strongest recovered semantics cover stock-client combat formulas, skill and
buff action structures, enemy level points, projectile records, audio Event
graphs and consumers, and typed joins between gameplay records and assets.
Server behavior, active IFix replacements, live blackboard values, and runtime
branch selection remain outside the proven boundary unless separately captured.

## Refresh

```bat
.\export.bat --from-game
.\export.bat --from-game --with-assets
python scripts\build_gameplay.py
python scripts\build_audio.py
python tools\endfield_source_graph.py build
```

Steps using installed native binaries validate `GameAssembly.dll` and
`global-metadata.dat` against their recorded fingerprints. Missing or mismatched
inputs skip only the affected native step and leave its previous report
untouched. Set `ENDFIELD_REQUIRE_NATIVE_EVIDENCE=1` for a hard audit gate.

## Evidence rules

Prefer, in order:

1. exact table keys, serialized fields, and versioned binary layouts;
2. source-scoped PathID/PPtr and authored foreign-key relations;
3. typed IL2CPP fields and fingerprint-locked native data flow;
4. exact hashes and normalized identifiers with a documented namespace;
5. labeled name or token similarity.

Never treat a global PathID, filename resemblance, native address order, or one
same-name asset as unique ownership. Preserve source layer, container, offset,
schema version, and validation status.

## Known data model

- StreamingAssets and Persistent table layers must be merged according to each
  dataset’s overlay contract; selecting the first matching file can lose patch
  rows.
- MemoryPack and FlatBuffer parsers are versioned by observed member/layout
  counts and fail visibly on drift.
- SkillData resolves phased actions, DamageUnits, targeting, child skills, and
  authored timing where decoded.
- BuffData composes modifiers, shields, tags, stacking, events, actions, and
  child buffs. Undecoded nested bodies remain byte-bounded diagnostics.
- Exact gameplay IDs prove ownership only in their authored namespace. Family,
  filename, animation, or prefix joins remain inferred.
- Legacy broad indexes under `webui/data/game_data/` are diagnostic previews,
  not active page or formula sources.

## Enemy stats and variants

Enemy level values come from exact authored rows in
`EnemyAttributeTemplateTable.levelDependentAttributes`. The WebUI shows only
levels present in source data; it does not infer a level from row position or
interpolate missing points.

Each enemy variant names an `attrTemplateId`. Variants sharing a template share
its raw HP/ATK/DEF curve, but may still differ through modifiers, born buffs,
AI, models, and other configuration. Shared displayed stats do not imply
identical live behavior.

## Combat formula boundary

For the shipped stock client, ordinary damage has the recovered shape:

```text
finalAttackValue
* weaknessDamageScalar
* criticalFactor
* defenseFactor
* (1 - shelterDamageScalar)
* max(0, elementalResistanceFactor)
* abnormalStatusFactor
* physicalInflictionFactor
```

Critical success uses `1 + CriticalDamageIncrease`. With the shipped
`efficiencyOfDEF = 0.01`, defense is:

```text
DEF >= 0: 1 / (1 + 0.01 * DEF)
DEF < 0:  2 - 0.99 ^ (-DEF)
```

For ordinary elemental types, the resistance term is
`(1 - resistance / 100) * typeDamageTakenScalar`. Real damage uses neutral
defense and elemental factors but still traverses other ordinary multipliers.
LifeDrain is a distinct early-return path using `finalAttackValue`.

DamageUnits, zones, modifiers, abnormal/physical infliction decorators, guard,
healing, shields, poise, and event processors add typed behavior outside this
single scalar. The browser must show their authored phase and conditions rather
than presenting the scalar as a complete combat simulator.

These conclusions describe the fingerprinted stock binary plus shipped tables.
They do not prove active IFix/server corrections, live target selection,
probability outcomes, evaluator order, or blackboard values.

## Projectiles and effects

Projectile records preserve template identity, movement, effects, hit behavior,
sound IDs, and source identity where decoded. A projectile template’s skill
bundle describes behavior owned by that template; it does not prove which
playable skill spawns it. A ranged-looking skill may use direct actions,
hitboxes, summons, or another system and need no projectile template.

Nonzero projectile sound values are direct Wwise Event IDs. HIRC traversal can
link possible media leaves, but switch/random/layer selection and actual
playback remain unobserved.

## Audio evidence

The audio pipeline separates:

- raw Wwise Event, Action, container, Sound, and media identity;
- exact Event-to-media graph relations;
- authored contexts from tables, Timeline, Lua, gameplay data, serialized
  components, and native consumers;
- runtime activation, selected branch, and heard media.

Wwise Event traversal proves possible library output, not a live caller or
audibility. Managed literals and lookup keys remain identity-only until exact
data flow reaches a typed playback API. Conditional and selector-based native
paths preserve their branch condition, method, callsite, target binding, and
binary fingerprints.

Native Audio evidence is evaluated against the explicitly selected client:
`global-metadata.dat` and its sibling `GameAssembly.dll` must both match the
reviewed fingerprints. A missing or different client removes only native
callsites, mappings, and addresses; authored table/component rows remain
available and visibly carry the unavailable diagnostic.

Responsive voice data retains every authored response position and tone
substitution while leaving live response/tone choice unresolved. AnimationClip
`TriggerVoice` callbacks remain distinct from ordinary audio callbacks and keep
all compatible owners when animation identity is shared.

`AIBark` is a separate high-level request layer. The current binary proves
`BarkSystem.Bark(AIBarkType)` resolves a bark id through its runtime dictionary,
then `AIBarkManager` reads the authored `AIBark` row and forwards its trigger
key, bark voice type, and speaker type through
`VoiceManager.PostAIBarkVoiceEvent` to `VoiceBarkProcessor.AIBark`. Generated
responsive contexts carry the matching bark rows and fingerprint-locked method
addresses. Enemy `common_attack`/`common_escape` voice definitions are not
present in that trigger-key catalog and remain unresolved rather than being
inferred from their names. Current CN coverage has 1,108 unique authored
response ids: 1,069 are already terminal story-line matches, 25 more have
direct decoded media, one resolves only through an exact Wwise Event, and 13
`sentenceType=32`/`speaker=any` ids have no AudioDialog, AudioVoTone,
AIBarkText, decoded-media, or current Wwise Event object. Those 13 remain
explicit authored-response gaps rather than synthetic audio identities.

Enemy response actions have a second exact native route. The current
`EnemyTriggerVoiceAction` static dictionary maps voice types `0..4` only to
`combat_alarm`, `combat_intobattle`, `combat_fighting`,
`combat_outbattle_flee`, and `combat_kill`, then `OnExecute` passes the chosen
key to `VoiceManager.ResponseOnEntity`. Fixed native callers additionally
prove `combat_hurt_lowhp`, `combat_hurt_stun`, `combat_alarm_yell`,
`defence_running`, `defence_reachcore`, and `combat_outbattle_flee` placements.
Neither `common_attack` nor `common_escape` occurs in the action dictionary or
the complete fixed-literal caller set. Two `common_attack` definitions do have
exact ResponsiveDialog membership and are resolved at that authored trigger
level; the other 34 `common_*` definitions remain a consumer-ownership gap
rather than a semantic alias for combat/flee behavior.

AudioDialog, responsive, and other patched tables merge StreamingAssets with
Persistent overlays. Shared SFX/music and language voice stay separate. Same-id
media in different packages or roots remains separately visible.

## Source graph

Primary database:

```text
reports/source_graph/endfield_source_graph.sqlite
```

Typical queries:

```bat
python tools\endfield_source_graph.py query ID_OR_NAME
python tools\endfield_source_graph.py story STORY_KEY
python tools\endfield_source_graph.py issues --limit 20
```

Graph edges retain source and evidence kind. Exact foreign keys, PPtrs, typed
binary paths, and authored contexts remain distinguishable from inferred name
joins. The default export graph includes only original AssetMap rows consumed
by WebUI material, shader, texture, and FMV edges; use `--full-source-graph` for
exhaustive Unity-object investigation.

## Diagnostics

Use generated reports for changing schemas, inventories, counts, fingerprints,
addresses, and exhaustive evidence:

```text
reports/export/
reports/assets/
reports/source_graph/
reports/story/build/
reports/story/recovery/
```

Do not copy volatile inventories into this file.

## Remaining gaps

- Server-side mission/property producers and activation policy.
- Active IFix/server combat overrides, live targets, evaluator chronology, and
  blackboard values.
- Additional family-specific MemoryPack and FlatBuffer schemas.
- Deeper Buff/Skill nested action semantics with fail-closed version gates.
- Broader exact world-streaming and scene decoding.
- Runtime projectile spawn ownership and remaining enum/branch semantics.
- More exact gameplay-to-asset, animation-controller, effect, and audio joins.
- Runtime-selected Wwise branches and per-language playback policy.
- Per-system negative/certification reports that remain actionable after input
  drift.
