# Liino Texture2D import contract refresh

Status: source-closed descriptor/import coverage for the refreshed generated
roster; exact compressed payload injection remains separately priority-gated.

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
`02A89272F454A91E91F2CFB485E97F98706946D1C13E3AA3C1E916430DEC509C`.
The existing 193-row native compressed-payload contract was re-pointed at this
import contract; its payload bytes and generated-copy authorization remain
unchanged (`398` copies). The native postprocessor's structural gate now
requires a positive count and `textures.Length == textureCount`, instead of the
stale literal 853.

## Liino coverage

The contract covers Liino body, cloth, face, hair, iris, skill, and item-widget
textures. Unity's `RefreshRecoveredCharacterMaterials` batch was run after the
contract refresh; the generated Liino importer profiles now match the current
native descriptor rows. The Liino eye-shadow material audit remains zero-failure
at queue 2900.

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

The post-refresh census reports zero descriptor drift across all generated
copies. Exact compressed payloads for newly added Liino/Jsspsi priority
surfaces are not silently invented: they remain outside the 193-row payload
selection until their native payload ownership is explicitly selected and
extracted.
