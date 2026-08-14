# WebUI recovery

## Current status

The static WebUI is the project’s primary surface. Story, Characters, Gameplay,
Audio, Assets, Text, and Updates are normal pages. Mission Pipeline is
experimental and appears only with `Show debug info`; Audio and Mission
Pipeline retain visible under-construction labels.

Story, localized references, character identities, gameplay semantics, assets,
audio, and update comparisons build reproducibly from a current
`export_full/`. Optional datasets fail visibly when absent or stale.

Retired Progression and Combat & Projectiles pages stay retired. Their useful
progression, projectile, asset, and sound information lives in Gameplay.

## Build and serve

```bat
.\setup_first_time.bat
.\export.bat
.\export.bat --from-game --with-assets
.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference
.\export.bat --mission-pipeline-data-only
.\export_assets.bat
python serve.py
python scripts\pack_webui.py
```

Before a builder reads an existing extraction, verify freshness with
`python scripts\verify_export_freshness.py`. Reuse an existing server at
`http://127.0.0.1:8765/` instead of starting another default instance.

## Stable data contracts

Primary generated data:

```text
webui/data/manifest.json
webui/data/lang/<LANG>/{index.json,conv/,mission/,reference/}
webui/data/lang/<LANG>/characters/index.json
webui/data/lang/<LANG>/gameplay/**
webui/data/lang/<LANG>/audio/{index,events,media}.json
webui/data/mission_pipeline/{index.json,missions/}
webui/data/assets/{index,gameplay_refs,story_media,videos}.json
webui/data/updates/latest.json
```

User-managed inputs:

- `webui/overrides/story_order.json`: active Story order; never regenerated.
- `webui/overrides/options.json`: manual option positions and responses.
- `webui/overrides/narrative_videos.json`: narrative-video attachment policy.
- Character merge/name overrides: live inputs written through `serve.py`.

Schema changes must update the builder and consumer together. Optional sidecars
must produce an explicit unavailable or degraded state instead of silent empty
data.

## Stable frontend behavior

- Disabling debug mode while Mission Pipeline is active returns to a normal
  page and normalizes the URL.
- Story issue and recovery-method filters remain visible; raw source blocks,
  Timeline evidence, cutscene diagnostics, and order tools remain debug-only.
- Story reset restores Story sort and default filters while preserving expanded
  mission groups.
- `sns_emoji_*` stays inline without hover/modal preview. Other SNS media keeps
  natural proportions with bounded previews.
- Characters keeps identity provenance and live override behavior.
- Gameplay owns progression, projectile, asset, and sound presentation. Exact
  and inferred ownership are labeled separately.
- Enemy level controls show only authored points; variants resolve their exact
  attribute template before displaying stats.

## Audio evidence boundary

Audio separates Event/media identity, Wwise graph relation, authored consumer,
and observed runtime execution. A stronger layer never appears unless its typed
evidence exists.

The current pipeline can join raw HIRC Events, decoded media, AudioDialog and
responsive-voice tables, Timeline audio, Lua consumers, selected serialized
components, gameplay actions, and fingerprint-locked native callsites. Direct
and conditional native consumers retain their method, callsite, target, and
branch evidence. Selector and dictionary paths stay distinct from direct
literal playback.

Missing or mismatched installed native inputs never erase authored Audio rows.
They suppress only build-locked callsites/mappings and expose a bounded
unavailable diagnostic, so the page cannot silently present stale native
addresses as current evidence.

Responsive voice contexts also expose exact matching `AIBark` request rows and
the fingerprint-locked native dispatch chain. The UI must keep the live
AIBarkType-to-bark-id dictionary choice, probability/cooldown selection, and
actual response branch unresolved; similarly named enemy voice definitions are
not AIBark evidence unless their trigger key occurs in the authored table. The
audio trigger catalog reports story-bound responses as resolved terminal,
direct/Wwise-only responses separately, and missing configured response ids as
non-playable authored gaps.

Responsive rows whose trigger key is one of the five exact
`EnemyTriggerVoiceAction` dictionary values now retain its numeric voice type
and native mapping callsite. Separate fixed native response callers cover
low-HP/stun, enemy battle-entry yell, patrol running, reach-core, and
leave-battle flee. Two `common_attack` rows are already resolved by exact
ResponsiveDialog membership; the other 34 `common_attack`/`common_escape` rows
remain definition-only highest-priority unknown-purpose rows because neither
exact native path names them.

Exact Wwise graph traversal proves possible media leaves, not the live
switch/random branch or audibility. String literals, definitions, lookup keys,
and same-name assets remain identity-only until they reach a typed playback
consumer. Shared media and language voice remain separate, and duplicate media
IDs retain physical package provenance.

The Audio view now uses purpose-priority ordering and explicit unknown,
partial, known, and Story-line-terminal filters. Story-line binding ends
purpose investigation for that media. Playback groups with at most 20
candidates remain expanded and materialized; only groups above that threshold
start collapsed. The runtime overview and responsive context rows expose the
exact five-entry `EnemyTriggerVoiceAction` mapping without upgrading it to a
live branch observation.

## Story and Mission Pipeline boundary

Story combines authored dialog structures, Timeline placement, mission/runtime
links, localized references, and manual order without flattening their evidence
types. Cutscene shapes, subtitle evidence, definition-only media, authored
placement, and runtime activation remain distinct.

Mission Pipeline shows typed trigger chains and their ownership/activation
gaps. Native registration, source order, code address, proximity, OCR, and
manual order never become mission chronology by themselves. Weak placement is
visually separate and cannot override exact placement.

## Updates and packaging

```bat
.\build_updates.bat OLD NEW
python scripts\pack_webui.py
```

Updates compares complete saved/current export roots only. The default feed
covers WebUI-facing exported text plus image, model, video, and decoded audio
assets. Local WebUI, report, memory, and scratch changes are excluded.

## Highest-value gaps

- Keep optional semantic sidecars visibly degraded rather than silently stale.
- Improve exact Gameplay-to-asset and sound ownership without weakening labels.
- Preserve clear evidence boundaries as Mission Pipeline gains runtime joins.
- Keep Characters false-positive exclusions and live overrides clean.
- Maintain accessible behavior across large Story, Gameplay, Audio, and Assets
  datasets.

## Verification

1. Run the smallest relevant builder after confirming export freshness.
2. Smoke-test all normal pages and debug-only Mission Pipeline routing.
3. Verify Story reset, issue/method filters, and SNS media fixtures.
4. Open representative playable and enemy entries; check variants,
   progression, skills, projectiles, sound, and asset links.
5. Check console errors and explicit degraded states.

Changing inventories and schema-specific counts belong in generated reports,
not this file.
