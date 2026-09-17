# `extend-data`: the path table and the bone matrices

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, catalog lane.** The `ExtendData` block: three files split by a single
entropy profile into two that decode completely and one that cannot be attacked at
the byte level at all. `StringPathHash.bin` is the game's complete source-path
table, so it is a global catalog rather than world data; `FacBoneTRS.bin` is
facial-bone animation. Neither is spatial.

## `extend-data`: two files are plain, two are opaque

A single entropy/adjacency profile separates them, calibrated against known-readable references
(plain JSON reads 5.111 bits/byte at +0.678; the decoded `regionIv` reads 6.301):

| file | bytes | entropy | adjacency | verdict |
| --- | --- | --- | --- | --- |
| `manifest.hgmmap` | 50,002,822 | **7.997** | +0.002 | ***indistinguishable from random*** |
| `CompressData.bin` | 873,686 | **7.994** | +0.016 | ***indistinguishable from random*** |
| `FacBoneTRS.bin` | 17,909,576 | 3.956 | +0.411 | plain |
| `StringPathHash.bin` | 157,726,628 | 4.022 | +0.379 | plain |

***`manifest.hgmmap` and `CompressData.bin` are encrypted or fully compressed and cannot be
parsed as they stand*** -- recorded so no one spends time on a byte-level attack.

### `FacBoneTRS.bin` is an array of 4x4 matrices

After a **14,216-byte head** of small integers, the rest is **279,615 records of 64 bytes**
(`17,895,360 / 64` exactly), and each is a row-major 4x4 affine transform:

| test | result |
| --- | --- |
| 4th column == `(0,0,0,1)` | **100.00%** |
| rows mutually orthogonal | 99.69% |
| uniform scale | 99.69% |
| **full TRS** | **99.69%** |
| *control at random offsets* | **2.495%** |

**A 40x separation from its control**, on the same acceptance test built for the chunk-data
transforms -- *so the tooling from one format carried straight over to another.* The name's
claim (facial bone TRS) is borne out by the contents rather than assumed from it.

## `StringPathHash.bin` is the game's complete source-path table

***157,726,628 bytes, decoded end to end with nothing left over.***

| offset | field |
| --- | --- |
| `+0` | u32 **19,234,928** -- offset of the string pool |
| `+4` | u32 **801,455** -- the string count |
| `+8 .. poolOffset` | index/hash table |
| `poolOffset .. EOF` | `801,455` x `[u32 byteLength][UTF-16LE bytes][u16 0x0000]` |

**Walking the pool fail-closed parses 801,455 of 801,455 strings and ends exactly on the last
byte, with 0 leftover** -- and the header's count was confirmed independently by scanning for
UTF-16 runs *before* the header was understood, which found the same 801,455.

***These are the real asset paths:*** 453,513 under `Data/`, 347,635 under `Assets/`/`assets/`;
by extension 253,670 `.ab`, 103,592 `.bytes`, 102,852 `.json`, 64,164 `.fbx`, 62,109 `.asset`,
30,856 `.png`, 29,959 `.mat`, 28,884 `.prefab`, 23,083 `.anim`.

```
Assets/Beyond/Arts/Entity/Actor/Loli/Wulfa/Materials/M_actor_wulfa_iris_01.mat
Assets/Beyond/Arts/Environment/SceneAssets/Map01/Prop/.../S_prop_map01_object+1_005_07a_lod0.fbx
Data/Streaming/PC/map01/Streaming/InitChunkData_4_14_0_0.bytes
Data/Bundles/Windows/main/4df843b7674ea0b7d4d078a2.ab
```

**This is the largest semantic anchor recovered here** -- *a name for essentially every asset the
game ships*, including the `.ab` bundle hashes and the chunk files this section has spent so long
on.

***A correction worth keeping.*** An earlier pass over this file searched for **8-bit ASCII**
runs, found only random-looking junk, and concluded it held no strings -- while 801,455 UTF-16
paths sat in it. **The byte-position census is what exposed it**: even positions varied, odd
positions ~90% zero, which is exactly how UTF-16LE ASCII looks. *The earlier finding that the
first words are "not hashes of VFS paths" stands, but the reason to doubt it was visible in the
zero pattern and was missed.*

### The index region: a 64-bit hash to path map

***Profiling the region in windows found the layout change the statistics had been hinting at.***
Up to byte **6,422,536** the words are ~37% zero and ~68% small with no high values; after it
they sit at **exactly 25.0% zero and 25.0% small** -- one word in four, which is the signature of
a **16-byte record**.

