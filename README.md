# Endfield Research Kit

Endfield Research Kit turns a local Windows installation of Endfield into an
offline research browser. Its static WebUI brings recovered dialogue, character
identities, gameplay data, maps, audio, visual assets, localized text, and version
comparisons into one searchable interface.

<p>
  <img src="res/story_screenshot.jpg" alt="Story browser with recovered reading image, dialogue, and mission rewards" height="100">
  <img src="res/gameplay_screenshot.jpg" alt="Gameplay browser with character skills, dataset tabs, and shared filters" height="100">
  <img src="res/map_screenshot.jpg" alt="Map browser with recovered Wuling terrain and regional layers" height="100">
  <img src="res/assets_screenshot.jpg" alt="Assets browser with exported media and linked metadata" height="100">
</p>

> [!CAUTION]
> This is an unofficial community project and is not affiliated with or endorsed
> by the game's developers or publishers. Use a legally obtained client, do not
> redistribute proprietary game content, and expect spoilers. Most recovery
> work was produced with LLM assistance and should be verified against the
> original data.
>
> Code and documentation are provided **AS IS**, without warranties or a
> commitment to support, compatibility, or continued maintenance.

## Quick start

Requirements: Windows, Git, Python 3 on `PATH`, and a local Endfield client.
Full media exports need substantial disk space; 64 GiB RAM is recommended for
the default export worker count. Text-only setup is much lighter.

```bat
git clone https://github.com/Variante/endfield_research_kit.git
cd endfield_research_kit
notepad endfield_paths.bat
.\setup.bat
```

