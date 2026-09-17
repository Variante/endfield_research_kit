# The bank's sections outside HIRC

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, audio lane.** The container level of the audio lane: the bank sections
that are not the object graph. `STMG`, `ENVS` and `INIT` are framed byte-exact, and
`ENVS` reuses the same point record the curve type does.

## The bank has four sections nothing parsed, and STMG is one of them

Censusing the section tags was overdue. Across 20,873 bank payloads there are exactly
two tags everywhere -- `BKHD` (834,940 bytes) and `HIRC` (26,995,526) -- and **one
bank carries five more**: `DATA` 5,913,232, **`STMG` 10,118**, `INIT` 347, `ENVS` 216,
`PLAT` 8, `DIDX` 84. *A section census costs nothing and should have been the first
thing done to this format.*

### `STMG` IS CLOSED: 10,118 of 10,118 bytes, byte-exact

```
u16                      observed 0
f32                      observed -60.0
u16                      observed 256
u16                      observed 50
u32 count                309
count x 12-byte record:  u32 id, u16 value, 6 bytes (all zero)
```

- **One instance in the whole corpus, so closure is not available as evidence and
  none is claimed from it.** Two checks stand in, neither needing the section to
  close:
  - **Distinctness.** At stride 12 the 309 ids are **all different**. At every other
    stride from 8 to 20 they collapse to between **107 and 220**. A stride that is not
    the record width reads each id from a sliding mix of two fields, and those
    collide. 12 rivals scored, **0** give distinct ids.
  - **What follows.** At 12 the word after the run is **15** -- a small count opening a
    further block. Every other stride lands on zero or an arbitrary large value.
- The record value is **1000 in 306**, and 3500, 500 and 0 once each.

### `STMG`'s trailing run is framed BACKWARD, and its count is what locates it

```
u32 count                269
count x 21-byte record:  u32 id, f32, u8 selector, 3 zero bytes, f32, f32, u8
4 trailing bytes         all zero
```

- **It has to be backward.** The block between the two runs is variable-length and is
  not framed, so the trailing run's start cannot be computed forward.
- **The record shape bounds the run; the count locates it.** Walking back while the
  three zero bytes at `+9` hold reaches **270** records where the true count is **269**
  -- the bytes happen to be zero one record early. So the boundary is settled by the
  count instead: over every length from 1 to 480, **exactly one** has a preceding word
  equal to itself. *A shape test that overshoots by one is not a boundary; a count that
  agrees with the run length is.*
- **The shape is discriminated the same way the leading run's was.** All 269 ids are
  distinct and all 269 carry the zero bytes; **7 rival strides from 14 to 24 give
  neither** -- between 108 and 133 distinct ids and between 126 and 162 zero runs. All
  **807** floats across the three float fields are finite and bounded, taking values
  like 0, -96, 1, 0.1, 10, 50 and 16000. The selector at `+8` is 0 in 210, 2 in 47 and
  1 in 12.
### `STMG`'s middle block, and why being bounded on both sides was the whole thing

```
u32 count                15
count x entry:  u32, u32, u8 zero, u32 records, 3 zero bytes   (13 bytes)
                records x 12-byte record: 8 bytes, u8 = 9, 3 zero bytes
```

- I said last batch this block was blocked on having one sample. **That was wrong, and
  the mistake is worth naming: one STMG, but FIFTEEN entries inside the block.** The
  sample size for an entry shape is 15, not 1.
- **What made it framable was being bounded on both sides.** Once the leading and
  trailing runs were located, the middle had a known start and a known end, so any
  candidate shape had to consume it *byte-exactly in exactly 15 steps*. Searching every
  shape of the form "head with a u32 count inside, then n records, then a tail" --
  head 4..40, count offset 0..head-4, record 1..32, tail 0..16, about **745,000
  candidates** -- **exactly one** does.
- **The content agrees independently of the search.** All 15 entry ids are distinct,
  the head's bytes at `+8` and `+10..+12` are zero in every entry, and the marker byte
  at record `+8` is **9 in all 45 records** with `+9..+11` zero. *A shape found by
  exhaustion needs content that the exhaustion did not select for.*
- Record counts per entry: 3 in six entries, 5 in three, 0/2/4 in two each.
- **Framed: 10,118 of 10,118. Nothing left over.** From 3,722 (36.8%) two batches ago.
- Each of the three blocks was located by **different** evidence, because each had
  something different available: the leading run by a forward count with a stride
  discriminated against eleven rivals; the trailing run by a backward count, unique
  over every length from 1 to 480; the middle by exhaustion plus closure.

### `ENVS` is a run of curves over the SAME point record `0x0B` uses

```
(repeat until the section ends)
u8, u8, u8 count, u8
count x point:  f32 x, f32 y, u32 interpolation
```

- ENVS has **no count of its own** -- the run ends when the bytes do -- so byte-exact
  closure is what makes the walk a frame rather than a scan. **Three** shapes close it
  with every curve non-empty, and the content separated them:

  | shape | codes 0..9 | curves with rising x |
  | --- | --- | --- |
  | **head 4, count at `+2`, 12-byte point** | **16 of 16** | **6 of 6** |
  | head 12, count at `+2`, 18-byte record | 3 of 10 | 1 of 3 |

  *Closure found three candidates; content picked one.* The third ran off the end of
  the section, which is its own rejection.
- 6 curves, 16 points; codes 4 (x8), 0, 1, 2 (x2 each), 6 and 7. Same vocabulary as
  numeric type `0x0B`'s element runs.
- **This is the second record the format shares between two places**, after the
  14-byte source record that types `0x02` and `0x0B` share. The 12-byte
  `(x, y, interpolation)` point appears in `ENVS` curves and in `0x0B` element runs.

### Every non-HIRC section of the bank format is now framed

| tag | instances | bytes | framed |
| --- | --- | --- | --- |
| `BKHD` | 20,873 | 834,940 | version field |
| `HIRC` | 20,873 | 26,995,526 | 10 types closed, `0x0B` at 3,937/4,325 |
| `DIDX` | 1 | 84 | 7 x 12 media entries |
| `DATA` | 1 | 5,913,232 | addressed by `DIDX` |
| `STMG` | 1 | 10,118 | **10,118 byte-exact** |
| `INIT` | 1 | 347 | **347 byte-exact** |
| `ENVS` | 1 | 216 | **216 byte-exact** |
| `PLAT` | 1 | 8 | **`Windows`** |

### `INIT` is a plugin NAME table, and it names the plugins the records use

```
u32 count                22
count x entry:  u16 company, u16 plugin, NUL-terminated ASCII name
```

Closes byte-exactly on 347 bytes. A wrong field order would not land on the section
end, which is the whole check for a section that appears once.

- **The plugin id word at the front of the 14-byte source record decomposes as
  `(plugin << 16) | company`**, and every company-2 value the corpus carries is named
  here: `0x00640002` **AkSineTone**, `0x00650002` **AkSilenceGenerator**, `0x00940002`
  **AkSynthOne**, `0x01990002` **AkMotion**. **973 of 147,262** source records name a
  plugin the game itself names.
- **Everything unnamed is company 1** -- `0x00040001` (132,056), `0x00140001` (12,512),
  `0x00080001` (1,721). INIT lists plugin DLLs; company 1 is the built-in codec set,
  which the engine does not need named. The gate requires the absences to be company 1
  *exactly*, because a company-2 id missing would mean the decomposition is wrong.
- `PLAT` is a single NUL-terminated platform name: **`Windows`**.
