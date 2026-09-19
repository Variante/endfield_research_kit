# The `CABMap` container index

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 1, container lane.** The index that maps a Unity CAB to its container,
read from the bytes. It sits below every asset question: without it a PathID
has no source root, and a source root is half of Unity object identity.

## CABMap container index

- **AnimeStudio's `Maps/*.bin` are CABMaps, not asset maps, and the format is now
  read byte-exact.** The framing comes from the writer itself --
  `AssetsHelper.DumpCABMap` in the submodule -- not from guessing at bytes: a
  .NET `BinaryWriter` stream of `string BaseFolder`, `int32 count`, then per entry
  a CAB name, a path, an `int64` offset, an `int32` dependency count and that many
  CAB names, with .NET's 7-bit encoded string length prefixes.
- Both current maps consume exactly to EOF: `endfield_persistent_assets.bin`
  (1,946 entries, 2,571,560 bytes) and `endfield_streamingassets_assets.bin`
  (254,723 entries, 47,318,490 bytes). Every CAB name is unique inside its file,
  which is what makes each map a map.
- **The dependency graph closes across the two maps, not within either.** Of
  661,808 edges only **3** name a CAB that appears nowhere. The persistent map is
  the reason to resolve across maps rather than within one: 10,025 of its distinct
  targets live in the streaming map and only 570 in its own, so a per-map check
  would report it as 95% dangling. 1,939 of its 1,946 CAB names also appear in the
  streaming map.
- **The CABMap offset is a physical byte offset into the `.chk`, and it lands
  inside a VFS logical file.** Joined against the VFS understanding ledger: all
  1,946 persistent entries land inside a ledger span, and 252,783 of 254,723
  streaming entries do. Two independently produced indexes -- AnimeStudio walking
  containers, the VFS audit walking blocks -- agree on where things are.
- **A coverage "hole" I reported here was my own bug. Retracted.** I compared
  *chunk filenames* and concluded the ledger never enumerated
  `VFS/0CE8FA57/4B06191A...chk` (222 MB, 1,053 containers). It does cover that
  content. Block `0CE8FA57` ships a **different chunk file in each VFS root** --
  `4B06191A...chk` under StreamingAssets, `F047E09F...chk` under Persistent -- and
  the ledger resolves each block from the **primary** root while the CABMap, built
  against StreamingAssets, names the fallback file. Both hold 1,053 containers.
  Same block, same count, different filename.
- Resolved by **block**, every block either map references is enumerated: nothing
  is missing in either direction. The check now keys on the block directory, and a
  test pins that so the filename comparison cannot come back.
- Two things worth carrying from the mistake. The repo already records that this
  VFS has two roots and that scans keyed on one silently mis-handle the other --
  **I hit the exact failure the notes warn about**, because I keyed a join on the
  most obvious identifier rather than the one the data is organised by. And I
  escalated it as a foundational problem before checking the sibling root, which
  is one `ls` away. **Check the cheap explanation before reporting a deep one.**
- **Every CAB is named by the logical bundle it sits in, and the relation is
  one to one.** Joining CABMap offsets to the ledger's logical-file spans names
  254,729 of 256,669 CABs, across 254,728 distinct bundles, of which **254,727
  hold exactly one CAB** and one holds two. The remainder split into 1,053 whose
  chunk is enumerated from the other VFS root and 887 whose offset falls inside no
  span; those two are counted separately because they are different situations.
- **Coverage and offsets need different join keys, and sharing one corrupts both.**
  Coverage keys on the *block*, because a block ships a different chunk file per
  root. Offsets key on the *chunk file*, because one block (`7064D8E2`) holds more
  than forty of them and merging their offset spaces invents matches. Keyed on the
  block, the join reported 256,601 names and "42 CABs in one bundle" -- a better
  looking number and a fabricated structure. The gate bounds both the one-to-one
  shape and the per-file maximum, since either bound alone passes a case it should
  not.
- **The CAB dependency graph is acyclic.** 254,732 nodes, 600,272 distinct edges,
  **zero back edges**, measured with an iterative walk rather than assumed.
  160,839 nodes have nothing depending on them and 141,896 depend on nothing. That
  a load order *exists* follows from this; which order the game actually uses does
  not, and is not claimed.
- 661,808 raw dependency entries reduce to 600,272 distinct edges, so **61,536
  entries repeat a dependency the same CAB already lists**. Both numbers are
  published: quoting only the distinct count misstates the file, quoting only the
  raw count misstates the graph. This is also why an earlier note said "661,808
  edges" -- that was the entry count, not the edge count.
- **Every CAB is accounted for, with exactly one documented exception.** 887 CAB
  *occurrences* sit at an offset the ledger does not enumerate; 886 of them are the
  same CAB *name* covered at its other occurrence, because a CAB appears once per
  VFS root and the ledger enumerates each block from one root only. One name is
  covered nowhere: `CAB-5dd5c779c787d592fb5184669bce5df9`, and it lives in
  `5B4A9EC7...chk` -- the chunk named by the ledger's single `shadowed_fallback`
  row. So the exception is a recorded shadowing decision, not a gap.
- **Judge coverage per CAB name, never per occurrence.** Per occurrence the same
  data reports 887 uncovered containers sitting in 865 unenumerated gaps, which
  reads like a large hole and is an artifact of the two roots. That is the third
  time in this domain that the two-root layout turned a correct measurement into a
  wrong conclusion; the other two were chunk-vs-block coverage and the CABMap
  offset join.
- Read by `scripts/webui/assets/cabmap.py`; report at
  [`reports/assets/cabmap_current_latest.json`](../../reports/assets/cabmap_current_latest.json).
  This is a container index only -- it says nothing about the objects inside a CAB,
  their types, names or path ids, and an offset is not a readable object without
  the container format that sits at it.
- Note for anyone wanting a texture or asset inventory: this map does **not**
  provide one. That needs an AnimeStudio export; the `.bin` maps only locate
  containers.