Read that way, the second part is **800,774 records** of:

| slot | content |
| --- | --- |
| 0 | **offset into the string pool** (max 138,491,050 against a pool of 138,491,700) |
| 1 | always zero -- padding, making slot 0 a u64 |
| 2, 3 | a **64-bit hash**, essentially all distinct |

***Every one of the 800,774 offsets lands exactly on a string record start -- 100.00%.***

```
0xcbb43c776a00a407 -> Data/Bundles/Windows/main/0054a391cac476902c17df24.ab
0xe77047c45d2ad392 -> Data/Terrain/PC/dung02_dg002/Terrain_2_1_1_H.bytes
0x08714e372c034651 -> Data/Json/LipSync/Chinese/au_dlg_c31m1_2_031.json
```

**So `StringPathHash.bin` is a complete 64-bit-hash to asset-path resolver for the whole game**,
and the name is exact.

#### The hash function itself is not identified, but it is constrained

***The resolver works by lookup; it cannot yet be computed.*** With 787,063 ground-truth
`(hash, path)` pairs available, the function was attacked directly and **32 combinations are now
eliminated**, all scoring **0 matches**:

| family | encodings | seeds |
| --- | --- | --- |
| `fnv1a-64`, `fnv1-64`, `djb2-64`, `sdbm-64` | utf-8, utf-8 lower, utf-16le, utf-16le lower | -- |
| **`xxHash64`**, **`Murmur64A`** | the same four | 0 and 1 |

`xxhash` and `mmh3` are not installed here, so **both were implemented from their published
definitions and checked against xxHash64's published test vectors first**
(in a since-deleted `scratch/hash64.py`; reimplement from the published definitions rather
than looking for that file)
(`""` seed 0 -> `0xef46db3751d8e999`, seed 1 -> `0xd5afba1336a3be4b`, both reproduced exactly).
*That check is what makes the negative meaningful: the algorithm is ruled out, not the
implementation.*

What the values do say:

* **bits 0-59 are uniform** -- each set in exactly 50% of hashes;
* **bits 60-63 are not** -- each set in only 28%;
* the **top nibble is `0x0` in 46.95%** of hashes while `0x1`-`0xF` take ~3.5% each, against
  6.25% for a uniform nibble;
* ***that skew tracks path length***, not asset type: the nibble-`0` share runs **28.76% for
  50-60 character paths and ~67% for paths over 80**, correlation **+0.316**. It looked like a
  type tag because `.fbx` paths (73%) are long and `.ab` paths (27%) are short -- **the
  extension correlation is a proxy for length.**

*A function whose top four bits stay clear more often as the input grows is a strong fingerprint*
and should identify it quickly once a wider hash library is available.

***The hash is non-linear, so differential recovery will not work.*** The pool contains many
paths differing in a single character, which for any polynomial or accumulate-style hash
(`h = h*M + c`) forces a *constant* difference for a fixed `(length, position, character delta)`.
Measured over 881 such groups: **796 vary and only 85 are constant, and every one of those 85 had
just a single observed pair** -- constant by having nothing to disagree with. **The same holds
for XOR.** *So the function ends in an avalanche finalizer*, which rules out the entire
linear-accumulate family structurally rather than one member at a time, and means the algorithm
must be identified by name rather than solved for.

**The remaining route is the engine binary** -- and a constant scan of it narrows nothing on its
own. Searching for the published 64-bit constants of seven hash families:

| binary | constants present |
| --- | --- |
| `UnityPlayer.dll` | **Murmur3 `fmix64` x58 each**, xxHash64 primes 1-5, CityHash k0-k2, FNV-1a64 |
| `GameAssembly.dll` | FNV-1a64 prime x70 / offset x62, xxHash64 primes |
| `HGP.dll` | xorshift64* x57, FNV-1a64 x10 |

***Presence is not use.*** These binaries carry several hash families at once, so the scan cannot
say which one writes this table -- *but the 58 `fmix64` pairs pointed at MurmurHash3_x64_128,
which is a different algorithm from the already-eliminated Murmur64A (MurmurHash2) and whose
`fmix64` finalizer matches the measured avalanche.* **It was implemented and tested: no match
across 4 encodings x 3 seeds x both 64-bit halves** (self-test: `murmur3_x64_128(b"", 0)` returns
`(0, 0)` as published).

