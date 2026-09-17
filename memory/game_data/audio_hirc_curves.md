# HIRC `0x0B`: the curve record and its element frame

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 3, audio lane.** The type the engine never parses, framed from bytes alone,
with its residue measured rather than guessed. Long, and largely a record of what
has already been excluded.

## `0x0B`'s element ends with a self-sizing trailer, and that explains the widths

- **The element's trailer chooses its own length from its first byte: `0` means 19
  bytes, `1` means 24.** That five-byte difference is the five-byte step the entry
  widths have shown all along -- 84/89, 132/137, 168/173 -- and it is an optional
  field's two forms, not two layouts.
- **What the trailer leaves behind is `17 + 12k`**: a 17-byte head and a run of
  twelve-byte records, the same record `0x08`, `0x12` and `0x0B`'s curves carry.
  Over the 3,891 bodies with exactly one entry and one element: **3,594 frame**
  (3,238 short trailer, 544 long), 109 are ambiguous, 188 leave a body that is not a
  whole number of records.
- **The evidence is the residue, not the parse.** Rival anchors pick exactly one
  trailer for just as many elements -- `-18/-23` picks one for **3,875**, more than
  the chosen `-19/-24`'s 3,782. Parsing separates nothing. But the bodies each
  anchor leaves behind do:

  | anchor | picks one trailer | leaves `17 + 12k` |
  |---|---:|---:|
  | `-17/-22` | 3,877 | 32 |
  | `-18/-23` | 3,875 | **0** |
  | **`-19/-24`** | 3,782 | **3,594** |
  | `-20/-25` | 3,418 | 6 |
  | `-21/-26` | 721 | 4 |

- **Rivals are not all independent, and the first version of this gate got that
  wrong.** `-19/-25` scores 3,108, which failed a tenfold-margin test -- but it
  scores that only because `-19` is right and most elements take the short trailer.
  An anchor sharing an endpoint is a near-duplicate, not an alternative. The gate now
  demands the chosen anchor win outright against every rival and by a wide margin
  against rivals sharing **neither** endpoint. *When scoring a two-part reading
  against rivals, rivals that share a part inherit its score; hold only the
  genuinely different ones to the wide margin.*
## `0x0B` has a whole-body frame: 4,115 of 4,325

```
u8  flag
u32 sourceCount, that many 14-byte source records
u32 entryCount
entryCount x entry:
    48 header bytes, the element count at +44
    elementCount x element:
        5 head bytes, the run count at +0
        runCount x run: 12 header bytes, the record count at +7,
                        then that many 12-byte records
        12 trailing bytes
        a trailer of 19 + 5 * flag bytes
u32 terminator, always 100
```

- **This type had no frame at all before.** Every counted run in it is a count the
  body declares, and every width was settled by scoring rivals the same way rather
  than by whether the parse closed.
- **Run the managed suite with `dotnet run --project
  tools/AnimeStudio/AnimeStudio.CLI.Tests`, never `dotnet test`.** That project is a
  console `Exe`, not a test-SDK project, so `dotnet test` finds no tests, prints no
  counts and **exits 0**. A green exit there means nothing ran. The real run ends
  with `Managed-reference and VFS recovery tests passed.`, and the `Error:` lines
  above it are its own negative cases.
- **The trailer length is `19 + 5 * flag`, and flags 0, 1 and 2 are each observed
  closing bodies exactly** -- 3,108, 575 and 32 elements. Three points on the line,
  not two and an extrapolation. Flag 2 was worth the check: adding it took the body
  frame from 3,683 to 3,715, and all 32 of the bodies it gained had failed on
  exactly `trailerFlag_02`. Anything above the highest observed flag is refused
  rather than assumed to continue.
- **The 388 fenced bodies, by reason:** `range_element_trailer_flag` 119,
  `range_element_runs` 102, `entries_do_not_reach_the_terminator` 94,
  `range_elements` 46, `range_element_head` 21,
  `trailing_zero_run_before_the_terminator` 6. None is partially framed into a
  result. (610 before the extended trailer, 464 before the trailing section.)
- **The largest bucket was two different things and is now named apart.** Of the 322
  bodies that stopped short of the terminator, **104 leave nothing but a run of
  zeros** -- 7 bytes in 98 of them, 5 in the other 6 -- and **218 leave real
  content**. Reporting one number hid that the second group is unread structure while
  the first may be padding. *When a fence bucket is the largest one, check whether it
  is one failure or several wearing the same name.*
- **What the 218 leave is recognisable.** A 44-byte leftover begins
  `00 00 40 3f 00 00 80 3f 09 00 00 00` -- 0.75, 1.0 and the interpolation code 9,
  which is the twelve-byte curve record this type already carries. The 32-byte
  leftovers carry an object id at +8. And every leftover of both sizes has `01`
  **ten bytes from the terminator**, which is where an element's short trailer puts
  its own marker.

### `0x0B` has a SECOND element trailer, opened by the trailing block: 3,861 of 4,325

The residue was not noise, and it said exactly what it wanted. Of the bodies that
walked all their entries and stopped short, **98 were 7 bytes short and 48 were 12
bytes short, all at flag 0** -- where the flag says the trailer should be 19.

- **The first byte of the element's trailing block is a second flag.** It is `1` in
  exactly those 146 elements and `0` in the 3,108 that frame at flag 0. A clean
  split, not a majority. When it is 1 the head is **`14 + 5 * k`**, with `k` the byte
  seven into the trailer: `k = 0` in 98 elements and `k = 1` in 48.
- **Every part beats its rivals corpus-wide, scored by whole-body closure.**

  | part | chosen | rivals |
  | --- | --- | --- |
  | which block byte opens it | `block[0]`: **3,861** | the other eleven positions: at most 3,719 |
  | the extended base | `14`: **3,861** | 10, 12, 13, 15, 16, 19: **3,715 each** -- they add nothing at all |
  | which byte scales it | `trailer[7]`: **3,861** | bytes that are merely zero in this group: 3,813, closing the `k = 0` bodies and failing the `k = 1` ones |
  | the step | `5`: **3,861** | 0, 3, 4, 6, 7, 8: 3,206 -- a wrong step loses bodies the plain branch had |

- **Coverage rises 3,715 -> 3,861 of 4,325 (85.9% -> 89.3%)**, and the plain flag
  counts are **unchanged at 3,108, 575 and 32**. The 146 are bodies that framed under
  neither branch, not bodies moved between them.
- **The step of 5 is borrowed, not established.** Only `k = 0` and `k = 1` occur,
  which is two points; the reader refuses anything above 1 rather than extrapolating.
  This is weaker evidence than the plain flag, where three values are each observed
  closing bodies, and the reader says so.
- **Every element that takes the extended branch carries plain flag 0** -- all 146.
  Recorded rather than required: making it a rule would hide the day it stops holding.

### `0x0B`'s body ends with a fixed 12-byte block

- **4,141 of 4,325 bodies (95.7%) end with `00 00 01 00 00 00 00 00 00 00 00 00`
  immediately before the u32 terminator**, and so do 3,713 of the 3,715 that framed
  before this batch. The two exceptions carry `00 04 01 01` in the first four bytes
  with the same eight zeros, so the shape is **four bytes that vary and eight that are
  zero**. Over the 3,861 close blocks the frame now reaches, the eight zeros hold
  **3,861 of 3,861**, against **0** for the same width read four bytes earlier.
- The trailer is therefore written as a head of `7 + 5 * flag` plus this 12-byte
  close (19 = 7 + 12, 24 = 12 + 12, 29 = 17 + 12). **For these bodies that split is
  not an independent fact** -- the trailer is the last thing before the terminator,
  so "the trailer ends with the block" and "the body ends with the block" say the
  same thing. It is written that way because the block is the same 12 bytes whether
  or not the body frames, which makes it a property of the format rather than of the
  walk.
- **This is why the extended head is `14 + 5k` and not `26 + 5k`:** the close is
  accounted for once, separately, in both branches.
- **The residue always ends at this block**, in every failing class. So the 464
  remaining failures misread body *interiors*; none of them has a different ending.

### `0x0B` has a trailing section, and it brought the multi-entry layout into the frame

