# Weapon Asset Entity Semantics - 2026-07-06

## Question

`memory/original_game_data_understanding_report_20260701.md` still lists
models/materials as only moderately understood: broad asset indexes and
PathID-resolved material/texture relations exist, but semantic entity-level
reconstruction is incomplete. This pass documents one strong current slice:
weapon `wpn_sword_0019` and its renderable `asset_entity` groups.

## Evidence Sources

Primary commands:

```bat
python tools\endfield_source_graph.py query wpn_sword_0019 --kind weapon --limit 20
python tools\endfield_source_graph.py used-by wpn_sword_0019_01 --kind asset_entity --limit 30
python tools\endfield_source_graph.py used-by wpn_sword_0019_vfx_01 --kind asset_entity --limit 40
```

Primary source rows:

- `export_full/structured/StreamingAssets/Table/WeaponBasicTable.json`
- `export_full/structured/Persistent/Table/WeaponBasicTable.json`
- `export_full/structured/StreamingAssets/Table/GemTagKeyToWeaponTable.json`
- `export_full/structured/StreamingAssets/Table/CharWpnRecommendTable.json`
- `export_full/structured/StreamingAssets/Table/GachaPoolWeaponPresetTable.json`
- `export_full/structured/StreamingAssets/Table/I18nTextTable_CN.json`
- `reports/source_graph/endfield_source_graph.sqlite`
- `reports/source_graph/summary.md`

Current graph-wide asset-entity counts:

- `asset_entity`: 10,678
- `entity_has_lod_model`: 30,830
- `entity_uses_material`: 2,009
- `entity_uses_texture`: 8,903
- `has_gameplay_asset_entity`: 132
- `weapon_model_asset_entity`: 130
- `asset_entity_used_by_gameplay`: 132
- `asset_entity_used_by_weapon_model`: 130

Catalog-scale weapon checks:

- `weapon_model_asset_entity` edges: 130
- distinct weapons with `weapon_model_asset_entity` edges: 70
- distinct weapon asset entities: 130
- weapons whose linked entity has LOD, material, and texture edges: 67

## Semantic Weapon Row

`WeaponBasicTable` defines `wpn_sword_0019` in both StreamingAssets and
Persistent table roots with matching fields:

```json
{
  "weaponId": "wpn_sword_0019",
  "rarity": 5,
  "maxLv": 90,
  "weaponType": 1,
  "modelPath": "Gameplay/Prefabs/Weapons/wpn_sword_0019.prefab",
  "levelTemplateId": "weapon_upgrade_curve_5star_1",
  "breakthroughTemplateId": "weapon_breakthrough_456star_B_1",
  "talentTemplateId": "wpn_potential_456star",
  "weaponPotentialSkill": "sk_wpn_sword_0019",
  "weaponSkillList": [
    "wpn_attr_agi_mid",
    "wpn_sp_attr_atk_mid",
    "sk_wpn_sword_0019"
  ]
}
```

The CN i18n name id `1961400820868472212` resolves to
`OBJ Edge of Lightness`. The `weaponDesc` text id resolves to a long unrelated
dialog-like text, so this pass does not use the description field as weapon
semantics without a separate text-table audit.

Other authored semantic links:

- `GemTagKeyToWeaponTable` has a single list containing `wpn_sword_0019`.
- `CharWpnRecommendTable` recommends the weapon for:
  - `chr_0007_ikut` in tier 2;
  - `chr_0019_karin` in tier 1;
  - `chr_0024_deepfin` in tier 1.
- `GachaPoolWeaponPresetTable` maps the weapon to perfect gem
  `gem_sword_0019_663`.

These links prove that the game tables treat `wpn_sword_0019` as a real
gameplay weapon with progression, recommendation, gem, and model-path metadata.

## Renderable Entity Binding

The source graph links `wpn_sword_0019` to two renderable asset entities through
`modelPath` evidence:

| Asset entity | Edge sources | Meaning |
| --- | --- | --- |
| `asset_entity:StreamingAssets/wpn_sword_0019_01` | `webui/gameplay`, `WeaponBasicTable` | main exported weapon model group |
| `asset_entity:StreamingAssets/wpn_sword_0019_vfx_01` | `webui/gameplay`, `WeaponBasicTable` | exported VFX model group sharing the weapon token |

The proof is strict token/modelPath evidence:

```json
{
  "modelPath": "Gameplay/Prefabs/Weapons/wpn_sword_0019.prefab",
  "token": "wpn_sword_0019",
  "assetEntity": "StreamingAssets/wpn_sword_0019_01"
}
```

The graph also adds lower-level `asset_used_by_gameplay` edges for exported
assets whose names include the same weapon token. Those are useful for lookup,
but the asset-entity edges are cleaner because they group LOD meshes and
material/texture dependencies under renderable entities.

## Catalog Cross-Check

A second weapon, `wpn_claym_0013`, confirms that this is not a one-off lookup
shape. It has two `weapon_model_asset_entity` edges:

- `asset_entity:StreamingAssets/wpn_claym_0013_01`
- `asset_entity:StreamingAssets/wpn_claym_0013_vfx_01`

The main `wpn_claym_0013_01` entity has:

