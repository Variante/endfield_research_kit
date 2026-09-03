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
  <img src="res/map_screenshot.png" alt="Map browser showing the full Wuling region with recovered elevation, color surface, and water layers" height="150">
</p>

> [!CAUTION]
> This is an unofficial community project and is not affiliated with or endorsed
> by the game's developers or publishers. Use a legally obtained client, do not
> redistribute proprietary game content, and expect spoilers. Most recovery
> work was produced with LLM assistance and should be verified against the
> original data.
>
> This project and its documentation are provided **AS IS**, without warranties
> of any kind. There is no promise of support, bug fixes, compatibility with
> future game or operating-system updates, or long-term maintenance. Use it at
> your own risk; you should not expect assistance or continued updates.

## Quick start

Requirements: Git, Python 3, a local Endfield client, adequate disk space, and
preferably 64 GiB RAM for default asset exports.

```bat
git clone https://github.com/Variante/endfield_research_kit.git
cd endfield_research_kit
notepad endfield_paths.bat
.\setup.bat
```

Set `ENDFIELD_GAME_ROOT` to the installed `Endfield_Data` directory.
`setup.bat` builds AnimeStudio, exports CN Story and Text data, and
starts or reuses `http://127.0.0.1:8765/`. Pass `--no-serve` to build without
starting the server. When setup finishes, the **Story** and **Text** pages are
ready to browse. The remaining pages are separate so the first useful build
finishes sooner.

For a complete refresh from the installed client, including exported media and
CN audio, run this after setup:

```bat
.\export.bat --from-game --with-assets
```

Asset decoding can take several hours and requires substantially more disk
space and memory than the initial Story/Text setup.

## WebUI

- **Story** reconstructs dialog, radio, SNS, cutscenes, options, media, and
  evidence-typed ordering.
- **Map** stitches authored regional screens with recovered grayscale elevation,
  colored surfaces, water, point clouds, missions, and exact world coordinates.
- **Characters** groups identity evidence and supports live merge/name
  overrides.
- **Gameplay** covers characters, equipment, enemies, progression, skills,
  projectiles, related assets, and recovered sound effects.
- **Audio** exposes decoded voices, music, sound effects, event relationships,
  and playback evidence.
- **Assets** browses exported images, videos, materials, models, and their
  recovered references.
- **Text** provides searchable localized tables and source records.
- **Updates** compares exported game data across two saved versions.

### Pages prepared by each command

After a command succeeds, the named pages are ready or refreshed. Pages not
listed keep their previously generated data.

| Command | Pages ready or refreshed | What it uses |
| --- | --- | --- |
| `.\setup.bat` | **Story**, **Text** | Installed client; also builds AnimeStudio and starts the WebUI server by default |
| `.\export.bat` | **Story**, **Text**, **Map**, **Characters**, **Gameplay** | The current, freshness-checked export; existing Assets and Audio are unchanged |
| `.\export.bat --from-game` | **Story**, **Text**, **Map**, **Characters**, **Gameplay** | Refreshes structured data from the installed client first |
| `.\export.bat --with-assets` | Every page except **Updates** | Reuses the current export and its existing media; also rebuilds Assets and relinks Audio |
| `.\export.bat --from-game --with-assets` | Every page except **Updates** | Complete installed-client refresh, including asset extraction and CN audio decoding |
| `.\export_assets.bat` | **Map**, **Characters**, **Gameplay**, **Audio**, **Assets** | Reuses current Story/Text and existing exported media |
| `.\export_assets.bat --from-game` | **Map**, **Characters**, **Gameplay**, **Audio**, **Assets** | Keeps Story/Text, but refreshes assets and CN audio from the installed client |
| `.\build_updates.bat OLD NEW` | **Updates** | Compares two complete export folders |

Asset-enabled commands without `--from-game` can only publish media already
present in the current export. Use `--from-game` when that media has not yet
been extracted or the installed client changed.

`python serve.py` serves whatever has already been generated; it does not build
page data. `python scripts\pack_webui.py` packages the current generated WebUI
without refreshing it.

Mission Pipeline recovery remains available as a separate direct Python
workflow, but is no longer a WebUI page or part of the WebUI export commands.

## Project map

- `webui/`: static browser, runtime overrides, and generated data.
- `scripts/`: maintained export, build, update, audio, and packaging tools.
- `tools/AnimeStudio/`: tracked exporter fork.
- `export_full/`: generated extraction from the installed client.
- `reports/`: generated inventories and audits.
- `memory/`: current conclusions, evidence boundaries, and recovery queues.
- `scratch/`: revisitable experiments; `tmp/`: disposable intermediates.
- `endfield_reconstruction_lab/`: character rendering and animation lab (Git submodule).

Only `tools/AnimeStudio` is initialized by `setup.bat`. The
`endfield_reconstruction_lab` and `tools/EndfieldCapture` submodules are
optional and are not required for the normal WebUI workflow.

Technical documentation:

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
