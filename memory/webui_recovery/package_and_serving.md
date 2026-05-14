# Package And Serving

This page records how the recovered WebUI is served locally and packaged for
sharing. It is not one of the in-browser tabs, but it is part of the complete
WebUI recovery solution.

## Local Serving

Run from the repo root:

```bat
python serve.py
```

Default URL:

```text
http://127.0.0.1:8765/
```

Optional port:

```bat
python serve.py 9000
```

The server exposes the static `webui/` files and generated data under
`webui/data/`. It is the quickest way to verify the recovered Story,
Reference, Updates, and Assets pages after running `export.bat`.

## Packaging

Run from the repo root:

```bat
.\package_webui.bat
```

or:

```bat
python scripts\package_webui.py
```

Dry run:

```bat
.\package_webui.bat --dry-run
```

Explicit output:

```bat
.\package_webui.bat -o endfield-story-exported-custom.zip
```

Default output name:

```text
endfield-story-exported-YYYYMMDD.zip
```

`YYYYMMDD` is today's local date. The package builder does not read `reports/`
to choose the name.

## Package Inputs

The package is built from:

```text
serve.py
webui/
export_full/
```

It uses `webui/data/assets/index.json` and `webui/data/assets/videos.json` to
resolve only displayed story/wiki media from `export_full/`.

It does not require:

```text
scratch/
reports/
tmp/
```

## Package Contents

The package includes:

- `serve.py`
- static WebUI files
- generated story/reference/update data
- filtered asset indexes
- exported images referenced by inline story/wiki media
- exported videos referenced by wiki media
- `README-webui-package.txt`

By default, the package removes the full Assets page from `index.html` and
installs an asset shim, because model and asset-browser payloads are too large
for the shareable story/reference package.

Use `--include-asset-browser` only when the receiving package should keep the
asset-browser UI shell. Even then, the package still filters media indexes and
does not include model/bundle payloads.

## Verification

Expected dry-run shape after the current default WebUI build:

```bat
.\package_webui.bat --dry-run
```

Check that output lists:

- WebUI root under this repo
- Export root under this repo
- output zip using today's date unless `-o` is passed
- text file count
- story image id count
- resolved image file count
- wiki video reference count
- resolved video file count
- `3D/model payloads: excluded`

If dry-run reports missing media, rebuild assets first:

```bat
python scripts\build_assets.py
```

If text or conversation data is stale, run the canonical refresh:

```bat
.\export.bat
```