Set `ENDFIELD_GAME_ROOT` to the installed `Endfield_Data` directory. `setup.bat`
builds AnimeStudio, exports CN Story and Text data, and starts or reuses
the [local WebUI](http://127.0.0.1:8765/). Pass `--no-serve` to build without
starting the server. When setup finishes, **Story** and **Text** are ready to
browse as text. Build media and the remaining pages separately:

```bat
.\export.bat map --from-game
.\export.bat --from-game
```

The first command prepares Map; the second prepares all pages except Updates,
including media and CN audio. Each page extracts only its own inputs. A full
media export can take several hours.

## WebUI

The main pages below follow the navigation bar order.

- **Story** reconstructs dialog, radio, SNS, cutscenes, options, media, and
  evidence-typed ordering, with local branch overviews.
- **Gameplay** has eight tabs: **Characters**, **Weapons**, **Essences**,
  **Equipment**, **Items**, **Enemies**, **Combat stages**, and **Activities**.
  Entity details include progression, skills, action references, projectiles,
  and related assets. Items includes buildings, effects, rewards, recipes,
  shops, and upgrades; Activities shows schedules, prerequisites, targets,
  and rewards.
- **Map** stitches authored regional screens with recovered grayscale elevation,
  colored surfaces, water, missions, encounters, patrols, and scene conditions.
- **Characters** groups identity evidence, lists complete source
  appearances with verified Story links, and supports live merge/name overrides.
- **Text** provides searchable localized tables, achievement targets,
  activity prerequisites, and configured rewards.
- **Audio** exposes decoded voices, music, sound effects, event relationships,
  and playback evidence.
- **Assets** browses exported images, videos, and models
  with their linked materials and recovered references.
- **Decoded** is a file viewer and SQL console over export output
  the other pages do not show: every Unity object document (MonoBehaviour,
  TextAsset, Material, AnimationClip, ...), every packed game file (such as
  LipSync), and the loose tables, JsonData, Lua, Terrain, shaders and fonts,
  plus the files nothing decodes yet (streaming chunks, irradiance volumes,
  extend data, patches), shown as bytes. Search by
  name, object name, PathID, or CAB; read JSON as a tree with base64 decoded
  inline; or query with read-only SQL. It also keeps the decoded datasets of
  the maintained binary readers.
- **Updates** compares exported game data across two saved versions.

**Recovery** is an additional tab revealed by **Show debug info**. It shows
source volume and declared recovery states. Activities and combat stages are
Gameplay tabs; recipes and machines are included in Items details.
Gameplay's Characters tab focuses on playable-character data, while the main
Characters page groups playable and non-playable identities and appearances.

Story recovery distinguishes authored structure, recovered order, and manual
corrections. Characters retains source appearances and unresolved identities
alongside verified Story links. For recovery status and remaining gaps, see the
[Story guide](memory/webui/story.md) and
[Characters guide](memory/webui/characters.md).

### Common commands

`export.bat` is grouped by page: name the pages to build (none means all of
them). After a command succeeds, the named pages are ready or refreshed; pages
not named keep their previously generated data.

| Command | Pages ready or refreshed | What it uses |
| --- | --- | --- |
| `.\setup.bat` | **Story**, **Text** | Installed client; also builds AnimeStudio and starts the WebUI server by default |
| `.\export.bat` | Every page except **Updates** | The current export, after checking that every input the pages read is present and current |
| `.\export.bat --from-game` | Every page except **Updates** | Extracts only what the pages read, decodes CN audio, then builds them |
| `.\export.bat story --from-game` | **Story**, **Text** | Text only: tables, JsonData and the Story Unity classes; no image, video or audio |
| `.\export.bat story-media --from-game` | **Story**, **Text** | Story with its images and videos |
| `.\export.bat story audio --from-game` | **Story**, **Text**, **Audio** | Text-only Story plus the Audio page, which also gives Story its voice lines |
| `.\export.bat map --from-game` | **Map** | Extracts only Map's inputs |
| `.\export.bat debug --from-game` | Every page except **Updates** | Extracts every supported structured block and Unity class, then builds every page |
| `.\export.bat --changed-only` | Every page, including **Updates** | Syncs installed data and media, then compares with the last successful sync |
| `.\build_updates.bat OLD NEW` | **Updates** | Compares two complete export folders |

Page names for commands are `story`, `story-media`, `map`, `characters`,
`gameplay`, `audio`, `assets`, and `data`. `story` also builds Text;
`gameplay` builds all of its catalogs. Plain `export.bat` extracts nothing:
it rebuilds from the existing export and refuses stale or missing inputs,
naming the pages to re-extract. Use `--from-game` to refresh client data.

### Shared data, serving, and packaging

A page publishes its own data and can show another page's last publication.
For example, Audio supplies Story's voice lines, while Assets supplies media
links on Map, Characters, and Gameplay. Build those pages to make their data
available. The [export diagram](res/export_pages.svg) shows the inputs and
shared publications; `.\export.bat PAGE --from-game --show-plan` previews a run.
An all-page extraction includes the remaining data exposed by Decoded, giving
it the same extraction coverage as `debug`.

`python serve.py` serves whatever has already been generated; it does not build
page data. **Decoded** also provides a live file viewer and SQL console:
they query the export's `Unity.sqlite` and `GameFiles.sqlite` live through
`serve.py`, so they need no build step but do need the repository's `serve.py`
(restart it after updating the code). A packaged WebUI shows only the published
decoded datasets on this page. Serve or package the current WebUI with:

```bat
python serve.py
python -m scripts.webui.package
```

Packaging uses the generated data as it stands; it does not refresh it.

Mission Pipeline recovery remains available as a separate direct Python
workflow, but is no longer a WebUI page or part of the WebUI export commands.

## Export layout and resource planning

The export in `export_full/` contains selected client data, with the newer
Persistent layer overlaid on StreamingAssets:

- `game/`: tables, JsonData, Lua, terrain, video, decoded audio, and converted
  Unity media, according to the selected scope.
- `game/Unity.sqlite`: decoded Unity object documents.
- `game/GameFiles.sqlite`: packed small-file data, including LipSync.
- `meta/`: source indexes, asset maps, extraction provenance, and diagnostics.
- `raw/`: supported payloads retained as bytes for inspection and recovery.

The builders publish browser data separately under `webui/data/`. Both export
and browser data are generated locally and excluded from version control.

Allow space for the export, staging/cache files, and generated browser data.
A full media export can occupy well over 100 GB; retaining an older export for
Updates needs additional space. Runtime and memory use depend on the selected
pages, client build, and worker count. Use `--asset-jobs 4` (or lower) with
`--from-game` to reduce peak memory at the cost of speed. See the
[command map](scripts/README.md) for export maintenance and migration tools.

## Project map

- `webui/`: static browser, runtime overrides, and generated data.
- `scripts/`: maintained export, build, update, audio, and packaging tools.
- `tools/AnimeStudio/`: tracked exporter fork, maintained on `endfield`.
- `export_full/`: generated extraction from the installed client.
- `reports/`: generated inventories and audits.
- `memory/`: current conclusions, evidence boundaries, and recovery queues.
- `scratch/`: revisitable experiments; `tmp/`: disposable intermediates.

Only `tools/AnimeStudio` is initialized by `setup.bat`. The
`tools/Cpp2IL-Endfield` submodule is optional and is not required for the normal
WebUI workflow.

Technical documentation:

- [`scripts/README.md`](scripts/README.md): command and script map.
- [`webui/README.md`](webui/README.md): frontend scope and data contracts.
- [`memory/README.md`](memory/README.md): recovery-topic index.
- [`AGENTS.md`](AGENTS.md): contributor and automation rules.

## License

Original project code and documentation are licensed under the
[MIT License](LICENSE). Third-party code and dependencies, including the
AnimeStudio and Cpp2IL-Endfield submodules, retain their own licenses and
copyright notices.

Game assets, extracted game data, and game content shown in screenshots are
excluded from this license and remain subject to their respective owners'
rights. The project license grants no permission to redistribute proprietary
game content.

## Acknowledgements

The local `tools/AnimeStudio` fork contains custom Endfield VFS, asset,
MonoBehaviour, shader, animation, and audio recovery work informed by
[fluffy-dumper](https://git.nekolab.app/fluffield/fluffy-dumper) and
[EIHRTeam/EndfieldStudio](https://github.com/EIHRTeam/EndfieldStudio). Many
thanks to those projects and their maintainers for the groundwork that made this
research workflow possible.

Shader recovery was also informed by
[Ruri.ShaderDecompiler](https://github.com/ShiyumeMeguri/Ruri.ShaderDecompiler).
It remains credited as historical/provenance work; the maintained Endfield
export path is being consolidated into AnimeStudio.

Special thanks to these LLM-driven community wiki projects. They are not
affiliated with this repository, but they are useful public references:

- [AIC | Endfield Industrial Terminal](https://endfield.prts.chat/)
- [PRTS | Rhodes Island Terminal](https://prts.chat/)

These resources complement this local research workspace; important claims
should still be checked against primary game data.