After the entry walk falls short, **one byte then the same 12-byte block and the same
trailer an element ends with** lands exactly on the terminator in **76 bodies**, all
of them multi-entry. Coverage **3,861 -> 3,937 of 4,325 (89.3% -> 91.0%)**.

- **The prefix is discriminated:** width 1 closes 76 and every other width from 0 to 9
  closes at most 10. The section costs nothing, because it is only attempted once the
  walk has already failed -- it can add bodies, never take one.
- **A length-only control closes 100, not 76, and the extra 24 are refused.** Accept
  any of the four observed trailer lengths and ignore the flag, and 24 more residues
  land exactly; but their block opening byte is `0xAF`, `0x55` or `0x59` and their
  selector is scattered. That is a total-length coincidence, not a section. *When a
  reading closes more cases than the rule that motivated it, the excess is the thing
  to look at, not the win.*
- The residue sizes made this findable: **32, 37, 39 and 44 are `13 + {19, 24, 26,
  31}`** -- 13 bytes plus each of the four trailer lengths already established on
  single-entry bodies.
- **The layouts that do NOT explain it, ruled out first.** A uniform wider entry
  header: no width from 8 to 200 closes any multi-entry body. All headers first and
  then all elements: likewise none. The element count somewhere other than `+44`: the
  sweep gives 3,861 at `+44` and at most 69 at every other offset. And the residue does
  not parse as more elements -- 122 of 142 stop at the first one. *Single-entry bodies
  cannot tell the interleaved layout from the headers-first one; both score 3,861. A
  corpus that cannot distinguish two readings is not evidence for either.*

### Four of my own claims were true only because every framed body had one element

The coverage gain broke four gates at once, and every one of them was right to break.
**This is the degenerate-input trap in its purest form: the corpus could not
distinguish the claim from a weaker one, so the claim looked exact.**

| claim | how it looked | what it is |
| --- | --- | --- |
| the element count is a count | untestable -- **1 in every framed entry** | now read at **0, 1, 2 and 3** (130, 3,871, 8, 4) with the walk consuming exactly that many |
| the entry count is a count | untestable -- **1 in every framed body** | now **1 in 3,861 and 2 in 76** |
| the word at header `+4` is a source id | **3,715 of 3,715** headers | **3,937 of 4,013** headers, but **3,937 of 3,937 bodies**: in a two-entry body **exactly one of the two** entries names a declared source |
| the 12-byte close ends in eight zeros | **3,861 of 3,861** trailers | its **content** is body-final -- **3,937 of 3,937 final** blocks, **0 of 38 interior** ones -- while its **length** is per element |

- **The last of these is the one worth keeping, and it splits in two.** Before this
  batch I could not tell whether the 12-byte close belonged to the element or to the
  body, because every framed body had exactly one element and the two readings made
  identical predictions.
  - Its **content** is body-final. Interior blocks end in eight zeros **0 of 38**
    times against **3,937 of 3,937** for final ones.
  - Its **length** is per element, and that is the opposite answer. Charging the 12
    bytes to every element closes **3,937**; charging them only to the last element of
    an entry, only to the last of the body, or only to the first each close **3,925**,
    and charging them to none closes **58**. So an interior element does consume a
    12-byte close -- it simply does not hold the eight-zero pattern.
  - *These are two different claims about the same twelve bytes, and the first draft
    of this note ran them together. A field's length and a field's content are
    separately testable and can have separate answers.*
- The source join is now counted **per body**, not per header. Per header the same
  data reads as a regression from 100% to 98.1%; per body it is exact, and the 76
  "misses" are one half of each two-entry body.
- The retired element-count gate had said: *"If a body ever closes with an entry
  declaring two elements, this fails -- and that failure is the good news, because it
  means the reading has finally been tested. Change it then, not before."* That is
  exactly what happened, so it was replaced rather than relaxed. *Write the tripwire
  that tells you when your own caveat has expired.*

### EVERY ENTRY AFTER THE FIRST BEGINS 4 BYTES EARLY: 3,937 -> 4,115

Identifying `+32` as a float handed over a second content check, and with two of them
the second entry header could be **located** rather than assumed.

- Two checks identify a first entry header, and both hold in **100%** of them: the word
  at `+4` is a source id the same body declares, and the word at `+32` is a plausible
  float.
- At the place the reader used to put the second header, **neither holds -- 0 of 216**
  two-entry bodies.
- Scanning every offset from `-32` to `+32` from the end of entry 1, **exactly one**
  passes either check: **`-4`**, in 168 of 216. **No other offset passes even once.**
- Scored corpus-wide the step-back closes **4,115** against 3,937 without it, and every
  rival step -- 2, 6, 8, 12, 16 -- lands at **3,861 to 3,863, below the baseline**.
- **The control flipped to agreement.** The same `+32` offset in later entry headers
  scored **2 of 26** while they were read four bytes late; with the step-back it scores
  **210 of 210**. *A control that becomes confirmation when an offset is corrected is
  the strongest evidence the correction was right.*
- **Which side owns the four bytes is not determined** and the reader says so: either
  the element walk over-consumes by four in the last element of a non-final entry, or
  the entry header is longer than 48. The reader compensates where the evidence is
  rather than inventing a field.
- The frame is now much simpler. 4,453 entries over 4,115 bodies; **338 declare zero
  elements and 4,115 declare one**, and the 338 step-backs are exactly those empty
  entries. Entry counts are exercised at **1, 2, 3, 4, 5 and 8**. Fences fall from 388
  to **210**.

### RETIRED: the trailing section was patching this, and WITHDRAWN: the interior blocks

Two earlier results do not survive the step-back, and both are removed rather than left
standing.

- **The "trailing section"** -- one byte, a block and a trailer, which closed 76
  multi-entry bodies -- **never fires** under the corrected frame: 0 of 4,325. It was
  compensating for the misplaced header. *A reading that compensates for a misplaced
  field is worse than no reading, because it makes the misplacement look closed.* The
  code and its gate are deleted.
- **The interior close blocks are withdrawn.** "The eight zeros belong to the block
  ending the BODY, not to each element" rested on interior blocks scoring **0 of 38**
  -- and those 38 existed only because the trailing-section reading placed a second
  header four bytes late. Under the corrected frame every framed body carries exactly
  one element, there are no interior blocks, and **the question is untestable again**.
  *Evidence produced by a reading is only as good as the reading.*
- The managed suite caught this too: its synthetic multi-entry body stopped framing the
  moment the reader learned the step-back, which is the test doing its job.

### `0x0B`'s word at `+32` IS A FLOAT, and negative zero is why it hid

Nine id populations had failed on this word: object references same-bank and
corpus-wide, source ids, media ids, **bank ids**, **STMG's 578 ids**, fixed-point
fractions, and the 24,231 identifier literal hashes. The last two populations only
existed after this batch framed STMG and published bank ids; both came back with **no
offset matching at all**.

Read as a **float**, in first entry headers it is **1,953 of 1,953 plausible** -- 823
exactly **negative zero**, and the rest in **-9.83 to 7.81** with most of them
negative.

| reading | plausible | share |
| --- | --- | --- |
| `+32` in the first entry header | **1,953 / 1,953** | **100%** |
| the same span at `+28`..`+31`, `+33`..`+39` | 202 / 3,116 | 6.5% |
| **`+32` in a LATER entry header** | **2 / 26** | **7.7%** |

- ***The `-0.0` is why this took so long.*** A band test that asks for
  `abs(v) > 1e-4` throws away `0x80000000` as "not a float" -- and that is **42%** of
  the field. **A field whose unset marker is negative zero looks unlike a float to any
  test that treats zero as uninteresting.** My own earlier float test on this header
  covered `+12` and `+20` and scored `+32` at 60.5%, which read as a miss.
- **The later-entry control is the sharp one, and it is a finding in itself.** The same
  offset one entry later scores 2 of 26, the rate of a shifted read. So the word is a
  float in the first entry header and **is not one after it** -- independent evidence
  that a later entry is **not the same 48-byte layout**, which is exactly what the 76
  trailing-section bodies have been hinting at.

### `+12`/`+20`: TEN populations eliminated, and what that leaves

The pair is now tested against everything the shipped data contains.

