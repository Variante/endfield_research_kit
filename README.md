# Endfield Research Kit

Endfield Research Kit turns a local Windows installation of Endfield into an
offline static research browser. The WebUI brings recovered Story, character
identities, gameplay data, exported assets, localized text, and game-update
comparisons into one searchable interface.

<p>
  <img src="res/story_screenshot.png" alt="Story browser showing text_e8m1_1 with its recovered reading image and dialog" height="150">
  <img src="res/story_screenshot2.png" alt="Gameplay browser showing 诀 with character skills, progression, projectiles, and audio" height="150">
  <img src="res/story_screenshot3.png" alt="Asset browser previewing the Endministrator female cloth OBJ model" height="150">
  <img src="res/story_screenshot4.png" alt="Updates browser showing the modified m_cs_video_dlg_sm2l6m1_9.mp4 entry" height="150">
</p>

> Research only. Use a legally obtained client, do not redistribute proprietary
> game content, and expect spoilers. Most recovery work was produced with LLM
> assistance and should be verified against the original data.

中文: [b站专栏](https://www.bilibili.com/opus/1212936027582234627)，[百度盘](http://pan.baidu.com/s/1nLaAc6-AdZAbZb6jGObtmA?pwd=94p7)

## Quick start

Requirements: Git, Python 3, a local Endfield client, adequate disk space, and
preferably 64 GiB RAM for default asset exports.

```bat
git clone https://github.com/Variante/endfield_research_kit.git
cd endfield_research_kit
notepad endfield_paths.bat
.\setup_first_time.bat
```

Set `ENDFIELD_GAME_ROOT` to the installed `Endfield_Data` directory.
`setup_first_time.bat` initializes and builds AnimeStudio, exports the core
WebUI data, and starts or reuses:

```text
http://127.0.0.1:8765/
```

Pass `--no-serve` to build without starting the server.

## What is in the WebUI

- **Story:** reconstructed dialog, radio, SNS, cutscenes, options, media, and
  evidence-aware ordering.
- **Characters:** grouped names and identity evidence from tables, Story, and
  exported assets, with live merge and display-name overrides.
- **Gameplay:** characters, weapons, equipment, enemies, usable items,
  progression requirements, skills, projectile summaries, related assets, and
  playable recovered sound effects.
- **Assets:** exported images, models, materials, video, and metadata.
- **Text:** searchable localized table rows.
- **Updates:** exported game-data differences between saved versions.
- **Mission Pipeline:** an experimental quest/Story evidence view available
  only when `Show debug info` is enabled.

## Common commands

```bat
:: Rebuild from the current export_full
.\export.bat

:: Refresh Story and assets from the installed game
.\export.bat --export-from-game --with-assets

:: Fast Story/Mission Pipeline recovery loop
.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference

:: Rebuild only Mission Pipeline data when Story inputs are current
.\export.bat --mission-pipeline-data-only

:: Rebuild asset indexes and relink existing CN audio
.\export_assets.bat

:: Refresh assets and CN audio from the installed game
.\export_assets.bat --export-from-game

:: Serve or package the WebUI
python serve.py
.\pack_webui.bat
```

`export.bat` reuses `export_full/` by default and verifies it against the
installed client. Use `--export-from-game` only for an intentional fresh
extraction. Asset export modes are `--focused-assets`, `--default-assets`, and
`--debug-assets`; use `--animestudio-jobs N` to reduce peak memory.

To build more languages:

```bat
python scripts\story_builder\build.py --languages CN EN JP --default-language CN
```

## Game updates

```bat
:: First export: create an empty Updates feed
.\build_updates.bat --init-build

:: Seed installed-game VFS change detection
.\build_updates_by_patch.bat --init-baseline

:: Detect, stage, publish, and report a game update
.\build_updates_by_patch.bat

:: Detection only
.\build_updates_by_patch.bat --check

:: Compare two complete extracted versions
.\build_updates.bat --previous-export-root OLD --export-root NEW --refresh-previous-export-baseline
```

Updates compare exported game-data roots. Local changes under `webui/`,
`reports/`, `memory/`, or `scratch/` are never game-data updates.

## Recovery snapshot

### Story

- The current CN coverage report contains 5,563 unique Story files across 490
  pipeline missions.
- 4,236 files have an accepted pipeline connection (76.1%); 4,457 have at
  least one normalized trigger or context route (80.1%).
- 1,327 files remain unlinked. Of those, 156 already have exact native
  playback but still lack a mission or quest activation bridge.
- The source-only graph is cycle-free, but proves only 1.54% of possible
  within-mission pairs. It is intentionally a partial order, not a claimed
  canonical playthrough.

Current counts and evidence breakdowns live in
[`reports/story/build/mission_pipeline_story_binding_coverage_CN.md`](reports/story/build/mission_pipeline_story_binding_coverage_CN.md)
and [`reports/mission_order/source_story_partial_order_CN.md`](reports/mission_order/source_story_partial_order_CN.md).
Stable conclusions and the recovery queue live in
[`memory/game_story_recovery.md`](memory/game_story_recovery.md).

### Character models and animation

- All 30 playable models are imported and render successfully.
- All 156 canonical post-model identities have generated prefab paths: 30
  playables, 2 NPC characters, 1 cutscene clone, 94 enemies, and 29
  ability/prop actors.
- Playable UI animation recovery covers 754 body clips and 321 private
  item/deco clips.
- Static Overview reconstruction is strong, but original HGRP lighting,
  shadows, material state, controller execution, IK, facial behavior, physics,
  and non-playable animation remain incomplete.

See
[`memory/character_render_and_animation_recovery.md`](memory/character_render_and_animation_recovery.md)
for the current evidence boundary.

## Repository layout

- `webui/`: static browser, runtime overrides, and generated data.
- `scripts/`: maintained export, build, update, audio, and packaging tools.
- `tools/AnimeStudio/`: tracked exporter fork.
- `export_full/`: generated extraction from the installed client.
- `reports/`: generated inventories and audits grouped by topic.
- `memory/`: concise current conclusions and recovery queues.
- `scratch/`: revisitable experiments; `tmp/`: disposable intermediates.
- `unity_endfield_graph_shader_lab/`: character rendering and animation lab.

Further documentation:

- [`scripts/README.md`](scripts/README.md): command and script map.
- [`webui/README.md`](webui/README.md): frontend scope and data contracts.
- [`memory/README.md`](memory/README.md): recovery-topic index.
- `AGENTS.md`: contributor and automation rules.

## Acknowledgements

The local `tools/AnimeStudio` fork contains custom Endfield VFS, asset,
MonoBehaviour, shader, animation, and audio recovery work informed by
[fluffy-dumper](https://git.nekolab.app/fluffield/fluffy-dumper) and
[EIHRTeam/EndfieldStudio](https://github.com/EIHRTeam/EndfieldStudio). Many
thanks to those projects and their maintainers for the groundwork that made
this research workflow possible.

Special thanks to these LLM-driven community wiki projects. They are not
affiliated with this repository, but they are useful public references:

- [AIC | Endfield Industrial Terminal](https://endfield.prts.chat/)
- [PRTS | Rhodes Island Terminal](https://prts.chat/)

These resources complement this local research workspace; important claims
should still be checked against primary game data.
