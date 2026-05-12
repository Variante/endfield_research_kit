# WebUI Export Benchmarks

Durable benchmark notes for the active WebUI refresh path.

## 2026-05-12 - No Content Update, Fast Assets

Command:

```bat
Measure-Command { & .\export.bat --fast-assets }
```

Result:

- Total wall time: `2465.5` seconds / `41.1` minutes.
- `StreamingAssets` structured dump: `522.093` seconds.
- `Persistent` structured dump: `505.495` seconds.
- AnimeStudio broad export: cache hit for all selected stages and sources; no
  stages reran.
- Remaining time was mostly CN `build_story.py`, plus freshness verification,
  DialogIdTable recovery, source-link building, Updates, and fast asset index
  refresh.

Follow-up observation:

- Initial benchmark output showed volatile local CrashSight files under
  `Plugins/x86_64/wesight/crashsight_data/` as game-data changes. These are
  now filtered by `scripts/webui/build_updates.py`.
- After rerunning `python scripts\webui\build_updates.py`, unchanged content
  produced `gameTotals.changed = 0`, `assetTotals.changed = 0`, and an empty
  Updates entry list.

Likely speed target:

- Add structured-dump caching or skip logic in `scripts/export_full_from_game.py`
  when source fingerprints are unchanged. On this run, the two structured dumps
  alone cost about `17.1` minutes.
