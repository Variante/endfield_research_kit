# What the audio corpus names, and what nothing reaches

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4, audio lane.** The payoff of the lane: which media are named by which
source records, the music subgraph that no named event reaches, and how much of the
corpus is actually accounted for. Also the cross-package join trap, three times.

## Types `0x02` and `0x0B` share one source record, and it accounts for the media

This is the first result in this lane that is about the corpus rather than about a
body layout, so its evidence is stated in full.

**The record.** Numeric type `0x02` carries exactly one 14-byte source record at body
offset 0. Numeric type `0x0B` carries a counted array of the same record after its
leading flag and count. That they are the same record is shown twice:

- **The word at `+0` is a plugin id from a closed set.** `0x0B` uses two values --
  `0x00040001` (3,506 records) and `0x00140001` (941) -- and **140,121 of `0x02`'s
  142,815** bodies open with one of exactly those two. `0x02` uses five more
  (`0x00080001`, `0x00650002`, `0x00640002`, `0x00940002`, `0x01990002`), so it is a
  superset rather than a different field.
- **The word at `+5` names a declared media id in 4,447 of `0x0B`'s 4,447 records,
  and in 0 of them at any other offset in the record.** That contrast is what makes
  `+5` the id field. A bare hit rate would not.

**The attribution.** Pooled over every package, **61,325 of the 61,333 declared media
ids are named by some source record** -- 60,049 by `0x02`, 1,279 by `0x0B`, 3 by both,
and **8 by no record at all**. The words one byte either side of the id field name
**0 and 2**. Before `0x0B` was allowed to contribute, 1,284 media had no owner; it
closed 1,276 of them.

**The join has to cross a file boundary, and that is a trap worth recording.** A
source record names media that a *different* package declares. The first version of
this census joined inside one package and scored **12 of 147,262** -- not a weak
result, a meaningless one. `media_ids_from_audit` already carried the warning in its
own docstring: *"joining inside one package answers a question nobody asked."* The
census is published from C# as distinct value sets and joined in Python, where the
packages are already pooled.

## THE CROSS-PACKAGE JOIN TRAP, THREE TIMES

This has now bitten three separate fields, and the pattern is always the same: a table
and its users live in **different `.pck` files**, so a join written inside the reader
scores near zero and looks like a negative result.

| field | package-local score | pooled score |
| --- | --- | --- |
| media ids named by source records | 12 of 147,262 | **61,325 of 61,333** |
| source ids reached from named events | (pooled from the start) | 163 |
| plugin ids named by `INIT` | **1** of 147,262 | **973** of 147,262 |

`media_ids_from_audit` has carried the warning in its own docstring the whole time:
*"joining inside one package answers a question nobody asked."* I wrote the C# join
twice more anyway. **When a table and its users are in separate files, the join belongs
in the pass that already unions the files** -- the reader collects, the audit joins.

## The 8 media nothing names, explained

- **7 of the 8** are declared by `default_banks.pck`, which has `sounds=0`,
  `externals=0` and **exactly 7 media entries** -- so all 7 come from its `DIDX`
  section (84 bytes = 7 x 12). They are the Init bank's **embedded** media, and the
  same 7 ids are also declared as streamed copies in `default_stream_0.pck`. The 8th is
  in `default_stream_2.pck` only.
- **None of the 8 is a bank id**: pooled over 20,863 bank ids, the intersection with
  the 61,333 media ids is **0**, so they are genuine audio that no HIRC source record
  names rather than banks miscounted as media.
- Externals exist in this corpus -- 28,277 in `default_chinese_stream.pck` and 1 in
  `hotfix_japanese_bD0.pck` -- but not in the packages the 8 live in.

## NOTHING outside HIRC references a music object either

Sliding a 32-bit window over all four unparsed sections -- 10,677 words -- **63 name a
HIRC object against 0.59 expected by chance**, so the references are real. Every one
is a **bus**: numeric type `0x12` 62 times and `0x08` once, all inside `STMG`. `INIT`,
`ENVS` and `PLAT` name nothing at all.

- Unaligned offsets were included deliberately. The source id inside the 14-byte
  source record sits at `+5`, which is not four-byte aligned, and testing only aligned
  words is exactly how that field stayed unidentified for so long.
- **Together with the object graph this closes the question.** Across every byte of
  the bank format -- the reference graph, the parent field, the `0x08`/`0x12` forest,
  every music relation, the action target word, and all four unparsed sections --
  **nothing references a music object from outside the music family.**