| population | size | matches at `+12`/`+20` |
| --- | --- | --- |
| object references, same bank | -- | 0 |
| object references, corpus-wide | 238,807 | 0 |
| source ids | 62,273 | 0 |
| media ids | 61,333 | 0 |
| bank ids | 20,863 | 0 |
| `STMG` ids | 578 | 0 |
| identifier-shaped literal hashes | 24,231 | 0 |
| **every raw metadata literal hash** | **49,324** | **0** |
| floats | -- | not plausible |
| fixed-point fractions of 2^32 | -- | **2.9%**, see below |

- **The fraction test, done properly with controls.** Several of the most common values
  *look* like fractions -- `0xAAAAAAA3` is near 2/3, `0x71C71C6A` near 4/9,
  `0x0F0F0F18` near 1/17 -- and that appearance is misleading. Asking for the closest
  rational with denominator <= 64 and an error within 1 ULP: `+12` scores **2.9%** and
  `+20` **2.8%**, against **100%** at `+28` and **96.4%** at `+36`, the two fields
  already known to be fractions. The near-misses are off by 7 or 8 ULPs, and a real
  fraction field here is exact. *An eyeball reading of the top few values is not a
  measurement; the field that IS this encoding scores 100%.*
- **What the values look like:** 373 distinct over 1,317 occurrences, so each repeats
  about three and a half times; popcount centred on 16, which is what random 32-bit
  values look like; range 1 to `0xFFFFFFFF`; equal to each other in **998 of 1,158**
  headers where both are nonzero.
- **So the pair is a hash or an id in a namespace the shipped files do not contain.**
  Random-looking, repeating, 32 bits wide, and matching nothing the game ships --
  including every string literal in `global-metadata.dat` at a chance rate of 0.05.
  Further population tests on this field are not worth running until a new namespace
  appears; the shipped ones are exhausted.

### The step-back is per ENTRY or per ELEMENT, and this corpus cannot tell

Applying it between elements as well as between entries changes nothing -- 4,115
either way -- because **every entry that frames carries at most one element**, so the
between-elements case never arises. Recorded as an indeterminacy rather than a choice:
the reader does it per entry because that is where the evidence was, and a corpus with
a multi-element entry would settle it.

### `0x0B`'s `+12` and `+20` are one field written twice

- Where both are nonzero they are **equal in 998 of 1,158 (86.2%)**. They share a top
  value and a distribution: minimum 1, median about 2.18e9, maximum `0xFFFFFFFF`.
- **Still unidentified.** The same nine populations failed on them. This is a
  structural observation, gated so it cannot quietly stop being true while the note
  claims it.

### CORPUS PROVENANCE: 10 banks ship twice, and one of them is the music bank

Looking at `0x0B`'s residue along a **provenance** axis instead of a grammar one
turned up something that qualifies a lot of numbers in this file.

- **All 4,325 type `0x0B` bodies live in 4 banks**, and bank **266542773** holds 4,260
  of them -- 2,130 in `audit_banks.pck` and 2,130 in `hotfix_main_b75.pck`, **byte-
  identical, all 2,130 of them**.
- Corpus-wide, **10 banks appear in more than one package**, duplicating **6,104 of
  323,049 objects (1.9%)**. Bank 266542773 alone accounts for 6,052 of those.
- **The duplication is concentrated in exactly the music types:**

  | type | counted | distinct | duplicated |
  | --- | --- | --- | --- |
  | `0x0A` | 4,158 | **2,112** | 49.2% |
  | `0x0B` | 4,325 | **2,195** | 49.2% |
  | `0x0C` | 742 | **373** | 49.7% |
  | `0x0D` | 2,431 | **1,230** | 49.4% |
  | `0x11` | 2,645 | 2,427 | 8.2% |
  | every other type | -- | -- | **under 0.2%** |

- **99.7% of music objects (11,507 of 11,656) live in that one bank.** The music family
  is one authored bank, shipped twice.
- **The closure RATE is unaffected**, because an exact copy closes exactly when its
  original does: `0x0B` is 3,937 of 4,325 and 1,998 of 2,195, both **91.0%**. What
  changes is the evidence base -- **197 distinct bodies are unexplained, not 388** --
  and the music-family size, **5,910 distinct rather than 11,656**.
- *A percentage over duplicated data is still the right percentage and the wrong
  sample size.* The audit now publishes the distinct count beside the total and gates
  their arithmetic, so the day a second bank starts shipping twice, something says so.
- **This is the cross-package trap for the FOURTH time.** A per-package census cannot
  see it: each package reports the bank once and looks unremarkable. After the media
  ids, the source ids and the plugin names, the rule is now unavoidable -- *if two
  sides of a question can land in different `.pck` files, the question belongs in the
  pass that unions them.*

### TWELVE BYTES AN ELEMENT that are always zero, and were never checked

Looking for a condition that could drive a conditional element rule meant looking at
the element bytes nobody had read.

- The element head is 5 bytes and **only byte 0 was used** (the run count). Bytes
  **1, 2 and 3 are zero in all 3,861** first elements that frame.
- The run header is 11 bytes and **only byte 7 was used** (the record count). **Nine of
  the other ten are zero** in every run header that frames -- only byte 3 varies.
- **Enforcing all twelve costs nothing: 4,115 bodies frame either way.** 30,582
  reserved bytes are now validated where the reader used to walk straight through
  them. *A field that is always zero is still a field, and a parser that does not check
  it will happily walk through garbage.*
- **It moves the fences to where the problem is.** 115 bodies are now rejected at
  `element_head_reserved_byte_is_not_zero`, and `range_element_trailer_flag` falls
  from **111 to 14** -- the desynchronisation is caught three steps earlier, at its
  cause instead of its symptom.

**A control that could not work, recorded rather than hidden.** Reading the same three
offsets five bytes on scores **11,774 zero of 12,843 (91.7%)**, because it lands on the
run header's *own* zero-invariant bytes. The neighbourhood is zero-rich, so shifting
within it cannot discriminate. ***A control has to land somewhere the claim does not
already predict.*** The gate publishes the number instead of pretending it
discriminates, and the evidence it rests on is the pair a bad control cannot produce:
coverage unchanged at 4,115, and 115 bodies caught that were previously walked through.

### `0x0B`'s residue is at a practical ceiling: six mechanisms swept and excluded

Every mechanism this format's own idioms suggest has now been tried on the 210, and
each was scored over the whole corpus rather than on the failing slice.

| mechanism | search space | best result |
| --- | --- | --- |
| a different uniform element grammar | ~2,300 shapes | 150-2,841 vs **4,115** |
| an extended entry header behind a flag | 1,728 triples | +8, and it fires on 14 bodies closing 0 of them |
| a different source-record width | 8..32, and a separate width after the first | 4,041 vs **4,115** |
| a gap before the entry count | -12..+16 | closes **nothing** when applied to all bodies |
| the step-back applied per element | -- | identical, the case never arises |
| shifting the failing element | -40..+40 | repairs **20 of 182**, at two inconsistent deltas |

Two further checks close off the easy explanations:

- **They are not dead data.** Every one of the 2,195 distinct `0x0B` objects is
  referenced by a `0x0A` counted array -- **100% of the framing ones and 100% of the
  failing ones**. The residue is live, referenced music tracks.
- **The surplus is not a constant.** For the 22 failing bodies simple enough that the
  frame can predict a length from their declared counts, the actual length exceeds it
  by 16, 38, 49 or 50 -- inconsistent. For the other 188 the element does not parse
  from its declared start at all, so no length can be predicted.

**The position, stated plainly: numeric type `0x0B` is at 4,115 of 4,325 counted and
2,087 of 2,195 distinct -- 95.1% either way -- and the residue resists every mechanism
the format's own vocabulary suggests.** Progress on it needs evidence this corpus does
not contain, not another sweep. *Recording a ceiling is worth more than a sweep that
was always going to fail, and cheaper than running it twice.*

### The 210 scale with body complexity, and the source region is NOT the cause

With the twelve reserved bytes now fencing at the cause, the failing bodies can be
characterised properly.

- **Shifting the failing element repairs only 20 of 182**, at two inconsistent deltas
  (`-36` and `+17`). The desynchronisation begins earlier than the element that
  reports it.
