# WebUI Recovery Solution

This folder records the current solution for recovering the static WebUI from
an installed Endfield client. It is intentionally detailed and operational, so
it lives in `memory/` instead of the root `README.md`.

## Canonical Refresh

From the repo root:

```bat
.\export.bat
python serve.py
```

`export.bat` is the current WebUI recovery pipeline:

1. `scripts/export_full_from_game.py --skip-raw-vfs --skip-source-inventory`
2. `scripts/webui/build_updates.py`
3. `scripts/webui/build_story.py --languages CN --default-language CN`
4. `scripts/webui/build_assets.py`

The pipeline writes the browser inputs under `webui/data/` and reads exported
game data from `export_full/`. It does not require `scratch/`, `reports/`, or
`tmp/` as active inputs. `reports/` remains an output area for generated
summaries and diagnostics.

## Page Files

- `story_page.md`: recovered Story page.
- `reference_page.md`: recovered Reference page.
- `updates_page.md`: recovered Updates page.
- `assets_page.md`: recovered Assets page.
- `package_and_serving.md`: packaging and local serving.

## Expected Generated WebUI Data

```text
webui/data/
  manifest.json
  index.json
  actors.json
  lang/
    CN/
      index.json
      actors.json
      conv/*.json
      mission/*.json
      reference/index.json
      reference/<source>/<table>.json
  updates/latest.json
  assets/index.json
  assets/videos.json
  assets/bundles/index.json
```

Extra language folders may exist when `build_story.py` is run with more
languages, for example:

```bat
python scripts\webui\build_story.py --languages CN EN JP --default-language CN
```

## Active Source Roots

The WebUI recovery path expects these active roots:

- installed game data: `D:\Program Files\Endfield Game\Endfield_Data`
- generated export root: `export_full/`
- WebUI output root: `webui/data/`
- update tracker state: `.game-data-tracker/`
- generated reports: `reports/`
- durable helper tools: `tools/`

Do not make the WebUI recovery depend on `scratch/` or `tmp/`. If an experiment
becomes necessary for repeatable recovery, promote the helper to `tools/` or an
active script path and document the promotion.
