# Display metadata source graph recovery - 2026-07-02

## Scope

Added structured source-graph recovery for cash-shop visibility, profile frame,
share, color, collection-label, shop-domain, and shop-channel development
metadata tables:

- `CashShopHideInGameTable.json`
- `UserAvatarTableFrame.json`
- `OverseaShareTable.json`
- `SKLandShareTable.json`
- `CashShopHasWeaponGoldPackTable.json`
- `GiftpackCashShopIdTable.json`
- `GiftpackCashShopClientShowDataTable.json`
- `RarityColorTable.json`
- `FactoryBlueprintIconBGColorTable.json`
- `CollectionLabelTable.json`
- `ShopDomainConst.json`
- `ShopChannelDevelopmentTable.json`

## Recovered semantics

- Cash-shop hide/show rows now link cash goods to visibility flags.
- User avatar frames now link icons and unlock items.
- Overseas share configs now link environment languages to allowed share-channel
  labels.
- SKLand share rows now expose board ids, tag ids, and localized names.
- Weapon gold-pack marker rows now link cash goods to the marker config.
- Giftpack shop id and client-show rows now link cash shops to labels,
  priorities, dynamic priorities, and localized names.
- Rarity and factory blueprint background color rows are queryable, with
  blueprint background image asset stems.
- Collection labels now group collection prefab entries recovered by the item
  submission pass.
- Shop-domain constants are queryable as display constants.
- Shop-channel development rows now expose per-level costs, unlocked goods,
  goods counts, random stock limit increases, and localized descriptions.

## Validation

Commands run:

```bat
python -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py build --db tmp\display_metadata_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The validation build completed with:

```text
Source graph: 1626654 nodes, 3053532 edges, 2232678 aliases
```

Targeted count checks:

```text
cash_shop_visibility              33 nodes
user_avatar_frame                 16 nodes
oversea_share_config              14 nodes
skland_share_type                 10 nodes
cash_shop_weapon_gold_pack        10 nodes
giftpack_cash_shop_label           7 nodes
giftpack_cash_shop_show_data       7 nodes
rarity_color                       6 nodes
factory_blueprint_icon_bg_color    7 nodes
collection_label                   7 nodes
display_const                      7 nodes
shop_channel_development           5 nodes
shop_channel_development_level    19 nodes

defines_cash_shop_visibility      33 edges
cash_goods_visibility             33 edges
defines_user_avatar_frame         16 edges
user_avatar_frame_unlock_item     16 edges
defines_oversea_share_config      14 edges
oversea_share_allows_channel      64 edges
defines_skland_share_type         10 edges
skland_share_type_name_text       10 edges
defines_cash_shop_weapon_gold_pack 10 edges
cash_goods_has_weapon_gold_pack_marker 10 edges
defines_giftpack_cash_shop_label   7 edges
giftpack_cash_shop_label_text      7 edges
cash_shop_has_giftpack_label       7 edges
defines_giftpack_cash_shop_show_data 7 edges
cash_shop_has_client_show_data     7 edges
giftpack_cash_shop_show_name_text  7 edges
defines_rarity_color               6 edges
defines_factory_blueprint_icon_bg_color 7 edges
defines_collection_label           7 edges
collection_label_has_entry        19 edges
defines_display_const              7 edges
defines_shop_channel_development   5 edges
shop_channel_development_has_level 19 edges
shop_channel_level_cost_item       19 edges
shop_channel_level_unlocks_goods 247 edges
shop_channel_level_desc_text       19 edges
shop_channel_level_upgrade_desc_text 19 edges
```