- **Failure rate rises sharply with body complexity**, and the source count is the
  sharpest predictor:

  | declared sources | closing | failing | fail rate |
  | --- | --- | --- | --- |
  | 1 | 4,041 | 172 | **4.1%** |
  | 2 | 70 | 28 | **28.6%** |
  | 4 | 2 | 6 | **75%** |
  | 0 | 0 | 4 | 100% |

  Entry count and body length track it: 1 entry 3.9%, 2 entries 15.0%, 4 entries
  37.5%; bodies under 200 bytes 3.6%, 200-300 14.4%, 400+ 40%.

- **But the source region is framed correctly, and two sweeps say so.** A separate
  width for records after the first: **14 is uniquely best** over 8 to 32 (4,115
  against 4,041 for every alternative). A gap between the records and the entry count:
  **0 is uniquely best** over `-12` to `+16`, and applying any gap to all bodies closes
  **nothing at all**.
- So the correlation is **complexity, not a located mechanism** -- exactly what a
  per-element error probability produces. *A predictor is not a cause; a sweep that
  confirms the field it points at is the difference.*
- One provenance note: bank **4247105105** in `init_banks.pck` fails **5 of 13
  (38.5%)** against 4.8% for the music bank. Thirteen bodies is too thin to conclude
  from, and it is recorded as a lead rather than a finding.

### Where the remaining 210 actually go wrong, and one methodological trap

Applying the content checks that found the four-byte step-back to the residue.

- **206 of the 210 failing bodies have a first entry header that passes both checks.**
  The walk starts in the right place and loses synchronisation later.
- **The 111 trailer-flag fences are a symptom, not a cause.** At the point of failure
  the trailing block's opening byte is scattered noise -- 4, 129, 2, 0, 100, 247, 82,
  15 -- so the walk is already lost before it reads the flag. The 36 that fail at a run
  count and the 21 at an element head are earlier detections of the same loss.
- **The zero-element entry advance is confirmed at 48.** Sweeping it from 17 to 52,
  only 48 reaches 4,115; every other value drops to 3,861.

**The trap, which nearly cost a batch.** Scanning *every* offset of a body for a window
passing both content checks produces coincidences: **130 failing bodies show a second
window exactly 17 bytes after the first**, consistently enough to look like a real
17-byte entry header. Sweeping that as a rule closes **3,861** -- below the baseline --
so it is a false positive of the scan, not a layout.

*The `-4` finding was clean because the scan was restricted to `[-32, +32]` and had a
unique answer.* A content check strong enough to locate a field within a restricted
window is not automatically strong enough to survive scanning a whole body. **When a
scan widens, its coincidence rate widens with it, and consistency across bodies is not
proof -- the same coincidence recurs for the same structural reason.**

### Two exhaustive searches over `0x0B`'s 388, both negative

The method that settled STMG's middle block -- enumerate every shape and let closure
discriminate -- applied to `0x0B`. Both searches came back empty, and that is worth
recording precisely so the ground is not re-walked.

**1. No uniform element grammar beats the shipped one.** Over the whole space of
element-head bytes 1..12, run-header bytes 5..16, record-count offset 0..runheader-1
and run-trailing bytes 0..3 -- about 2,300 combinations -- **656 close at least one
currently-failing body and none reaches 3,937**.

| gained of the 388 | head | run header | count at | trailing | whole corpus |
| --- | --- | --- | --- | --- | --- |
| 88 | 11 | 14 | +9 | 0 | **150** |
| 81 | 5 | 16 | +7 | 1 | **2,841** |
| 0 | **5** | **11** | **+7** | **1** | **3,937** (shipped) |

The shipped grammar is a **local maximum over the entire four-parameter space**. Every
shape that gains on the residue collapses the corpus.

**2. No extended entry header selected by a flag.** The trailer turned out to be
`7 + 5*flag` normally and `14 + 5*k` when the trailing block opens with 1, so the same
idiom was tested on the entry header: 48 bytes normally, `48 + extra` when some header
byte equals some value. **1,728 (selector, value, extra) triples**; three beat the
baseline, by **+8, +2 and +2**, with **zero losses**.

- The best is `header[44] == 3 -> +12`. Zero losses looked encouraging until the
  mechanism was checked: **`header[44]` is the low byte of the element count**, the rule
  fires on **14** bodies whose first entry declares 3 elements, and it closes **0 of
  those 14**. The +8 comes from later entries in multi-entry bodies, not from the
  population the rule describes.
- All three rejected. *A rule that gains without losing is not thereby right; check
  that the gain comes from the cases the rule is about.* Out of 1,728 trials a maximum
  of +8 on 388 candidates is what noise looks like.

**So the 388 need something that is neither a global grammar change nor a
flag-selected header variant.** Both of the format's known idioms have been tried and
neither fits.

### What does NOT explain `0x0B`'s remaining 388, tested and eliminated

Recorded so the same ground is not re-walked. Each was scored over the whole corpus
by whole-body closure, not on the failing slice alone.

| hypothesis | result |
| --- | --- |
| a wider entry header, uniform | **no width from 8 to 200** closes a single multi-entry body |
| all headers first, then all elements | likewise none; and note single-entry bodies score **3,861 either way**, so they cannot tell these two layouts apart at all |
| the element count somewhere other than `+44` | `+44`: **3,861**; every other offset from 0 to 44: **at most 69** |
| the residue is more elements | **122 of 142** stop at the first one |
| a different source-record width | no width from 8 to 32 rescues any of the 50 out-of-range bodies |
| a missing field before or after the entry count | gaps 0-16 either side rescue **2** at post-8, and cost the rest of the corpus |
| the close belongs only to some elements | see above -- every element, **3,937** against 3,925 |

- **The 119 trailer-flag fences almost all land at element index 1**, in single-entry
  bodies declaring two or more elements, with the flag and the block's opening byte
  both scattered. So the walk is already lost by then: **the first element's length is
  wrong**, not the second element's flag.
- **Shifting the second element does not repair them.** Of the 128 single-entry
  multi-element bodies, only **20** close at *any* offset in `[-40, +80]`, and those
  20 split between `-36` and `+17`. A single repeated delta would be a missing fixed
  field; this is not one.
- The 50 bodies whose counts come back wildly out of range have leading byte 0 and
  declared source counts of 0 to 4 -- indistinguishable on both from the 3,937 that
  frame.

### `0x0B`'s residue, measured rather than guessed

(Superseded in part by the section above: 76 of these now frame.) Of the 4,325
bodies, **306 declare more than one entry** (240 declare 2, 34 declare
3, 16 declare 4, 2 declare 5, 10 declare 6 or more) and **4 declare none**. Among the
4,019 single-entry bodies, **128 declare more than one element** (113 declare 2, 14
declare 3, 1 declares 4).

- **146 of the multi-entry bodies walk every entry and leave residue**; 100 more
  desynchronise at a run count, which is what a wrong entry-header width looks like.
  The entry header is not known to be 48 bytes for entries after the first.
- The multi-entry residues **contain curve records** -- `0.75, 1.0, code 9` and
  `float, 1.0, code 4` among them -- so they are unread element data, not padding.

### Correction: `0x0B`'s run splits 11 + 12n + 1, and its records ARE curve records

- **The run header is 11 bytes, not 12**, followed by the records and then one
  trailing byte. `11 + 12n + 1` and `12 + 12n` are **the same length**, so the body
  frame closes the same 3,715 bodies either way -- which is exactly why the split
  could not be settled by closure and had to be settled by what the records contain.
- Under the 11-byte header **all 4,086 records carry an interpolation code of 0 to 9**,
  spanning every value with no gaps: `9`:2017, `4`:1003, `1`:485, `7`:280, `8`:103,
  `0`:77, `5`:74, `2`:25, `6`:14, `3`:8. Under 12 the codes are noise and only the
  zeros pass. The control reading -- the same word one byte either side -- lands in
  range **377 of 9,376** times.
- **This corrects my own earlier measurement and restores the memory claim it
  appeared to contradict.** Reading the records at the 12-byte boundary showed codes
  in range for only 1,644 of 4,304, all of them zero, and I nearly recorded that the
  curve record is *not* in `0x0B`. The boundary was off by one byte; the claim was
  right.
