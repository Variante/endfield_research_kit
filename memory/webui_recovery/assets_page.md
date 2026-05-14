# Assets Page Recovery

The Assets page is the exported asset browser at `webui/index.html#assets`.
It indexes exported images, models, materials, videos, related files, and
browser-preview metadata from `export_full/`.

## User-Facing Page

Frontend files:

- `webui/index.html`: `#assets-view`, asset filters, preview stage, inspector.
- `webui/assets.js`: asset index loading, filtering, previews, related files,
  material/texture relationships, deep links, and download links.
- `webui/style.css`: asset browser layout, preview stage, and inspector panels.

Main controls:

- path/name/category search
- type chips
- source selector
- sort selector
- virtualized asset list
- image/model/video preview where supported
- raw file link
- download links
- related files/materials/textures/references

## Builder

Primary command:

```bat
python scripts\build_assets.py
```

`export.bat` runs this after Story.

The builder calls:

- `build_asset_indexes(...)` from `scripts/asset_builder/index.py`
- `write_story_media_index(...)` from `scripts/asset_builder/story_media.py`
- bundled demo archive helpers from `scripts/asset_builder/bundles.py`

## Inputs

Current preferred exported asset roots:

```text
export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/
export_full/recovered/AnimeStudio-cli/Persistent/convert_by_type/
export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/Material/
export_full/recovered/AnimeStudio-cli/Persistent/json_by_type/Material/
```

The indexer also uses structured and older compatibility roots where supported
by the existing code:

```text
export_full/structured/
export_full/StreamingAssets/
export_full/Persistent/
```

Material JSON under `json_by_type/Material` is the canonical material metadata
source. Converted files under `convert_by_type/` are the browser-facing media
and model sources.

## Outputs

```text
webui/data/assets/index.json
webui/data/assets/videos.json
webui/data/assets/bundles/index.json
webui/data/assets/bundles/*.zip
```

`index.json` is the searchable asset catalog. `videos.json` is separate so the
package builder can include only displayed wiki/story video references.
`bundles/` contains generated browser download bundles and their index.

## Recovery Behavior

The Assets page should expose exported assets without becoming a recovery
debugger. The current scope is:

- file search and filtering
- previewable image/model/video display
- metadata inspection
- related file relationships
- material and texture links
- deep links with `?asset=<relative-path>#assets`

Keep heavyweight recovery experiments out of the frontend. If a new recovery
view is needed, document and build it intentionally instead of letting
exploration-only data leak into `assets.js`.

## Verification

After rebuilding:

```bat
python scripts\build_assets.py
python serve.py
```

Check:

- `webui/data/assets/index.json` exists.
- `webui/data/assets/videos.json` exists.
- `webui/data/assets/bundles/index.json` exists.
- the Assets tab loads the count and filter chips.
- selecting an image shows an image preview.
- selecting a model shows model metadata and a preview when the browser supports
  that format.
- material and texture related-file links resolve to indexed entries.
