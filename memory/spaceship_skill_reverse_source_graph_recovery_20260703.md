# Spaceship Skill Reverse Source-Graph Recovery - 2026-07-03

## Scope

Spaceship skill semantics already linked characters to their authored spaceship
skills and linked each skill to its room type. This pass added reverse edges so
queries from a skill or room type can recover ownership and applicability
without relying only on incoming forward-edge scans.

## Added Reverse Edges

- `spaceship_skill_owned_by_character`
- `spaceship_room_type_has_skill`

These mirror:

- `character_has_spaceship_skill`
- `spaceship_skill_applies_to_room_type`

The character reverse edge preserves the authored `skillIndex` payload from
`SpaceshipCharSkillTable.skillList[*]`.

## Validation

Focused temp graph:
`tmp/spaceship_skill_reverse_validate.sqlite`

Counts from `ingest_spaceship_semantics()`:

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `character_has_spaceship_skill` | 108 | `spaceship_skill_owned_by_character` | 108 |
| `spaceship_skill_applies_to_room_type` | 140 | `spaceship_room_type_has_skill` | 140 |

CLI smoke checks:

- `python tools\endfield_source_graph.py query spaceship_skill_chr_0004_pelica_1_1 --kind spaceship_skill --db tmp\spaceship_skill_reverse_validate.sqlite --limit 12`
  showed `spaceship_skill_owned_by_character` back to
  `character:chr_0004_pelica` and `spaceship_room_type_has_skill` from
  room type `0`.
- `python tools\endfield_source_graph.py query 0 --kind spaceship_room_type --db tmp\spaceship_skill_reverse_validate.sqlite --limit 12`
  resolved the room type and its existing room-level context.

SQL sampling confirmed character ownership rows such as
`spaceship_skill_chr_0004_pelica_1_1 -> chr_0004_pelica` with
`{"skillIndex":0}`.

`python -m py_compile tools\endfield_source_graph.py` passed.