- So the twelve-byte curve record is confirmed in **three** numeric types by a test
  with a working control: `0x08` and `0x12`'s tail units (314 records, all in range,
  codes 9/4/7/1/0/8/5) and `0x0B`'s element runs.
- **The lesson, and it is the sharpest form of one this session keeps teaching.** Two
  layouts of equal total length are indistinguishable by closure *no matter how large
  the corpus*. When a frame closes and its contents look like noise, suspect the
  internal split before suspecting the claim -- and settle it on content, because
  length cannot.

### The region after `0x0A`'s `0x0B` reference is a FLOAT BLOCK, and `+4` is the exception

Reading every word after the reference as a float and asking how many are finite and
in 1e-2..1e4:

| offset | nonzero | plausible float | note |
|---|---:|---:|---|
| `+4` | 2,130 | **14%** | the odd one out |
| `+8` | 3,748 | **95%** | median 5.689, mode **4.4766** (1,565) |
| `+12` | 311 | 87% | |
| `+16` | 334 | 95% | |
| `+20` | 3,816 | **93%** | already recorded as an authored value |

- **`+8` is a float field and had never been identified.** The reader uses it only as
  the *control* for the `+4` fraction test -- where it works correctly, since a float
  is not a small rational -- but nothing ever asked what it is in its own right. *A
  word used as a control is still a field; passing as a control says what it is not,
  never what it is.*
- So the block after the `0x0B` reference is mostly floats, and `+4` is the one word
  that is not. Its values -- `0x55555555`, `0xAAAAAAAB`, `0x89D89D8A`, `0xE8BA2E8B`,
  `0x71C71C71` -- are `p/q` in Q32 for `q` in 3, 7, 9, 11, 13, 49. That it differs in
  kind from its neighbours is now measured rather than assumed.
- A test I wrote to check whether those values have repeating binary expansions
  returned 100% for **every** offset including the floats, so it discriminates nothing
  and is **discarded**. It is recorded here only so the next attempt does not rebuild
  it. *A structural test that passes everything has not been run; it has been
  mis-written.*

### QUALIFIED: `0x0A`'s "fraction" is a mixed value set, not a fraction field

The discriminator that separates a real fixed-point field from a test artefact is
**how many denominators it uses**, and applying it to `0x0A` qualifies a finding I
strengthened two batches ago.

| field | passes `IsSmallFraction` | distinct fractions | denominators |
|---|---|---:|---|
| `0x0B` `+28` | 100% | **5** | **3, 6, 2** |
| `0x0B` `+36` | 96.3% | **18** | **3, 6, 2**, then a tail |
| `0x0A` fraction | 67.4% | **42** | 3, **13, 11, 7, 23, 9, 19, 49** |
| `0x0B` `+12` | 42.0% | **76** | 13, 17, 7, 3, 23, 19 -- no family |

- `0x0B`'s established fields use a **tight, authored family**: 1/3, 2/3, 1/6, 1/2,
  5/6. `0x0A`'s spreads across denominators 13, 11, 49, 23 and 19, which no one
  authors.
- **The field's real shape is a small repeated value set**: only **237 distinct
  values** over 2,130 bodies, the ten commonest covering **50%**. Its top value is
  `0x408F4000`, which is the **float 4.4766**, seen 203 times -- and the control word
  four bytes on holds that same value **1,565** times. So the field mixes
  float-shaped and fraction-shaped members.
- **What survives**: the field is still sharply different from its control -- 67.4%
  against 3.2%, a 20x margin, and random words pass at 0 of 2,130. Something real is
  there. **What does not survive**: calling it a fixed-point fraction. That reading
  over-reads a permissive test.
- *`IsSmallFraction` with denominators to 64 is too generous for structured data. It
  passes 42% of `0x0B`'s `+12`, which is definitely not a fraction field. The
  discriminating question is not "is this value a small rational" but "does this field
  use a handful of denominators".*
- `0x0B` `+44` is confirmed as the element count from the other side: raw values `1`
  in 3,903 entries, `2` in 133, `3` in 14, `4` in 1.

### The fixed-point fraction is in two types, and they are NOT the same quantity

Three measurements, and the conclusion is a negative worth keeping.

1. **The `0x0A` fraction reading is much stronger than previously recorded.** Under
   the reader's own tolerance (16 parts in 2^32, denominators to 64): **1,435 of
   2,130** nonzero values are small fractions, the control word four bytes further
   on manages **121 of 3,748**, and **0 of 2,130 random 32-bit words** pass. The
   random control is the one that settles it -- a test that admitted arbitrary words
   would not have been evidence at all.
2. **`0x0A` -> `0x0B` does not carry the fraction.** For the 1,864 `0x0A` bodies with
   a nonzero fraction whose reference resolves to a framed `0x0B`, the value equals
   one of that `0x0B`'s two entry-header fractions in **58** cases. Shuffling the
   pairing gives **52**. That is chance, on the one edge in this format known to be
   one-to-one.
3. **The value distributions differ in kind.** `0x0B`'s entry fractions are a tight
   set -- 0, 1/3, 2/3, 1/2, 1/6. `0x0A`'s spread across 7/13, 1/3, 10/11, 2/3, 4/9,
   27/49, 4/7 and more, with denominators 7, 9, 11, 13, 49.

So the two types share an **encoding**, not a **meaning**. *A representation found in
two places is a lead, not a link -- test whether the values actually travel along the
reference before treating it as one.* The cheapest such test is the shuffle: score the
real pairing against a permuted one, and a difference of 58 against 52 says stop.

### Four fields read in the 48-byte entry header -- and one caveat about the frame

Censused over the 3,715 entries of closing bodies only; an entry header from a body
that later fails says nothing, because the walk that reached it may be desynchronised.

| offset | reading | evidence | control |
|---|---|---|---|
| `+0`, `+8` | constant zero | 3,715 each | -- |
| `+4` | **source id, joined** | it is one of the source ids the **same body** declares: **3,715 of 3,715** | -- |
| `+16`, `+24` | a **symmetric float pair** | `low == -high` in **1,218 of 1,404** nonzero pairs; `low <= high` in 1,264 | the neighbouring word at `+12`: **0 of 1,391** |
| `+28`, `+36` | **fixed-point fractions of 2^32** | small rationals in **2,735 of 2,804** | the word at `+40`: **0 of 3,715** |
| `+40` | a **bounded float**, in every entry | 3,715 of 3,715 in 1e-3..1e4; range 3.951 to 10.1, median 7.548, 889 distinct | `+4` and `+12`: **420 of 4,806** |
| `+44` | element count | see below | -- |

- **The source id sits at record offset 5, which is NOT four-byte aligned.** Testing
  the 14-byte source record's aligned words -- 0, 4 and 8 -- against the header's `+4`
  finds **no match at all**; offset 5 matches **every one of the 4,321**. That is why
  this field read as unidentified for so long, and it is the second time in two
  batches that a field turned out not to be where alignment suggests. *A join that
  fails at every aligned offset has not been disproved; it has been tested at the
  wrong offsets.*
- **Nor are they among the audio-named literal hashes.** All twelve offsets score
  **0 of 4,321** against the 221 audio literal hashes the named-reach audit loads.
- *A correction on how I read that.* I dismissed this as "no discriminating power",
  which is backwards. With 221 hashes against 2^32, the expected chance matches over
  4,321 words is **0.0002** -- so the test can never produce a false positive, and a
  single hit would have been decisive. Finding none is a narrow but real elimination,
  not a failed experiment. **A test with a tiny false-positive rate is powerful for
  confirming and weak for refuting; say which of the two you got.**
- **The stronger test has now been run, and it is decisively negative.** Against the
  **24,231** distinct hashes of every identifier-shaped literal in
  `global-metadata.dat` -- not the 221 audio-filtered ones -- **all twelve offsets
  score 0**. Expected chance matches are **0.024**, so a single hit would have been
  conclusive and there are none.
- `scripts/audio_semantics/hirc_named_reach.py` already exposes `broad_literals()` for
  exactly this: identifier-shaped literals without the audio prefix vocabulary. **The
  population I said I would need was already a function in the repo.**