- Gated with its expiry in mind: a music type appearing here fails the audit. **That
  failure is the good news.**

## NOTHING in the HIRC object graph reaches the music family's media

The previous batch asked what addresses the music subgraph. The answer, over every
relation this reader has resolved, is **nothing** -- and the evidence is now complete
rather than suggestive, because the relations can be enumerated.

| relation | edges | any music type at either end? |
| --- | --- | --- |
| main reference graph | 230,247 | **no** -- sources `04/05/06/07`, targets `02/05/06/07/09` |
| parent field (its inverse) | 199,445 | **no** -- 13 type pairs, all in `02/05/06/07/09` |
| `0x08`/`0x12` forest | 412 | no |
| music hierarchy at `+9` | 7,084 | internal only: `0A->0C`, `0A->0D`, `0C->0C`, `0D->0C` |
| `0x0C`'s counted array | 2,980 | internal only: `->0A`, `->0C`, `->0D` |
| `0x0A`'s counted array | 3,903 | internal only: `->0B` |
| **action target word** | 23,455 resolvable | **8 land on `0x0C`; none on `0A`, `0B` or `0D`** |

- **The family is large and well connected internally**: 11,656 objects, 7,305
  downward edges from 4,607 sources, 4,351 objects with no incoming edge (3,764
  `0x0A`, 489 `0x0D`, 98 `0x0C`). **Every `0x0B` has an incoming edge** -- none is a
  root -- so the tracks are owned.
- **Entering it from outside there are 5 edges in the whole corpus**, all
  `action_03 -> type0C`, resolved within the same bank. All 5 land on objects that are
  **roots**, **none of the 5 has an outgoing edge**, and together they reach **0**
  source ids.
- So the family's **1,279 media are reached by nothing**. Extending the named walk to
  read `0x0B`'s source records changed the reach numbers by exactly nothing --
  120 identifiers, 218 source ids, before and after.
- *This is written as a gate, not a note.* If a later reading reaches even one source
  id through the music family, `reachedSourceIdCount` becomes positive and the audit
  fails. **That failure is the good news.** The same pattern retired the `0x0B`
  element-count caveat two batches ago.
- The gate also refuses when the walk has **no edges**, because an empty edge set
  reaches nothing and looks exactly like isolation. *A negative result needs proof
  that the instrument was working.*
- What this does **not** say: that music is unreachable at runtime. It says no
  relation resolved here reaches it, so whatever drives music is **outside the HIRC
  object graph**. That bounds the search rather than ending it.

## The music subgraph is not reachable from any named event

- **Actions almost never address music.** Of the 23,455 action target words that
  resolve to an object in the package, the types are `0x05` 7,709, `0x02` 7,466,
  `0x09` 3,869, `0x06` 3,826, `0x04` 393, `0x07` 126, `0x08` 46, `0x15` 12 -- and
  **`0x0C` 8**. None at all reach `0x0A`, `0x0B` or `0x0D`.
- **The named walk confirms it from the other side.** Starting at the 199 named
  `0x04` objects and following gated reference vectors, the walk arrives at types
  `0x03` (310), `0x02` (225), `0x09` (127), `0x05` (91), `0x06` (18), `0x07` (4) and
  `0x04` (1). **It never arrives at a music type.**
- So the **1,279 media owned by `0x0B` are reached by no named event**, and the 163
  media a named event does reach are all owned by `0x02`. Extending the walk to read
  `0x0B`'s source records changed the reach numbers by **nothing** -- 120 identifiers
  reaching 218 source ids, before and after -- which is itself the measurement.
- What this does **not** say: that music is unreachable at runtime. It says the
  music types are not addressed through the action target word or through any gated
  reference vector, so whatever addresses them is not in this graph.

## How much of the audio corpus is actually named

| | count | share of declared media |
| --- | --- | --- |
| media ids declared by the packages | 61,333 | 100% |
| named by some source record | 61,325 | **99.99%** |
| reachable from a named `0x04` event | 163 | **0.27%** |

The gap is not a defect in the walk. Only **221** audio-shaped literals survive in
`global-metadata.dat`, matching 199 objects; the event names for the rest are not
shipped as managed literals. *Coverage of the structure and coverage of the names are
different numbers, and quoting one for the other would overstate both.*
