# The HIRC object graph, and the types that are closed

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 3, audio lane.** The first structure above byte layout: the relations, how
they are told apart, and the per-type layouts that are closed byte-exact. Long,
because it is one continuous investigation.

## The first structure above byte layout: `0x08`/`0x12` form a forest

The leading word of every `0x08` and `0x12` body names another object. Followed as a
parent relation **per bank**, over 121 banks and 412 objects:

- **Zero cycles.** No object is its own ancestor anywhere in the corpus. A cycle
  would have meant the leading word is not a parent at all, so this is gated as
  equality with zero.
- **Depth runs to 7**, mode 2: `0`:123, `2`:126, `3`:64, `4`:32, `5`:23, `6`:21,
  `1`:18, `7`:5. It is a real hierarchy, not a flat list -- which the gate checks,
  because acyclicity is free when nothing is connected.
- **`0x08` is above, `0x12` below.** Internal nodes: `0x08` **68**, `0x12` **2**.
  Leaves: `0x08` 93, `0x12` **249**. The four objects with *no parent at all* are all
  `0x08`.
- **120 of 121 banks contribute exactly one tree**; one bank contributes three.

**The distinction that a first version of this gate got wrong.** An object with **no
parent** is a root of the relation; an object naming a parent that is merely **not in
this bank** is a root only of that bank's fragment. There are 119 of the second kind
and **all 119 are `0x12`**. Scored together they looked like 119 `0x12` roots, which
contradicts `0x12` being a leaf; scored apart they say something else entirely --
**a `0x12` object's parent usually lives in a different bank.** Corpus-wide those
references resolve: `0x12` -> `0x08` 201, `0x08` -> `0x08` 154, `0x12` -> `0x12` 48.

*Building this graph on deduplicated object ids gives 3 trees over 278 objects
instead of 121 over 412, because ids repeat across banks. A relation is only as
well-defined as the scope its endpoints are resolved in.*

## Three relation kinds, told apart by in-degree and symmetry

| relation | edges | a target is named by | reverse edge present | reading |
|---|---:|---|---:|---|
| main reference graph | 240,898 | exactly one referrer | -- | owner -> owned |
| `0x08`/`0x12` leading word | 275 | many children | -- | child -> parent |
| music types (`0A`,`0C`,`0D`) | 24,430 | many | **73.9%** | **mutual, neither** |

- **The music relation is symmetric.** Of 24,430 same-bank edges, 4,598 point at an
  object that was never scanned (only `0A`, `0C` and `0D` bodies are) and so cannot be
  asked the question; of the 19,832 that can, **14,652 have their reverse present**.
  Mutual across every type pair: `0A`<->`0D` 3,570 each way, `0C`<->`0D` 2,431,
  `0C`<->`0A` 588, `0C`<->`0C` 1,474.
- **So these edges cannot be read as parenthood in either direction**, and the music
  types do not form a hierarchy the way the other two relations do.
- **Not cliques either.** Neighbours of a node are linked to each other **0.1%** of
  the time, which rules out the reading that these bodies simply share a list of
  sibling ids.
- The graph has 7,341 back edges, which is exactly what a mostly-symmetric relation
  produces -- every mutual pair is a two-cycle. *Running a cycle check on a relation
  before checking whether it is symmetric answers the wrong question.*
- **Two corrections to my own earlier statements, both measured.**
  1. I said a shape analysis of the music edges "would be measuring the noise as much
     as the structure". Wrong by three orders of magnitude: expected chance matches
     are `646,465 x 213,138 / 2^32` = **32**, which is **0.13%** of 24,515.
  2. I assumed package-wide resolution was inflating the count. Also wrong --
     **24,430 of 24,515 music references are same-bank**, a difference of 85. Only
     0.35% leave the bank, against 119 of 275 for the `0x08`/`0x12` relation, which
     is the one that really does reach across banks.

### The two reference relations in this format run in OPPOSITE directions

Both are forests, so shape alone does not tell them apart. **In-degree does.**

| | edges | a target is named by |
|---|---:|---|
| main reference graph (`05`->`02`, `07`->`07`, `09`->`05`, `04`->`03`, ...) | 240,898 | **exactly one** referrer, always |
| `0x08`/`0x12` leading word | 275 | **many** children -- 50 of 70 parents have two or more, and one has 16 |

- The main graph's `targetsWithMultipleReferrers` is **0 over 240,898 edges**, the
  `0x09` child vectors included. Every
  object there is named exactly once, which is what an **owner -> owned** edge looks
  like: a `0x05` object owns its `0x02` objects and no other object owns them.
- The `0x08` relation is the reverse: many children name one parent, which is what a
  **child -> parent** edge looks like.
- So the format carries downward ownership in one place and upward attachment in
  another, and the two must not be merged into one graph. **The `0x08`/`0x12`
  leading word is deliberately NOT in the main reference graph**, and adding it would
  break that graph's one-referrer-per-target closure -- which is a reason to keep them
  apart, not a defect.
- Gated by `the_hierarchy_runs_opposite_to_the_main_reference_graph`, which asserts
  the contrast rather than assuming it: the two relations are built by different code
  and nothing else would notice if one drifted into the other's shape.
- *Two relations can have the same shape and opposite meaning. Direction is not
  visible in "is it a forest"; it is visible in how many times a target is named.*

Gated by `the_shared_hierarchy_is_a_forest`, `almost_every_bank_contributes_one_tree`
and `numeric_type_12_is_a_leaf`. Nothing here claims what the relation *means* -- only
that it is a forest, that the two types occupy fixed positions in it, and that the
`0x12` end reaches across banks.

### The curve record's values cannot be tested for propagation in this corpus

- The shuffle test that retired the fraction link has **no power** on the curve
  record, and this is a property of the corpus rather than a result about the data.
  Of the 408 reference edges inside `0x08`/`0x12`, only **17** have curve records at
  *both* ends.
- Worse, the obvious statistic is degenerate: "the two ends share an interpolation
  code" scores **17 of 17 on the real pairing and 17 of 17 shuffled**, because the
  alphabet is ten values of which two (9 and 4) cover about 87% of all records. Any
  two bodies share a code. Requiring a whole matching record gives 15 against 13 --
  seventeen samples, no power.
- *Before running a shuffle control, check that the statistic can tell the pairings
  apart at all. A test that scores identically on shuffled data has not produced a
  negative result; it has produced no result.*
- What the distributions do show, as corroboration rather than a link: the codes have
  the same two dominant values everywhere. `0x08`/`0x12` tail units run 9 at 44.9%
  and 4 at 41.7% of 314 records; `0x0B` element runs 9 at 49.4% and 4 at 24.5% of
  4,086. Same enum, same defaults, different mix.
- **`0x08` framed byte-exact in 96 of its 161 bodies at this point** -- superseded
  below by `0x08` IS CLOSED TOO: 161 of 161. Layout, end to end:
  a 32-bit reference, the counted key/value block type `0x16` uses (a count, that
  many one-byte keys, that many four-byte values as parallel runs), a one-entry
  list whose key sizes its value (`0x15` -> 11 bytes, `0x1D` -> 27, exactly 16
  apart), the fixed nine-byte signature `02 e8 03 00 00 00 00 c0 c2`, a zero word,
  a counted run of six-byte entries, and five zero bytes.
- Two details are the whole difference between this and the earlier attempt.
  The one-entry list's key **predicts** its value width, so an unobserved key is
  held unsupported instead of walked with a guessed width. And the entry run
  carries **one extra byte when its count is nonzero and nothing at all when the
  count is zero** -- which the bodies declaring no entries fix, rather than being
  assumed.
- The 65 remaining bodies are fenced by named reason, never skipped:
  `trailer_is_not_five_bytes` 40, `word_after_signature_is_not_zero` 11,
  `signature_not_where_expected` 9, `range_properties` 4,
  `second_list_is_not_one_entry` 1. Those names are where the next attempt starts.
- `0x08` is deliberately **not** one of the closure-gated body lanes: a lane
  publishes a closed-form byte total and this type has none. Its gate forbids only
  what a partial framing must not do -- leave a body neither framed nor accounted
  for, report an ambiguous body, or pass with nothing framed at all.
- **The "zero word" after the middle block is a count too.** It is followed by that
  many **18-byte** elements. It reads as zero in 396 of the 412 bodies of both types,
  which is exactly why it was checked as a constant; the 16 that declare 1, 2, 3 or 7
  are what expose it. The width was **solved for**, not guessed: asking which element
  width lets each of those bodies close gives 18 for all of them, uniquely in 13 of
  14. That took `0x08` from 128 to **142 of 161**.
- **Third time this pattern has cost bodies in this layout.** The tail block's unit
  count, this middle-run count, and (earlier) the second-list count all looked like
  constants because the overwhelming majority of bodies declare the same value.
  *Before checking any field as a constant in this layout, look at its value
  distribution over both types -- a field that is 0 in 96% of bodies and small
  elsewhere is a count.*
## What "142,815 of 142,815 exact" does and does not establish

- **Six body lanes report 100% exact. That rate is real, but it is not one claim --
  it is a dozen claims of very different strength sharing a number.** The nine-group
  frame is optional almost everywhere: most bodies skip most groups, so a lane can
  frame every body exactly while one of its groups has been seen a handful of times.
- The reports published **group entry totals** and nothing else, and an entry total
  cannot be read on its own. `groupAEntries: 11` in type `0x06` might be eleven
  bodies with one entry or one body with eleven. Those are completely different
  amounts of evidence and only the first says anything about a layout.
- So every lane now also publishes **how many exact bodies exercise each group** and
  **the largest count any single body declares**, recorded at the one choke-point
  every framer passes through (`RecordHircBodyFrame`), so no lane can be added
  without it.
- **Pooled across all six lanes, nothing is thin.** The least-seen real group is
  group E at **324 bodies**; group C is at 85,397. The nine-group frame is well
  supported.
- **Per lane, several groups are very thin:**

  | lane | group | bodies |
  |---|---|---:|
  | `0x07` | group E items/vertices | **4** |
  | `0x06` | group A entries | **11** |
  | `0x05` | group H states/state elements | **12** |
  | `0x06` | group H groups/props/states | **14** |

- **Both numbers are true and the second is the one a reader needs.** Pooling is
  legitimate *only because* the nine groups are the same layout wherever they appear
  -- which is itself the claim under test, not a premise. "Group E's layout is
  established" rests on 324 bodies. "Type `0x07` frames group E correctly" rests on
  **four**. The `widestSingleBodyPerGroup` column is what rules out the one-fat-body
  case: group H's states are widest-1 or widest-2, so the 12 and 14 really are that
  many separate observations.
- Gated by `every_group_reports_the_bodies_behind_it`: a lane that counts group
  entries without counting the bodies behind them is refused, and a report with no
  groups at all fails rather than passing vacuously. The thin groups themselves are
  **reported, not gated** -- the corpus contains what it contains, and the point is
  to make the weak claim legible rather than to fail on it.
- **The rule this adds.** A completion rate over a corpus of mostly-optional
  structure is an average of claims, not a claim. Before reading one as evidence,
  ask which parts of the layout the passing bodies actually exercised -- and count
  bodies, not entries, because one body can carry a whole total.

## The shared frame's constants: closure never settled three of the four

- **Audited every constant in the shared framer by scoring it against every rival
  value, and closure turns out to be the wrong test for three of them.** The
  audit was prompted by the terrain retraction, where a claim validated only on
  degenerate inputs collapsed; the question asked here was the same one -- what do
  the *passing* bodies have in common?