- So `0x0B`'s `+12`, `+20` and `+32` are eliminated as object references (same-bank
  and corpus-wide), source and media ids, floats, fixed-point fractions, **and name
  hashes**. Five populations, all negative, all properly powered.
- **None of the header words is a source id either.** Scored against the full
  source-id population, every offset including `+12`, `+20` and `+32` matches **zero**
  -- so those remain unread, now eliminated as object references, name hashes, floats,
  fractions **and** source ids.
- **The opaque words are not references.** Tested against the same-bank id set and the
  corpus-wide one, **none** of the twelve header words resolves to an object -- `+4`
  matches 8 ids out of 4,321 and the rest match zero. That confirms the standing note
  that `0x0B` points at media rather than objects, and closes "reference" as a reading
  for `+12`, `+20`, `+32` and `+44`.
- **`+12` and `+20` are not floats either**: only **2.0%** of their values land in
  1e-3..1e4, and they range over plus and minus 5e37. They remain unread.
- *A float field is not established by its own values being finite -- almost any
  32-bit word is a finite float. It is established by neighbouring words read the same
  way not being plausible.* Here `+40` is 100% in band against 8.7% for its
  neighbours.

- The float pair sits around plus or minus five: `(-5.16, +5.16)`, `(-4.84, +4.84)`,
  `(-5.48, +5.48)`. What it bounds is not claimed.
- The fractions read 0, 1/3, 2/3, 1/2 and 1/6 -- **the same fixed-point encoding
  `0x0A` carries**, which is now confirmed in two numeric types. Entries where both
  range words are zero are excluded, and a zero fraction is excluded, because zero
  satisfies both properties for free.
- **Both controls score exactly zero.** A word read one field away satisfies neither
  property in a single entry.

**The caveat, and it is about this reader rather than the format.** The word at `+44`
is read as an element count, and it is **1 in every one of the 3,715 entries the frame
closes**. Reading it as a count and reading it as the constant 1 produce the same
3,715 bodies, so **nothing in the corpus distinguishes them** and the "count" is a
hypothesis. Entries declaring 0, 2, 3 or 4 exist -- 370, 221, 48 and 7 of them -- and
every one is in a body that fails to frame.

This is stated as a gate, `the_type11_element_count_is_not_yet_a_count`, which holds
while the count is 1 everywhere. **When a body finally closes with two elements the
gate fails, and that failure is the good news**: the reading will have been tested for
the first time. *A field named as a count in a frame that never sees it take another
value has been assumed, not measured -- and the assumption should be visible in the
gate rather than buried in the field's name.*

### The 119 trailer-flag fences: the size is found, the selector is not

- **A 17-byte trailing block instead of 12 closes 89 of the 119**, taking the body
  frame from 3,715 to 3,804 of 4,325. And `17 - 12 = 5`, the same optional five-byte
  step the element trailer and the entry widths both show.
- The size is discriminated: `(17,)` alone closes only **91** bodies, `(12, 16)`
  gains nothing, and `(12, 16, 17)` gains less than `(12, 17)` because 16 mis-matches
  first. So 17 is specifically right, not merely bigger.
- **But the selector is undetermined, and it is not adopted.** Thirteen byte
  positions separate the two groups perfectly -- element head bytes 1 to 4, run
  header bytes 0 to 4 and 7 to 9. The 89 are a completely homogeneous population:
  every one has exactly one run, that run declares zero records, and its head bytes
  1 to 4 are nonzero, while **2 of 3,804** twelve-byte-block elements have a nonzero
  head there and **none** has one run with zero records.
- So the two populations differ in every measured respect and nothing in the corpus
  can say which difference is the switch. Picking one of the thirteen would be
  arbitrary; taking `(12, 17)` as a fallback search would resolve the choice *by
  closure*, which is the exact failure mode that made the terrain codec's nibble
  reading look right for 6,442 files. **Measured, recorded, not adopted.**
- What would settle it: a `0x0B` body with a populated element head and more than one
  run, or one run declaring records. None exists in this corpus.

**A second property, measured later and worth only what it is worth.** Under the
17-byte block the fenced elements come out at size **53** in 93 of the 119 and **41**
in 20. Every element size closing bodies produce is of the form `36 + 12a + 5b` --
36, 41, 72, 77, 84, 89, 96, 120, 125, 137 -- and 53 fits it as `36 + 12 + 5`. So the
reading yields family-consistent sizes rather than arbitrary ones.

*But the family test is weak and saying so matters more than the result.* With 12 and
5 coprime, every size above **79** is representable, so the test is **vacuous** there;
across 36 to 139 it rules out only **22 of 104** candidates, or 21%. Size 53 passing
is corroboration, not evidence, and it does not change the standing conclusion that
the 12-vs-17 selector is undetermined. *Check a length model's Frobenius number before
quoting it -- this is the second length family in this format where most of the range
is free.*

## THE 218 ARE MOSTLY NOT AN ELEMENT PROBLEM AT ALL

Reading one failing body against a closing one -- the method that cracked `0x08`,
rather than the ten enumerations that did not -- settles where the problem lives.

- **Every one of the 3,715 bodies that frames has exactly ONE entry carrying exactly
  ONE element.** No exceptions. The entry/element shape `(1, (1,))` is the only shape
  the reader has ever parsed successfully.
- **142 of the 218 declare an entry with ZERO elements**, in shapes like `(2, (0,0))`
  54 times, `(2, (0,2))` 32, `(2, (0,1))` 24, `(3, (0,0,0))` 22. **No closing body has
  that shape.** Four more declare zero entries.
- So for most of this bucket the element walk is not at fault. **The multi-entry
  layout has never been parsed**, the 48-byte header width is verified only for the
  single-entry case, and the entry count -- like the element count already gated -- has
  never been read at any value but 1 by a successful walk.
- **The remaining 70** have the same `(1, (1,))` shape as every closing body. Those,
  and only those, are a genuine element-level mystery.

**The bucket decomposed, by (zero-element entries, residue bytes):**
`(0,12)` 48, `(2,32)` 36, `(1,44)` 24, `(1,32)` 22, `(3,112)` 16, `(0,16)` 10,
`(2,44)` 8, `(2,37)` 8, `(0,49)` 6, `(0,38)` 4.

- **The residue does not scale with the number of zero-element entries.** Two zero
  entries with a 32-byte residue is 16 each; one with 44 is 44; three with 112 is
  37.3. No constant per entry, so the multi-entry layout is not "a fixed extra block
  per empty entry".
- **The 48 bodies with the closing shape and a 12-byte residue**: the residue is
  `00 00 01 00 00 00 00 00 00 00 00 00` -- a mostly-zero twelve bytes with `01` at
  offset 2. It passes a curve-record test, but only as `(0.0, 0.0, 0)`, which **a run
  of zeros passes for free**. Not a curve record.
- **Not a doubled trailing block either.** A 24-byte block closes **0** of 4,325 and a
  36-byte block 0, against 3,715 for 12.

*Four more readings eliminated. The pattern across this whole bucket is that every
candidate that closes anything closes only the degenerate members -- zero runs, zero
records, all-zero blocks -- and the content test catches each one. That is now the
single most reliable signal in this investigation: if a reading's successes are all
zero-filled, it is wrong.*

*Ten hypotheses about element widths failed because the residue was never mostly an
element problem. When a residue resists every reading of structure X, check whether
the failing bodies even have the same shape at level X-1 as the ones that work.* Here
one query -- the distribution of (entryCount, elementCounts) over closing versus
failing bodies -- would have redirected the whole investigation.

Gated: `the_type11_element_count_is_not_yet_a_count` now also refuses if the entry
count is ever read at another value in a closing body, which would mean the
multi-entry layout had finally been parsed and this note needed revising.

### The 218 are a PARTIAL ELEMENT, mis-entered by exactly four bytes

Applying the lesson that closed `0x08` -- when a walk desynchronises, look for the
next occurrence of something it already parses correctly:

- **152 of the 218 residues END with a valid element trailer** -- 122 with the 19-byte
  form, 26 with 24, 4 with 29. So the residue is not extra data appended to a finished
  body. It is the **tail of an element the walk entered too late**.
