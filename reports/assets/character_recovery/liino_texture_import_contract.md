# Liino Texture2D import contract refresh

Status: source-closed descriptor/import coverage and exact native payload
coverage for the refreshed generated roster's selected Liino surfaces.

## Evidence

The current installed AssetMap resolves every generated character texture to a
unique source object: 897 Texture2D objects, 1,541 generated copies, zero
missing rows, and zero ambiguous rows. A targeted AnimeStudio `Texture2D` dump
materialized all 897 native descriptors, including the 22 Liino-owned rows and
the three Persistent `T_item_widget_liino_04_*` rows. Census SHA-256:
`096E6157190C90001F3573D400BF76A03465ED317479BB7CDDFAAAE343F9DA41`.

The regenerated `character_texture_import_contract.json` now contains 897
rows, with exact source offsets/object hashes, descriptor hashes, dimensions,
format, mip count, color space, and importer profiles. Contract SHA-256:
`D8322676C26F4FE35179C2ABE722404682216423915E8F79EF3B51D4DB2A0284`.
The exact native compressed-payload contract now points at this importer
contract and contains 215 rows / 420 generated-copy owners, including a new
22-row Liino selection. Payload contract SHA-256:
`A4BB97C58C8784E85ECE85A4D2F8188BDC403E608082084BA7BFE5CB4A7E92A9`.
Combined payload storage is 213 unique files / 442,888,176 bytes for
444,635,856 logical bytes. The native postprocessor's structural gate now
requires a positive count and `textures.Length == textureCount`, instead of the
stale literal 853.

## Liino coverage

The contract covers Liino body, cloth, face, hair, iris, skill, and item-widget
textures. Unity's `RefreshRecoveredCharacterMaterials` batch was run after the
contract refresh; the generated Liino importer profiles now match the current
native descriptor rows. The Liino eye-shadow material audit remains zero-failure
at queue 2900. AnimeStudio native Texture2D payload manifests were extracted
for all 22 selected Liino rows (body, cloth, face, hair, iris, skill, and
item-widget), with exact payload size/hash/layout checks and Playable PNG GUID
and pixel-hash ownership.

## Validation

- AnimeStudio descriptor census: 897/897 resolved, zero missing/ambiguous.
- Unity batch refresh: exit code 0; the editor completed the material/texture
  refresh without a project exception.
- Full `verify_overlay_shadow_recovery.py`: passed; it now checks all 87 eye/
  eye-white overlay materials and 50 shared eye-mask imports against the
  refreshed contract.
- `scratch/reverse_engineering/eye_shadow_cluster_visibility/verify.py`:
  passed without its former stale-contract skip; runtime-input and chronology
  checks also pass.
- Native payload verifier: 215 objects / 420 copies / 213 unique payload files;
  Unity batch validator reports `passed=True` with 444,635,856 logical bytes.

The post-refresh census reports zero descriptor drift across all generated
copies. The new Liino payload rows are source-manifest-gated; Jsspsi and other
unselected priority surfaces remain outside the payload selection rather than
being assigned guessed compressed bytes.
