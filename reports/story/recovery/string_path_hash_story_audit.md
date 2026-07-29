# StringPathHash Story audit

- classification: **resource_availability_only**
- mission-graph action: **none**
- selected Story roots: 3
- registered resource paths: 34
- exact consumer hits: 0

## Validated format

### `main` registry

- source: `tmp/story/root_selector_string_path_hash/Data/ExtendData/Main/StringPathHash.bin`
- SHA-256: `680140a7c4d2167fe5bb29e04f352334b664bcb69d6f73c067df10efd12bfa96`
- entries / strings: 538,806
- bucket table: 4,310,448 bytes
- entry table: 8,620,896 bytes as `hash:int64 + stringPoolOffset:uint64`
- string pool: `byteLength:uint32 + UTF-16LE bytes + null:uint16`

### `initial` registry

- source: `tmp/story/root_selector_string_path_hash/Data/ExtendData/Initial/InitStringPathHash.bin`
- SHA-256: `ea083af2b707bf30cf256bc44892af9d90458b5589d944b0be0abc51428dbc17`
- entries / strings: 1,659
- bucket table: 13,272 bytes
- entry table: 26,544 bytes as `hash:int64 + stringPoolOffset:uint64`
- string pool: `byteLength:uint32 + UTF-16LE bytes + null:uint16`

Native metadata identifies `StringPathHash` as an eight-byte hash value and `StringPathHashBinary` as the owner of the main/init mapping dictionaries. Its public lookup direction is hash to original path.

## Selected roots

### `cutscene_e11m2_liexi_xs_m_01_last_01`

- `main` `0x0aa84f7045c3b530` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_01/Prefab/cutscene_e11m2_liexi_xs_m_01_last_01_Actor.prefab`
- `main` `0x0a8ff4acee5277b3` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_01/Playable/cutscene_e11m2_liexi_xs_m_01_last_01_Light.playable`
- `main` `0x05323d5aa9d35b33` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_01/Prefab/cutscene_e11m2_liexi_xs_m_01_last_01_Light.prefab`
- `main` `0x09af93fa220dd1c6` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_01/Playable/cutscene_e11m2_liexi_xs_m_01_last_01.playable`
- `main` `0x0af55f9cc3bfb83e` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_01/Prefab/cutscene_e11m2_liexi_xs_m_01_last_01_Effect.prefab`
- `main` `0x0b8be19424a1f344` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_01/Playable/cutscene_e11m2_liexi_xs_m_01_last_01_Others.playable`
- `main` `0x07bcdf3776202626` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_01/Prefab/cutscene_e11m2_liexi_xs_m_01_last_01.prefab`
- `main` `0x089735a767dcba54` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_01/Prefab/cutscene_e11m2_liexi_xs_m_01_last_01_Others.prefab`
- `main` `0x0a41605781d32c97` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_01/Prefab/cutscene_e11m2_liexi_xs_m_01_last_01_Audio.prefab`
- `main` `0x0039d94b933052d0` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_01/Playable/cutscene_e11m2_liexi_xs_m_01_last_01_Actor.playable`
- `main` `0x0e14c548061ae4a9` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_01/cutscene_e11m2_liexi_xs_m_01_last_01.json`
- `main` `0x044e181ef97979ce` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_01/Playable/cutscene_e11m2_liexi_xs_m_01_last_01_Effect.playable`
- `main` `0x02be8bbe2ea1b717` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_01/Playable/cutscene_e11m2_liexi_xs_m_01_last_01_Audio.playable`

### `cutscene_f1m9d3_1`

- `main` `0x077d84a098e06f2c` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_f1m9d3_1/Playable/cutscene_f1m9d3_1_Effect.playable`
- `main` `0x0e631581223a9ff7` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_f1m9d3_1/Playable/cutscene_f1m9d3_1_Light.playable`
- `main` `0x0e56808fb8f281a9` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_f1m9d3_1/cutscene_f1m9d3_1.json`
- `main` `0x00d4e954ae7ed803` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_f1m9d3_1/Playable/cutscene_f1m9d3_1_Audio.playable`
- `main` `0x095890dccafd4684` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_f1m9d3_1/Playable/cutscene_f1m9d3_1.playable`
- `main` `0x03c32e50312f50fa` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_f1m9d3_1/Playable/cutscene_f1m9d3_1_Actor.playable`
- `main` `0x0862273d596ff0a1` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_f1m9d3_1/Prefab/cutscene_f1m9d3_1_Actor_showOld.prefab`
- `main` `0x007dda5b332de536` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_f1m9d3_1/Playable/cutscene_f1m9d3_1_Others.playable`

### `cutscene_e11m2_liexi_xs_m_01_last_02`

- `main` `0x0a4f110056e076f3` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_02/Prefab/cutscene_e11m2_liexi_xs_m_01_last_02_Light.prefab`
- `main` `0x01ae97670c577666` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_02/Prefab/cutscene_e11m2_liexi_xs_m_01_last_02.prefab`
- `main` `0x075e33d9a80e9626` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_02/Playable/cutscene_e11m2_liexi_xs_m_01_last_02.playable`
- `main` `0x02a83cc489e5c8b9` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_02/cutscene_e11m2_liexi_xs_m_01_last_02.json`
- `main` `0x0802d7fb4af4cd14` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_02/Prefab/cutscene_e11m2_liexi_xs_m_01_last_02_Others.prefab`
- `main` `0x07d39461ec3630ae` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_02/Playable/cutscene_e11m2_liexi_xs_m_01_last_02_Effect.playable`
- `main` `0x0e7a06c9f7a12d70` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_02/Playable/cutscene_e11m2_liexi_xs_m_01_last_02_Actor.playable`
- `main` `0x0691886a471764f0` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_02/Prefab/cutscene_e11m2_liexi_xs_m_01_last_02_Actor.prefab`
- `main` `0x0d8499b18d272afe` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_02/Prefab/cutscene_e11m2_liexi_xs_m_01_last_02_Effect.prefab`
- `main` `0x062c2609d3941c57` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_02/Prefab/cutscene_e11m2_liexi_xs_m_01_last_02_Audio.prefab`
- `main` `0x095c556f35664153` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_02/Playable/cutscene_e11m2_liexi_xs_m_01_last_02_Light.playable`
- `main` `0x00feb93c931291b7` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_02/Playable/cutscene_e11m2_liexi_xs_m_01_last_02_Audio.playable`
- `main` `0x01d1bec7c10b48a4` -> `Assets/Beyond/DynamicAssets/Gameplay/CutsceneTransition/cutscene_e11m2_liexi_xs_m_01_last_02/Playable/cutscene_e11m2_liexi_xs_m_01_last_02_Others.playable`

## Exact-consumer census

- structured export: 91,231 files / 7,241,491,260 bytes; 0 hits
- AnimeStudio object indexes: 1,337,486 rows; 0 hits
- adjacent supplied binaries: 1 files / 789,844 bytes; 0 hits
- current native binaries: 1 files / 280,436,712 bytes; 0 hits

Both little- and big-endian 64-bit byte forms were searched in binary sources; signed, unsigned, and hexadecimal text forms were searched in the object indexes.

## Conclusion

The validated binary is a hash-to-resource-path diagnostic dictionary. The selected paths are registered, but no exact 64-bit hash consumer occurs in the scanned structured data, AnimeStudio object indexes, supplied adjacent binaries, or current native binaries.

Registration in StringPathHash.bin proves that a resource can be resolved by its opaque hash. It does not identify who requests that resource, when it plays, or which mission/quest owns it. A dynamically computed hash, a runtime-only/server selector, or an unscanned encoded source remains outside this exact-consumer census.