- Taking the trailer off leaves an element body, and **104 of those 152 are exactly
  four bytes short of `17 + 12k`** -- 13 where 17 is wanted, 25 where 29 is, 93 where
  97 is. The walk over-consumes by **4 bytes** in the element before it.
- **No global constant change accounts for it.** Head 5->1 closes 10 bodies, block
  12->8 or 12->16 closes 0, trailer 19->15 or 19->23 closes 0, head 5->9 closes 0.
  The chosen `(5, 12, 19)` closes 3,715 and nothing else comes close.

**ELIMINATED, and the "four bytes" framing with it.** I read the shortfall as one
element consuming four bytes too many. Every version of that fails:

* shortening each element in turn by four and re-running the walk: **0 of 322**;
* *growing* each element in turn by four: **0 of 322**;
* shortening one element by four **and** taking one extra element at the end, which is
  the only way a shift and the entry's element count can both be satisfied: **0**;
* alternative entry-header widths (44, 52, 56) and element-count offsets (4, 8, 40,
  48): **0** each, against 3,715 for the chosen 48 and +44.

So "four bytes" is not a walk error at all. It is an **arithmetic property of the
residue lengths**: the residue bodies are `13 + 12k` -- 13 in 66 bodies, 25 in 30, 37
in 4 -- which is four less than the `17 + 12k` a complete element body takes. That is
a description of the residue, not a diagnosis of the walk, and I turned one into the
other without checking.

**Also eliminated again, with the content test this time.** The residue lengths are
consistent with a 1-byte-head element -- 13 is `1 + 12`, 25 is `1 + 12 + 12`, 93 is
`1 + 80 + 12` -- but reading them that way still closes only the same **66**, every
one with **zero runs and therefore zero records**. The interpolation-code test has
nothing to check, so the arithmetic consistency is all there is. Third time this
reading has been measured and third time it is degenerate.

**What survives, and it is still the most useful thing known about this bucket**: 152
of the 218 residues end with a valid element trailer, so they are element *tails*
rather than appended data. The mechanism that leaves them is not a single mis-sized
element.

*Searching for a flag also failed for a reason worth keeping: once a walk
desynchronises, every element after the divergence is noise, so comparing the LAST
element of a failing body against good ones compares nothing. No byte separated the
two groups, and that result means nothing either.*

### FIVE eliminations on the 218, so the next attempt does not repeat them

The residue of numeric type `0x0B` bodies that leave real content before the
terminator. Sizes: `32`:58, `12`:48, `44`:32, `112`:16, `49`:10, `16`:10, `37`:8,
then singles.

1. **Not one more element the entry count failed to declare.** Walking elements
   greedily after the declared ones takes **zero** extra in **every** body.
2. **Not whole elements of any observed shape.** The element sizes bodies that close
   actually use are 36, 41, 72, 84, 96, 120, 89, 77, 125, 137. Only **4 of 218**
   residues have a size in that set. This is independent of (1) and reaches the same
   place.
3. **Not a variant element with a one-byte head.** It closes 66, but every one of
   those declares a run count of zero, so only the fixed bytes are exercised and the
   interpolation-code test has nothing to check. Retracted in full.
4. **Not explained by the 17-byte trailing block.** Allowing it takes the frame to
   3,804 and drops the trailer-flag fences from 119 to 6, but grows this bucket from
   218 to 236. The two fence buckets have independent causes.
5. **Not a counted array of curve records.** Locating the first curve-shaped window
   and stepping back four bytes -- the move that closed `0x0A` -- gives no count in
   any body: 150 of 218 have no room for one and the rest disagree.

*Elimination (2) is the cheapest of the five and should have been first: comparing
the residue's size against the sizes the structure is actually observed to take costs
one query and rules out the whole "it is another one of those" family.*

### Two eliminations on the 218, kept for the record

- **It is NOT one more element the count at +44 failed to declare.** Walking elements
  greedily after the declared ones -- taking every element that parses until the
  terminator -- takes **zero** extra elements in **every** body, and closes exactly
  the same 3,715. The residue does not parse as an element at all.
- **RETRACTED: the "66 of 218" one-byte-head reading is a length coincidence.**
  I recorded it as "a fixed rule with no free parameter" and it is not evidence at
  all. Every one of those 66 residues declares a **run count of zero**, so the
  reading consumes only its fixed parts: `1 + 12 + 19 = 32` and `1 + 12 + 24 = 37`,
  which are exactly the two residue sizes that close. It produces **zero records**,
  so the interpolation-code test -- the thing that settled the run split -- has
  nothing to test. Same trap as the flat terrain tiles, in a third costume.
- What the residue sizes actually are: `32`:58, `12`:48, `44`:32, `112`:16, `49`:10,
  `16`:10, `37`:8, then singles. Only **92** are of the form `32 + 12k` and **20** of
  `37 + 12k`; **106 fit neither**, so most of the residue is not even the right length
  to be a trailing element of the known shape.
- **Also eliminated: the 17-byte trailing block does not explain the 218.** Allowing
  it takes the frame to 3,804 and drops the trailer-flag fences from 119 to 6, but
  the `entries_do_not_reach_the_terminator` bucket *grows* from 218 to 236. So the
  two fence buckets have independent causes, and a reading that fixes one is not
  corroborated by the other.
- *When a candidate reading closes a residue, check what it exercised. A rule whose
  counted runs are all zero has been confirmed by arithmetic on its constants, not by
  the data.*
- Not a closure-gated lane, for the same reason `0x08` is not. The gate is a floor
  at 80% -- there to catch a regression, not to assert the frame is complete, which
  it is not.

## `0x0B`'s element is now a forward frame

```
element body:
  u8  runCount            -- element[0]
  4   head bytes
  runCount x run:
      12-byte run header, the record count at +7
      count x 12-byte record
  12  trailing block
then the trailer: first byte 0 -> 19 bytes, 1 -> 24
```

- **1,103 of the 1,151 elements that declare a run close exactly**, and the best
  rival frame closes **17**. Rivals varying the head, the run header width, the
  count's offset and the trailing block all score 0-17.
- **Scored over every element instead, the finding would have evaporated**: the
  chosen frame closes 3,594 and a rival closes 2,508, a ratio of 1.4. The 2,491
  elements that declare no runs close under almost any frame whose head and trailing
  block add up, and they outnumber the ones that walk a run two to one. Same frame,
  same corpus, completely different strength of claim -- which is why the gate reads
  `frameClosesWithRuns` and its control requires a rival to be visibly inflated by
  the empty ones.
- Run counts: 0 in 2,491 elements, 1 in 835, 2 in 242, 3 in 26.
- **How the layout fell out**, in order, because the sequence is the method:
  1. `element[0]` is 0 in exactly the 2,491 elements with no records -- so it is a
     run count, not a record count.
  2. For `element[0] == 1`, `k = 1 + element[12]` in **all 835**. The `+1` is the
     run's own twelve-byte header.
  3. For `element[0] == 2`, the second run's count sits at `element[24 + 12*c1]` in
     **242 of 242**, and at no other relative offset. That fixed the run stride at
     `12 + 12*c` and the count's place at `+7`.
  4. The lengths then forced a fixed twelve-byte block after the runs: an element
     with no runs is 17 body bytes, and 17 = 5 + 12.
- **Earlier searches missed it by looking for one count.** `element[8]` equals `k`
  in 575 of 1,103 -- a genuine half-fit that is not the rule and led nowhere,
  because `k` is a *total* over runs, not a field. *When a count field explains
  roughly half a corpus, consider that the quantity is a sum before hunting a better
  offset.*
- The degenerate trap caught this one too: scored without excluding `k = 0`, eight
  different offsets "carry k" in 2,491 elements, because an all-zero field matches a
  zero count for free. The census excludes them, and the code says why.
- Gated by `the_type11_trailer_anchor_beats_its_rivals` with
  `the_type11_trailer_is_not_settled_by_parsing` as its stated control: if the chosen
  anchor ever also wins on how many elements it can parse, the residue test is doing
  no work and the gate fails loudly.
