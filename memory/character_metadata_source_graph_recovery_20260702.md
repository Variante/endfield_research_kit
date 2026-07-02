# Character Metadata Source Graph Recovery - 2026-07-02

## Scope

Added first-class source graph coverage for compact character, bloc, and gacha
metadata tables that were present in exported game data but not yet represented
as semantic graph nodes:

- `BlocDataTable`
- `CharBattleTagTable`
- `CharacterConst`
- `CharGachaConst`

## Recovered Semantics

`BlocDataTable` describes bloc/faction-like character group metadata. The graph
now emits `bloc` nodes keyed by row id with label, English-name, icon, and tag
properties. It links rows to bloc nodes, bloc names to text, bloc icons to asset
aliases, and bloc tag ids to both generic `tag` nodes and existing
`character_tag` nodes.

`CharBattleTagTable` describes battle-tag labels for characters. The graph now
emits `character_battle_tag` nodes, text references for `battleTagText`, and
links to matching `character_tag` ids.

`CharacterConst` contains scalar and list constants for character systems,
including progression limits and weapon EXP item ids. Because its rows are not
object dictionaries, its semantic handler must run before the normal
dict-shaped character support table guard. The graph now emits
`character_const` nodes and typed item refs for item-like constant values such
as `weaponExpItem`.

`CharGachaConst` contains character gacha constants. The graph now emits
`gacha_const` nodes and typed refs for item ids, reward ids, activity ids, and
character gacha pool ids.

## Validation

Built a focused temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\character_metadata_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

```text
Source graph: 1628438 nodes, 3057406 edges, 2234969 aliases
```

Focused semantic counts:

```text
NODE character_battle_tag 27
NODE character_const 6
NODE bloc 8
NODE gacha_const 13
EDGE defines_character_battle_tag 27
EDGE character_battle_tag_text 27
EDGE character_battle_tag_ref 27
EDGE defines_character_const 6
EDGE character_const_item_ref 3
EDGE defines_bloc 8
EDGE bloc_has_tag 8
EDGE bloc_has_character_tag 8
EDGE defines_gacha_const 13
EDGE gacha_const_item_ref 3
EDGE gacha_const_reward_ref 7
EDGE gacha_const_activity_ref 1
EDGE gacha_const_pool_ref 1
```
