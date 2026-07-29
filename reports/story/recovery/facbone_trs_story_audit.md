# FacBoneTRS Story audit

- classification: **factory_animation_transform_only**
- mission-graph action: **none**
- source: `tmp/story/facbone_trs/Data/ExtendData/Main/FacBone/FacBoneTRS.bin`
- SHA-256: `d0882963c6a90c9f19ef41eb5f0983b83b925b075e7ea7d1f2ffc9ef2640c5a4`
- bytes: 17,909,576

## Current ExtendData inventory

- VFS index: `tmp/story/extend_data_inventory/current.json`
- blocks / chunks / files: 2 / 2 / 4

- `Data/ExtendData/Initial/InitStringPathHash.bin`: 305,796 bytes (`InitialExtendData`)
- `Data/ExtendData/Main/CompressData.bin`: 789,844 bytes (`ExtendData`)
- `Data/ExtendData/Main/FacBone/FacBoneTRS.bin`: 17,909,576 bytes (`ExtendData`)
- `Data/ExtendData/Main/StringPathHash.bin`: 118,687,426 bytes (`ExtendData`)

## Validated layout

- unit hash table: 84 buckets / 84 guid entries / 2,020 bytes
- bone table: 762 records from 2,024 to 14,216
- matrix table: 279,615 64-byte matrices from 14,216 to 17,909,576
- frame-count range per bone: 2 to 1,102
- non-finite matrix floats: 0
- duplicate bone hashes within a unit: 6

Every unit, bone, and matrix range forms a gap-free, non-overlapping partition and the final matrix ends exactly at EOF.

## Native reader

- `Beyond.Gameplay.Factory.FacBoneTRSBinary.InitMain` (`0x060004c5`, `0x18449b330`): memory-maps FacBoneTRS.bin, retains its base pointer, and initializes the unit lookup table
- `Beyond.Gameplay.Factory.FacBoneTRSBinary._InitTable` (`0x060004c6`, `0x18449bb30`): initializes the unit hash table from file base + 4
- `Beyond.Gameplay.Factory.FacBoneTRSBinary.TryGetBoneTRS` (`0x060004c7`, `0x1869bf644`): looks up signed guid, scans 16-byte bone entries for a 64-bit bone hash, bounds-checks frame, and copies one 64-byte matrix
- `Beyond.Gameplay.Factory.STATICVATDATA.GetBoneTRS` (`0x060069bd`, `0x1874e4ae0`): gets the entity's current VAT frame, hashes boneName with StringHash64, and calls TryGetBoneTRS

## Story relevance

- exact encoded target hits: 0

The complete file is an exact guid -> bone hash -> frame -> 64-byte matrix lookup. The native caller supplies an entity VAT frame and hashed bone name; the schema has no Story key, mission, quest, LevelScript, phase, or playback-owner field. No unresolved Story root occurs in ASCII or UTF-16LE form.

This closes the hash-gated current FacBoneTRS.bin as a Story carrier. It does not classify runtime/server state, future ExtendData files, or arbitrary semantic meaning assigned to numeric guids outside this reader path.