- Supersedes the earlier note that "the 53 + 12k head widths that close are a fit
  rather than a layout". That measurement was made from the front, looking for a
  count in the first 53 bytes. The structure is anchored to the **end**, which the
  earlier attempt could not see -- and which is the third time in this type that
  tabulating from the end worked where the head resisted.
- Type `0x0B` carries **no** same-bank object references at all -- it is pointed to
  by `0x0A`, and points at media instead. The corpus has only 7 DIDX entries in
  total, so its media is streamed rather than embedded, and `0x0B`'s source ids
  match neither the DIDX ids nor type `0x02`'s source ids. Those are simply
  disjoint id sets, which is not evidence against the layout.
- `0x0B` is *not* yet the witness that would resolve the node frame's group B
  width. Its bodies would only make group B nonempty if the frame starts at offset
  0, which is exactly what is not established. Group B remains unresolved.
- Method that paid off and is worth reusing: mirror the C# node frame in Python
  under `tmp/`, then **prove the mirror first** against an already-closed type.
  The mirror reproduced all 48,740 type `0x07` bodies exactly before it was used
  on anything, which is what makes its music-type failures trustworthy. Iterating
  in Python avoids a C# rebuild per hypothesis; nothing from the mirror ships.
- **Numeric HIRC type `0x0E` is framed byte-exact, and it does not use the shared
  node frame.** 24,145 bodies / 5,143,855 bytes, every one consumed from its first
  byte to its declared object-body end. Layout: a fixed 21-byte head, an optional
  20-byte block, 19 opaque bytes, a byte-counted list whose entries each carry one
  selector byte plus a `u16` element count plus that many 12-byte elements, and two
  closing bytes that read as zero everywhere.
- The branch is decided by a byte, not by a search. The candidate layout was found
  by sweeping shapes, which left 6,218 of the bodies with two start offsets that
  both consumed exactly -- so the sweep alone could not fix the prefix. Byte 1 of
  the body settles it: it is 0 or 1 across the whole corpus, and it predicts prefix
  21 versus prefix 41 in every single body. The framer therefore reads the flag and
  computes the prefix; it never searches, and any other flag value fails closed.
  **Do not weaken this to "take the earliest offset that parses"** -- that would
  reintroduce the ambiguity the flag byte removes.
- The minority branch is real, not a degenerate fit: its 164 bodies span 37 distinct
  bodies, 89 banks, 130 object ids, 3 files, 23 lengths and 21 distinct optional
  blocks. That check is the standing lesson from the group I and group H fixed
  widths, applied before publishing rather than after being caught.
- This lane carries a **closed-form byte identity** the other lanes cannot: framed
  bytes must equal `24 * bodies + 12 * elements + 3 * entries + 20 * optionalBlocks`.
  It holds exactly at 5,143,855. That is an equation, not the containment inequality
  the node-frame lanes use, so a miscounted element or entry cannot hide in slack.
  See [`reports/animestudio/hirc_type14_body_current_latest.md`](../../reports/animestudio/hirc_type14_body_current_latest.md).
- What stays open on `0x0E`: the 21-byte head and 20-byte block are consumed by
  extent only; the 12-byte element is not split internally (only its trailing word
  is published as a histogram, bounded 0..9); and the two closing zero bytes cannot
  be distinguished from an always-empty counted list in this corpus. The 12-byte
  elements are **not** claimed to be points, curves, or samples of anything.
- **Layer 5 opens: numeric HIRC type `0x04` is the object that shipped managed
  code addresses by name.** The evidence is a unique cross-table reference, not a
  label. `global-metadata.dat` `stringLiteral` rows give 221 exact audio-like
  strings the game's own code contains; 203 of their hashes equal a HIRC object
  identity, and **all 203 land on type `0x04` and none on any other type**. The
  hash is the shipped `AudioHashGenerator`: FNV-1 over UTF-16 code units, folding
  ASCII `A`-`Z` before each XOR. Type `0x04` is 22,910 of the 323,034 objects (7.09%), so coincidence
  would scatter about 140 of those 151 matches onto other types; none did. That
  share is measured from the reader's own type histogram by `named_type_share`,
  not asserted in prose. The gate refuses to
  publish if a single match ever lands elsewhere, because that would dissolve the
  identification rather than weaken it -- never turn this into a percentage.
- Walking from a named type `0x04` object through reference vectors alone reaches
  numeric type `0x02` objects, whose bounded 14-byte prefix yields a source id:
  63 of the 151 named objects reach at least one, 134 source ids in total. The
  other 88 reach none, almost always because the walk hits an edge leaving the
  bank -- 98 such edges, counted and never followed. The walk also uses the type
  `0x03` target word, which is **not** a gated reference vector (only about three
  quarters of those words name an object in their own bank), so it is reported as
  what it is rather than folded in.
  See [`reports/animestudio/hirc_named_reach_current_latest.md`](../../reports/animestudio/hirc_named_reach_current_latest.md).
- What Layer 5 does **not** license, even now. A reached source id does not mean
  posting the identifier plays that media; nothing here establishes ordering,
  selection, mixing, audibility, or that the media is ever decoded. Only the type
  `0x04` entry point has a name -- every other object on the path is still
  anonymous, and an edge leaving the bank still resolves to nothing this corpus
  can see.
- Be precise about what the reference graph is. The only direction it establishes
  is physical: which object's body holds the four-byte value. Over that byte-level
  direction the relation is acyclic with at most one holder per target, which is
  why the reader can walk it and report a depth. Do **not** promote that to
  parenthood, containment, membership, a tree, or a root: those are semantic
  readings the join does not license, and neither endpoint of an edge has a name.
  Ordering, selection, mixing and playback are equally unclaimed. The absence of a
  cross-bank edge is a property of this corpus, not a proven rule.
- Two further properties are readable straight off the published table, because
  with zero multi-referrer targets the references into a type are that many
  distinct objects of it: type `0x03` shows 28,379 referenced against 28,379
  objects, so every one is referenced exactly once; type `0x04` shows 0 referenced
  against 22,910 objects, so no type `0x04` object is ever the target of a
  reference.
- The null model for that result is per bank, not corpus-wide, because resolution
  only ever looks inside one bank. With 323,034 objects over 20,873 banks the
  reference-weighted expectation is about **0.15** chance resolutions, not the
  ~16 a corpus-wide pool would suggest. The finding is roughly two orders of
  magnitude stronger than a whole-corpus null implies -- but it argues the values
  *are* identities, still not what the edges mean.
- A bounded read-only probe shows how far the node frame reaches: it consumes
  cleanly from byte 0 for every type `0x06` (4,573) body and, after the counted
  state correction, for all 5,158 type `0x09` bodies, each leaving a regular
  type-specific suffix, while types
  `0x0B`, `0x0E`, `0x12`, `0x16` and `0x08` reject it outright and
  `0x0A`/`0x0C`/`0x0D` match only in part. Type `0x09`'s suffix looks like a
  counted four-byte reference vector followed by a second counted section and
  one trailing byte; type `0x06`'s is more varied and not yet decoded. Treat
  this as a prioritisation signal, not a framing claim: no suffix is parsed and
  no maintained reader accepts those types yet.
- AKPK entries, Wwise numeric media ids, Events, containers, switches, random
  nodes, RTPC curves, and authored consumers keep their native identities.
  Same-id files in different roots are not collapsed by filename stem.
- Authored Event requests, controller callbacks, Timeline clips, Lua calls,
  serialized AudioCue trees, external sources, and responsive-voice tables are
  typed consumer evidence. They do not prove the selected runtime arm.
- A source prefab or component proves a possible emitter, not scene
  instantiation or level ownership.
- Native method names and callsites are accepted only with exact-build hashes
  and bounded argument/control-flow validation. Literal, dictionary, selector,
  callback, and external-source paths remain distinct.
- Runtime trace bundles must be complete, verified, language-compatible, and
  source-matched. They prove the captured request only; playback success,
  audibility, and DSP response remain separate gaps.
- Unsupported codec/plugin media, absent historical/language chunks, decode
  failures, and mapping failures are reported independently.

Detailed changing investigations live under `reports/story/recovery/audio/`.
Page behavior and focused publication belong in
[`webui/audio.md`](../webui/audio.md).
