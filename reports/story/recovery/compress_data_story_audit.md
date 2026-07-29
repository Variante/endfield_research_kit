# CompressData Story audit

- Container records: **290**
- Decompressed logical bytes: **15,960,452**
- Logical type: `NodeCanvas.BehaviourTrees.BehaviourTree`
- Typed serialized BehaviourTrees: **570** (569 compressed / 1 inline)
- Pool index join: **290/290**, 0 missing, 269 shared by multiple assets
- Logical Story/owner hits: **0**
- Exact actionable gap-name hits on carrier assets: **0**
- Finding: `complete_ai_behaviour_tree_pool_no_story_or_owner_carrier`

## Validated layout

- Header: `recordCount:uint32 + absoluteOffsets:uint32[recordCount]`
- Record: `compressedLength:uint32 + originalLength:uint32 + brotliPayload[compressedLength]`
- Logical encoding: `UTF-16LE JSON`

## Logical class namespaces

| Namespace | Occurrences |
|---|---:|
| `NodeCanvas.BehaviourTrees` | 28,679 |
| `Beyond.Gameplay.AI` | 12,606 |
| `NodeCanvas.Framework` | 2,114 |
| `NodeCanvas.Tasks.Actions` | 1,281 |
| `NodeCanvas.Tasks.Conditions` | 947 |
| `System` | 734 |
| `NodeCanvas.Framework.Variable`1[[System.Single, mscorlib, Version=4.0.0` | 704 |
| `NodeCanvas.Framework.Variable`1[[Beyond.Gameplay.AI.AIEntity, Gameplay.Beyond, Version=0.0.0` | 426 |
| `NodeCanvas.Framework.Variable`1[[System.Int32, mscorlib, Version=4.0.0` | 248 |
| `NodeCanvas.Framework.Variable`1[[Beyond.Gameplay.AI.Config.EnemyAISkillData, Gameplay.Beyond, Version=0.0.0` | 207 |

## Evidence boundary

Complete offset/length validation, successful Brotli decode, exact original-length match, UTF-16LE JSON parse, typed logical BehaviourTree identity, and exact serialized-object join through _enableGraphStringCompress/_serializedGraphStringIndex.

CompressData.bin is the compressed JSON pool for AI NodeCanvas BehaviourTree assets. It is not a Story selector or mission-owner registry on the reviewed build.

This does not classify other ExtendData files, future builds, runtime-added compressed records, server state, or indirect selectors outside this exact current pool.