- Two rules make the scoring fair, and both matter more than the result:
  1. **Score a constant only over the bodies that exercise it.** A body declaring a
     middle run of zero frames identically under every element width. Scoring all
     412 bodies buries the real margin under 398 that cannot tell the values apart
     -- and it did: the first cut of this census reported a best rival of 202
     against the chosen 325, which looked like a near-tie and was an artefact.
  2. **Reduce on corpus totals, not per package.** A per-package maximum of the best
     rival is not the corpus-wide best rival.
- What the corpus says, per constant (`chosen` / `exercising bodies` /
  `zero-trailer hits` / `best rival's hits` / `rivals that close every body`):

  | constant | chosen | exercising | chosen | best rival | rivals that close all |
  |---|---:|---:|---:|---:|---:|
  | `middleBlockBytes` | 9 | 408 | 325 | 0 | **0** |
  | `entryBytes` | 6 | 267 | 203 | 0 | **6** |
  | `middleRunElementBytes` | 18 | 14 | 10 | 0 | **2** |
  | `trailerBytes` | 5 | 408 | 325 | 0 | **12** |

- **Only `middleBlockBytes` is settled by closure.** Six entry widths close all 267
  bodies that carry an entry run. Three element widths close all 14 that carry a
  middle run. *Every* trailer length "closes", because a remainder that does not
  match simply routes the body to the tail block instead of refusing it -- so that
  constant was never under any test at all.
- What settles them is the **zero trailer**: landing exactly on five bytes that are
  all zero. Each chosen value wins that outright and every rival scores **zero**.
- **This corrects a stated reason, not a result.** The code comment claimed the
  18-byte element width "was solved for by asking which one lets each of them
  close". Widths 5 and 11 also close all fourteen. The width is right; the
  justification recorded for it was insufficient, and a reader trusting it would
  have believed the constant was better established than it was.
- Both facts are now **gates**, not remarks. `every_shared_constant_beats_its_rivals`
  demands a strict margin over the best rival and a nonzero score of its own; and a
  control gate demands that some rival still close every body, so that if closure
  ever did become the discriminator the reasoning here would fail loudly rather than
  rot quietly. Published per candidate in `hircSharedConstants` so the margin is
  re-measured every run.
- **The general rule, and it is the same one the terrain codec taught.** A constant
  fitted by "which value makes the parse close" is only established if the rivals
  are scored the same way and lose. Fit and discrimination are different claims, and
  a closure rate reports the first while sounding like the second.

## The fences are closed: `0x12` is complete, `0x08` is 160 of 161

Two readings closed 22 of the 23 fenced bodies. Both were *missing* structure, not
mis-sized structure, which is why widening ranges had never helped.

**1. A null leading reference carries a second 32-bit word.** Four `0x08` bodies
open `00 00 00 00` and then a word before the property count. Read without it they
ask for 74, 205 or 167 properties in a body far too short to hold them; read with
it, the second list's key lands on `0x15` in all four. That is the evidence -- where
the rest of the frame lands, not whether the count looks plausible. (An earlier
version of this idea was withdrawn because it "changed the exact count by zero".
It did, at the time, because these four were also failing later for the tail-block
reason below; fixing one without the other shows nothing.)

**2. A tail block ends with a section, and the old reading hardcoded its absence.**
The block is:

```
u8 zero, u8 unitCount, u8 zero          -- unitCount may be 0
unitCount x unit                         -- 12 head bytes, records, a byte, records
u8 entryCount
  entryCount == 0: one byte closes the body
  entryCount >  0: entries, then u8 one, u32 reference, u8 zero, u8 recordCount
                   recordCount x record
```

- An **entry** is 3 bytes, or 4 when the high bit of its first byte is set. The same
  high-bit width trick the format uses elsewhere. In bodies carrying several, the
  entries' first bytes run 0, 1, 2, ... .
- A **record** is `u32 id, u8 valueCount, u8 zero, valueCount x u16, valueCount x
  float`. `valueCount` is 1 in 36 of 38 records, **which is exactly why the record
  looked like a fixed 12 bytes** -- 4+1+1+2+4 = 12. Two records declare 2 and are 18
  bytes.
- **The two bytes the old code took for a fixed closing word were `entryCount = 0`
  plus its one closing byte.** So it framed the 64 bodies whose section is absent
  and none of the 18 whose section is present. A hardcoded constant standing in for
  an optional structure, for the second time this session -- the terrain codec's
  "closing run of exactly five literals" was the same mistake.

**Result.** `0x08` 142 -> **160 of 161**; `0x12` 247 -> **251 of 251, complete**.

## `0x08` IS CLOSED TOO: 161 of 161, and `0x12` 251 of 251

The last body's tail unit carries **three** bytes after its 12-byte head rather than
two, with the record count in the **middle**. The flag is the **high bit on head byte
6**: 111 units read `(count, pad)` with the bit clear, 1 reads `(pad, count, pad)`
with it set, and there are no counter-examples either way.

**One unit is thin evidence and the closure is not what carries this.** What does is
the content. Under the wide reading that body's **eight records all become curve
records** -- interpolation codes 9, 9, 9, 9, 5, 4, 4, 4, with values like (0.0, 1.0),
(0.005, 0.0), (100.0, 0.0), (60.0, 0.0) and (1.0, 0.0) -- and the body lands exactly
on its two-byte absent section. Under the narrow reading they are noise. *Eight
independent twelve-byte windows agreeing on a ten-value enum is the evidence; the one
unit is not.*

How it was finally found, after several wrong attempts: **the unit heads repeat.**
Unit 0's head begins `48 6a 10 56` and so does unit 1's -- and under the narrow
reading unit 1 appeared to start one byte earlier, at a `00` followed by those same
four bytes. A walk that lands one byte before a structure it has already seen is off
by one, and the repeated head is what makes that visible. *When a walk desynchronises,
look for the next occurrence of something it has already parsed correctly.*

Superseded by this: the earlier guesses that the head is 13 bytes, and that the count
is "whichever of the two bytes is nonzero". The head is 12 bytes and the gap is what
widens.

**The one body left, now characterised by content rather than by guesswork.**

- The two bytes after each tail unit's 12-byte head are a record count and a pad.
  Across all **110** units in the corpus: **109** read `(n, 0)` and **one** reads
  `(0, 3)`. Neither order is ever ambiguous -- **no unit has both bytes nonzero and
  none has both zero** -- so in 109 units the count is first and in one it is second.
- **The `(0, 3)` unit's three records are genuine curve records**, which is what makes
  the reading content-verified rather than size-fitted: `(0.0, 1.0, code 9)`,
  `(0.005, 0.0, code 9)`, `(100.0, 0.0, code 9)`. Reading the count as 0 skips them.
- **But "the count is whichever byte is nonzero" does not close the body.** It fixes
  the first unit and then the *second* unit's head fails its `b[+4] == 0` check, so
  the body needs more than the count. The corpus goes 160/161 either way, with the
  fence merely moving from `truncated_tailSectionEntry` to `unit_shape`.
- The earlier guess -- a 13-byte head signalled by the high bit on head byte 6 -- is
  superseded: the head is 12 bytes and the pair after it is what varies.
- *A rule that fixes the symptom you were looking at and breaks the next check has not
  been validated by the thing it fixed. Re-run the whole walk, not the failing step.*

**How these were found**, because the method is reusable: dump each fenced body
from its failure cursor to the end and read the bytes. Both structures were legible
by eye within a couple of samples -- the records end in recognisable floats
(`00 00 80 3f` = 1.0, `00 00 c8 42` = 100.0), which anchors the record boundary, and
from there the counts fall out. Widening a range would never have found either.

- The `range_tail_block_units` bodies declare **zero** units. Reading two of them by
  hand gives a tidy structure -- `00 00 00`, a count, a zero byte, that many 3-byte
  entries with an index running 0, 1, 2, ..., then `01`, a `u32`, a zero byte, a unit
  count, and that many 12-byte `(u32, u32, float)` units, closing the body exactly.
  It reproduces those two samples to the byte.
- **It is wrong, and this was checked before any of it was written into the reader.**
  Across the ten bodies it closes **1**, and that one's indices are not ascending;
  five type `0x08` bodies diverge at the byte after the entry run and four type
  `0x12` bodies one byte earlier. Two samples were enough to invent a layout and not
  nearly enough to test one.
- The alternative -- that the *entry run* walk is wrong for these bodies, so the tail
  does not start where the reader thinks -- is now **eliminated**: trying every run
  length from 0 to 63 makes the tail frame as a unit block for **none** of the 19
  bodies still fenced. The tail of these bodies is a different structure, not a
  misplaced start.
- **What the fence hides, censused rather than framed.** 40 bodies carry a tail
  after the entry run, and 27 of them end in a counted run of **twelve-byte
  records**: two 32-bit floats and a 32-bit code. The run is anchored from the
  **end**, never walked forward -- the tail must finish with a zero 16-bit word, and
  the count must sit exactly two bytes before a run of that many records. Zero tails
  are ambiguous and zero lack a count; the other 13 have no zero word at the end.
- The discriminator, and the reason this is not just arithmetic that fits: the
  record's **third field takes only five values across all 80 records** (0, 1, 4, 7
  and 9). Read at a wrong offset it would be arbitrary 32-bit noise. The first field
  reads as a float and takes values like -180, -96, -75, -48, -36, -18, 0, 0.6, 1,
  75, 100 and 180 -- recorded as an observation, not a claim; nothing establishes
  what any of them measures.
- **The tail block is framed, and both types now use it.** After the entry run a
  body either ends on the five zero bytes or carries this block, which finishes it:
  a 15-byte head, a record count, one byte, that many 12-byte records, and a zero
  `u16`. That took `0x08` from 96 to **109 of 161** exact and `0x12` from 213 to
  **245 of 251**.
- **The "fifteen-byte head" was a one-unit block. The tail is a counted run of
  units.** Layout: a zero byte, a **unit count**, a zero byte, then that many units,
  then a zero `u16`. A unit is `u32, zero byte, two bytes, u32, one byte`, then its
  own record count, one byte, and that many 12-byte records. Reading it this way took
  `0x08` from 115 to **128 of 161** and `0x12` from 245 to **247 of 251**.
- Why the old reading looked right: the unit count is 1 in every body that framed
  under it, so the whole 15 bytes looked constant. *A single-element counted run is
  indistinguishable from a fixed head -- find a body with two before believing a
  head is fixed.*
- This also settles the three bytes I had published as a per-type selector. They are
  **per unit**, not per type: across the corpus they take `020002`, `060200`,
  `060300`, `020402`, `020502`, `020100`, `022300`, `043100`. Publishing rather than
  checking them is what kept that reading recoverable -- a check would have been
  wrong and would have hidden it.