- four LOD meshes;
- one material,
  `StreamingAssets-materials/Material/M_wpn_claym_0013_01_pDA638754E5DFF082.json`;
- five texture slots:
  - `_BaseMap`: `T_wpn_claym_0013_01_D_p4AFB7EC441AFDC15.png`
  - `_EmissionMap`: `T_wpn_claym_0013_01_E_pCB46A33326159F38.png`
  - `_BumpMap`: `T_wpn_claym_0013_01_N_p265D21ACDBE14105.png`
  - `_MetallicGlossMap`: `T_wpn_claym_0013_01_P_pC01EC3C656E0AAA0.png`
  - `_ParallaxTex`: `T_fx_flow_156_M_pBDDD7222A26F331A.png`

This broader check supports using the weapon asset-entity bridge as a catalog
surface: it has enough coverage to answer many weapon visual lookup questions,
while still stopping short of runtime prefab proof.

## Main Model Entity

`asset_entity:StreamingAssets/wpn_sword_0019_01` has:

- `lodModelCount=4`
- `materialCount=1`
- `textureCount=4`

LOD mesh files:

| LOD | Asset |
| --- | --- |
| 0 | `StreamingAssets/Mesh/S_wpn_sword_0019_01_lod0_p2BB64D1E1646281E.obj` |
| 1 | `StreamingAssets/Mesh/S_wpn_sword_0019_01_lod1_p71BB20090302281E.obj` |
| 2 | `StreamingAssets/Mesh/S_wpn_sword_0019_01_lod2_p543C40D1DF8F281E.obj` |
| 3 | `StreamingAssets/Mesh/S_wpn_sword_0019_01_lod3_pEB60061B6F35281E.obj` |

Material:

```text
StreamingAssets-materials/Material/M_wpn_sword_0019_01_p3503E5B7B47DCEEC.json
```

Texture slots resolved through material PathID evidence:

| Material slot | Texture |
| --- | --- |
| `_BaseMap` | `StreamingAssets/Texture2D/T_wpn_sword_0019_01_D_pA3BE1605770BBB16.png` |
| `_BumpMap` | `StreamingAssets/Texture2D/T_wpn_sword_0019_01_N_p659923B4066CC0F9.png` |
| `_MetallicGlossMap` | `StreamingAssets/Texture2D/T_wpn_sword_0019_01_P_p479C41F662A92166.png` |
| `_ParallaxTex` | `StreamingAssets/Texture2D/T_fx_flow_221_M_p362C100BD7F6A7ED.png` |

This is the strongest recovered visual chain for the weapon: gameplay weapon
row -> modelPath token -> renderable entity -> LOD meshes -> material ->
texture slots.

## VFX Entity

`asset_entity:StreamingAssets/wpn_sword_0019_vfx_01` is also linked to the same
weapon through `modelPath` token evidence. It has four small LOD mesh files and
no material/texture edges in the current graph:

| LOD | Asset |
| --- | --- |
| 0 | `StreamingAssets/Mesh/S_wpn_sword_0019_vfx_01_lod0_p117C25CC7DE7281E.obj` |
| 1 | `StreamingAssets/Mesh/S_wpn_sword_0019_vfx_01_lod1_p51384067A011281E.obj` |
| 2 | `StreamingAssets/Mesh/S_wpn_sword_0019_vfx_01_lod2_pA6294E05FCB6281E.obj` |
| 3 | `StreamingAssets/Mesh/S_wpn_sword_0019_vfx_01_lod3_p950758B3551F281E.obj` |

The current graph does not prove how, when, or whether the runtime prefab
instantiates this VFX entity separately from the main model. It only proves
that the exported model group shares the weapon token and is grouped as a
renderable entity.

## Current Understanding

For this weapon, entity-level reconstruction is strong enough for practical
lookup:

- the gameplay weapon is anchored by `WeaponBasicTable.modelPath`;
- two renderable `asset_entity` groups are recovered from exported model names;
- the main entity has full LOD mesh coverage plus one material and four texture
  slots;
- material-to-texture links use resolved PathID evidence rather than only name
  substring matching;
- catalog-scale checks show 70 weapons linked to 130 weapon asset entities, and
  67 of those weapons have linked entities with LOD, material, and texture
  edges;
- item/icon-style direct asset edges exist, but the asset-entity chain is the
  cleaner renderable catalog surface.

## Boundary

This pass does not prove runtime prefab composition. The following remain
outside the current evidence:

- exact Unity prefab hierarchy for `Gameplay/Prefabs/Weapons/wpn_sword_0019.prefab`;
- runtime material variant selection or shader keyword state;
- animation, socket, attachment, or VFX activation timing;
- scene-specific weapon swaps;
- whether the long `weaponDesc` text id is a bad source row, a placeholder, or
  an unrelated text collision.

The safe claim is export-backed semantic lookup, not runtime render fidelity.

## Next Checks

- Compare more weapon rows to see how often each weapon has both `_01` and
  `_vfx_01` asset entities.
- Inspect one character or interactive object with `model_config_asset_entity`
  or `interactive_template_asset_entity` edges to contrast weapon modelPath
  evidence with decoded model-config evidence.
- If runtime prefab files become available, join `modelPath` directly to Unity
  prefab component references instead of relying on token-to-exported-model
  grouping alone.
