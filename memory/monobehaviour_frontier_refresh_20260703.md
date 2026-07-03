# MonoBehaviour frontier refresh - 2026-07-03

## Scope

Rebuilt a fresh MonoBehaviour decoded index from the current `export_full`
AnimeStudio JSON output instead of relying on stale `webui/data/decoded`.

Command:

```bat
python scripts\build_decoded_index.py --export-root export_full --sources StreamingAssets Persistent --types MonoBehaviour --output tmp\decoded_index_mono_refreshed_20260703 --jobs 8
```

The first Codex shell wrapper timed out after 15 minutes, but the detached
Python process completed shortly after. No overlapping scan was started.

Then regenerated the frontier report from the fresh temp index:

```bat
python scripts\build_monobehaviour_frontier_report.py --index tmp\decoded_index_mono_refreshed_20260703\index.json --json reports\monobehaviour_frontier_latest.json --md reports\monobehaviour_frontier_latest.md
```

## Result

Fresh decoded index:

- files: `1,064,294`
- decoded: `1,063,560`
- partial: `734`
- unparsed: `0`
- groups: `1,478`

Fresh frontier:

- residual files: `734`
- residual groups: `21`

This supersedes the stale `webui/data/decoded/index.json` frontier that reported
`3,644` residual files across `148` groups. In particular, the old top groups
for `CombineCondition`, `fields-m_Navigation`, and many guide actions are no
longer current blockers in the refreshed scan.

## Current Top Residual Groups

| group | residual |
| --- | ---: |
| `MonoBehaviour/StreamingAssets/camera/cinematic/class_ProjectileTemplateData` | 300 |
| `MonoBehaviour/StreamingAssets/camera/cinematic/class_AbilityEntityTemplateData` | 161 |
| `MonoBehaviour/Persistent/gameplay/ability/class_EnemyTemplateData` | 78 |
| `MonoBehaviour/StreamingAssets/gameplay/ability/class_EnemyTemplateData` | 78 |
| `MonoBehaviour/StreamingAssets/managed-reference/class_LineFollower` | 48 |
| `MonoBehaviour/StreamingAssets/gameplay/ability/class_CharacterTemplateData` | 28 |
| `MonoBehaviour/Persistent/camera/cinematic/class_ProjectileTemplateData` | 10 |

## Interpretation

The current highest-value decoder frontier is the gameplay template family:

- `ProjectileTemplateData`
- `AbilityEntityTemplateData`
- `EnemyTemplateData`
- `CharacterTemplateData`

Those groups share nested `AbilitySystemData`, `SkillDataBundle`,
`EffectActionCfg`, movement, model, and template component tails. The repeated
partial marker is no longer broad unparsed guide data; it is concentrated in
known template/tail structures.

The stale WebUI decoded index should not be used as the authoritative recovery
ranking until rebuilt or replaced by a current temp index.