- Only the bytes zero in every body of both types are checked (the prefix's `[0]` and
  `[2]`, and each unit's `[4]`).
- **The 15-byte head's first word is a reference, and it names a numeric type
  `0x12` object.** 13 of the 27 located tails have a head of that width. Its word at
  offset 3 resolves to a same-bank object 5 times; the other 8 name objects the
  package does not ship, which is the same pattern type `0x03` targets show. The
  **control** -- the word at offset 10 of the same head, classified identically --
  resolves **zero** times. Object population 213,138, so chance resolutions across
  13 draws are expected at 0.000645; observing 5 settles it. Every resolved target
  is type `0x12`, and the gate fails rather than widening if a second type appears.
- Two readings of those words are **eliminated**. They are not names: 0 of 26 match
  an FNV-1 hash of any of the 49,324 distinct `global-metadata.dat` string literals.
  And the word at offset 10 is not a reference at all -- it is distinct in every
  body and resolves nowhere.
- What remains unexplained in the tail: the 14 located tails whose head is wider
  than 15 bytes, and the bytes of the 15-byte head other than its first word. That
  is where the next attempt starts -- and the `0x12` link says to attack type `0x12`
  alongside it rather than separately.
- **A rule that looked right and is withdrawn.** Bodies whose leading reference is
  null appeared to carry an extra 32-bit word before the property count. Adding
  that rule changes the exact count by **zero**, and not one of the four
  null-reference bodies frames under it. It was fitted to nothing. The general
  lesson: when a special case is suggested by a handful of bodies, check that
  removing it changes the count before keeping it.
- **Numeric type `0x12` shares `0x08`'s layout, and 213 of its 251 bodies framed
  byte-exact at this point** -- superseded below by `0x12` 251 of 251, complete.
  Reference, counted key/value block, a second list whose key sizes
  its value, nine bytes, a zero word, the counted run of six-byte entries with its
  extra byte when the count is nonzero, five zero bytes. Two of the three
  second-list keys are `0x08`'s own: `0x15` -> 11 bytes, `0x1D` -> 27, plus `0x0A`
  -> 12. All 38 fenced bodies carry one reason, `trailer_is_not_five_bytes`.
- **How the widths were found, and why it is not a guess.** Everything after the
  second list is deterministic, so each body was asked which value width closes it
  exactly. Every body that closes has **exactly one** such width, and the width is a
  function of the key alone. Do not fit widths by eye; solve for them this way.
- **The nine bytes are a field, not a signature -- and `0x08` proves it inside its
  own type.** Read as `(u8 flag, u32, float)` the corpus carries four variants:
  `0x08` -> `(2, 1000, -96.0)` in 148 bodies, `(2, 0, -96.0)` in 8 and
  `(2, 500, -96.0)` in 1; `0x12` -> `(0, 0, -96.3)` in all 251. A magic does not vary
  in exactly one 32-bit slot, and the values are round decimals.
- **The two framers are now one.** Dropping the literal signature match and the
  "second list declares one entry" rule -- neither of which the shared layout
  justifies -- took `0x08` from 109 to **115 of 161** without moving `0x12`. Both
  the middle block's value and the second-list count are *published as selectors*
  rather than checked, because each type is uniform in them and a uniform corpus
  cannot tell a rule from a habit.
- **An ambiguity left open on purpose.** Key `0x0A` always arrives with a list count
  of 3 and a 12-byte value; the other keys always arrive with a count of 1. So "the
  key decides the width" and "the count multiplies a per-key width of 4, 11 and 27"
  predict the same bytes everywhere in this corpus. The simpler rule is implemented.
- **The 38 fenced `0x12` bodies carry `0x08`'s tail.** Same code censuses both. 34
  of the 38 have their trailing twelve-byte record run located by a unique count
  (100 records, third field only 4 and 9); zero are ambiguous; 4 have no zero word
  at the end and are read no further than the entry run. So of 251 bodies, 213 frame
  outright, 34 more are censused to their trailing run, and **4 remain opaque**.
- **Where the two types part, and it matters.** `0x12`'s tail-head words were
  classified exactly as `0x08`'s -- and they resolve to a package object **zero**
  times, control included. Sharing a layout does not make the same field mean the
  same thing. Do not carry `0x08`'s "names a `0x12` object" finding across.
- **What made this fast**: `0x08`'s tail head names a `0x12` object, so the two were
  attacked together. The reusable lesson is the one `0x16` already taught, now
  twice confirmed -- *when a small type resists, look for a structure another type
  already closes*, and here the whole layout was shared, not just a block.
- The other small types do **not** share `0x08`'s head. Their leading word names
  nothing in 119 of 251 `0x12` bodies, all 453 `0x10` bodies, and all 2,645 `0x11`
  bodies, so offset 0 is simply not a reference field for them. `0x12`'s first
  reference sits at offset 39 in a third of its bodies, which is the thread to
  pull there.
- **Numeric HIRC type `0x16` is framed byte-exact: 778 bodies / 16,635 bytes.**
  Layout: a byte count, then that many one-byte keys followed by that many
  four-byte values as **two parallel runs rather than interleaved pairs**, then one
  anonymous byte, then the node frame's group I structure verbatim.
- It closed fast because most of it was already proven. Group I is the same
  structure the reader frames byte-exactly on types `0x02`, `0x05`, `0x06` and
  `0x07`, so the only new part was the key/value block. **When a small type
  resists, check whether it ends with a structure another type already closes** --
  that is what turned this one from a decode into a ten-line framer.
- The parallel-runs detail is the one thing worth remembering about the block: an
  interleaved reading of key-then-value fails immediately, and the giveaway was
  that body length is exactly `4 + 5 * count` for the short bodies.
- `0x16` shares *only* group I, not the whole node frame, so it carries the group I
  residuals and none of the others. Its property keys and group I key widths are
  **per-element** selector families -- one observation per counted thing, not per
  body -- so they reconcile against their own counters rather than the body total.
  The lane framework now supports that kind of family explicitly; the first attempt
  bounded them by exact bodies and the gate correctly rejected it.
  See [`reports/animestudio/hirc_type22_body_current_latest.md`](../../reports/animestudio/hirc_type22_body_current_latest.md).
- None of the small types `0x08`, `0x10`, `0x11`, `0x12`, `0x16` open with the node
  frame. `0x08` and `0x12` begin *with* a same-bank reference at offset 0 (157/161
  and 132/251), which is a different head from every type seen so far and is the
  obvious next thread.
- **The music types `0x0A`-`0x0D` are framed, all four exactly, from the SDK
  deserializer** (see [`audio_hirc_parser.md`](audio_hirc_parser.md)). They do
  open with the shared node frame -- one flag byte in for `0x0A`, `0x0C` and
  `0x0D`, and after the source and playlist lists for `0x0B` -- which is why the
  offset-0 attempts recorded here died on group H and on a nonempty group B. The
  corpus observations below (names near the end of `0x0C`, the reference
  hierarchy, the offset-9 parent) all remain true; they are marker names, decision
  tree keys, transition rule ids and `DirectParentID` respectively.
- **The music family is one authored bank shipped twice.** Bank 266542773 appears
  byte-identical in `audit_banks.pck` and `hotfix_main_b75.pck`, and it holds 99.7%
  of the music objects, so every music count above is roughly double the distinct
  population (`0x0A` 2,112, `0x0B` 2,195, `0x0C` 373, `0x0D` 1,230 distinct).
  Corpus-wide, 10 banks ship in more than one package, duplicating 1.9% of objects,
  almost all of it this one bank. A per-package census cannot see this; the audit
  publishes the distinct count beside the total and gates their arithmetic.
- **Numeric type `0x0C` carries NAMES at fixed distances from the end of its body.**
  The words 12 and 24 bytes from the end are FNV name hashes of shipped string
  literals in **406 of 1,484 draws** over the 742 bodies -- against a chance
  expectation of **0.017**. Recovered values: `High` (72), `Low` (70), `Loop` (62),
  `WIN` (42+38), `Start`, `NONE`, `skip`, `General`, `END`, `Normal`, `Default`.
  146 bodies carry a name at *both* offsets.
- **Every music body references other objects, and the music types form a
  hierarchy.** Offering every 32-bit word of every body against the package's object
  set: **24,515 references across all 7,331 bodies, and not one body comes up
  empty.** Chance expectation over the 646,465 words offered is about 2. Edges:
  `0x0C`->`0x0D` 4,429, `0x0A`->`0x0B` 4,325, `0x0D`->`0x0A` 3,610, `0x0A`->`0x0D`
  3,570, `0x0C`->`0x0A` 3,262, `0x0D`->`0x0C` 2,431, `0x0C`->`0x0C` 1,920,
  `0x0A`->`0x0C` 588, plus small counts to `0x11`, `0x12` and `0x16`.
- **`0x0A` -> `0x0B` is one-to-one, and it is the only music edge that is.** 4,325
  edges reaching 4,325 distinct objects, none twice, out of a population of 4,325:
  every `0x0B` object is named by exactly one `0x0A` reference and none is missed.
- **The `0x0A` -> `0x0B` reference has a fixed place, measured from the END.** It
  sits **69 bytes from the end** in 3,707 of 4,325 cases, then -73 (288), -77 (59),
  -82 (52): four distances cover **94.9%**. Measured from the *front* the same
  references spread over 41, 36, 46, 45, 40, 48, 52, ... with no concentration at
  all. This is the first anchor the music types have had, and it only exists in
  end-coordinates.
- The secondary distances are 4 apart (-69, -73, -77), so an optional 4-byte field
  shifts the anchor -- the same kind of optional field `0x0D`'s lengths and `0x0B`'s
  entry widths both show.
- **`0x0A`'s HEAD has a rule: `36 + 5 * body[14]`.** Byte 14 is a count of five-byte
  elements, and it equals `(headLength - 36) / 5` in **3,441 of 3,441** bodies of
  the dominant family, including all 2,246 where the count is nonzero. Across the
  whole type the rule predicts a `0x0B` reference in **3,750 of 4,144** bodies.
- **Three controls, and they are what make it a finding.** Ignoring the count and
  reading at a fixed 36 scores **31.1%**; the position four bytes later scores
  **7.5%**; four bytes earlier scores **0.0%**. So the count is what places the
  reference, not proximity.
- **Byte 17 says whether the rule applies, and it is near-perfect.** Where
  `body[17] == 0` the rule places the reference in **3,744 of the 3,745** bodies
  that have one to place. Where it is nonzero: 6 of 144. Those 144 have longer
  heads, at `36 + 7 + 5k` (43, 48, 53) and a second family (52, 54, 59).
- **Mind the denominator.** Of the 394 bodies the rule "misses", **255 carry no
  `0x0B` reference at all** -- there is nothing there to find and nothing the rule
  got wrong. The real miss count is 139. The gate uses the denominator it can
  actually derive (bodies with `body[17] == 0`, which still includes those 255), so
  its threshold is 0.90 while the measurement against applicable bodies is 0.9997.
  The two numbers are not in conflict; they count different things, and the gate
  says which.
- **`0x0A` carries a SECOND reference, at offset 9 of its fixed head, and it names
  only `0x0C` or `0x0D`.** Over the 4,000 conditioned bodies it resolves in
  **3,999** -- 3,413 to `0x0D`, 586 to `0x0C`, one to nothing. Never a third type.
- **The fixed 36-byte head is half accounted for.** Conditioned on `body[17] == 0`,
  **16 of the first 36 bytes take a single value and all 16 are zero**. The varying
  positions fall in runs at 1, 5..12, 14..16, 18..20, 23..24, 28 and 32..33 -- the
  8-byte run at 5..12 contains the offset-9 reference, and `u32@1` and `u32@5` are
  zero in 3,736 and 3,624 of 3,744 bodies respectively.
- **The five-byte head element is fully read: a zero byte, a 16-bit value and two
  zero pad bytes.** Over the 3,052 elements in confirmed bodies: **0** with a
  nonzero leading byte, **0** with nonzero padding, and the value takes only
  **0, 1, 2, 3, 4** (598 / 2,240 / 186 / 26 / 2). So each element carries one small
  enumeration and nothing else.
- **The element census must be conditioned on the rule being confirmed, not merely
  on the discriminant.** Under `body[17] == 0` alone the same measurement gives 61
  nonzero leading bytes, 77 nonzero pads and 31 distinct values -- because a body
  whose reference is not where the rule says has no element boundary, so those bytes
  are being read at arbitrary offsets. Condition on the confirmed rule and every
  violation disappears.
- So `0x0A`'s head now reads end to end: 36 fixed bytes (16 of them constant zeros),
  then `body[14]` elements of `00 <u16 0..4> 00 00`, then the `0x0B` reference.
  What it leaves: the remaining varying fields inside the 36, the 144 bodies with a
  nonzero byte 17, and the 255 with no `0x0B` reference.
- **Byte 17 flags the longer head but does NOT determine its length** -- 36 distinct
  values over 126 bodies, 6 of them mapping to two different extras. It is a flag.
- **The count for the second run is `body[21]`, and the rule generalises.**
  `head = 36 + 5*body[14] + (7 + 5*body[21] if body[17] != 0 else 0)`.
  Byte 21 equals the second run's element count in **76 of 76** bodies of the
  `7 + 5k` family, all 56 with a nonzero count included. Over the whole type the
  generalised rule predicts the reference in **3,833 of 3,841** applicable bodies --
  **99.79%** -- against 3,744 for the single-run form.
- **The `0x0B` reference is an OPTIONAL four-byte field, and the 255 bodies without
  one are not anomalies.** Measured from the end of the head, **all 255 have a tail
  of exactly 65 bytes**, while the bodies that carry a reference sit at 69 (3,383)
  and longer. 69 - 65 = 4: the reference itself. Those bodies still carry the
  offset-9 head word (247 to `0x0D`, 8 to `0x0C`), so they are ordinary bodies with
  one field absent.
- That closes two of the three populations the head rule had excluded: 144 with a
  second counted run (framed), 255 with the reference absent (explained).
- **The third shape is a fixed 16-byte block, and `body[21]`'s MAGNITUDE selects
  it.** Where byte 17 is nonzero, byte 21 read as a count gives the five-byte run --
  but in some bodies it is part of a 32-bit value instead, taking 65, 97, 111 or
  243, and those carry a fixed 16-byte block. A count here is never above a handful,
  so the magnitude separates them cleanly: `byte21 <= 16` gives the run in 76 of 76
  bodies, `byte21 > 16` gives the block in 31 of 37.
- The complete rule:
  `head = 36 + 5*body[14] + (0 if body[17]==0 else 7 + 5*body[21] if body[21] <= 16 else 16)`.
  It predicts the reference in **3,875 of 3,903** applicable bodies, and the
  population it cannot reach at all drops from 62 to **14**.
- Searching for a *count* in those bodies found nothing above 80% under
  `base + width*byte` for base 0/7/12 and width 1/5. The answer was not a count --
  it was a fixed block selected by how big a byte is. *When "find the count" stops
  working, ask what the byte is when it is not a count.*
- Why byte 21 was invisible before: in the single-run family it is one of the 16
  **constant zero** bytes of the fixed head, so the second term vanishes and the
  general rule reduces to the special one. *A count that is zero in the population
  you are looking at is indistinguishable from padding.*
- **Every one of `0x0A`'s 4,158 bodies is now in a named category.**
  **3,875** have their `0x0B` reference placed by the head rule; **255** carry no
  reference at all, which the 65-vs-69 tail length explains as an absent optional
  field; and **28** are a residue the rule cannot place.
- The 28 are characterised, not just counted: their `body[14]` takes values like 35
  and 61 that are not counts (the implied extra comes out negative), `body[17]` is
  zero in 7 of them even though the head is long, and their actual head offsets
  cluster at 48, 51, 53, 54 and 59. A fourth shape, or variant bodies.

## `0x0A` IS CLOSED: the reference is a counted array, and the count is always right

```
u32 count
count x u32  -- type 0x0B object ids, four bytes apart
```

- **The word immediately before the first reference is a count, and it equals the
  number of references that follow in ALL 3,903 bodies that carry one.** Zero
  mismatches. Run lengths: 1 in 3,565 bodies, 2 in 271, 3 in 58, 4 in 5, 6 in 4.
- **Numeric type `0x0A` now has no unexplained bodies**: 3,903 counted arrays plus 255
  carrying no reference is its whole population of 4,158. The residue that stood at
  28, then at 3, is **zero**.
- **This supersedes the three-branch head rule and the two end anchors rather than
  competing with them.** Each was locating the first element of an array whose length
  it had no way to see; where they disagreed or reached nothing, the array was simply
  longer than one. The 28-body residue and the 3 that survived the anchors were
  bodies with 2 and 3 references.
- The gate is equality, and it also requires the run lengths to vary: a corpus where
  every array held one element could not tell a count from the constant 1 -- the same
  trap that left `0x0B`'s element count untested.
- *Three separate rules, each partly right, were describing one simpler thing. When
  rules accumulate around a field -- a head rule with three branches, then two end
  anchors, then a residue -- suspect that the field is a different shape, not that
  the rules need a fourth case.*

### The end anchor takes the 28-body residue down to 3

- **The reference sits at one of a small set of distances from the END: `-69` in
  3,707 bodies and `-73` in 288.** The head rule works from the front and needs three
  of the body's bytes to be counts; the anchor needs nothing, so it reaches what the
  head rule cannot.
- **Combined, the type is accounted for: 3,875 placed by the head rule, 25 more by
  the anchor alone, 255 with no reference at all (the absent optional field), and
  three left.** The 28-body residue is now **3**.
- **The control is the whole evidence, and it is perfect.** A fixed distance from the
  end lands on *something* in every body, so a hit count says nothing. Every distance
  within five bytes that is *not* an anchor -- `-64` to `-68`, `-70`, `-71`, `-72`,
  `-74`, `-75` -- names a type `0x0B` object in **zero** bodies.
## The hierarchy is carried TWICE: a parent field inverse to the reference graph

- **Numeric types `0x02`, `0x05`, `0x06`, `0x07` and `0x09` name their owner at a
  fixed front offset** -- 8 for all but `0x02`, which uses 22.
- **Over 199,445 checkable cases the child's declared parent names the child back,
  with ZERO disagreements**, across 13 type pairs: `02`->`05` 129,413, `07`->`07`
  28,425, `05`->`06` 17,572, `05`->`07` 7,138, `02`->`07` 6,881, `06`->`07` 3,653,
  `09`->`07` 3,308, and smaller.
- The two readings come from **entirely different bytes**: the parent field is one
  word at a fixed offset, the reference graph is framed from each body's own counted
  runs. Their agreeing is the strongest cross-check this format allows, and it is
  gated as equality rather than a rate.
- **Two offsets the sweep also found are NOT parents, and the inverse test is what
  established that.**
  * `0x04` at offset 1 names a `0x03`, and the graph has `0x04` naming `0x03` too --
    the **same** direction, so it is that edge and not its inverse. 22,317 of its
    22,335 cases disagreed.
  * The music types at offset 9 are likewise downward.
- *A field that names a plausible object is not a parent until something independent
  says which way it points.* Both of these look exactly like the real parent fields
  and are not; nothing but the inverse test separates them.

## CORRECTION: the music offset-9 reference was already known

The previous two entries presented the music parent at front offset 9 as a
discovery. **It was not.** The reader has censused it all along as
`musicHeadReferences`: 7,084 bodies at offset 9, 242 at offset 5, selected by byte 2,
7,326 of 7,331 resolved. I rediscovered a field the report prints every run.

What the sweep did add, and what stands:
- the **non-music** parent fields, which are new;
- the **inverse test**, which is new and is what tells a parent from a child;
- the target types and forest shape of the music relation, which the existing census
  records the offset of but not the structure.

*Before presenting a located field as new, grep the reader for the offset.* The
sweep's value was the types nobody had swept, not the one already covered.

## THE MUSIC HIERARCHY: every music type has a parent at front offset 9

**All four music types name another object at front offset 9**, and the targets
chain:

```
0x0A --(3,461)--> 0x0D --(2,321)--> 0x0C --(716)--> 0x0C
  |                                   ^
  +--------------(586)----------------+
```

- Coverage: `0x0A` 97% of its bodies, `0x0C` 96%, `0x0D` 95%. Over the whole music
  corpus **7,084 of 7,331 objects (96.6%) name a parent**, 192 have none, 55 name one
  in another bank.
- Walked per bank: **zero cycles**, depth to **9** with a mode of 4, and **1,538 of
  3,066 parents named by several children** apiece (up to 16+).
- **That is the shape the `0x08`/`0x12` relation has** -- a forest, child-to-parent,
  many children per parent -- in an unrelated family of types, at a different offset,
  and spanning three types rather than one. What it means is still not claimed; that
  the pattern recurs is the finding.
- **`0x0B` completes the picture from the other side**: 2,713 of its 4,325 bodies
  name a `0x0A` at front offset **83**, which is the reverse of the `0A`->`0B` edge
  the head rule and end anchor place. The mutual music edges measured earlier are that
  pairing, seen from the aggregate.
- The sweep that found all of this is one measurement: **for each type, which front
  offsets carry a reference in more than 30% of bodies?** It took minutes and answered
  a question three previous passes had got wrong by measuring from the end.
- **How it was found, and it corrects the framing of the previous entry.** The census
  measures distance from the **end**, and from the end `0x0C` looks entirely unlocated
  -- 3,757 distinct distances for 9,634 references. Measured from the **front** it is
  3,193 distinct offsets, just as scattered, **except that one offset carries 716 of
  them.** A type can be unlocated in aggregate and still have a located field; the
  aggregate hides it.
- *Measure locality from both ends. A field at a fixed front offset is invisible to an
  end-distance census whenever body lengths vary, and every type here has variable
  bodies.*
- For the record, `0x0A` is more concentrated from the front too: **32** distinct
  front offsets against 77 end distances. The end anchor at `-69` is real and
  controlled, but the front is where these references are actually placed.

## `0x0C`'s list is LOCATED: a counted array at `32 + 5 * body[14]`

```
body[14]                 -- a count of five-byte optional fields
u32 count   at 32 + 5*body[14]
count x u32 at 36 + 5*body[14]   -- object ids
```

- **704 of the 704 arrays found there resolve completely** -- every entry naming an
  object in the same bank. 38 bodies have a count outside 1..64 and are not tested.
- Lengths spread 1 to 9+: `2`:270, `3`:148, `1`:80, `9`:70, `4`:60, `5`:24, `7`:22,
  `6`:20, `8`:10. Targets: `0D` 1,942, `0C` 644, `0A` 394.
- Selector values: 0 in 595 bodies, 1 in 122, 2 in 23, 6 in 2.
- **The control is total: 0 of 4,928 rival attempts resolve.** Read at base 28, 30,
  31, 33, 34, 36 or 40 the same test never even finds a usable count, let alone an
  array that resolves.
- **Base and step are settled by different evidence.** The base by resolution -- 32
  works and its neighbours find nothing. The step by *coverage* -- a step of 5 finds
  an array in 704 bodies where 0, 4, 6 and 8 find one in 564, and the 140 extra are
  exactly the bodies whose selector byte is nonzero. *A step that did not match the
  data would not reach more bodies; it would reach the same ones and fail on them.*
- This **locates a field**, not the type. Most bodies still carry references after
  the array -- 9 or more in 246 bodies, and 4,928 references in total across the type,
  targeting `0D` 5,470 times, `0A` 1,306 and `0C` 1,214.
- **ELIMINATED: there is no second counted array.** Applying the same step-back move
  after the first array appears to work in 438 bodies -- until you look at the counts.
  **Every one of them is 1**, and the run after it is length 1 in 702 of 704 bodies.
  A count of one before a single reference is satisfied by any word holding 1, so the
  match is worth nothing. The gap from the array's end to the next reference is also
  large and variable -- 99 bytes in 406 bodies, 126 in 240, 107 in 32 -- so whatever
  holds the remaining references is not adjacent to the array.
- **The remaining references are NOT scattered either -- they start at a computed
  position.** Measuring the first reference after the array as
  `offset - 4*arrayLength - 5*selector` gives **135 in 406 bodies and 162 in 240** --
  **646 of 704, or 92%** -- with every other value in single digits. So the next block
  begins at `135 + 4n + 5k` or `162 + 4n + 5k`, the two differing by 27.
- **The selector is INSIDE the region, at `arrayEnd + 96`.** Dumping the 99- and
  126-byte regions side by side shows them **identical for 96 bytes**, then diverging:
  a flag byte, and 27 further bytes when it is 1. So
  `nextBlock = arrayEnd + 99 + 27 * flag`, holding in **646 of 686** bodies (94.2%).
- *That is why scanning the body header found nothing.* The only "pure" bytes there
  were 9 to 12 at 86%, and those **are** the parent reference -- objects under a
  common parent sharing a layout, not a flag. **A selector that turns out to be an
  identifier is not a selector, and a selector need not be in the header at all.**
- **The multiplier stops at 1.** Flag 2 exists in 14 bodies and puts the next block at
  155, 167 or 215, not the 153 a repeat would predict. So it gates one block rather
  than counting them, and the gate refuses values above 1 instead of extrapolating.
- The 40 misses are all flag 0 with gaps of 107, 190 or 355 -- the rule places the
  block, but something else can lengthen the region further.

### What the 96-byte region holds, and a constant shared across three types

| offset | distinct | commonest |
|---|---:|---|
| `+0` | 11 | `0` in 674 |
| `+4` | 13 | **`0x408F4000` = float 4.4766 in 670** |
| `+8`, `+12` | **1** | constant `0` in all 704 |
| `+16` | 12 | **`0x42F00000` = float 120.0 in 670** |
| `+20` | 4 | bytes `04 04 00 00` in 666 |
| `+84` | **1** | constant `0` in all 704 |

- From offset **27** the region carries a run of 32-bit words -- 4, 1, **-1**, 1,
  **-1**, 0, 4, 0, 7, 0, 1 -- so the region is **not aligned throughout**: an aligned
  prefix, then a run starting at a 3-byte offset. Reading it as u32s from 0 gives
  nonsense like `0x01FFFFFF`, which is a misaligned view of `01 00 00 00 ff ff ff ff`.
- **`0x408F4000` is a constant shared across the music hierarchy and absent from its
  leaf**: `0x0C`'s region `+4` **670 of 704**, `0x0A`'s `+8` **1,565 of 4,144**, and
  it appears somewhere in **2,056 of 2,431** `0x0D` bodies -- but in only **4 of
  4,325** `0x0B` bodies.
- That is the same value that dominates `0x0A`'s float block and appears as the top
  value of its `+4` field. So a single authored default is reused by `0x0A`, `0x0C`
  and `0x0D` -- the three types that form the parent chain -- and not by `0x0B`, which
  hangs off it. Nothing here says what it means.
- *A constant's distribution across types is evidence about which types share a
  concept. It costs one query and does not require framing anything.*

**The region's internal layout, from where its sentinels sit.** The four-byte `-1`
values land at region `+35` and `+43` in **700 of 704** bodies, and **every one is at
an offset congruent to 3 mod 4**. The floats at `+4` and `+16` are at `0 mod 4`. Two
grids, three bytes apart, so:

```
5 x u32      at  0 .. 19     -- includes the 4.4766 and 120.0 constants
3-byte field at 20 .. 22     -- `04 04 00` in most bodies
18 x u32     at 23 .. 94     -- includes the two -1 sentinels at 35 and 43
1 byte       at 95
flag         at 96           -- gates the 27-byte block
```

- 23 + 4x18 = 95 exactly, so the 3-byte field at 20 is what shifts the grid and the
  region divides with nothing left over.
- **38 of the 96 bytes are constant across all 704 regions**, in runs at 7-17, 24-26,
  40-42, 49-50, 52-54, 57-58, 64-66, 73-74, 80-82 and 84-87.
**Read at the recovered alignment, the region's 23 words are legible:**

| offset | reading | evidence |
|---|---|---|
| `+4` | **float** | plausible in **704 of 704**; 4.4766 in 670 |
| `+16` | **float** | plausible in **704 of 704**; 120.0 in 670 |
| `+8`, `+12` | **constant zero** | 704 of 704 each |
| `+31`, `+35` | **`1` then `-1`** | 700 each -- a value/sentinel pair |
| `+39`, `+43` | **`1` then `-1`** | 700 each -- a second pair |
| `+27` | small int, 30 distinct | 698 of 704 are <= 64 |
| `+51` | small int, `4` | 558 |
| `+71` | `0x400` = 1024 | 646 |
| `+91` | `0x100` = 256 | 698 |
| `+23`, `+63`, `+75`, `+79`, `+83`, `+87` | zero in almost all | |

- The float test has its control built in: at `+4` and `+16` it passes **704 of 704**,
  and at `+0`, `+8` and `+12` -- the same grid, four bytes away -- it passes **none**,
  because those hold zero. Two float fields, not twenty-three.
- The two `(1, -1)` pairs eight bytes apart are the clearest structure in the region.
  Nothing here says what they select.

- *Misaligned-looking words are a symptom, not a fact. Reading this region as u32s
  from its start produced values like `0x01FFFFFF` and `0x00FFFFFF`, which are not
  values at all -- they are a `-1` seen through a three-byte shift. Finding where a
  known sentinel actually sits is the cheapest way to recover a grid.*
- So `0x0C` is better described than "a variable-length list": a parent at 9, a
  counted array at `36 + 5k`, and a further block at a position computed from the
  array's length. What that block contains, and what chooses 135 over 162, are open.
- *The move that found the array is the same move that produced this false positive.
  What separates them is the length spread: the first array's lengths run 1 to 9 and
  the second's are all 1. A counted-array claim is only as good as the variation in
  its counts.*
- It came from applying the move that closed `0x0A` -- find a reference, step back
  four bytes, look for a count -- to a different type. That move has now worked twice
  and failed once (the `0x0B` residue), which is a better record than any of the
  width-enumeration attempts.

## `0x0C` keeps its references in a list; `0A` and `0D` keep theirs in fields

Asked of a census the reader has published for many runs: **how many distinct end
distances does each edge kind use?** A reference read from a fixed field lands at the
same distance body after body; one inside a variable-length list lands wherever the
preceding content leaves it.

| source | edges | bodies | edges/body | distinct distances | **edges per distance** |
|---|---:|---:|---:|---:|---:|
| `0x0A` | 8,701 | 4,158 | 2.1 | 112 | **77.7** |
| `0x0D` | 6,173 | 2,431 | 2.5 | 162 | **38.1** |
| `0x0C` | 9,641 | **742** | **13.0** | **5,021** | **1.9** |

- Per edge kind the separation is total and has an empty middle: `0A`->`0B` 135.2,
  `0A`->`0D` 81.1, `0A`->`0C` 73.5, `0D`->`0A` 43.5, `0D`->`0C` 43.4 --- then nothing
  --- `0C`->`0C` 2.5, `0C`->`0D` 2.1, `0C`->`0A` 1.6.
- **So `0x0C`'s references are not at fixed offsets and `0x0A`'s and `0x0D`'s are.**
  That is why a fixed-offset rule was findable for `0A`->`0B` and has never been
  findable for anything out of `0C`: there is no offset to find.
- **Correction to the "about 13 per body" reading, which was mine and was wrong.**
  13.0 is a mean over a wildly skewed distribution: the **median is 4** and the
  maximum is **2,172**. Ten of the 742 bodies carry **5,217 of the 9,634 references**.
  Nor is it a list -- only **6 of 742** bodies have all their reference positions
  mutually 4-aligned, and the same id typically appears at **4** scattered positions
  (mean 5.5, max 74), at gaps like 111, 264 and 201 within one 703-byte body. So a
  `0x0C` body mentions a handful of targets repeatedly, rather than listing many.
- **The split itself survives that.** Excluding the ten outlier bodies takes `0x0C`
  from 1.9 to **3.7** edges per distance, still an order of magnitude below `0x0D`'s
  38.1 and `0x0A`'s 82.9. *Check whether a ratio is carried by a handful of rows
  before building on it -- and quote the median beside the mean whenever the maximum
  is three orders of magnitude above it.*
- **The two edges into type `0x11` are NOT classified.** 118 and 130 references across
  19 and 22 distances gives about 6 per distance, which is between the groups. A
  hundred-odd samples cannot say which side they belong to, and the first version of
  this gate failed on correct data by trying to force them. *A discriminator with an
  empty middle still needs a minimum sample size, or the small cases land in the gap
  and get assigned by the threshold rather than by the data.*
- Read off `edgeDistanceFromEnd` again. **Two findings in a row have come from asking
  new questions of an unchanged census rather than from new probes** -- alignment
  modulo four, and now distinct-distance counts. When a lead runs dry, re-read what is
  already published before collecting more.

### The rule is ALIGNMENT, not a list of anchor distances

- Enumerating anchors would have been fitting, and I nearly did it. Scanning every
  end distance shows **30** at which some body carries a `0x0B` reference, most with
  a handful of bodies: 81:9, 84:2, 85:4, 86:6, 87:6, 91:2, 112:2, 165:2. Adding those
  to an "anchor set" is just recording where the references happened to be.
- **The structure is that the distance from the end is 4-byte aligned.** 4,161 of the
  4,325 `0x0A` -> `0x0B` references -- **96.2%** -- sit at a distance congruent to 1
  modulo 4, with `-69` carrying 3,707 of them and the rest trailing off through 73,
  77, 81, 85, 89, 93, 97, 101.
- **Two controls, and both are needed.**
  1. *Aligned from the FRONT instead*: **47.7%**. Body lengths are spread across all
     four residues (2:1844, 1:1612, 3:635, 0:67), so the two questions are genuinely
     different and the end is the one that answers.
  2. *Every other music edge kind, measured identically in the same bodies*:
     `0C`->`0D` **3.9%**, `0C`->`0A` **4.5%**, `0D`->`0C` 14.7%, `0D`->`0A` 47.3%,
     `0A`->`0D` 43.0%. Corpus-wide 36.9%. So alignment is a property of **this edge**,
     not of the format or of the measurement.
- The generalisation I hoped for -- that all music references are end-aligned --
  **fails**, and its failure is what makes the `0A`->`0B` number mean something. *An
  attempted generalisation that fails is worth as much as one that succeeds: the
  cases it fails on become the control the original claim never had.*
- Read off `edgeDistanceFromEnd`, which the reader had been publishing all along.
  **The question was answerable from data already in the report**; no new collection
  was needed, only the idea of taking each distance modulo four.

- **A neighbouring offset is only a control if it is not itself part of the
  structure.** The first version of this gate scored `-73` as a control and failed on
  correct data. The head rule's own distance distribution -- 69, 73, 77, 82, 93, 125
  -- was already saying `-73` belongs to the family; I had the evidence and used it
  as its own refutation.
- **`u32@5` is a CROSS-PACKAGE reference, and it names numeric type `0x08`
  objects.** It is zero in almost every body; the 120 nonzero words take **four**
  distinct values and **none of them resolves inside its own package** -- which is
  why an earlier pass recorded it as "resolves nowhere". Joined against the whole
  corpus every one resolves: `0xF1339B46` (62), `0x4106E10A` (26), `0xEB239E75` (24)
  and `0xFD63C75F` (8) are all type `0x08` objects, plus one `0x0B` in a variant.
- **The lesson: "resolves nowhere" may mean the wrong id set was used.** The reader
  works per package, so a package-local set cannot see a cross-package edge. Before
  concluding a word is not a reference, try the corpus-wide set.
- **`float@16` in the fixed head is a bounded, whole-numbered value with a -96
  floor.** Range **[-96, 98]**, whole in 3,146 of the 3,594 in range, modes 0.0
  (1,622), 98.0 (192), 2.0 (176), -10.0 (175), -15.0 (122). The floor is the same
  -96 the `0x08`/`0x12` middle block carries. Gated at 1,856 nonzero whole values
  against an **overlapping** control window at offset 14 that carries **0**.
- The control overlaps the field by two bytes on purpose -- a window sharing most of
  its bytes is the hardest one to beat -- and it had to be judged on *both*
  properties, not just the range: at offset 14 the bytes read as a denormal near
  zero, which is trivially inside any band. **A range test alone accepts everything;
  the control has to be scored exactly like the candidate.**
- **What the 20 varying bytes of the fixed head actually hold** (conditioned on
  `byte17 == 0` and the rule confirmed, 3,744 bodies): `u32@5` takes only **5
  distinct values** and is zero in 3,624 -- an enumeration or a rare id, not a
  reference (it resolves nowhere). `u32@9` is the `0x0C`/`0x0D` reference.
  `byte@13` is constant zero. `byte@14` is the element count (0/1/2). `byte@15` and
  `byte@16` are small (0, 2, 5, 6). `byte@18`, `@19`, `@20` have 21, 23 and 8
  distinct values and look like parts of one 32-bit value. `byte@23` and `@24` are
  mixed. `byte@28` and `byte@33` are **booleans** (0/1, split 1,888/1,856 and
  3,146/598). `byte@32` takes 0, 1, 2, 3.
- **Twenty bytes past the reference sits an AUTHORED float, and its values look
  like tempo.** Over the 3,744 conditioned bodies it is finite in all of them,
  **whole in 3,727** (99.5%) and inside `[50, 200]` in 3,435 (91.7%). Its range is
  55 to 190 and its modes are **120.0** (1,557), 130, 110, 90.
- A float that is an exact integer 99.5% of the time is **authored, not computed** --
  that is the gated claim. That its range and modes are those of musical tempo, in
  the music object hierarchy, is recorded as an **observation**: it is the obvious
  reading and nothing here proves it.
- **`tail+8` is the opposite kind of field, and that contrast is the proof the
  offsets are right.** Whole in **202 of 3,744** against `tail+20`'s 3,727. Over the
  tail-69 subset it is whole in **0 of 3,321**. Two adjacent floats behaving that
  differently is what a real field boundary looks like; a reader slicing one
  quantity at two arbitrary places would get similar behaviour from both. The gate
  checks the contrast, not just the field.
- `tail+8` runs 3.366 to 6.533 with 85 distinct values (mode 4.477) and is **not a
  function of `tail+20`**: 12 of the 72 distinct `tail+20` values carry more than one
  `tail+8`, and no ratio, product or log relation between them is constant. Whatever
  it is, it is independent.
- **The tail's first 29 bytes are now fully accounted for** (tail-69 bodies, 3,321):
  `+0` the `0x0B` reference; `+4` a `u32` zero in 1,886 and taking 50 other values;
  `+8` the never-whole float; `+12` and `+16` `u32`s zero in 3,317 of 3,321; `+20`
  the authored float; `+24..27` four bytes reading `04 04 <0|1> 00` -- only **5
  distinct** 32-bit values across the corpus, so a packed flag record and not a
  number; `+28` constant zero. Seven 32-bit fields and a byte.
- **The 4-byte insertion sits immediately after the reference, before the float.**
  Tracking two fields by their signatures across the two tail lengths pins it: the
  never-whole float moves from `+8` to `+12` in **all 217** long-tail bodies, and the
  authored float from `+20` to `+24` in **all 217**. The reference stays at `+0`. So
  everything from `+8` onward shifts by exactly 4 and the extra field lands in the
  `+4..+7` region.
- That also rules out my own guess. I expected the insertion at `+12` or `+16`
  because those are zero in 3,317 of 3,321 -- the shape an optional field usually
  hides in. It is not there. **A field's being almost always zero says it could be
  optional, not that it is**; tracking a field with a distinctive signature across
  the two populations answers the question and a zero-rate does not.
- `+4` is also the one field whose behaviour differs between the two: zero in 1,886
  of 3,321 short tails and **never zero** in the 217 long ones.
- **`tail+4` is a 32-bit FIXED-POINT FRACTION of one.** Its nonzero values land on
  simple rationals to within a few parts in 10^10: `0x55555555` = 1/3,
  `0xAAAAAAAB` = 2/3, `0x92492492` = 4/7, `0xE8BA2E8B` = 10/11, `0x89D89D8A` = 7/13,
  `0x71C71C71` = 4/9, `0x0F0F0F0F` = 1/17, plus 27/49, 13/19, 4/23, 20/37. Over the
  corpus **1,399 of 1,804** nonzero values match a denominator <= 64; the same test
  on `tail+8` (a float) matches **114 of 3,614**. A 24x gap.
- Read it as bytes or as a rational, never as an integer or a float: as a `u32` it
  looks like arbitrary large numbers, and as a float it is nonsense. That is the
  second field in this tail whose meaning only appears in the right representation,
  after `tail+24`'s packed `04 04 <0|1> 00`.
- **The tail's optional 4-byte field is localized, and it is not counted.** Aligning
  the 3,321 tail-69 bodies against the 217 tail-73 bodies: from the **end** their
  constant profiles agree at **every one of 69 positions**, so the longer tail is the
  shorter one with four bytes inserted, not a different shape. From the **front**
  they agree to `tail+28` and diverge at `tail+29`. So the extra four bytes sit
  **within the first 29 bytes after the `0x0B` reference**.
- The constant word `0x5BBBD648` moves with the end, as expected: bytes 187 and 91
  sit at `tail+58,+59` in the 69-byte tails and at `tail+62,+63` in the 73-byte ones.
- **No byte inside the tail counts the extension either.** Best match for
  `tail == 69 + 4*byte` over the tail's own 69 positions is `tail+30` at 3,492 of
  3,585 -- but only **171 of the 264** bodies where the count would be nonzero, which
  is the giveaway. The high total is carried by zero bytes matching a zero count.
  *Always report the informative subset alongside the total.*
- **No single head byte predicts the tail length.** Tails are 69 (3,321), 73 (217),
  77 (44), 82 (32) -- steps of 4 -- and `69 + 4*byte` matches at best **2,829 of
  3,744** (byte 33), with byte 32 at 2,168 and byte 16 at 2,783. So the tail's
  optional fields are counted from **inside the tail**, not from the head. Do not
  spend another pass looking for a head byte that sizes the tail.
- **Conditioning on the anchor makes the tail legible.** Restricted to the 3,419
  `0x0A` bodies with exactly one `0x0B` reference and it at -69, **21 of the last 69
  byte positions are constant** -- against **6 of 101** over the unconditioned
  population. Constants include the word `0x5BBBD648` at -13, `0x00000002` at -30,
  `0x0298DF12` at -26, `0x02` at -23 and -30, and zero runs at -27..-29, -39..-42,
  -48..-49.
- The varying positions in that window fall in runs of **8 and 4 bytes** (-2..-9,
  -15..-22, -31..-38, -43..-46), i.e. whole 32-bit fields. So the region from the
  anchor to the end looks like a fixed record with `u32` slots, and that is where a
  `0x0A` framing attempt should start -- backwards from the end, conditioned on the
  anchor, never forwards from the head.
- **The two edges that looked the same are eliminated.** `0x0D`->`0x0C` has an edge
  total of exactly 2,431 -- the `0x0D` body count, which is what made it look like a
  bijection -- and reaches **578 of 742** objects, 382 of them repeatedly.
  `0x0C`->`0x0D` reaches every one of its 2,431 targets but reaches **1,628** of
  them twice.
- So a one-to-one claim needs **all three** measurements and an edge total supplies
  none of them: distinct targets equal to the population, no target reached twice,
  and the edge total equal to both. Two of the three neighbours here pass one or two
  of those conditions and fail the rest.
- The method that works when a type will not frame: **do not look for the reference,
  offer every word.** Object ids are sparse enough that the id space does the
  discrimination. It found three references per `0x0D` body where framing found one.
- **This is the first semantic recovery inside the music types**, and the way in was
  anchoring from the **end**. Their heads are variable -- only three byte positions
  from the front take a single value across the corpus -- but the tail is not:
  `0x0A` carries the constant word `0x5BBBD648` thirteen bytes from the end in all
  4,158 bodies; `0x0C` holds the constant bytes `0x64` (100) at -2 and `0x32` (50)
  at -4 in all 742; `0x0D` has **30** constant byte positions in its last 120, and
  every one of them is `0x00`. *When a type's head resists, tabulate from the end.*
- **Type `0x0D`'s body lengths are `165 + 34a + 5b`.** 2,273 of 2,431 fit, 130 do
  not, 28 are ambiguous; the modal `(a, b)` are `(1,0)` 906, `(1,1)` 410, `(2,0)`
  352, `(2,1)` 239, `(1,2)` 78, `(0,0)` 41. The 5 matches the optional field
  `0x0B`'s entry widths also show (84/89, 132/137, 168/173).
- **The arithmetic check that makes this worth believing.** 34 and 5 are coprime, so
  every `d >= 132` is representable for free (Frobenius number 131) and a fit there
  means nothing. Only **91** of the 2,431 bodies are in that range; **2,210** fit
  uniquely with `d < 132`, where roughly half the integers are representable at all.
  And it is type-specific: `0x0A` does **not** fit this shape (3,807 of 4,158 fail
  against base 101), so it is not just small-coefficient coverage.
- **The bytes do NOT back the "34-byte repeating element" reading, and it is
  withdrawn as a structural claim.** Each length group is internally very uniform --
  157 of 165 positions take a single value in the 165-group, 159 of 199 in the
  199-group -- but the groups do **not** align with each other. Comparing their
  fixed-position profiles gives only 70/89 to 91/141 agreement end-aligned and
  similar front-aligned, where a base-plus-inserted-element layout would give
  agreement everywhere both profiles are constrained.
- A trap inside that measurement: restricting the comparison to a window where both
  profiles happen to be constrained gives **1.0** at several different insertion
  points, including two that contradict each other. Score an alignment over the
  whole overlap, never over a window chosen after seeing the data.
- So `165 + 34a + 5b` is a real regularity **of the lengths** and nothing more. The
  length groups are different shapes, not one shape with a repeated block.
- **Count the constants, and do not read a distinct-value count as a byte value.**
  The first version of this tabulation printed a constant as two hex digits and a
  varying position as its number of distinct values, in the same column. A position
  with 64 distinct values printed as `64` and was read as the constant byte `0x64`.
  `0x0D` has no `100` or `50` anywhere near its end -- that was the bug, not the
  data. Print a sigil for varying positions.
- The census is in the maintained reader and gated, but the gate **skips when no
  names are supplied**: the corpus gate's reader run does not load the metadata
  literals -- the named-reach tool does -- and a census with nothing tested means
  the question was never asked, not that the answer is no.
- **The twelve-byte curve record is NOT in the music types.** Scanning every offset
  of all 7,331 bodies for a `u32` count followed by that many `(float, float,
  interp <= 9)` records finds it in 33 of 4,158 `0x0A`, 18 of 742 `0x0C` and **0 of
  2,431 `0x0D`**. At those rates, over a scan of every offset, these are chance
  fits. The record is in `0x08`, `0x12` and `0x0B`; the music types are the first
  miss, so the cross-type heuristic has a boundary.
- **The trap that nearly made this a finding, and it is the second time this
  session.** The same scan without a variation requirement reports the record in
  **2,423 of 2,431** `0x0D` bodies. Every one of those is a run of **zero bytes**:
  zeros are finite floats and zero is a valid interpolation code, so a zero-filled
  region satisfies every bound for free. The earlier music-type tail match failed
  the same way with `entries_0`.
- **General rule, now written down because it has cost two false results.** Before a
  structural test's hit rate means anything, check it against the degenerate input
  that satisfies it trivially -- a run of zeros, a count of zero, a single-element
  list. If the degenerate case passes, the rate is measuring how much of the corpus
  is degenerate, not how well the structure fits.
- **Two fresh eliminations on the music types (2026-09-15). Read these before
  trying the next idea.**
  (a) *Their head is not a fixed skeleton.* Tabulating every byte position across
  the whole corpus, only offsets 0, 3 and 4 take a single value in `0x0A` and
  `0x0D` (plus offset 34), and `0x0C` has none at all in its first five. A head read
  off one body -- "nine zero bytes, then the reference, then zeros, then a flag" --
  looks convincing and is over-fitting. Tabulate positions first.
  (b) *They do not share the `0x08`/`0x12` tail.* The tail block fits 2 of 7,331
  bodies. The entry-run-plus-five-zeros tail appears to fit 2,344 `0x0D` bodies --
  and every one of those is `entries_0`, which is just "the last six bytes are
  zero". A count of zero makes that test vacuous; check the count distribution
  before believing a tail match.
- **Do not try to locate the frame by searching for a start offset.** Every music
  body admits many offsets at which the node frame parses cleanly -- typically 2
  to 12, and up to 12 for `0x0B`. The frame is permissive enough that "it parsed"
  carries almost no information here, which is a stronger version of the ambiguity
  that type `0x0E` had. A structural predictor is required, as with the `0x0E`
  flag byte.
- **Types `0x0A`, `0x0C` and `0x0D` share one head, and each names exactly one
  same-bank object.** Body byte 2 selects where the 32-bit word sits: zero puts it
  at offset 9, nonzero at offset 5. Under that rule 7,326 of 7,331 bodies resolve
  -- all 4,158 `0x0A`, all 2,431 `0x0D`, and 737 of 742 `0x0C` -- with zero
  unresolved, zero null, and no unobserved discriminant.
- The five exceptions are all `0x0C` bodies whose **first** byte is 6 rather than
  0. That is a different head shape: their offset 9 is null and their offset 5
  names nothing, so neither branch applies. They are excluded from the claim and
  **counted in the published total** rather than dropped, so the denominator stays
  the whole population. `0x0A` and `0x0D` are byte 0 == 0 in every body. Observed byte 2 values are 0 (6,368), 1 (194) and 2
  (27); anything else must fail closed, because a fourth value has no branch.
  This is gated inside the reference-graph report and is a Layer-4 identity fact
  only: it says nothing about direction, containment, or meaning.
- **That folding is load-bearing, and getting it wrong cost 46 names.** The first
  version of this lane carried its own `fnv1_utf16` without the case fold, even
  though `identifiers.audio_hash_generator_compute` already mirrored the shipped
  implementation correctly. 46 shipped literals contain capitals -- every
  `Au_UI_Button_*`, `Au_UI_Event_*` and similar -- and all of them were missed.
  Correcting it took the lane from 151 to 203 named objects, 63 to 109 reaching a
  source, and 57 to 83 reaching media. **Never re-implement a hash this repo
  already mirrors**; the duplicate is what drifted, not the original.
- The falsification property survives the correction and is stronger for it: all
  203 matches still land on type `0x04` and none anywhere else.
- That corrects an earlier reading in this file. Fixing the word at offset 9 for
  every body resolves only 97.3% of `0x0A` and 95.5% of `0x0D`, and the shortfall
  looks like missing references. It is not: those bodies put the word at offset 5,
  and the byte that says so is right there. **A rule that is "nearly always right"
  is worth one more look for the byte that makes it always right** -- the same
  lesson type `0x0E` taught. The residue really did name nothing in any bank --
  which is a fact about those words only. **Do not read it as "no cross-bank
  evidence anywhere"**, as this note once did: the numeric type `0x03` target word
  crosses banks routinely, and that is recorded above.
- Type `0x0A` also carries a *second* group of references: a counted run of
  same-bank object ids, and byte 14 is a count of five-byte elements -- the run
  starts at exactly `32 + 5 * byte14` for the clean cases. This run is **not**
  gated and is not in the reference graph, because it cannot be located in 255 of
  4,158 bodies. But a fit of `base + w14*byte14 + w17*byte17` only reaches 96.8%,
  and byte 17 takes values like 95 and 110, so it is not a second count and the
  correlation is partly spurious. At least one further variable-length interior
  region is unisolated, so **no `0x0A` layout is established and no lane exists.**
- **Type `0x0B` opens with a counted run of 14-byte source records, and they share
  numeric type `0x02`'s plug-in id space.** Layout of the head: one byte, a 32-bit
  record count, then that many records of plug-in id (`u32`), stream-type byte,
  source id (`u32`), and five further bytes. All 4,447 records across 4,325 bodies
  carry a plug-in id type `0x02` also uses -- only `0x00040001` (3,506) and
  `0x00140001` (941), both from type `0x02`'s seven-value set.
- **Every field of that record is now named, from outside the bytes.** The leading
  byte is `uFlags`, the count is `numSources`, and the record is Wwise's
  `AkBankSourceData`: the five trailing bytes are `uInMemoryMediaSize` (`u32`) plus
  `uSourceBits` (`u8`). Two independent sources agree with the byte-derived framing
  rather than merely permitting it -- wwiser's v150 definitions give the field
  sequence, and the Wwise 2023.1.19 SDK decodes the plug-in ids. Verified against
  13 MusicTrack bodies in `init_banks.pck`, every one ending its source run at
  offset 19, which is exactly the 14-byte stride this note derived.
- **The plug-in ids are codec ids, and they name the audio the banks ship.** The
  packing is `(codecID << 16) | (companyID << 4) | pluginType`, so `0x00040001` is
  `AKCODECID_VORBIS` and `0x00140001` is `AKCODECID_AKOPUS_WEM` -- Vorbis and
  Opus-in-WEM. `companyID 0` is Audiokinetic throughout and `pluginType 1` is
  `AkPluginTypeCodec`, so every source in this corpus is a **built-in codec**: no
  third-party or premium plug-in is referenced anywhere, which is why the base SDK
  is sufficient and no plug-in bundle is needed.
- Why that is evidence for the 14-byte stride rather than a coincidence: plug-in
  ids are sparse 32-bit values, not small integers, so a wrong stride would put
  arbitrary bytes in that field and they would leave the set immediately. The
  records *after the first* are what actually test it -- 106 bodies declare 2 to 4
  records, contributing 230 such records, and every one landed in the set.
- **Every `0x0B` body ends with the 32-bit word 100** -- 4,325 of 4,325, no other
  word observed. Gated on equality with the body count, not a rate, because one
  exception would mean the reader is looking at a different layout.
- **After the record run comes a 32-bit entry count, that many variable-width
  entries, then that terminator.** Counts run 0 to 8 (4,019 bodies declare one).
  The first entry's leading word is 0 in 4,295 bodies and 1 in 26, and its *second*
  word is one of the body's own declared source ids in all 4,321 bodies that
  declare an entry -- the four declaring zero carry no echo, which is the control.
  What fixes the entry start is that **no other offset in a 48-byte window echoes
  a source id even once**; source ids are sparse 32-bit values, so this is not
  something arbitrary bytes produce. No body carries more echoes than it declares
  (4,261 match exactly, 64 carry fewer because later entries, being
  variable-width, do not land on four-byte boundaries).
- **Retraction.** The earlier reading of this tail as fixed 88-byte entries is
  withdrawn. It called 2,221 bodies exact because the run finished at EOF -- which
  it could only do by swallowing the terminator. The 88 was the 4-byte count plus
  the *modal* 84-byte entry, not a stride; entry widths are 84, 89, 120, 132, 168,
  137, ... The "248 entries name something other than a declared source" figure
  came from that same wrong stride and is withdrawn with it.
- **Inside a `0x0B` entry, three more fields are count-shaped.** Tabulating every
  32-bit slot across the 4,019 single-entry bodies (the entry is everything between
  the entry count and the terminator):
  `u32@0` is the flag (0 in 4,005, 1 in 14), `u32@4` is the source id, **`u32@8` is
  zero in all 4,019**, and then `u32@44` is 1/2/3 and never 0 (3,891/113/14),
  `u32@48` is 0/1/2/3 (2,833/903/253/...) and `u32@56` is 0/3/4/... -- the same
  "mostly one small value" shape that turned out to be a count three times in the
  `0x08`/`0x12` layout.
- **The elements they count are variable-length, so this is not yet a frame.**
  Solving `48 + c44 * w == entryWidth` gives a unique `w` for 3,618 of 4,019 bodies
  but `w` itself ranges over 36, 41, 43, 47, 72, 77, 84, 89, 96, 108 -- so `u32@44`
  counts something whose size is decided inside it, exactly like the tail's units.
- **The same twelve-byte record the `0x08`/`0x12` tail carries is inside `0x0B`'s
  entries too**, and it is now censused and gated. Where `u32@56` is nonzero,
  `u32@60` is a record count and the records start at offset 64: two floats and a
  32-bit interpolation code. Over the corpus: 775 entries of 4,019 carry them, 3,124
  declare none, 120 have an unusable count, **0 run past the end**, and the 1,759
  records' codes are **0 through 9 with no gaps and nothing above 9**.
- That contiguous ten-value enum is the discriminator. A 32-bit field read at a
  wrong offset would be noise, so the gate refuses any code outside a small range.
  The first float takes 0.0 (793), 0.11, 0.13, 0.1, 2.33, ... -- an observation, not
  a claim; nothing here establishes what it measures.
- So the twelve-byte curve record is now confirmed in **three** numeric types --
  `0x08`, `0x12` and `0x0B`. When a new type resists, look for it.
- Two regularities worth carrying in: entry widths come in pairs five bytes apart
  (84/89, 132/137, 168/173) with identical counts, so some five-byte field is
  optional; and once a base is chosen the remaining widths differ by multiples of 12,
  which is the record size the `0x08`/`0x12` tail also uses.

## The typed v150 parse: effects, buses, and the NodeBase tail

Above the anonymous body framing recorded above sits a *typed* v150 read of the
same objects, which resolves fields by name because the Wwise 2023.1.17
serialization order is known. Everything here is **authored serialized data**: none of it is
runtime DSP, effective inheritance, branch choice, or audibility. Per-build
addresses, symbol hashes and changing row counts belong to the generated Audio
evidence and to `reports/story/recovery/audio/`, not here.

### Effect slots and the built-in plug-in parameter blocks

- The v150 HIRC parser publishes **exact NodeBase effect slots and output-bus
  IDs**. Effect definitions retain physical PCK/bank scope, built-in plug-in
  class identity, and parameter hashes.
- Fingerprinted shipped `SetParamsBlock` layouts decode exact authored base
  settings for **Gain, Delay, Compressor, Expander, three-band Parametric EQ,
  Meter, Matrix Reverb, Pitch Shifter, Harmonizer and Stereo Delay**. Guitar
  Distortion exposes three pre-EQ and three post-EQ bands plus distortion type,
  drive, tone, rectification, output gain and wet/dry mix.
- The v150 **FX-slot bit vectors** are decoded: direct NodeBase slots expose
  authored bypass, ShareSet and rendered bits, while Audio/Aux Bus slots expose
  the bypass/ShareSet subset. **These flags are not runtime DSP/audibility
  proof** and remain separate from node-level `bypassAll` and dynamic BypassFX
  controls.
- **RoomVerb** exposes all 37 public authoring controls and all 31 ER pattern
  names. Its 11 additional private algorithm-tuning IDs retain exact values with
  native-use roles: five feed early-reflection tap-pattern synthesis (endpoint
  pairs plus seeded per-tap variation, then ER-grid normalization), one feeds
  six-channel coefficient derivation, two feed a seeded secondary
  reflection-pattern generator, and three remain **name/read-unresolved** in the
  audited native path.
- **Convolution Reverb** exposes its 13 public runtime controls plus exact
  impulse-response plug-in media IDs. Its two private rows retain exact native
  forwarding evidence: SetParam 34 reaches a wrapper field and both convolution
  processing paths, while serialized byte 56 reaches a second wrapper field and
  runtime state. **The current CPU consumer does not expose a read of the
  forwarded scalar**, so public names and final DSP roles remain fail-closed,
  and **IR IDs are not emitted as playable WEM leaves**.
- **Mastering Suite** exposes its four output-device modules: six EQ bands, four
  multiband-compressor bands with crossover/link controls, overall plus 12
  serialized channel gains, and limiter mode/threshold/timing/output/link
  values. Its SetParam IDs **100 and 200 remain exact unnamed codes**: binary
  evidence pins them to native storage fields, but **no direct read is observed
  in the audited runtime region**, so the UI labels them storage-only and keeps
  those definitions visibly partial rather than inferring processing-order or
  profile semantics. The 12 channel gains map exactly from serialized offsets
  235..279 to consecutive native fields at stride 4, while **speaker names
  remain unresolved**.

### The Bus forest, typed and complete

- Type-8/type-18 HIRC objects publish the **complete 279-bus parent hierarchy**
  -- 276 parent edges and three roots -- which is the typed reading of the
  `0x08`/`0x12` forest recorded above.
- Typed v150 `CAkBus` parsing consumes the property, positioning, Aux, duck and
  bus-state fields **before** InitialFX, and proves the serialized effect count
  on all 279 buses: 128 have an explicit zero-count list (including the 50 Audio
  Bus and 11 Auxiliary Bus rows previously recovered by sibling correlation),
  while 151 carry 247 decoded non-empty slots.
- The Bus parser continues through the v150 suffix **in its actual order --
  InitialRTPC before StateChunk** -- and parses all 279 Bus payloads exactly.
  Parameter labels use the current RTPC table; out-of-range IDs such as
  `0x1802`/`0x1804` remain **explicit custom/internal numerics rather than
  guessed DSP names**.

### The NodeBase tail

- The same v150 NodeBase tail parser recovers the authored **AuxParams
  bitvector, four conditional User-Defined Aux Bus slots, and the Early
  Reflections Bus ID**, with field-level fail-closed diagnostics. The current
  unique-payload audit passes every node payload, finds populated User slots
  reaching 25 Aux Buses, a large Game-Defined Use bit population, and **no
  populated Early Reflections target**.
- **Game-Defined Bus IDs, listeners and send levels are runtime API inputs and
  remain unresolved rather than projected as static routes.**
- The NodeBase parser also continues through AdvSettings, StateChunk and
  InitialRTPC; an independent audit matches production offsets and row counts on
  every unique node payload, recovering State Group occurrences, RTPC curves and
  points.
- Exact initial **AkPropID v150 bundles** are published: traversed nodes carry
  authored values and min/max ranges, with raw U32 and finite-float forms
  preserved, and typed ID/integer unions retain integer labels **rather than
  fake tiny floats**. Initial BypassFX/BypassAllFX property IDs **do not occur
  in the current banks**; direct NodeBase bypass flags remain a separate exact
  field and dynamic bypass is still unresolved. Effective inheritance, live
  State/RTPC/modulator values, platform DSP and audibility remain gaps.

### RTPC and GameParameter names: symbol-to-ID only

- The generated summary carries a **hash-pinned IL2CPP cross-match for six
  game-side GameParameter symbols**: `AU_RTPC_CINE_CTRL_VOL_AMB`, `...VOL_MU`,
  `...VOL_SFX`, `...IS_MUTE_BY_SDK_WEBVIEW`, `...IS_SURROUND_CHANNELS` and
  `...GLOBAL_VOL_MASTER_IOS_WORKAROUND`, each against its own node and Bus curve
  occurrences. **This is symbol-to-ID evidence only**; `0x1802`/`0x1804` remain
  custom/internal Wwise property IDs with **no guessed DSP names and no
  live-value claims**. Event/media RTPC and Bus-control rows reuse the same
  exact-name catalog, and unmatched IDs remain numeric/custom.
- The schema-117 semantic payload publishes `controlCatalog.staticRtpcAlignment`:
  a six-name canonical `AU_RTPC_*` contract that aligns exact numeric HIRC IDs
  with serialized InitialRTPC curve/property evidence and same-event
  Set/ResetGameParameter controls, published as **`authoredStatic` evidence
  only**. The explicit selected `global-metadata.dat` + `GameAssembly.dll` hash
  gate is required; a missing or mismatched selected/source hash, a malformed or
  incomplete contract, or stale serialized evidence **fails closed and withholds
  static names and rows**. Runtime parameter values, setter execution, target
  objects, selected branches, DSP and audibility remain runtime-only.
- Some Set/ResetGameParameter rows share an exact ID with an InitialRTPC curve
  target and are exposed as `sameEventInitialRtpcId` **authored curve-target
  joins**, while the GameParameter name and live value remain unresolved.
- A small set of unique InitialRTPC IDs is joined to exact metadata `au_rtpc_*`
  literals. The catalog keeps the exact authored Event/context, controlled AkProp
  targets, response-point count and interpolation mix; **it does not claim a
  live RTPC update or an audible result.**
- Generated event evidence preserves State property values and complete RTPC
  points/accumulation/scaling, with known control hashes **named only by exact
  FNV/native evidence**.

### Non-playback Action tails, and the selector packages

- The same v150 pass decodes non-playback Action tails **directly from the bank
  bytes**. SetState, SetSwitch, Set/ResetGameParameter, Stop/Pause/Resume, Seek,
  value/filter actions and FX slot actions are all `typedExactV150` in the
  current named-event evidence, with **zero failed control tails**; the
  per-category counts live in the generated evidence. The parser preserves typed
  Event->Action object paths and type labels, action ordinals, FNV IDs, value
  ranges, fade curves, active-action bit vectors, exception buses and FX slot
  indices.
- The semantic projection joins State/Switch Action group references and exact
  value references. It covers the **three native-backed selector roles** --
  voice identity, surface material, and local/remote routing -- plus ten exact
  current-metadata music State groups. Typed type-6 selector packages use the
  same 15-row catalog, and **unmatched IDs remain numeric**.
- The authored v150 Type-6 selector subset is published only on lazy
  Event-detail records as `selectorBranches`. Package child IDs join decoded
  media **only** through exact same-bank `soundObjectIds` evidence; malformed or
  cross-bank structures stay unresolved and fail closed, while runtime selector
  choice and audibility remain unresolved.
- **Any unsupported or truncated tail is published as `failedClosed` with an
  offset and a reason.** These are authored trigger parameters, not evaluated
  runtime state, effective inheritance, selected branch, DSP execution, or
  audibility.

### What the media projection may say about all of this

The Audio page projects the typed catalog onto each possible media leaf. The
projection's shape is a durable contract even though its row counts are not:

- each media leaf is projected onto its **exact serialized Event output-bus
  paths**, with effect and unresolved bus IDs kept as references into the typed
  catalog; **runtime branch selection and effective DSP are not inferred**.
- media whose typed NodeBase evidence has `outputBusNodeCount=0` receive an
  explicit `noExplicitOutputBusSerialized` status. **This is not treated as a
  default route, as silence, or as proof of an effect-free path.**
- media rows carry bounded exact **direct NodeBase effect slots** from Event
  `postProcessSummary.effectNodes`, separate from output-Bus effects. Each
  summary preserves the effect ID/plugin, node and slot, authored parameter
  summary and slot flags **without claiming live DSP execution or audibility**.
- they carry exact serialized **Wwise media-edge types and selection paths**
  (`directSound`, `layerChild`, `randomAlternative`, `switchCandidate`,
  sequence/music edges) plus root Action IDs. These are **authored candidate
  relations, not runtime branch or caller traces**.
- they publish a compact **serialized effect chain** combining direct-node slots
  with each leaf-to-root Bus path, capped per row. Direct-node slots are shown
  before Bus slots, and Bus slots preserve serialized path/slot order. **This is
  an authored binary join, not observed runtime DSP ordering, inherited values,
  branch choice, or audibility.**
- they keep compact references to serialized **Bus controls**; full points and
  plug-in parameters remain in the unique Bus catalog and are resolved by Bus ID
  instead of duplicated per leaf.
- serialized **Bus ducking** is projected compactly, preserving target Bus,
  attenuation, fade and target-property fields. **Runtime duck activation and
  audibility are not inferred.**
- exact **User-Defined Aux slots** are projected compactly, with unique Aux
  Bus/slot targets over their underlying send occurrences. Source-node types,
  flags, root Actions and target Bus IDs remain visible; **Game-Defined IDs and
  live send levels are runtime-only.** Each target also retains its exact
  serialized Aux Bus parent path and effect-Bus IDs, linking the possible send
  route into the typed Bus/DSP catalog.
- NodeBase **authored property values and ranges** are summarized per possible
  media path as distinct property and range signatures; raw U32 forms and full
  node provenance remain in Event evidence.
- bounded exact **StateChunk overrides and InitialRTPC response shapes** are
  published from possible Event paths, each RTPC summary keeping at most eight
  points and marking truncation. **These joins describe authored serialized
  controls, not live setter values, selected branches, effective inheritance,
  platform DSP, or audibility.**
- media rows also receive a separate **Event-level context summary** for the
  possible media set, carrying compact consumer kinds, roles, owners and
  situations. This is broader than exact `mediaRefs` and remains explicitly
  **non-selected and runtime-unobserved**; each row keeps at most 32 distinct
  summaries and reports when the list was truncated.
