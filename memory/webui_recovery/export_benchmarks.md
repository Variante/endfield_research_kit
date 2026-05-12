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

## 2026-05-12 - `build_story.py` CN Story Build Speed Pass

Commands:

```bat
python -m cProfile -o reports\build_story_cprofile_20260512.prof scripts\webui\build_story.py --languages CN --default-language CN
Measure-Command { python scripts\webui\build_story.py --languages CN --default-language CN }
```

Findings:

- Before the speed pass, the profiled CN build took `807.3` seconds. The main
  hotspot was related DialogTree discovery: `_iter_related_dialog_tree_paths`
  spent `683.4` seconds scanning every AnimeStudio stem for each scene.
- Switching related-tree prefix lookup to binary search over the existing sorted
  stem index reduced the real wall-clock CN build to `92.8` seconds.
- Caching mission timeline relative path rendering and avoiding generated-output
  `Path.resolve()` calls reduced the real wall-clock CN build to `73.6` seconds.
- A tested `os.scandir` replacement for AnimeStudio file iteration did not
  improve real wall time on this machine (`78.6` seconds), so it was not kept.

Remaining likely targets:

- AnimeStudio file discovery still has to index a very large MonoBehaviour
  export directory.
- Raw reference bundle generation still scans `479` tables and writes about
  `45.9 MB` of reference data.
- Mission timeline recovery is now less dominated by path canonicalization, but
  it remains one of the larger story-build stages.
