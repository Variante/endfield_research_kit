# Source Story gap queue and LevelScript dialog-exit recovery (2026-07-15)

## Scope and evidence boundary

This pass continued the source-only Story reconstruction after baseline commit
`9b6e02c`. It used only the refreshed installed-game export, generated Story
bundles derived from that export, and recovered GameAssembly/IL2CPP metadata.
It did not read or promote `webui/overrides/story_order.json`, OCR proposals,
gameplay-video order, numeric scene suffixes, generated UI rank, or manual
option overrides.

The output remains a partial order. A shared file, level, trigger, or quest is
not treated as proof that two scenes run in a particular order.

## Prioritized source gap queue

`scripts/story_recovery/build_source_story_gap_queue.py` now builds a
transparent recovery queue from the strict partial-order report. The score is
only a work-priority score; every weighted contribution is emitted in the JSON
so it cannot be mistaken for chronology.

Important controls added while validating the queue:

- core Story isolation is counted separately from ambient `env` rows and
  standalone video entries;
- a quest attachment is actionable only when diagnostic evidence associates
  the quest with a Story scene but no strict source edge attaches it;
- gameplay-only quests with no Story evidence remain visible but unscored;
- main-story (`e*`) missions form the first priority bucket, followed by event,
  major, character, and other missions.

After the dialog-exit promotion below, the main-story bucket contains 58
missions and 1,769 scenes. Its largest work frontier remains LevelScript
control flow. `e10m4` is the highest total-score main mission because of 39
core isolated scenes; `e7m3` is the highest-ranked main mission whose primary
frontier is LevelScript control flow (8 untyped multi-scene contexts).

Generated outputs:

- `reports/mission_order/source_story_gap_queue_CN.json`
- `reports/mission_order/source_story_gap_queue_CN.md`

## Recovered `LevelEvent_OnDialogExit` semantics

The default CodeRegistration address in
`build_levelscript_actionbase_tag_audit.py` was stale (`0x18a31fac0`). The
current installed client uses `0x18c439740`; rebuilding the MemoryPack union
mapping with that address recovered all 10,779 LevelScript header rows by name.

The relevant control-flow fact is stronger than file adjacency:

1. the recovered header type is `LevelEvent_OnDialogExit`;
2. the header payload names the dialog whose exit fires the event;
3. `ActionHeader.nextId` selects the first `actionList` record;
4. each record's authored `nextId` selects the next action;
5. Story references resolved in that chain therefore run after the named
   dialog exits and in action-chain order.

Promotion is deliberately conservative. A chain is accepted only when the
header resolves to exactly one same-mission Story scene and every action record
resolves to zero or one Story scene. Self-only references are discarded. A
record containing two Story targets rejects the whole candidate as ambiguous.

The CN rebuild produced exactly six new strong edges across five missions:

- `misc_dlg_c16m4_2d5 -> radio_c16m4_33`
- `misc_dlg_e3m1_1d5 -> radio_e3m1_1d5`
- `dlg_e3m6_105 -> dlg_e3m6_11`
- `dlg_e7m3_3 -> radio_e7m3_6`
- `dlg_sm2l2m7_8 -> black_sm2l2m7_1`
- `black_sm2l2m7_1 -> dlg_sm2l2m7_9`

All six were new and none contradicted an existing strong path. The two
`sm2l2m7` edges come from separate action records in one exit-handler chain,
not from assuming an order between unrelated records or files.

## Coverage change

Before this promotion the strict report had 1,710 strong edges and 4,878
comparable scene pairs. After rebuilding CN Story data and rerunning the audit:

- strong edges: 1,716 (`+6`);
- comparable scene pairs: 4,903 (`+25` through transitive reachability);
- comparable-pair rate: 2.4198%;
- isolated scenes: 4,529 (`-1`);
- weak-only scenes: 1,595 (`-8`);
- cyclic SCCs: unchanged at 39 across 30 missions.

The `e7m3` local improvement is one new strong edge, seven additional
comparable pairs (126 to 133), and one fewer weak-only scene. Its existing
six-scene source cycle is unchanged, confirming the promotion did not create a
new cycle.

## Next source-only frontier

The next LevelScript pass should continue from event semantics rather than
file order. Audit other recovered event types only when their trigger meaning
provides a directional Story relationship and validate them globally with the
same ambiguity, reverse-path, and cycle controls. Separately, `e10m4` needs
source-link discovery for its isolated radio/dialog/text scenes; its problem is
not currently an untyped multi-scene LevelScript context.