**Seven families and 44 combinations are now eliminated**, every one with a verified
implementation. *Identifying the function needs the routine disassembled rather than more
candidates guessed*, which is a larger task than this section has needed so far and is recorded
as the next step rather than attempted here.

#### The resolver works on the chunk data

***`InitChunkData` carries these hashes, and they resolve.*** Over 25 large chunk files and
6,101,502 aligned u64 words:

| set | matches | rate |
| --- | --- | --- |
| **the real 787,063 hashes** | **179,537** | **2.9425%** |
| decoy: same set with the low bit flipped | 4 | 0.0001% |
| decoy: same set with bit 40 flipped | 0 | 0.0000% |

***The decoy control is what makes this safe to claim.*** A random-u64 control scores 0% here
too, but chunk data is not random -- it is adjacent float pairs -- so a decoy of **identical size
and magnitude** is the honest test, and it lands at 1 in 10,000 of the real rate.

Resolved, a chunk's hashes name its asset dependencies -- NavMesh chunks, HLOD meshes, character
`.fbx`, effect textures, terrain `.bytes`, `.ab` bundles. **A single hash repeats thousands of
times within one file** (4,487x for the top asset in one `_Global_` chunk), which is what
per-instance storage of a shared mesh reference looks like.

*This was nearly discarded.* The cross-level references and the heavy repetition looked like
false positives, and the reasoning "a `blackbox02` chunk would not reference `map02` assets"
was wrong on both counts -- **`_Global_` chunks reference shared assets, and repetition is
per-instance.** The decoy control settled it where intuition would have thrown away a true
result.

##### Where these hashes appear, and where they do not

| data | real hits | decoy |
| --- | --- | --- |
| **`InitChunkData`** | **2.94%** on large files, 1.02% on small | 0 |
| `StreamingChunkData` | **0** | 0 |
| `StreamingChunkInfo` | **0** | 0 |
| `LAYER_*`, `iv` payloads, `iv` index | **0** | 0 |
| `table` block | **0** | 0 |

***The hashes are specific to `InitChunkData`.*** Not terrain, not irradiance volumes, not the
config tables, and -- *the sharpest of these* -- **not `StreamingChunkData`**, which is the same
format family from the same directories. **So `Init` chunks declare asset dependencies and
`Streaming` chunks do not**, which is a semantic distinction between the two that the structural
work never surfaced: the pair have matching layouts and differ in what they carry.

### Region A: a second hash table, keyed by something else

Bytes 8 to 6,422,536 are **802,816 slots of 8 bytes** -- and `802,816 = 784 x 1024`, a capacity
rather than a count. **299,979 slots (37.37%) are entirely empty** and 502,837 are occupied,
which is a load factor around 0.63: *this is an open-addressing hash table.* The first word is
hash-like -- all distinct over a 100,000 sample, spanning the full u32 range -- and the second is
usually small (`1, 2, 3, 4 ...` in a decaying tail).

***What it is keyed by is not any of the obvious things.*** Each tested against a control:

| reading | result | control |
| --- | --- | --- |
| region B's 64-bit hash, low or high half | 0.03% / 0.10% | 0.016% |
| an offset landing on a string record | 1.37% | 0.57% |
| a string index (`<= 802,816`) | 0.14% | -- |
| `crc32` / `fnv1a-32` / `fnv1a-64` of the paths | 0.04-0.08% | 0.056% |
| **the 24-hex bundle id** from the 253,670 `.ab` paths, any 4-byte slice | **0.01-0.02%** | 0.013% |

***The slot layout is tighter than first recorded.*** At stride 8 from byte 8 the zero-fractions
are `[0.38, 0.38, 0.38, 0.84, 0.38, 1.00, 1.00, 1.00]`, so **the second field is effectively a
single byte**, not a u32 -- the 4.29-billion maximum quoted earlier came from a ~0.5% tail, not
the common case. *An apparent set of sub-region "shifts" was an artefact of profiling with a
window size that is not a multiple of 8*, which rotates the stride phase every window; region A
is uniform throughout.

**So the file holds *two* hash tables over the same string pool**: region B keys 800,774 paths by
a 64-bit hash and resolves at 100%, while region A keys ~502,837 entries by a 32-bit value that
is *not* derived from the path text by any function tried, *nor* related to region B's hash.
**It is plausibly keyed by something other than the path** -- a GUID, a bundle id, an object id
-- which would explain every negative above at once. ***Recorded as open; the resolver in region
B is the usable half.***
